import os
from datetime import timedelta


class Config:
    APP_NAME = "netflix-clone-backend-fastapi"
    APP_VERSION = "1.0.0"

    DATABASE_URL = "sqlite:///./netflix_clone.db"

    JWT_SECRET_KEY = "netflix-clone-secret-key-2026"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    SUPER_APP_BE_URL = os.getenv("SUPER_APP_BE_URL", "http://127.0.0.1:8000")

    SERVICE_APP_CLIENT_ID = "serviceapp.demo"
    SERVICE_APP_REDIRECT_URI = "netflixclone://callback"
