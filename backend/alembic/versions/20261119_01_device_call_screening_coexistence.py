"""device call screening coexistence fields (SSOT §1.2.1).

Revision ID: 20261119_01
Revises:
Create Date: 2026-11-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261119_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("device") as batch:
        batch.add_column(sa.Column("call_screening_held_by", sa.String(length=256), nullable=True))
        batch.add_column(
            sa.Column(
                "call_screening_peers",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("device") as batch:
        batch.drop_column("call_screening_peers")
        batch.drop_column("call_screening_held_by")
