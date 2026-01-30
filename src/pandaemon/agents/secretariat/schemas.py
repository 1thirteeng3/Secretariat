"""Schemas for Secretariat agent."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    """Request to create a new note."""

    content_body: str = Field(description="Main content of the note")
    title_hint: str | None = Field(
        default=None,
        description="Suggested title (will be sanitized)",
    )
    target_folder_hint: str | None = Field(
        default=None,
        description="Target folder path within vault (e.g., 'Projects/AI')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags to add (without # prefix)",
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for the note",
    )


class NoteResponse(BaseModel):
    """Response after note operation."""

    status: Literal["success", "error"]
    internal_path: str = Field(description="Full path to the note file")
    obsidian_uri: str = Field(description="Obsidian URI link (obsidian://...)")
    title: str = Field(description="Final sanitized title")
    word_count: int = Field(default=0)
    tags: list[str] = Field(default_factory=list)
    error: str | None = None


class SearchNotesRequest(BaseModel):
    """Request to search notes."""

    query: str = Field(description="Search query")
    limit: int = Field(default=10, ge=1, le=50)
    folder: str | None = Field(default=None, description="Limit search to folder")


class NoteMetadata(BaseModel):
    """Parsed YAML frontmatter from a note."""

    id: str | None = None
    title: str | None = None
    created: datetime | None = None
    modified: datetime | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
