
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jwt_utils import decode_access_token
from app.infrastructure.db.session import get_db
from app.infrastructure.db.models.user_model import UserModel

oauth2_scheme = settings.oauth2_scheme


def get_current_user(
    database_session: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> UserModel:
    token_data: dict[str, Any] = decode_access_token(token)

    user_id: str | None = token_data.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user: UserModel | None = database_session.get(UserModel, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return user
