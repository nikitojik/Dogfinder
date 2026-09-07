"""Add location to listings

Revision ID: cbec10218f64
Revises: 1e6924c33cf0
Create Date: 2026-09-07 19:21:36.484040

"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cbec10218f64"
down_revision: str | Sequence[str] | None = "1e6924c33cf0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("listings", "location")
