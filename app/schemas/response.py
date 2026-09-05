from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.response import ResponseStatus
from app.schemas.user import UserRead


class ResponseCreate(BaseModel):
    message: str = Field(min_length=10, max_length=2000)
    contact_phone: str | None = Field(default=None, max_length=20)


class ResponseStatusUpdate(BaseModel):
    status: ResponseStatus


class ResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    message: str
    contact_phone: str | None
    status: ResponseStatus
    created_at: datetime
    author: UserRead
