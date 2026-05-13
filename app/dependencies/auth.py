import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Role

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        logger.warning("Token validation failed", extra={"operation": "token_validation"})
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        logger.warning("Token user no longer exists", extra={"operation": "token_validation", "user_id": user_id})
        raise credentials_error
    logger.debug("Token validated", extra={"operation": "token_validation", "user_id": user.id})
    return user


def require_roles(*roles: Role) -> Callable:
    allowed = {role.value for role in roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def ensure_owner_or_admin(owner_id: int, current_user: User) -> None:
    if current_user.role == Role.admin.value or current_user.id == owner_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own content")
