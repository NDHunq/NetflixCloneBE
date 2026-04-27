from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.config import Config
from app.db.database import Base, SessionLocal, engine
from app.models.user import create_user, get_user_by_phone
from app.models.sso_identity import SSOIdentity  # noqa: F401 - register model metadata


app = FastAPI(title=Config.APP_NAME, version=Config.APP_VERSION)
import logging

# Cấu hình logging cơ bản để hiển thị logger.info ra terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        user = get_user_by_phone(db, "0901234567")
        if not user:
            create_user(
                db=db,
                phone_number="0901234567",
                full_name="Nguyen Van A",
                password="Password1",
            )
            print("Default user created: 0901234567 / Password1")
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "netflix-clone-backend-fastapi"}


app.include_router(auth_router)
