import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.common import Role
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


def count_users(db: Session) -> int:
    return db.scalar(select(func.count(User.id))) or 0


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username.strip().lower()))


def create_user(db: Session, payload: UserCreate) -> User:
    if get_user_by_username(db, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    if payload.role == Role.admin and count_users(db) > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the first registered user can choose the admin role",
        )

    user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role.value)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User registered", extra={"operation": "user_register", "user_id": user.id})
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user and verify_password(password, user.password_hash):
        logger.info("Login succeeded", extra={"operation": "login", "user_id": user.id})
        return user
    logger.warning("Login failed", extra={"operation": "login"})
    return None
