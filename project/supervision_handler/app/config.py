import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "plc"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "root"),
}

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "plc-mes-api")
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "120"))

API_USER = os.getenv("API_USER", "admin")
API_PASSWORD = os.getenv("API_PASSWORD", "admin123")

LIVE_POLL_MS = int(os.getenv("LIVE_POLL_MS", "500"))
