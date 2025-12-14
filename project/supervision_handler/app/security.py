import time
import jwt
from functools import wraps
from flask import request, jsonify
from .config import JWT_SECRET, JWT_ISSUER, JWT_EXPIRES_MIN

def create_token(sub: str) -> str:
    now = int(time.time())
    payload = {
        "iss": JWT_ISSUER,
        "sub": sub,
        "iat": now,
        "exp": now + JWT_EXPIRES_MIN * 60,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"], issuer=JWT_ISSUER)

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing_bearer_token"}), 401
        token = auth.split(" ", 1)[1].strip()
        try:
            request.jwt = decode_token(token)
        except Exception as e:
            return jsonify({"error": "invalid_token", "detail": str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper
