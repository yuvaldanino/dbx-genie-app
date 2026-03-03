"""Application state loader — reads state.json written by setup script."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class TableInfo(BaseModel):
    """Table metadata from state.json."""

    full_name: str
    table_name: str
    comment: str = ""


class BrandingConfig(BaseModel):
    """Branding configuration snapshot."""

    company_name: str
    description: str
    logo_path: str = ""
    primary_color: str = "#1a73e8"
    secondary_color: str = "#ea4335"


class AppState(BaseModel):
    """Full application state loaded from state.json."""

    space_id: str
    display_name: str
    catalog: str
    schema_name: str
    warehouse_id: str = ""
    tables: list[TableInfo] = []
    sample_questions: list[str] = []
    branding: BrandingConfig


def _read_volume_file(volume_path: str) -> str:
    """Read a file from a UC Volume via the Databricks SDK."""
    from databricks.sdk import WorkspaceClient

    ws = WorkspaceClient()
    resp = ws.files.download(volume_path)
    return resp.contents.read().decode("utf-8")


@lru_cache(maxsize=1)
def get_state() -> AppState:
    """Load and cache app state from state.json."""
    state_path_str = os.environ.get("STATE_FILE_PATH", "state.json")

    if state_path_str.startswith("/Volumes/"):
        raw = _read_volume_file(state_path_str)
    else:
        state_path = Path(state_path_str)
        if not state_path.exists():
            raise FileNotFoundError(f"State file not found: {state_path}")
        raw = state_path.read_text()

    data: dict[str, Any] = json.loads(raw)
    return AppState(**data)
