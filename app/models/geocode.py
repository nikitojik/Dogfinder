from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class GeocodeCache(Base, TimestampMixin):
    __tablename__ = "geocode_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    display_name: Mapped[str | None] = mapped_column(String(500))

    def __repr__(self) -> str:
        return f"GeocodeCache(query={self.query!r}, lat={self.lat}, lon={self.lon})"
