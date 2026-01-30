"""Secretariat agent - Obsidian vault manager (the sovereign scribe)."""

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from unidecode import unidecode

from pandaemon.agents.base import BaseAgent
from pandaemon.agents.secretariat.schemas import CreateNoteRequest, NoteResponse
from pandaemon.kernel.schemas import AgentResponse

logger = logging.getLogger(__name__)


class SecretariatAgent(BaseAgent):
    """
    Secretariat Agent - Obsidian vault manager.
    
    The Secretariat is the "sovereign scribe" responsible for:
    - Creating notes with proper YAML frontmatter
    - Atomic file writes with lock checking
    - Folder validation and title sanitization
    - ASCII transliteration for filenames
    """

    def __init__(self, vault_path: Path) -> None:
        self._vault_path = vault_path
        self._inbox_folder = "Inbox"  # Default folder for new notes

    @property
    def name(self) -> str:
        return "secretariat"

    @property
    def description(self) -> str:
        return "Obsidian vault manager - creates, edits, and retrieves notes"

    def get_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions for Secretariat."""
        return [
            {
                "name": "create_note",
                "description": "Create a new note in the Obsidian vault",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content_body": {
                            "type": "string",
                            "description": "Main content of the note",
                        },
                        "title_hint": {
                            "type": "string",
                            "description": "Suggested title for the note",
                        },
                        "target_folder_hint": {
                            "type": "string",
                            "description": "Target folder (e.g., 'Projects/AI')",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags without # prefix",
                        },
                    },
                    "required": ["content_body"],
                },
            },
            {
                "name": "get_note",
                "description": "Retrieve a note by title or path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to note (relative to vault)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Note title to search for",
                        },
                    },
                },
            },
            {
                "name": "search_notes",
                "description": "Search notes by content or title",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
        ]

    async def execute(self, action: str, parameters: dict[str, Any]) -> AgentResponse:
        """Execute a Secretariat action."""
        if action == "create_note":
            return await self._create_note(parameters)
        elif action == "get_note":
            return await self._get_note(parameters)
        elif action == "search_notes":
            return await self._search_notes(parameters)
        else:
            return AgentResponse(
                status="error",
                error=f"Unknown action: {action}",
            )

    async def _create_note(self, params: dict[str, Any]) -> AgentResponse:
        """Create a new note in the vault."""
        try:
            request = CreateNoteRequest(**params)
        except Exception as e:
            return AgentResponse(status="error", error=f"Invalid parameters: {e}")

        # Generate title from hint or content
        title = self._generate_title(request.title_hint, request.content_body)
        safe_title = self._sanitize_filename(title)

        # Determine target folder
        folder_path = self._resolve_folder(request.target_folder_hint)

        # Generate unique ID
        note_id = datetime.now().strftime("%Y%m%d%H%M%S")

        # Normalize tags (lowercase, no #)
        tags = [self._normalize_tag(t) for t in request.tags]

        # Build YAML frontmatter
        frontmatter = {
            "id": note_id,
            "title": title,
            "created": datetime.now().isoformat(),
            "status": "seed",
            "tags": tags,
        }
        if request.aliases:
            frontmatter["aliases"] = request.aliases

        # Build full content
        content = self._build_note_content(frontmatter, request.content_body)

        # Determine file path
        file_path = folder_path / f"{safe_title}.md"

        # Handle duplicates
        file_path = self._ensure_unique_path(file_path)

        # Check for locks
        if self._is_locked(file_path):
            return AgentResponse(
                status="error",
                error=f"File is locked: {file_path}",
            )

        # Atomic write
        try:
            self._atomic_write(file_path, content)
        except Exception as e:
            return AgentResponse(status="error", error=f"Write failed: {e}")

        # Generate Obsidian URI
        relative_path = file_path.relative_to(self._vault_path)
        obsidian_uri = f"obsidian://open?vault={self._vault_path.name}&file={relative_path}"

        # Response
        word_count = len(request.content_body.split())
        response = NoteResponse(
            status="success",
            internal_path=str(file_path),
            obsidian_uri=obsidian_uri,
            title=title,
            word_count=word_count,
            tags=tags,
        )

        return AgentResponse(
            status="success",
            response=f"Created note: {title} ({word_count} words)",
            data=response.model_dump(),
        )

    async def _get_note(self, params: dict[str, Any]) -> AgentResponse:
        """Retrieve a note by path or title."""
        path = params.get("path")
        title = params.get("title")

        if path:
            file_path = self._vault_path / path
            if not file_path.suffix:
                file_path = file_path.with_suffix(".md")
        elif title:
            # Search for note by title
            file_path = self._find_note_by_title(title)
            if not file_path:
                return AgentResponse(
                    status="error",
                    error=f"Note not found: {title}",
                )
        else:
            return AgentResponse(
                status="error",
                error="Must provide path or title",
            )

        if not file_path.exists():
            return AgentResponse(
                status="error",
                error=f"Note not found: {file_path}",
            )

        content = file_path.read_text(encoding="utf-8")

        return AgentResponse(
            status="success",
            response=content[:500] + ("..." if len(content) > 500 else ""),
            data={
                "path": str(file_path),
                "content": content,
            },
        )

    async def _search_notes(self, params: dict[str, Any]) -> AgentResponse:
        """Search notes by content."""
        query = params.get("query", "")
        limit = params.get("limit", 10)

        if not query:
            return AgentResponse(status="error", error="Query required")

        results = []
        query_lower = query.lower()

        for md_file in self._vault_path.rglob("*.md"):
            # Skip hidden and trash
            if any(part.startswith(".") for part in md_file.parts):
                continue
            if ".trash" in str(md_file).lower():
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    relative_path = md_file.relative_to(self._vault_path)
                    results.append({
                        "path": str(relative_path),
                        "title": md_file.stem,
                        "snippet": self._extract_snippet(content, query),
                    })
                    if len(results) >= limit:
                        break
            except Exception:
                continue

        return AgentResponse(
            status="success",
            response=f"Found {len(results)} notes matching '{query}'",
            data={"results": results},
        )

    # ==================== Helper Methods ====================

    def _generate_title(self, hint: str | None, content: str) -> str:
        """Generate a title from hint or content."""
        if hint and hint.strip():
            return hint.strip()

        # Use first line or first 50 chars
        first_line = content.split("\n")[0].strip()
        if first_line:
            return first_line[:50]

        return f"Note {datetime.now().strftime('%Y%m%d')}"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a filename for filesystem compatibility."""
        # Transliterate to ASCII
        name = unidecode(name)

        # Remove/replace illegal characters
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        name = re.sub(r"\s+", " ", name).strip()

        # Limit length
        if len(name) > 100:
            name = name[:100].rsplit(" ", 1)[0]

        return name or "Untitled"

    def _normalize_tag(self, tag: str) -> str:
        """Normalize a tag (lowercase, no #, no spaces)."""
        tag = tag.lstrip("#").strip().lower()
        tag = re.sub(r"\s+", "-", tag)
        return tag

    def _resolve_folder(self, hint: str | None) -> Path:
        """Resolve target folder, falling back to Inbox."""
        if hint:
            folder = self._vault_path / hint
            if folder.exists() and folder.is_dir():
                return folder

        # Fallback to Inbox
        inbox = self._vault_path / self._inbox_folder
        inbox.mkdir(parents=True, exist_ok=True)
        return inbox

    def _build_note_content(self, frontmatter: dict[str, Any], body: str) -> str:
        """Build full note content with YAML frontmatter."""
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n\n{body}"

    def _ensure_unique_path(self, path: Path) -> Path:
        """Ensure the path is unique by appending a number if needed."""
        if not path.exists():
            return path

        base = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1

        while True:
            new_path = parent / f"{base} ({counter}){suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def _is_locked(self, path: Path) -> bool:
        """Check if a file is locked."""
        lock_path = path.with_suffix(path.suffix + ".lock")
        return lock_path.exists()

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically using temp file + rename."""
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file in same directory (for atomic rename)
        fd, temp_path = tempfile.mkstemp(
            suffix=".tmp",
            prefix=".pandaemon_",
            dir=path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            # Atomic rename
            os.replace(temp_path, path)
            logger.info(f"Created note: {path}")
        except Exception:
            # Cleanup temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _find_note_by_title(self, title: str) -> Path | None:
        """Find a note by title (case-insensitive)."""
        title_lower = title.lower()

        for md_file in self._vault_path.rglob("*.md"):
            if md_file.stem.lower() == title_lower:
                return md_file

        return None

    def _extract_snippet(self, content: str, query: str, context: int = 50) -> str:
        """Extract a snippet around the query match."""
        lower_content = content.lower()
        lower_query = query.lower()

        pos = lower_content.find(lower_query)
        if pos == -1:
            return content[:100]

        start = max(0, pos - context)
        end = min(len(content), pos + len(query) + context)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet
