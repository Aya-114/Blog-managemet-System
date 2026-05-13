import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.session import get_db
from app.dependencies.auth import require_roles
from app.models.user import User
from app.schemas.common import Role
from app.schemas.user import UserAdminUpdate, UserRead
from app.services.user_service import get_user_by_username

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[UserRead])
def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(Role.admin)),
):
    stmt = select(User).order_by(User.id).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(Role.admin)),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.username is None and payload.password is None and payload.role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes provided")

    new_username = payload.username if payload.username is not None else user.username
    new_role = payload.role.value if payload.role is not None else user.role
    password_is_same = payload.password is None or verify_password(payload.password, user.password_hash)

    if new_username == user.username and new_role == user.role and password_is_same:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes provided")

    if payload.username is not None and payload.username != user.username:
        if get_user_by_username(db, payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
        user.username = payload.username

    if payload.role is not None:
        if user.id == current_admin.id and payload.role != Role.admin:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin cannot demote their own account")
        user.role = payload.role.value

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    logger.warning("Admin updated user", extra={"operation": "admin_user_update", "user_id": current_admin.id})
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(Role.admin)),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin cannot delete their own account")

    db.delete(user)
    db.commit()
    logger.warning("Admin deleted user", extra={"operation": "admin_user_delete", "user_id": current_admin.id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
