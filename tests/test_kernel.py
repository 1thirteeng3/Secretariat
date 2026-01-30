"""Tests for kernel components."""

import pytest

from pandaemon.kernel.schemas import IntentType, StandardizedAction, StandardizedPrompt


class TestSchemas:
    """Test kernel schemas."""

    def test_intent_type_enum(self) -> None:
        """Test IntentType enum values."""
        assert IntentType.ACT.value == "act"
        assert IntentType.CREATE.value == "create"
        assert IntentType.QUERY.value == "query"
        assert IntentType.CONVERSE.value == "converse"

    def test_standardized_prompt(self) -> None:
        """Test StandardizedPrompt model."""
        prompt = StandardizedPrompt(
            raw_input="Create a note about AI",
            intent=IntentType.CREATE,
            source="telegram",
        )
        
        assert prompt.raw_input == "Create a note about AI"
        assert prompt.intent == IntentType.CREATE
        assert prompt.source == "telegram"
        assert prompt.timestamp is not None

    def test_standardized_action(self) -> None:
        """Test StandardizedAction model."""
        action = StandardizedAction(
            agent="secretariat",
            action="create_note",
            parameters={"content_body": "Test content"},
            confidence=0.95,
        )
        
        assert action.agent == "secretariat"
        assert action.action == "create_note"
        assert action.confidence == 0.95


class TestLLMClient:
    """Test LLM client abstraction.
    
    Note: These tests are minimal as they require API keys for full testing.
    """

    def test_import_llm_module(self) -> None:
        """Test that LLM module imports correctly."""
        from pandaemon.kernel.llm import LLMClient, Message, LLMResponse
        
        # Just verify imports work
        assert LLMClient is not None
        assert Message is not None
        assert LLMResponse is not None

    def test_message_model(self) -> None:
        """Test Message model."""
        from pandaemon.kernel.llm import Message
        
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_llm_response_model(self) -> None:
        """Test LLMResponse model."""
        from pandaemon.kernel.llm import LLMResponse
        
        response = LLMResponse(
            content="Hello back!",
            model="test-model",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        assert response.content == "Hello back!"
        assert response.model == "test-model"


class TestKernelRouter:
    """Test kernel router.
    
    Note: Full router tests require LLM configuration.
    """

    @pytest.mark.asyncio
    async def test_router_import(self) -> None:
        """Test that router imports correctly."""
        from pandaemon.kernel.router import KernelRouter
        
        router = KernelRouter()
        assert router is not None
