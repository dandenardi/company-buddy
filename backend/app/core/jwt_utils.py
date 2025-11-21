from datetime import datetime, timedelta
from jose import jwt

from app.core.config import settings


def create_access_token(data: dict) -> str:
    """
    Create JWT token with expiration based on settings.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expires_minutes)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt
