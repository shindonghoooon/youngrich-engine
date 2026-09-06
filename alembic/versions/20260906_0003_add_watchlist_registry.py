"""Add independent watchlist memberships and immutable onboarding receipts."""
from alembic import op
import sqlalchemy as sa

revision = "20260906_0003"
down_revision = "20260904_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_memberships",
        sa.Column("membership_id", sa.String(120), primary_key=True),
        sa.Column("company_id", sa.String(100), sa.ForeignKey("companies.company_id"), nullable=False),
        sa.Column("instrument_id", sa.String(100), sa.ForeignKey("instruments.instrument_id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("tracking_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tracking_stopped_at", sa.DateTime(timezone=True)),
        sa.Column("reference_analysis_snapshot_id", sa.String(120), sa.ForeignKey("analysis_snapshots.snapshot_id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_source", sa.Text(), nullable=False),
        sa.UniqueConstraint("instrument_id", name="uq_watchlist_instrument"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_watchlist_status"),
    )
    op.create_table(
        "onboarding_records",
        sa.Column("request_id", sa.String(100), primary_key=True),
        sa.Column("instrument_id", sa.String(100), sa.ForeignKey("instruments.instrument_id"), nullable=False),
        sa.Column("analysis_snapshot_id", sa.String(120), sa.ForeignKey("analysis_snapshots.snapshot_id"), unique=True),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("onboarding_records")
    op.drop_table("watchlist_memberships")
