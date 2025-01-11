from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import uuid

app = FastAPI()

# Хранилище ключей (замените на базу данных)
keys_db = {}


# Генерация нового ключа
@app.post("/generate_key")
def generate_key(hwid: str, days_valid: int):
    key = str(uuid.uuid4())
    expiry_date = datetime.utcnow() + timedelta(days=days_valid)
    keys_db[key] = {"hwid": hwid, "expiry_date": expiry_date, "active": True}
    return {"key": key, "expiry_date": expiry_date}


# Проверка ключа
@app.post("/verify_key")
def verify_key(key: str, hwid: str):
    if key not in keys_db:
        raise HTTPException(status_code=404, detail="Key not found")

    key_data = keys_db[key]
    if not key_data["active"]:
        raise HTTPException(status_code=403, detail="Key is deactivated")

    if key_data["hwid"] != hwid:
        raise HTTPException(status_code=403, detail="HWID mismatch")

    if datetime.utcnow() > key_data["expiry_date"]:
        raise HTTPException(status_code=403, detail="Key expired")

    return {"status": "Key valid"}


# Деактивация ключа
@app.post("/deactivate_key")
def deactivate_key(key: str):
    if key not in keys_db:
        raise HTTPException(status_code=404, detail="Key not found")
    keys_db[key]["active"] = False
    return {"status": "Key deactivated"}
