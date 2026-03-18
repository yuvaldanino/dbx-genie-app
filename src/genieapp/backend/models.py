"""Pydantic models for the GenieApp API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .. import __version__


# --- Version ---

class VersionOut(BaseModel):
    """Application version info."""

    version: str

    @classmethod
    def from_metadata(cls) -> VersionOut:
        return cls(version=__version__)


# --- App Config ---

class BrandingOut(BaseModel):
    """Branding configuration sent to frontend."""

    company_name: str
    description: str
    logo_path: str | None = ""
    primary_color: str | None = "#1a73e8"
    secondary_color: str | None = "#ea4335"
    accent_color: str | None = ""
    chart_colors: list[str] | None = []


class TableInfoBrief(BaseModel):
    """Brief table info for config responses."""

    full_name: str
    table_name: str
    comment: str = ""


class AppConfigOut(BaseModel):
    """Full app config for frontend initialization."""

    space_id: str
    display_name: str
    sample_questions: list[str] = []
    branding: BrandingOut
    tables: list[TableInfoBrief] = []


# --- Chat ---

class ChatMessageIn(BaseModel):
    """User chat message input."""

    question: str
    conversation_id: str | None = None
    space_id: str | None = None


class ChartSuggestion(BaseModel):
    """Suggested chart configuration based on query results."""

    chart_type: str = Field(description="bar, line, pie, area, kpi, map, or table")
    x_axis: str | None = None
    y_axis: str | None = None
    title: str = ""


class ChatMessageOut(BaseModel):
    """Genie response with data and chart suggestion."""

    conversation_id: str
    message_id: str = ""
    status: str  # COMPLETED, FAILED, etc.
    description: str = ""
    sql: str = ""
    columns: list[str] = []
    data: list[dict] = []
    row_count: int = 0
    chart_suggestion: ChartSuggestion | None = None
    error: str | None = None
    suggested_questions: list[str] = []
    query_description: str = ""
    is_truncated: bool = False
    is_clarification: bool = False
    error_type: str = ""


class FeedbackIn(BaseModel):
    """Thumbs up/down feedback for a Genie response."""

    conversation_id: str
    message_id: str
    rating: str = Field(description="THUMBS_UP or THUMBS_DOWN")


class ChatStartOut(BaseModel):
    """Initial response from async chat start."""

    conversation_id: str
    message_id: str


class ChatStatusOut(BaseModel):
    """Polling response for message status."""

    status: str  # FETCHING_METADATA, ASKING_AI, EXECUTING_QUERY, COMPLETED, FAILED
    is_complete: bool


# --- Tables ---

class ColumnInfo(BaseModel):
    """Column metadata."""

    name: str
    type: str
    comment: str = ""


class TableInfoOut(BaseModel):
    """Table summary for list view."""

    full_name: str
    table_name: str
    comment: str = ""


class TableDetailOut(BaseModel):
    """Full table detail with columns."""

    full_name: str
    table_name: str
    comment: str = ""
    columns: list[ColumnInfo] = []
    row_count: int = 0


# --- Export ---

class ExportRequest(BaseModel):
    """Export request parameters."""

    conversation_id: str
    format: str = Field(default="csv", description="json or csv")


# --- Conversations ---

class ConversationOut(BaseModel):
    """Conversation summary."""

    conversation_id: str
    first_question: str = ""
    message_count: int = 0


class ConversationMessageOut(BaseModel):
    """A single message pair (question + response) in a conversation."""

    question: str
    response: ChatMessageOut | None = None


# --- Spaces ---

class SpaceOut(BaseModel):
    """A created Genie Space session."""

    space_id: str
    company_name: str
    description: str | None = ""
    logo_path: str | None = ""
    primary_color: str | None = "#1a73e8"
    secondary_color: str | None = "#ea4335"
    accent_color: str | None = ""
    chart_colors: list[str] | None = []
    created_at: str | None = ""


class CreateSpaceIn(BaseModel):
    """Input for creating a new Genie Space."""

    company_name: str
    description: str
    logo_url: str = ""


class CreateSpaceOut(BaseModel):
    """Response after triggering space creation."""

    run_id: str


class JobStatusOut(BaseModel):
    """Status of a pipeline job run."""

    run_id: str
    status: str  # RUNNING, COMPLETED, FAILED, CANCELLED
    space_id: str | None = None
    error: str | None = None


# --- Users ---

class UserOut(BaseModel):
    """User profile response."""

    user_id: str
    email: str = ""
    username: str = ""
    default_template: str = "simple"
    preferences: dict = {}


class UserPreferencesIn(BaseModel):
    """Input for updating user preferences."""

    default_template: str | None = None
    preferences: dict | None = None
