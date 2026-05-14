from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: int | None = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentRead(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    parent_id: int | None
    created_at: datetime
    updated_at: datetime
    children: list["CommentRead"] = Field(default_factory=list)


CommentRead.model_rebuild()
