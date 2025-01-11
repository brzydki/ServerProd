from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from pydantic import BaseModel

app = FastAPI()


keys_db = {}

class KeyInfo(BaseModel):
    key: str
    expires_at: datetime
    ip: str = None
    hwid: str = None
    active: bool = True

@app.post("/check_key")
def check_key(key: str, ip: str, hwid: str):
    if key not in keys_db:
        raise HTTPException(status_code=404, detail="Invalid key")

    key_info = keys_db[key]
    if not key_info.active:
        raise HTTPException(status_code=403, detail="Key is deactivated")
    if datetime.utcnow() > key_info.expires_at:
        raise HTTPException(status_code=403, detail="Key has expired")
    if key_info.ip and key_info.ip != ip:
        raise HTTPException(status_code=403, detail="IP mismatch")
    if key_info.hwid and key_info.hwid != hwid:
        raise HTTPException(status_code=403, detail="HWID mismatch")

    return {"status": "ok"}


@app.post("/activate_key")
def activate_key(key: str, ip: str, hwid: str):
    if key not in keys_db:
        raise HTTPException(status_code=404, detail="Invalid key")

    key_info = keys_db[key]
    if not key_info.active:
        raise HTTPException(status_code=403, detail="Key is deactivated")


    if key_info.ip is None:
        key_info.ip = ip
    if key_info.hwid is None:
        key_info.hwid = hwid

    return {"status": "activated"}


@app.post("/create_key")
def create_key(key: str, duration_days: int):
    expires_at = datetime.utcnow() + timedelta(days=duration_days)
    keys_db[key] = KeyInfo(key=key, expires_at=expires_at)
    return {"status": "key_created", "expires_at": expires_at}
