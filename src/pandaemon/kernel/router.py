"""Kernel router - Intent recognition and agent dispatch."""

import json
import logging
from typing import Any

from pandaemon.config import get_settings
from pandaemon.kernel.llm import LLMClient, Message, get_llm_client
from pandaemon.kernel.schemas import AgentResponse, IntentType, StandardizedAction

logger = logging.getLogger(__name__)


ROUTER_SYSTEM_PROMPT = """You are the Pandaemon Kernel, a cognitive router that classifies user intent and routes to the appropriate agent.

Available agents and their capabilities:
1. SECRETARIAT - Obsidian vault management
   - create_note: Create a new note in the vault
   - get_note: Retrieve a note by title or path
   - search_notes: Search notes by content

2. GARDENER - Semantic connections and queries
   - query: Answer questions about notes using semantic search
   - find_connections: Find related notes
   - run_garden: Scan vault and update semantic index

3. REMOTE_DJ - Spotify music control
   - play: Play music (song, album, playlist)
   - pause/resume: Pause or resume playback
   - next/previous: Skip tracks
   - set_volume: Adjust volume
   - get_devices: List Spotify devices

4. BLACK_OPS - Browser automation
   - navigate: Go to a URL
   - extract: Extract content from a webpage
   - browser_task: Execute complex browser automation

5. SYSTEM - System commands
   - status: Get system status
   - help: Show available commands

Analyze the user's message and respond with a JSON object:
{
    "intent": "act|create|query|deploy|converse|system",
    "agent": "secretariat|gardener|remote_dj|black_ops|system|none",
    "action": "specific action name",
    "parameters": {extracted parameters},
    "confidence": 0.0-1.0
}

If the message is general conversation with no specific action, use agent "none" and intent "converse".
Extract relevant parameters from the message (e.g., note content, search query, folder hints, tags).

Examples:
- "Create a note about quantum physics" → secretariat/create_note with content
- "What did I write about entropy?" → gardener/query
- "Play Focus Noir playlist" → remote_dj/play with query
- "Pause the music" → remote_dj/pause
- "Go to google.com and search for AI news" → black_ops/browser_task
- "Hello, how are you?" → none/converse"""


class KernelRouter:
    """
    Central router that classifies intent and dispatches to agents.
    
    The kernel is the "nervous system" of Pandaemon - it receives all
    inputs and routes them to the appropriate spoke agents.
    """

    def __init__(self) -> None:
        self._llm: LLMClient | None = None
        self._agents: dict[str, Any] = {}
        self._settings = get_settings()

    async def initialize(self) -> None:
        """Initialize the kernel and load agents."""
        # Initialize LLM client
        try:
            self._llm = get_llm_client()
            logger.info(f"Kernel using LLM provider: {self._llm.provider_name}")
        except ValueError as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self._llm = None
        
        # Load available agents
        await self._load_agents()
        
        logger.info(f"Kernel initialized with agents: {list(self._agents.keys())}")

    async def _load_agents(self) -> None:
        """Dynamically load available agents."""
        # Import agents here to avoid circular imports
        from pandaemon.agents.secretariat import SecretariatAgent
        from pandaemon.agents.gardener import GardenerAgent
        from pandaemon.agents.remote_dj import RemoteDJAgent
        from pandaemon.agents.black_ops import BlackOpsAgent
        
        # Secretariat requires vault path
        if self._settings.obsidian_vault_path:
            self._agents["secretariat"] = SecretariatAgent(
                vault_path=self._settings.obsidian_vault_path
            )
            logger.info("Loaded Secretariat agent")
        
        # Gardener also requires vault path
        if self._settings.obsidian_vault_path:
            self._agents["gardener"] = GardenerAgent(
                vault_path=self._settings.obsidian_vault_path,
                vector_db_path=self._settings.vector_db_path,
            )
            logger.info("Loaded Gardener agent")

        # Remote DJ (Spotify) - requires credentials
        if self._settings.has_spotify():
            self._agents["remote_dj"] = RemoteDJAgent()
            logger.info("Loaded Remote DJ agent")
        else:
            logger.warning("Remote DJ disabled: Spotify not configured")

        # Black Ops (Browser) - always available
        self._agents["black_ops"] = BlackOpsAgent()
        logger.info("Loaded Black Ops agent")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        for name, agent in self._agents.items():
            if hasattr(agent, "shutdown"):
                await agent.shutdown()
                logger.info(f"Shut down agent: {name}")

    async def process(self, message: str, source: str = "api") -> dict[str, Any]:
        """
        Process an incoming message.
        
        1. Classify intent using LLM
        2. Route to appropriate agent
        3. Return response
        """
        # If no LLM, return error
        if not self._llm:
            return {
                "status": "error",
                "error": "No LLM provider configured",
            }
        
        # Classify intent
        action = await self._classify_intent(message)
        logger.info(f"Classified intent: {action.agent}/{action.action} (confidence: {action.confidence})")
        
        # Handle conversation (no agent needed)
        if action.agent == "none" or action.intent == IntentType.CONVERSE:
            response = await self._converse(message)
            return {
                "status": "success",
                "response": response,
                "action": "converse",
            }
        
        # Handle system commands
        if action.agent == "system":
            return await self._handle_system_command(action)
        
        # Dispatch to agent
        agent = self._agents.get(action.agent)
        if not agent:
            return {
                "status": "error",
                "error": f"Agent '{action.agent}' not available",
            }
        
        # Execute action
        try:
            result: AgentResponse = await agent.execute(action.action, action.parameters)
            return {
                "status": result.status,
                "response": result.response,
                "action": f"{action.agent}/{action.action}",
                "data": result.data,
                "error": result.error,
            }
        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "action": f"{action.agent}/{action.action}",
            }

    async def _classify_intent(self, message: str) -> StandardizedAction:
        """Use LLM to classify user intent."""
        if not self._llm:
            raise ValueError("No LLM configured")
        
        response = await self._llm.complete(
            messages=[Message(role="user", content=message)],
            system=ROUTER_SYSTEM_PROMPT,
            temperature=0.3,  # Lower temperature for more consistent classification
            max_tokens=500,
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content)
            return StandardizedAction(
                agent=data.get("agent", "none"),
                action=data.get("action", "converse"),
                parameters=data.get("parameters", {}),
                confidence=data.get("confidence", 0.8),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse intent response: {e}")
            # Default to conversation
            return StandardizedAction(
                agent="none",
                action="converse",
                parameters={"message": message},
                confidence=0.5,
            )

    async def _converse(self, message: str) -> str:
        """Handle general conversation."""
        if not self._llm:
            return "I'm not fully configured yet. Please set up an LLM provider."
        
        response = await self._llm.complete(
            messages=[Message(role="user", content=message)],
            system="You are Pandaemon, a helpful cognitive daemon assistant. Be concise and helpful.",
            temperature=0.7,
            max_tokens=1000,
        )
        return response.content

    async def _handle_system_command(self, action: StandardizedAction) -> dict[str, Any]:
        """Handle system-level commands."""
        if action.action == "status":
            return {
                "status": "success",
                "response": f"Pandaemon is running. Agents: {list(self._agents.keys())}",
                "action": "system/status",
            }
        
        if action.action == "help":
            help_text = """Available commands:
- Create notes: "Create a note about [topic]"
- Query notes: "What did I write about [topic]?"
- Find connections: "Find notes related to [topic]"
- Status: "Status" or "System status"
"""
            return {
                "status": "success", 
                "response": help_text,
                "action": "system/help",
            }
        
        return {
            "status": "error",
            "error": f"Unknown system command: {action.action}",
        }
