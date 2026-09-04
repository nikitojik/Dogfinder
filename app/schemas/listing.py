from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.listing import Kind, Sex, Size, Status
from app.schemas.user import UserRead


class ListingCreate(BaseModel):
    kind: Kind
    title: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    happened_at: datetime

    breed: str | None = Field(default=None, max_length=60)
    color: str | None = Field(default=None, max_length=60)
    size: Size | None = None
    size_note: str | None = Field(default=None, max_length=120)
    sex: Sex = Sex.UNKNOWN

    contact_phone: str | None = Field(default=None, max_length=20)


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    happened_at: datetime | None = None
    status: Status | None = None

    breed: str | None = Field(default=None, max_length=60)
    color: str | None = Field(default=None, max_length=60)
    size: Size | None = None
    size_note: str | None = Field(default=None, max_length=120)
    sex: Sex | None = None

    contact_phone: str | None = Field(default=None, max_length=20)


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: Kind
    status: Status
    title: str
    description: str | None
    happened_at: datetime

    breed: str | None
    color: str | None
    size: Size | None
    size_note: str | None
    sex: Sex

    contact_phone: str | None
    created_at: datetime
    owner: UserRead


class ListingPage(BaseModel):
    items: list[ListingRead]
    total: int
    limit: int
    offset: int
