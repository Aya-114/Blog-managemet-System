from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.post import PostCreate, PostRead, PostUpdate
from app.services.cache import cache_service
from app.services.post_service import create_post, delete_post, get_post_or_404, list_posts, update_post

router = APIRouter(prefix="/posts", tags=["posts"])


def _post_to_json(post) -> dict:
    return PostRead.model_validate(post).model_dump(mode="json")


@router.get("", response_model=list[PostRead])
def get_posts(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    author_id: int | None = None,
    search: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = f"posts:v2:list:{skip}:{limit}:{author_id}:{search or ''}"
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return cached
    data = [_post_to_json(post) for post in list_posts(db, skip, limit, author_id, search)]
    cache_service.set_json(cache_key, data)
    return data


@router.get("/{post_id}", response_model=PostRead)
def get_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cache_key = f"posts:v2:item:{post_id}"
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return cached
    post = get_post_or_404(db, post_id)
    data = _post_to_json(post)
    cache_service.set_json(cache_key, data)
    return data


@router.post("", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def add_post(payload: PostCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = create_post(db, payload, current_user)
    cache_service.delete_pattern("posts:*")
    return post


@router.put("/{post_id}", response_model=PostRead)
def edit_post(
    post_id: int,
    payload: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = update_post(db, post_id, payload, current_user)
    cache_service.delete_pattern("posts:*")
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_post(db, post_id, current_user)
    cache_service.delete_pattern("posts:*")
    cache_service.delete_pattern(f"comments:post:{post_id}:*")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
