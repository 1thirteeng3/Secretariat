"""Tests for Secretariat agent."""

from pathlib import Path

import pytest

from pandaemon.agents.secretariat.agent import SecretariatAgent
from pandaemon.agents.secretariat.schemas import CreateNoteRequest


class TestSecretariatAgent:
    """Test suite for Secretariat agent."""

    @pytest.fixture
    def agent(self, temp_vault: Path) -> SecretariatAgent:
        """Create a Secretariat agent with temp vault."""
        return SecretariatAgent(vault_path=temp_vault)

    def test_agent_properties(self, agent: SecretariatAgent) -> None:
        """Test agent name and description."""
        assert agent.name == "secretariat"
        assert "Obsidian" in agent.description

    def test_get_tools(self, agent: SecretariatAgent) -> None:
        """Test tool definitions."""
        tools = agent.get_tools()
        assert len(tools) == 3
        
        tool_names = [t["name"] for t in tools]
        assert "create_note" in tool_names
        assert "get_note" in tool_names
        assert "search_notes" in tool_names

    @pytest.mark.asyncio
    async def test_create_note_basic(
        self, agent: SecretariatAgent, temp_vault: Path
    ) -> None:
        """Test basic note creation."""
        result = await agent.execute("create_note", {
            "content_body": "This is a test note about AI.",
            "title_hint": "Test AI Note",
            "tags": ["test", "ai"],
        })
        
        assert result.status == "success"
        assert "Test AI Note" in result.response
        assert result.data["title"] == "Test AI Note"
        assert "test" in result.data["tags"]
        assert "ai" in result.data["tags"]
        
        # Verify file was created
        note_path = Path(result.data["internal_path"])
        assert note_path.exists()
        
        content = note_path.read_text()
        assert "This is a test note about AI." in content
        assert "tags:" in content  # YAML frontmatter

    @pytest.mark.asyncio
    async def test_create_note_without_title(
        self, agent: SecretariatAgent
    ) -> None:
        """Test note creation without title hint."""
        result = await agent.execute("create_note", {
            "content_body": "First line becomes the title\n\nRest of content.",
        })
        
        assert result.status == "success"
        assert "First line becomes the title" in result.data["title"]

    @pytest.mark.asyncio
    async def test_create_note_folder_validation(
        self, agent: SecretariatAgent, temp_vault: Path
    ) -> None:
        """Test note creation with folder hint."""
        result = await agent.execute("create_note", {
            "content_body": "Project note content.",
            "title_hint": "Project Note",
            "target_folder_hint": "Projects",
        })
        
        assert result.status == "success"
        assert "Projects" in result.data["internal_path"]

    @pytest.mark.asyncio
    async def test_create_note_fallback_to_inbox(
        self, agent: SecretariatAgent
    ) -> None:
        """Test fallback to Inbox when folder doesn't exist."""
        result = await agent.execute("create_note", {
            "content_body": "Note for nonexistent folder.",
            "title_hint": "Inbox Note",
            "target_folder_hint": "NonexistentFolder",
        })
        
        assert result.status == "success"
        assert "Inbox" in result.data["internal_path"]

    @pytest.mark.asyncio
    async def test_get_note_by_path(
        self, agent: SecretariatAgent, temp_vault: Path
    ) -> None:
        """Test retrieving note by path."""
        # Create a note first
        await agent.execute("create_note", {
            "content_body": "Retrievable content.",
            "title_hint": "Retrievable Note",
        })
        
        result = await agent.execute("get_note", {
            "path": "Inbox/Retrievable Note.md",
        })
        
        assert result.status == "success"
        assert "Retrievable content" in result.data["content"]

    @pytest.mark.asyncio
    async def test_get_note_by_title(
        self, agent: SecretariatAgent, temp_vault: Path
    ) -> None:
        """Test retrieving note by title."""
        await agent.execute("create_note", {
            "content_body": "Find me by title.",
            "title_hint": "Findable Note",
        })
        
        result = await agent.execute("get_note", {
            "title": "Findable Note",
        })
        
        assert result.status == "success"
        assert "Find me by title" in result.data["content"]

    @pytest.mark.asyncio
    async def test_search_notes(
        self, agent: SecretariatAgent, temp_vault: Path
    ) -> None:
        """Test searching notes."""
        # Create multiple notes
        await agent.execute("create_note", {
            "content_body": "Note about quantum physics.",
            "title_hint": "Quantum Note",
        })
        await agent.execute("create_note", {
            "content_body": "Note about classical mechanics.",
            "title_hint": "Classical Note",
        })
        
        result = await agent.execute("search_notes", {
            "query": "quantum",
        })
        
        assert result.status == "success"
        assert len(result.data["results"]) >= 1
        assert any("Quantum" in r["title"] for r in result.data["results"])


class TestSecretariatHelpers:
    """Test helper methods."""

    @pytest.fixture
    def agent(self, temp_vault: Path) -> SecretariatAgent:
        return SecretariatAgent(vault_path=temp_vault)

    def test_sanitize_filename(self, agent: SecretariatAgent) -> None:
        """Test filename sanitization."""
        assert agent._sanitize_filename("Normal Title") == "Normal Title"
        assert agent._sanitize_filename("Title: With Colons") == "Title With Colons"
        assert agent._sanitize_filename("Café Naïve") == "Cafe Naive"
        assert agent._sanitize_filename("A" * 200)[:100]  # Should truncate

    def test_normalize_tag(self, agent: SecretariatAgent) -> None:
        """Test tag normalization."""
        assert agent._normalize_tag("#MyTag") == "mytag"
        assert agent._normalize_tag("Multi Word") == "multi-word"
        assert agent._normalize_tag("  Spaces  ") == "spaces"
