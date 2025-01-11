from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import sqlite3

app = FastAPI()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("keys.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        hwid TEXT,
        expiry_date TEXT,
        active INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

# Функция проверки ключа
@app.post("/validate_key/")
def validate_key(key: str, hwid: Optional[str] = None):
    conn = sqlite3.connect("keys.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM keys WHERE key = ?", (key,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Key not found")

    stored_hwid, expiry_date, active = row[2], row[3], row[4]
    if not active:
        raise HTTPException(status_code=403, detail="Key is deactivated")
    if expiry_date and datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S") < datetime.now():
        raise HTTPException(status_code=403, detail="Key has expired")

    # Привязка HWID при первой активации
    if not stored_hwid:
        cursor.execute("UPDATE keys SET hwid = ? WHERE key = ?", (hwid, key))
        conn.commit()
    elif stored_hwid != hwid:
        raise HTTPException(status_code=403, detail="HWID mismatch")

    conn.close()
    return {"message": "Key is valid"}

# Добавление нового ключа
@app.post("/add_key/")
def add_key(key: str, expiry_days: int):
    expiry_date = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("keys.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO keys (key, hwid, expiry_date, active) VALUES (?, ?, ?, ?)",
                       (key, None, expiry_date, 1))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Key already exists")
    conn.close()
    return {"message": "Key added successfully"}

# Деактивация ключа
@app.post("/deactivate_key/")
def deactivate_key(key: str):
    conn = sqlite3.connect("keys.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE keys SET active = 0 WHERE key = ?", (key,))
    conn.commit()
    conn.close()
    return {"message": "Key deactivated"}
