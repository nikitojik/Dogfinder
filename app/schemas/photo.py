from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.storage import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE


class UploadUrlRequest(BaseModel):
    content_type: str
    size_bytes: int = Field(gt=0, le=MAX_FILE_SIZE)

    @field_validator("content_type")
    @classmethod
    def check_content_type(cls, value: str) -> str:
        if value not in ALLOWED_CONTENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
            raise ValueError(f"Допустимые типы: {allowed}")
        return value


class UploadUrlResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int


class PhotoConfirm(BaseModel):
    object_key: str = Field(max_length=255)


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    thumb_url: str | None
    is_primary: bool
    sort_order: int
    created_at: datetime
