from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate
from app.services.cache import cache_service
from app.services.comment_service import (
    comment_to_dict,
    create_comment,
    delete_comment,
    get_comment_or_404,
    list_comments_for_post,
    update_comment,
)

router = APIRouter(tags=["comments"])


@router.get("/posts/{post_id}/comments", response_model=list[CommentRead])
def get_comments(
    post_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = f"comments:post:{post_id}:{skip}:{limit}"
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return cached
    data = [comment_to_dict(comment) for comment in list_comments_for_post(db, post_id, skip, limit)]
    cache_service.set_json(cache_key, data)
    return data


@router.post("/posts/{post_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = create_comment(db, post_id, payload, current_user)
    cache_service.delete_pattern(f"comments:post:{post_id}:*")
    return comment_to_dict(comment)


@router.get("/comments/{comment_id}", response_model=CommentRead)
def get_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cache_key = f"comments:item:{comment_id}"
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return cached
    data = comment_to_dict(get_comment_or_404(db, comment_id))
    cache_service.set_json(cache_key, data)
    return data


@router.put("/comments/{comment_id}", response_model=CommentRead)
def edit_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = update_comment(db, comment_id, payload, current_user)
    cache_service.delete_pattern(f"comments:post:{comment.post_id}:*")
    cache_service.delete_pattern(f"comments:item:{comment_id}")
    return comment_to_dict(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = get_comment_or_404(db, comment_id)
    post_id = comment.post_id
    delete_comment(db, comment_id, current_user)
    cache_service.delete_pattern(f"comments:post:{post_id}:*")
    cache_service.delete_pattern(f"comments:item:{comment_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
