"""Base agent interface."""

from abc import ABC, abstractmethod
from typing import Any

from pandaemon.kernel.schemas import AgentResponse


class BaseAgent(ABC):
    """
    Abstract base class for all Pandaemon agents (spokes).
    
    Each agent is a module that handles specific functionality:
    - Secretariat: Obsidian vault management
    - Gardener: Semantic connections
    - Remote DJ: Spotify control
    - Black Ops: Web automation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for routing."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]:
        """
        Get tool definitions for this agent.
        
        Returns a list of tool definitions in the format:
        {
            "name": "tool_name",
            "description": "What the tool does",
            "parameters": { JSON Schema }
        }
        """
        ...

    @abstractmethod
    async def execute(self, action: str, parameters: dict[str, Any]) -> AgentResponse:
        """
        Execute an action with the given parameters.
        
        Args:
            action: The action name (e.g., "create_note")
            parameters: Action parameters
            
        Returns:
            AgentResponse with status and results
        """
        ...

    async def shutdown(self) -> None:
        """Cleanup on shutdown. Override if needed."""
        pass
