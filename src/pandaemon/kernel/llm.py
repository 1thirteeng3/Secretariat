"""Model-agnostic LLM client abstraction."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from pandaemon.config import get_settings

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """Chat message."""
    role: str  # "user", "assistant", or "system"
    content: str


class LLMResponse(BaseModel):
    """Response from LLM."""
    content: str
    model: str
    usage: dict[str, int] = {}


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion from the model."""
        ...

    @abstractmethod
    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> tuple[LLMResponse, list[dict[str, Any]] | None]:
        """Generate completion with tool calling support."""
        ...


class AnthropicClient(LLMClient):
    """Anthropic Claude client."""

    def __init__(self, api_key: str) -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._default_model = "claude-3-5-sonnet-20241022"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using Claude."""
        model = model or self._default_model
        
        # Convert messages to Anthropic format
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        
        response = await self._client.messages.create(
            model=model,
            messages=anthropic_messages,
            system=system or "",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> tuple[LLMResponse, list[dict[str, Any]] | None]:
        """Generate completion with tool calling."""
        model = model or self._default_model
        
        anthropic_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        
        # Convert tools to Anthropic format
        anthropic_tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            }
            for tool in tools
        ]
        
        response = await self._client.messages.create(
            model=model,
            messages=anthropic_messages,
            system=system or "",
            tools=anthropic_tools,
            max_tokens=4096,
            **kwargs,
        )
        
        # Extract tool calls
        tool_calls = []
        text_content = ""
        
        for block in response.content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })
        
        return (
            LLMResponse(
                content=text_content,
                model=model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            ),
            tool_calls if tool_calls else None,
        )


class GeminiClient(LLMClient):
    """Google Gemini client."""

    def __init__(self, api_key: str) -> None:
        from google import genai
        self._client = genai.Client(api_key=api_key)
        self._default_model = "gemini-2.0-flash"

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using Gemini."""
        from google.genai import types
        
        model = model or self._default_model
        
        # Build contents for Gemini
        contents = []
        for m in messages:
            if m.role == "system":
                continue  # System handled separately
            role = "user" if m.role == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=m.content)],
            ))
        
        # Create config with system instruction
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system
        
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        
        return LLMResponse(
            content=response.text or "",
            model=model,
            usage={
                "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            },
        )

    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> tuple[LLMResponse, list[dict[str, Any]] | None]:
        """Generate completion with tool calling."""
        from google.genai import types
        
        model = model or self._default_model
        
        # Build contents
        contents = []
        for m in messages:
            if m.role == "system":
                continue
            role = "user" if m.role == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=m.content)],
            ))
        
        # Convert tools to Gemini format
        gemini_tools = []
        for tool in tools:
            # Convert JSON Schema to Gemini Schema
            gemini_tools.append(types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=tool["name"],
                        description=tool["description"],
                        parameters=tool["parameters"],
                    )
                ]
            ))
        
        config = types.GenerateContentConfig(
            tools=gemini_tools,
        )
        if system:
            config.system_instruction = system
        
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        
        # Extract tool calls
        tool_calls = []
        text_content = ""
        
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    text_content += part.text
                if hasattr(part, 'function_call') and part.function_call:
                    fc = part.function_call
                    tool_calls.append({
                        "id": fc.name,  # Gemini doesn't have separate IDs
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })
        
        return (
            LLMResponse(
                content=text_content,
                model=model,
                usage={
                    "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                },
            ),
            tool_calls if tool_calls else None,
        )


class DeepSeekClient(LLMClient):
    """DeepSeek client using OpenAI-compatible API."""

    def __init__(self, api_key: str) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )
        self._default_model = "deepseek-chat"

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using DeepSeek."""
        model = model or self._default_model
        
        # Build messages list
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        
        for m in messages:
            if m.role == "system":
                continue  # Already handled
            openai_messages.append({"role": m.role, "content": m.content})
        
        response = await self._client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=model,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    async def complete_with_tools(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]],
        model: str | None = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> tuple[LLMResponse, list[dict[str, Any]] | None]:
        """Generate completion with tool calling."""
        model = model or self._default_model
        
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        
        for m in messages:
            if m.role == "system":
                continue
            openai_messages.append({"role": m.role, "content": m.content})
        
        # Convert tools to OpenAI format
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]
        
        response = await self._client.chat.completions.create(
            model=model,
            messages=openai_messages,
            tools=openai_tools,
            max_tokens=4096,
            **kwargs,
        )
        
        # Extract tool calls
        tool_calls = []
        choice = response.choices[0]
        text_content = choice.message.content or ""
        
        if choice.message.tool_calls:
            import json
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {},
                })
        
        return (
            LLMResponse(
                content=text_content,
                model=model,
                usage={
                    "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "output_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            ),
            tool_calls if tool_calls else None,
        )


def get_llm_client(provider: str | None = None) -> LLMClient:
    """
    Get an LLM client for the specified provider.
    
    If no provider specified, uses the default from settings.
    Falls back to available providers if preferred is not configured.
    """
    settings = get_settings()
    provider = provider or settings.default_llm_provider
    
    # DeepSeek priority (if configured)
    if provider == "deepseek" and settings.deepseek_api_key:
        return DeepSeekClient(settings.deepseek_api_key)
    
    if provider == "anthropic" and settings.anthropic_api_key:
        return AnthropicClient(settings.anthropic_api_key)
    
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiClient(settings.gemini_api_key)
    
    # Fallback to any available provider (DeepSeek first)
    if settings.deepseek_api_key:
        logger.info("Using DeepSeek as LLM provider")
        return DeepSeekClient(settings.deepseek_api_key)
    
    if settings.anthropic_api_key:
        logger.warning(f"Requested provider '{provider}' not available, falling back to Anthropic")
        return AnthropicClient(settings.anthropic_api_key)
    
    if settings.gemini_api_key:
        logger.warning(f"Requested provider '{provider}' not available, falling back to Gemini")
        return GeminiClient(settings.gemini_api_key)
    
    raise ValueError("No LLM provider configured. Set DEEPSEEK_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY.")

