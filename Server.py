from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

DATABASE_URL = "postgresql://postgres:TsgOlDKGQPHBfjJjjwZkyGrUYpbvZdlX@postgres.railway.internal:5432/railway"

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

class LicenseKey(Base):
    __tablename__ = "license_keys"
    key = Column(String, primary_key=True, index=True)
    hwid = Column(String, nullable=True)  # HWID привязывается после активации
    expiration_date = Column(String, nullable=False)  # Дата окончания действия
    active = Column(Boolean, default=True)  # Статус ключа

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

@app.post("/deactivate")
def deactivate_key(key: str, db=Depends(get_db)):
    license_key = db.query(LicenseKey).filter(LicenseKey.key == key).first()
    if not license_key:
        raise HTTPException(status_code=404, detail="Key not found")
    license_key.active = False
    db.commit()
    return {"message": "Key deactivated successfully"}
