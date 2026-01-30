"""Black Ops agent - Browser automation for special operations."""

import asyncio
import logging
import random
from pathlib import Path
from typing import Any

from pandaemon.agents.base import BaseAgent
from pandaemon.agents.black_ops.schemas import (
    BrowserTaskRequest,
    ExtractRequest,
    ExtractionResult,
    NavigateRequest,
)
from pandaemon.config import get_settings
from pandaemon.kernel.schemas import AgentResponse

logger = logging.getLogger(__name__)


class BlackOpsAgent(BaseAgent):
    """
    Black Ops Agent - Browser automation for hostile environments.
    
    Uses browser-use (Playwright) for human-like browser automation:
    - Navigate with random delays
    - Extract content from pages
    - Execute complex multi-step tasks via LLM
    - Optional proxy rotation for anonymity
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._browser = None
        self._context = None
        self._page = None
        self._initialized = False

    @property
    def name(self) -> str:
        return "black_ops"

    @property
    def description(self) -> str:
        return "Browser automation agent for web extraction and automation tasks"

    def get_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions for Black Ops."""
        return [
            {
                "name": "navigate",
                "description": "Navigate to a URL and optionally take a screenshot",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "wait_for": {"type": "string", "description": "CSS selector to wait for"},
                        "screenshot": {"type": "boolean", "default": False},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "extract",
                "description": "Extract text content from a webpage",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to extract from"},
                        "selector": {"type": "string", "description": "CSS selector for content"},
                        "extract_links": {"type": "boolean", "default": False},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "browser_task",
                "description": "Execute a complex browser task described in natural language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"},
                        "url": {"type": "string", "description": "Starting URL"},
                        "max_steps": {"type": "integer", "default": 10},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "close_browser",
                "description": "Close the browser and cleanup resources",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    async def execute(self, action: str, parameters: dict[str, Any]) -> AgentResponse:
        """Execute a Black Ops action."""
        if action == "navigate":
            return await self._navigate(parameters)
        elif action == "extract":
            return await self._extract(parameters)
        elif action == "browser_task":
            return await self._browser_task(parameters)
        elif action == "close_browser":
            return await self._close_browser()
        else:
            return AgentResponse(status="error", error=f"Unknown action: {action}")

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        await self._close_browser()

    async def _ensure_browser(self) -> bool:
        """Ensure browser is initialized."""
        if self._initialized and self._page:
            return True

        try:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()

            # Browser options
            launch_options: dict[str, Any] = {
                "headless": self._settings.browser_headless,
            }

            # Add proxy if configured
            if self._settings.browser_proxy:
                launch_options["proxy"] = {"server": self._settings.browser_proxy}

            self._browser = await playwright.chromium.launch(**launch_options)

            # Create context with realistic viewport
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

            self._page = await self._context.new_page()
            self._initialized = True
            logger.info("Browser initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False

    async def _add_human_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Add random delay to mimic human behavior."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def _navigate(self, params: dict[str, Any]) -> AgentResponse:
        """Navigate to a URL."""
        try:
            request = NavigateRequest(**params)
        except Exception as e:
            return AgentResponse(status="error", error=f"Invalid parameters: {e}")

        if not await self._ensure_browser():
            return AgentResponse(status="error", error="Failed to initialize browser")

        try:
            # Add jitter before navigation
            await self._add_human_delay(200, 1000)

            # Navigate
            await self._page.goto(request.url, wait_until="domcontentloaded")

            # Wait for specific element if requested
            if request.wait_for:
                await self._page.wait_for_selector(request.wait_for, timeout=10000)

            # Take screenshot if requested
            screenshot_path = None
            if request.screenshot:
                screenshot_path = Path("./data/screenshots") / f"screenshot_{hash(request.url)}.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                await self._page.screenshot(path=str(screenshot_path))

            title = await self._page.title()

            return AgentResponse(
                status="success",
                response=f"Navigated to: {title}",
                data={
                    "url": request.url,
                    "title": title,
                    "screenshot": str(screenshot_path) if screenshot_path else None,
                },
            )

        except Exception as e:
            return AgentResponse(status="error", error=f"Navigation failed: {e}")

    async def _extract(self, params: dict[str, Any]) -> AgentResponse:
        """Extract content from a page."""
        try:
            request = ExtractRequest(**params)
        except Exception as e:
            return AgentResponse(status="error", error=f"Invalid parameters: {e}")

        if not await self._ensure_browser():
            return AgentResponse(status="error", error="Failed to initialize browser")

        try:
            # Navigate first
            await self._add_human_delay()
            await self._page.goto(request.url, wait_until="domcontentloaded")

            # Get title
            title = await self._page.title()

            # Extract content
            if request.selector:
                element = await self._page.query_selector(request.selector)
                content = await element.inner_text() if element else ""
            else:
                # Try common main content selectors
                for selector in ["main", "article", "#content", ".content", "body"]:
                    element = await self._page.query_selector(selector)
                    if element:
                        content = await element.inner_text()
                        break
                else:
                    content = await self._page.inner_text("body")

            # Extract links if requested
            links = []
            if request.extract_links:
                link_elements = await self._page.query_selector_all("a[href]")
                for link in link_elements[:50]:  # Limit to 50 links
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    if href and text.strip():
                        links.append({"href": href, "text": text.strip()[:100]})

            result = ExtractionResult(
                url=request.url,
                title=title,
                content=content[:5000],  # Limit content length
                links=links,
            )

            return AgentResponse(
                status="success",
                response=f"Extracted {len(content)} chars from: {title}",
                data=result.model_dump(),
            )

        except Exception as e:
            return AgentResponse(status="error", error=f"Extraction failed: {e}")

    async def _browser_task(self, params: dict[str, Any]) -> AgentResponse:
        """Execute a complex browser task using browser-use."""
        try:
            request = BrowserTaskRequest(**params)
        except Exception as e:
            return AgentResponse(status="error", error=f"Invalid parameters: {e}")

        try:
            # Import browser-use
            from browser_use import Agent
            from langchain_anthropic import ChatAnthropic

            # Create LLM for browser-use
            if not self._settings.anthropic_api_key:
                return AgentResponse(
                    status="error",
                    error="browser_task requires ANTHROPIC_API_KEY",
                )

            llm = ChatAnthropic(
                model_name="claude-3-5-sonnet-20241022",
                api_key=self._settings.anthropic_api_key,
            )

            # Create browser-use agent
            agent = Agent(
                task=request.task,
                llm=llm,
            )

            # Run the task
            result = await agent.run(max_steps=request.max_steps)

            return AgentResponse(
                status="success",
                response=f"Task completed: {request.task}",
                data={"result": str(result)},
            )

        except ImportError:
            return AgentResponse(
                status="error",
                error="browser-use not installed. Run: pip install browser-use langchain-anthropic",
            )
        except Exception as e:
            return AgentResponse(status="error", error=f"Browser task failed: {e}")

    async def _close_browser(self) -> AgentResponse:
        """Close browser and cleanup."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()

            self._page = None
            self._context = None
            self._browser = None
            self._initialized = False

            return AgentResponse(status="success", response="Browser closed")

        except Exception as e:
            return AgentResponse(status="error", error=f"Failed to close browser: {e}")
