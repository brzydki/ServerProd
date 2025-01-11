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
def activate_key(key: str, hwid: str, db=Depends(get_db)):
    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    if not license_key.active:
        raise HTTPException(status_code=403, detail="Key is deactivated")
    if license_key.expiration_date < datetime.now().strftime("%Y-%m-%d"):
        raise HTTPException(status_code=403, detail="Key is expired")
    if license_key.hwid and license_key.hwid != hwid:
        raise HTTPException(status_code=403, detail="Key is already bound to another HWID")

    license_key.hwid = hwid
    db.commit()
    return {"message": "Key activated successfully"}

# Валидация ключа
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

# Деактивация ключа
@app.post("/deactivate")
def deactivate_key(key: str, db=Depends(get_db)):
    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    license_key.active = False
    db.commit()
    return {"message": "Key deactivated successfully"}

# Генерация нового ключа
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

# Продление срока действия ключа
@app.post("/extend")
def extend_key(key: str, additional_days: int, db=Depends(get_db)):
    """
    Продление срока действия существующего ключа.
    :param key: Ключ для продления.
    :param additional_days: Количество дополнительных дней.
    """
    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    current_expiration_date = datetime.strptime(license_key.expiration_date, "%Y-%m-%d")
    new_expiration_date = current_expiration_date + timedelta(days=additional_days)
    license_key.expiration_date = new_expiration_date.strftime("%Y-%m-%d")
    db.commit()
    return {"message": "Key expiration extended", "new_expiration_date": license_key.expiration_date}

# Реактивация ключа
@app.post("/reactivate")
def reactivate_key(key: str, db=Depends(get_db)):
    """
    Реактивация ключа, если он был деактивирован.
    :param key: Ключ для активации.
    """
    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    license_key.active = True
    db.commit()
    return {"message": "Key reactivated successfully"}
