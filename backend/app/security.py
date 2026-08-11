from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from .config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

# Role constants shared across the API layer
ROLE_ADMIN = "Administrator"
ROLE_EXECUTIVE = "Executive"
ROLE_FINANCE = "Finance Officer"
ROLE_HR = "HR Officer"
ROLE_APPROVER = "Department Head"
ROLE_STAFF = "Staff"
ROLE_FRONTLINE = "Frontline Staff"
ROLE_OPS = "Operations Manager"
ROLE_PASSENGER = "Passenger"

ALL_ROLES = [ROLE_ADMIN, ROLE_EXECUTIVE, ROLE_FINANCE, ROLE_HR, ROLE_APPROVER, ROLE_STAFF, ROLE_FRONTLINE, ROLE_OPS, ROLE_PASSENGER]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, site_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "site_id": site_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
