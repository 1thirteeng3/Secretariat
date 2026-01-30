"""Standardized schemas for kernel communication."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Classification of user intent."""
    
    ACT = "act"           # Execute an action (play music, run script)
    CREATE = "create"     # Create new content (note, task)
    QUERY = "query"       # Retrieve/search information
    DEPLOY = "deploy"     # Publish/post content
    CONVERSE = "converse" # General conversation
    SYSTEM = "system"     # System commands (status, help)


class StandardizedPrompt(BaseModel):
    """Standardized input format for all agents."""
    
    raw_input: str = Field(description="Original user input")
    intent: IntentType = Field(description="Classified intent")
    source: str = Field(default="api", description="Message source (api, telegram, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now)
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    # Extracted entities (populated by router)
    target_agent: str | None = Field(default=None, description="Target agent name")
    action: str | None = Field(default=None, description="Specific action to perform")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Action parameters")


class StandardizedAction(BaseModel):
    """Standardized output format from router."""
    
    agent: str = Field(description="Target agent to handle request")
    action: str = Field(description="Action to perform")
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class AgentResponse(BaseModel):
    """Response from an agent."""
    
    status: str = Field(description="success or error")
    response: str | None = Field(default=None, description="Human-readable response")
    data: dict[str, Any] = Field(default_factory=dict, description="Structured data")
    error: str | None = Field(default=None, description="Error message if failed")


class ToolDefinition(BaseModel):
    """Definition of a tool/action available to agents."""
    
    name: str = Field(description="Tool name")
    description: str = Field(description="What the tool does")
    parameters: dict[str, Any] = Field(description="JSON Schema for parameters")
    agent: str = Field(description="Agent that owns this tool")
