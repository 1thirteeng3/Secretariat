"""Schemas for Gardener agent."""

from datetime import datetime

from pydantic import BaseModel, Field


class GardenerState(BaseModel):
    """Persistent state for the Gardener daemon."""

    last_run: datetime = Field(description="Timestamp of last garden run")
    processed_notes: dict[str, str] = Field(
        default_factory=dict,
        description="Map of note path -> content hash",
    )
    total_connections: int = Field(default=0)
    total_insights: int = Field(default=0)


class ConnectionInsight(BaseModel):
    """A semantic connection between two notes."""

    source_note: str = Field(description="Path to source note")
    target_note: str = Field(description="Path to connected note")
    similarity: float = Field(ge=0.0, le=1.0)
    insight_text: str = Field(description="LLM-generated insight about the connection")


class QueryRequest(BaseModel):
    """Request to query notes semantically."""

    query: str = Field(description="Natural language query")
    k: int = Field(default=5, ge=1, le=20, description="Number of results")


class QueryResult(BaseModel):
    """Result from semantic query."""

    path: str
    title: str
    snippet: str
    similarity: float


class GardenRunResult(BaseModel):
    """Result of a garden maintenance run."""

    notes_processed: int
    connections_found: int
    insights_generated: int
    duration_seconds: float
