from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def create_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now,
                       "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
                       "type": "access"}, settings.SECRET_KEY, algorithm="HS256")


def token_subject(token: str) -> UUID:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"],
                         options={"require_exp": True, "require_sub": True})
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return UUID(payload["sub"])
