"""baseline

Revision ID: eb31b0ad02ef
Revises: 37f07f435de9
Create Date: 2026-01-07 09:50:17.373760+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb31b0ad02ef'
down_revision: Union[str, None] = '37f07f435de9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
