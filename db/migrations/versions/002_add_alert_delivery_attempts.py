"""add alert_delivery_attempts

Revision ID: 002_add_alert_delivery_attempts
Revises: 001_initial
Create Date: 2024-01-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_alert_delivery_attempts"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create alert_delivery_attempts table
    op.create_table(
        "alert_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="CASCADE"),
    )

    # Create index
    op.create_index(
        "idx_alert_delivery_attempts_alert_created",
        "alert_delivery_attempts",
        ["alert_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_alert_delivery_attempts_alert_created", table_name="alert_delivery_attempts")

    # Drop table
    op.drop_table("alert_delivery_attempts")
