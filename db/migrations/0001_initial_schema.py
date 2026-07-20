"""Initial schema — sessions, conversation_turns, queries, opportunity_scores.

Revision: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(50)),
        sa.Column("turn_count", sa.Integer, default=0),
        sa.Column("last_sector", sa.String(200)),
        sa.Column("last_countries", sa.JSON),
    )

    op.create_table(
        "conversation_turns",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(100),
                  sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_index", sa.Integer, nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("sector", sa.String(200)),
        sa.Column("target_countries", sa.JSON),
        sa.Column("summary", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("session_id", "turn_index", name="uq_session_turn"),
    )
    op.create_index("ix_conversation_turns_session_id", "conversation_turns", ["session_id"])

    op.create_table(
        "queries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(100),
                  sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("sector", sa.String(200)),
        sa.Column("target_countries", sa.JSON),
        sa.Column("provider", sa.String(50)),
        sa.Column("agents_called", sa.JSON),
        sa.Column("summary", sa.Text),
        sa.Column("errors", sa.JSON),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_queries_session_id", "queries", ["session_id"])
    op.create_index("ix_queries_created_at", "queries", ["created_at"])

    op.create_table(
        "opportunity_scores",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("query_id", sa.Integer,
                  sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hs_code", sa.String(20), nullable=False),
        sa.Column("destination_country", sa.String(10), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("score_breakdown", sa.JSON),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_opportunity_scores_query_id", "opportunity_scores", ["query_id"])
    op.create_index("ix_opportunity_scores_country", "opportunity_scores", ["destination_country"])


def downgrade() -> None:
    op.drop_table("opportunity_scores")
    op.drop_table("queries")
    op.drop_table("conversation_turns")
    op.drop_table("sessions")
