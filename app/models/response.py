import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as Enum
from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.listing import Listing
    from app.models.user import User


class ResponseStatus(str, enum.Enum):
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    NEW = "new"


class Response(Base, TimestampMixin):
    __tablename__ = "responses"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[ResponseStatus] = mapped_column(
        Enum(ResponseStatus, name="response_status"), default=ResponseStatus.NEW
    )
    listing: Mapped["Listing"] = relationship(back_populates="responses")
    author: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("listing_id", "author_id", name="uq_response_per_user"),
        Index("ix_responses_listing_status", "listing_id", "status"),
    )

    def __repr__(self) -> str:
        return f"Response(id={self.id}, listing_id={self.listing_id}, status={self.status})"
