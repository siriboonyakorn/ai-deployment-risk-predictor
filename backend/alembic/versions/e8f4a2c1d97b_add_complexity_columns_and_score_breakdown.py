"""add complexity columns and score breakdown

Revision ID: e8f4a2c1d97b
Revises: d5a2e89f3b71
Create Date: 2026-02-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8f4a2c1d97b"
down_revision: Union[str, None] = "d5a2e89f3b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Commits: add complexity columns ---
    op.add_column("commits", sa.Column("avg_cyclomatic_complexity", sa.Float(), nullable=True))
    op.add_column("commits", sa.Column("max_cyclomatic_complexity", sa.Float(), nullable=True))
    op.add_column("commits", sa.Column("avg_maintainability_index", sa.Float(), nullable=True))
    op.add_column("commits", sa.Column("complexity_rank", sa.String(2), nullable=True))

    # --- RiskAssessments: add score_breakdown_json, update default model_version ---
    op.add_column("risk_assessments", sa.Column("score_breakdown_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("risk_assessments", "score_breakdown_json")
    op.drop_column("commits", "complexity_rank")
    op.drop_column("commits", "avg_maintainability_index")
    op.drop_column("commits", "max_cyclomatic_complexity")
    op.drop_column("commits", "avg_cyclomatic_complexity")
