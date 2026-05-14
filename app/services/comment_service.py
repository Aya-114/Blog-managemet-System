import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import ensure_owner_or_admin
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentUpdate

logger = logging.getLogger(__name__)


def comment_to_dict(comment: Comment) -> dict:
    return {
        "id": comment.id,
        "content": comment.content,
        "post_id": comment.post_id,
        "author_id": comment.author_id,
        "parent_id": comment.parent_id,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat(),
        "children": [comment_to_dict(child) for child in sorted(comment.children, key=lambda item: item.created_at)],
    }


def get_comment_or_404(db: Session, comment_id: int) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


def list_comments_for_post(db: Session, post_id: int, skip: int, limit: int) -> list[Comment]:
    if db.get(Post, post_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    stmt = (
        select(Comment)
        .where(Comment.post_id == post_id, Comment.parent_id.is_(None))
        .order_by(Comment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def create_comment(db: Session, post_id: int, payload: CommentCreate, current_user: User) -> Comment:
    if db.get(Post, post_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if payload.parent_id is not None:
        parent = get_comment_or_404(db, payload.parent_id)
        if parent.post_id != post_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent comment belongs to another post")
    comment = Comment(
        content=payload.content.strip(),
        post_id=post_id,
        author_id=current_user.id,
        parent_id=payload.parent_id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    logger.info("Comment created", extra={"operation": "comment_create", "user_id": current_user.id})
    return comment


def update_comment(db: Session, comment_id: int, payload: CommentUpdate, current_user: User) -> Comment:
    comment = get_comment_or_404(db, comment_id)
    ensure_owner_or_admin(comment.author_id, current_user)
    comment.content = payload.content.strip()
    comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    logger.info("Comment updated", extra={"operation": "comment_update", "user_id": current_user.id})
    return comment


def delete_comment(db: Session, comment_id: int, current_user: User) -> None:
    comment = get_comment_or_404(db, comment_id)
    ensure_owner_or_admin(comment.author_id, current_user)
    db.delete(comment)
    db.commit()
    logger.warning("Comment deleted", extra={"operation": "comment_delete", "user_id": current_user.id})
