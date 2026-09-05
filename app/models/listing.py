import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.response import Response
    from app.models.user import User


class Kind(str, enum.Enum):
    LOST = "lost"
    FOUND = "found"


class Status(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class Sex(str, enum.Enum):
    UNKNOWN = "unknown"
    MALE = "male"
    FEMALE = "female"


class Size(str, enum.Enum):
    SMALL = "small"  # до 35 см в холке
    MEDIUM = "medium"  # 35–55 см
    LARGE = "large"  # свыше 55 см


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[Kind] = mapped_column(Enum(Kind, name="listing_kind"))
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="listing_status"), default=Status.ACTIVE
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    breed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(60))
    sex: Mapped[Sex] = mapped_column(Enum(Sex, name="dog_sex"), default=Sex.UNKNOWN)
    size: Mapped[Size | None] = mapped_column(Enum(Size, name="dog_size"))
    size_note: Mapped[str | None] = mapped_column(String(120))
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    owner: Mapped["User"] = relationship(back_populates="listings")
    responses: Mapped[list["Response"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_listings_feed", "kind", "status", "happened_at"),)

    def __repr__(self) -> str:
        return f"Listing(id={self.id}, kind={self.kind}, title={self.title!r})"
