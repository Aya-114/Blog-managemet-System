import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import ensure_owner_or_admin
from app.models.post import Post
from app.models.user import User
from app.schemas.common import Role
from app.schemas.post import PostCreate, PostUpdate

logger = logging.getLogger(__name__)


def get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


def list_posts(db: Session, skip: int, limit: int, author_id: int | None = None, search: str | None = None) -> list[Post]:
    stmt = select(Post)
    if author_id is not None:
        stmt = stmt.where(Post.owner_id == author_id)
    if search:
        like_term = f"%{search.strip()}%"
        stmt = stmt.where(Post.title.ilike(like_term) | Post.content.ilike(like_term))
    stmt = stmt.order_by(Post.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def create_post(db: Session, payload: PostCreate, current_user: User) -> Post:
    if current_user.role not in {Role.admin.value, Role.author.value}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only authors and admins can create posts")
    post = Post(title=payload.title.strip(), content=payload.content.strip(), owner_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.info("Post created", extra={"operation": "post_create", "user_id": current_user.id})
    return post


def update_post(db: Session, post_id: int, payload: PostUpdate, current_user: User) -> Post:
    post = get_post_or_404(db, post_id)
    ensure_owner_or_admin(post.owner_id, current_user)
    if payload.title is not None:
        post.title = payload.title.strip()
    if payload.content is not None:
        post.content = payload.content.strip()
    post.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    logger.info("Post updated", extra={"operation": "post_update", "user_id": current_user.id})
    return post


def delete_post(db: Session, post_id: int, current_user: User) -> None:
    post = get_post_or_404(db, post_id)
    ensure_owner_or_admin(post.owner_id, current_user)
    db.delete(post)
    db.commit()
    logger.warning("Post deleted", extra={"operation": "post_delete", "user_id": current_user.id})
