"""Inspect migration state through Alembic APIs, without parsing console output."""

from __future__ import annotations

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import Connection


class MigrationStatus(BaseModel):
    """Closed technical receipt; revision spelling is owned by Alembic."""

    model_config = ConfigDict(
        extra="forbid", validate_by_name=True, hide_input_in_errors=True
    )
    expected_heads: list[str] = Field(alias="expectedHeads")
    current_heads: list[str] = Field(alias="currentHeads")


def read_heads(config: Config, connection: Connection) -> MigrationStatus:
    """Read scripts and an explicitly supplied connection; never migrate or connect."""
    scripts = ScriptDirectory.from_config(config)
    current = MigrationContext.configure(connection).get_current_heads()
    return MigrationStatus(
        expected_heads=sorted(scripts.get_heads()), current_heads=sorted(current)
    )
