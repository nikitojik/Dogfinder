from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.services.storage import public_url

if TYPE_CHECKING:
    from app.models.listing import Listing


class Photo(Base, TimestampMixin):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    thumb_key: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer)
    is_primary: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    listing: Mapped["Listing"] = relationship(back_populates="photos")

    def __repr__(self) -> str:
        return f"Photo(id={self.id}, listing_id={self.listing_id})"

    @property
    def url(self) -> str:
        return public_url(self.object_key)

    @property
    def thumb_url(self) -> str | None:
        return public_url(self.thumb_key) if self.thumb_key else None
