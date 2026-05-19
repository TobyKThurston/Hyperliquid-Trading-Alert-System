"""initial

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create rule_type enum (if not exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE rule_type_enum AS ENUM ('price_threshold', 'percent_move', 'candle_close', 'macd_cross');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create delivery_status enum (if not exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE delivery_status_enum AS ENUM ('pending', 'delivered', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create rules table
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "rule_type",
            postgresql.ENUM(
                "price_threshold",
                "percent_move",
                "candle_close",
                "macd_cross",
                name="rule_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), server_default="0"),
        sa.Column("discord_webhook_url", sa.String(), nullable=True),
        sa.Column("generic_webhook_url", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create alerts table
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("rule_type", sa.String(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("trigger_value", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column(
            "delivery_status",
            postgresql.ENUM(
                "pending", "delivered", "failed", name="delivery_status_enum", create_type=False
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("delivery_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_delivery_attempt", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["rules.id"], ondelete="CASCADE"),
    )

    # Create candles table
    op.create_table(
        "candles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), server_default="900", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Create worker_cursors table
    op.create_table(
        "worker_cursors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("worker_id", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("last_processed_timestamp", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create unique constraints
    op.create_unique_constraint(
        "uq_alert_window", "alerts", ["rule_id", "window_start", "window_end"]
    )
    op.create_unique_constraint(
        "uq_candle_symbol_time_interval", "candles", ["symbol", "timestamp", "interval_seconds"]
    )
    op.create_unique_constraint("uq_worker_cursor", "worker_cursors", ["worker_id", "symbol"])

    # Create indexes
    op.create_index("idx_alerts_rule_id", "alerts", ["rule_id"])
    op.create_index(
        "idx_alerts_delivery_status",
        "alerts",
        ["delivery_status"],
        postgresql_where=sa.text("delivery_status = 'pending'"),
    )
    op.create_index("idx_alerts_triggered_at", "alerts", [sa.text("triggered_at DESC")])
    op.create_index(
        "idx_rules_active_symbol",
        "rules",
        ["is_active", "symbol"],
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        "idx_candles_symbol_timestamp", "candles", ["symbol", sa.text("timestamp DESC")]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_candles_symbol_timestamp", table_name="candles")
    op.drop_index("idx_rules_active_symbol", table_name="rules")
    op.drop_index("idx_alerts_triggered_at", table_name="alerts")
    op.drop_index("idx_alerts_delivery_status", table_name="alerts")
    op.drop_index("idx_alerts_rule_id", table_name="alerts")

    # Drop unique constraints
    op.drop_constraint("uq_worker_cursor", "worker_cursors", type_="unique")
    op.drop_constraint("uq_candle_symbol_time_interval", "candles", type_="unique")
    op.drop_constraint("uq_alert_window", "alerts", type_="unique")

    # Drop tables
    op.drop_table("worker_cursors")
    op.drop_table("candles")
    op.drop_table("alerts")
    op.drop_table("rules")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS delivery_status_enum")
    op.execute("DROP TYPE IF EXISTS rule_type_enum")
