"""Schemas for Black Ops agent."""

from pydantic import BaseModel, Field


class NavigateRequest(BaseModel):
    """Request to navigate to a URL."""

    url: str = Field(description="URL to navigate to")
    wait_for: str | None = Field(
        default=None,
        description="CSS selector to wait for after navigation",
    )
    screenshot: bool = Field(default=False, description="Capture screenshot")


class ExtractRequest(BaseModel):
    """Request to extract content from a page."""

    url: str = Field(description="URL to extract from")
    selector: str | None = Field(
        default=None,
        description="CSS selector for content (uses main content if not specified)",
    )
    extract_links: bool = Field(default=False, description="Also extract links")


class ClickRequest(BaseModel):
    """Request to click an element."""

    selector: str = Field(description="CSS selector of element to click")
    wait_after: int = Field(default=1000, description="Milliseconds to wait after click")


class TypeRequest(BaseModel):
    """Request to type text into an element."""

    selector: str = Field(description="CSS selector of input element")
    text: str = Field(description="Text to type")
    submit: bool = Field(default=False, description="Press Enter after typing")


class BrowserTaskRequest(BaseModel):
    """Request for a complex browser task using browser-use."""

    task: str = Field(description="Natural language description of the task")
    url: str | None = Field(default=None, description="Starting URL (optional)")
    max_steps: int = Field(default=10, ge=1, le=50, description="Maximum steps to take")


class ExtractionResult(BaseModel):
    """Result of content extraction."""

    url: str
    title: str | None = None
    content: str
    links: list[dict[str, str]] = Field(default_factory=list)
    screenshot_path: str | None = None
