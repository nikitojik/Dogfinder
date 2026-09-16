import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationKind(str, enum.Enum):
    NEW_RESPONSE = "new_response"
    NEW_MATCH = "new_match"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    kind: Mapped[NotificationKind] = mapped_column(
        SAEnum(NotificationKind, name="notification_kind")
    )
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column()

    sent: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("kind", "listing_id", "subject_id", name="uq_notification"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"Notification(kind={self.kind}, listing_id={self.listing_id}, "
            f"subject_id={self.subject_id})"
        )
