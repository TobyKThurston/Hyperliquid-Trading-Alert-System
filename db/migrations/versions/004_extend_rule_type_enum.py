"""extend rule_type_enum with rsi, bollinger_bands

Revision ID: 004_extend_rule_type_enum
Revises: 003_add_api_keys
Create Date: 2026-04-17 00:00:01.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "004_extend_rule_type_enum"
down_revision: str | None = "003_add_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres: add new enum values. IF NOT EXISTS makes this re-runnable.
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in some
    # Postgres versions, so we commit explicitly.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE rule_type_enum ADD VALUE IF NOT EXISTS 'rsi'")
        op.execute("ALTER TYPE rule_type_enum ADD VALUE IF NOT EXISTS 'bollinger_bands'")


def downgrade() -> None:
    # Postgres does not support removing values from an enum without
    # rebuilding the type and rewriting every row. Leaving the values in
    # place on downgrade is the standard safe choice.
    pass
