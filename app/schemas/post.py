from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    content: str = Field(..., min_length=1)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    content: str | None = Field(default=None, min_length=1)


class PostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    owner_id: int
    author_username: str | None = None
    created_at: datetime
    updated_at: datetime
