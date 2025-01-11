from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid  # Для генерации уникальных ключей

DATABASE_URL = "postgresql://postgres:TsgOlDKGQPHBfjJjjwZkyGrUYpbvZdlX@postgres.railway.internal:5432/railway"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# Модель таблицы LicenseKey
class LicenseKey(Base):
    __tablename__ = "license_keys"
    key = Column(String, primary_key=True, index=True)
    hwid = Column(String, nullable=True)  # HWID привязывается после активации
    expiration_date = Column(String, nullable=False)  # Дата окончания действия
    active = Column(Boolean, default=True)  # Статус ключа

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

# Функция получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Активация ключа
@app.post("/activate")
def activate_key(request: dict, db=Depends(get_db)):
    key = request.get("key")
    hwid = request.get("hwid")

    if not key or not hwid:
        raise HTTPException(status_code=400, detail="Missing 'key' or 'hwid' in request body")

    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    
    # Если ключ не найден, возвращаем ошибку
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    
    # Если ключ деактивирован, возвращаем ошибку
    if not license_key.active:
        raise HTTPException(status_code=403, detail="Key is deactivated")
    
    # Если ключ истек, возвращаем ошибку
    if license_key.expiration_date < datetime.now().strftime("%Y-%m-%d"):
        raise HTTPException(status_code=403, detail="Key is expired")
    
    # Если HWID уже привязан, проверяем, совпадает ли он с текущим HWID
    if license_key.hwid and license_key.hwid != hwid:
        raise HTTPException(status_code=403, detail="Key is already bound to another HWID")
    
    # Если HWID ещё не привязан, привязываем его
    if not license_key.hwid:
        license_key.hwid = hwid
        db.commit()

    return {"message": "Key activated successfully"}

@app.get("/validate")
def validate_key(key: str, hwid: str, db=Depends(get_db)):
    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    if not license_key.active:
        raise HTTPException(status_code=403, detail="Key is deactivated")
    if license_key.expiration_date < datetime.now().strftime("%Y-%m-%d"):
        raise HTTPException(status_code=403, detail="Key is expired")
    if license_key.hwid != hwid:
        raise HTTPException(status_code=403, detail="HWID mismatch")
    return {"message": "Key is valid"}

@app.post("/generate")
def generate_key(expiration_days: int, db=Depends(get_db)):
    """
    Генерация нового ключа.
    :param expiration_days: Срок действия ключа в днях.
    """
    new_key = str(uuid.uuid4())  # Генерация уникального ключа
    expiration_date = (datetime.now() + timedelta(days=expiration_days)).strftime("%Y-%m-%d")
    license_key = LicenseKey(key=new_key, expiration_date=expiration_date, active=True)
    db.add(license_key)
    db.commit()
    return {"message": "Key generated successfully", "key": new_key, "expiration_date": expiration_date}
