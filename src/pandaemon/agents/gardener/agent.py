"""Gardener agent - Ontology daemon for semantic connections."""

import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from pandaemon.agents.base import BaseAgent
from pandaemon.agents.gardener.schemas import (
    ConnectionInsight,
    GardenerState,
    GardenRunResult,
    QueryResult,
)
from pandaemon.kernel.schemas import AgentResponse

logger = logging.getLogger(__name__)


# Constants from architecture
SIMILARITY_THRESHOLD = 0.75
MAX_LLM_CALLS_PER_RUN = 50
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
PANDAEMON_GARDEN_DELIMITER = "--- %% PANDAEMON_GARDEN %% ---"


class GardenerAgent(BaseAgent):
    """
    Gardener Agent - Ontology daemon for semantic connections.
    
    The Gardener is responsible for "tectological maintenance":
    - Differential vault scanning
    - Vector embedding with sentence-transformers
    - Finding semantic connections between notes
    - Synthesizing insights using LLM
    - Grafting connections back into notes
    """

    def __init__(self, vault_path: Path, vector_db_path: Path) -> None:
        self._vault_path = vault_path
        self._vector_db_path = vector_db_path
        self._state_file = vector_db_path / "gardener_state.json"
        self._collection_name = "pandaemon_notes"
        
        # Lazy-loaded components
        self._chroma_client = None
        self._collection = None
        self._embedding_model = None
        self._llm = None

    @property
    def name(self) -> str:
        return "gardener"

    @property
    def description(self) -> str:
        return "Semantic connections daemon - finds and synthesizes relationships between notes"

    def get_tools(self) -> list[dict[str, Any]]:
        """Get tool definitions for Gardener."""
        return [
            {
                "name": "query",
                "description": "Answer a question using semantic search over your notes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language question",
                        },
                        "k": {
                            "type": "integer",
                            "description": "Number of results",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "find_connections",
                "description": "Find notes semantically related to a topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic to find connections for",
                        },
                        "k": {
                            "type": "integer",
                            "description": "Number of connections",
                            "default": 5,
                        },
                    },
                    "required": ["topic"],
                },
            },
            {
                "name": "run_garden",
                "description": "Run the garden maintenance (vectorize new notes, find connections)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "force": {
                            "type": "boolean",
                            "description": "Force re-process all notes",
                            "default": False,
                        },
                    },
                },
            },
        ]

    async def execute(self, action: str, parameters: dict[str, Any]) -> AgentResponse:
        """Execute a Gardener action."""
        # Ensure components are initialized
        await self._ensure_initialized()

        if action == "query":
            return await self._query(parameters)
        elif action == "find_connections":
            return await self._find_connections(parameters)
        elif action == "run_garden":
            return await self._run_garden(parameters)
        else:
            return AgentResponse(
                status="error",
                error=f"Unknown action: {action}",
            )

    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        if self._chroma_client:
            # ChromaDB doesn't require explicit shutdown
            pass

    # ==================== Core Methods ====================

    async def _ensure_initialized(self) -> None:
        """Lazy initialization of heavy components."""
        if self._chroma_client is None:
            await self._initialize_vector_db()
        if self._embedding_model is None:
            await self._initialize_embeddings()

    async def _initialize_vector_db(self) -> None:
        """Initialize ChromaDB client and collection."""
        import chromadb
        from chromadb.config import Settings

        self._vector_db_path.mkdir(parents=True, exist_ok=True)

        self._chroma_client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self._vector_db_path),
            anonymized_telemetry=False,
        ))

        # Get or create collection
        self._collection = self._chroma_client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(f"ChromaDB initialized at {self._vector_db_path}")

    async def _initialize_embeddings(self) -> None:
        """Initialize sentence-transformers model."""
        from sentence_transformers import SentenceTransformer

        self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")

    async def _query(self, params: dict[str, Any]) -> AgentResponse:
        """Query notes using semantic search."""
        query = params.get("query", "")
        k = params.get("k", 5)

        if not query:
            return AgentResponse(status="error", error="Query required")

        if not self._collection or not self._embedding_model:
            return AgentResponse(status="error", error="Gardener not initialized")

        # Embed query
        query_embedding = self._embedding_model.encode(query).tolist()

        # Search
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
        )

        # Format results
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append(QueryResult(
                    path=doc_id,
                    title=Path(doc_id).stem,
                    snippet=results["documents"][0][i][:200] if results["documents"] else "",
                    similarity=1 - results["distances"][0][i] if results["distances"] else 0,
                ).model_dump())

        return AgentResponse(
            status="success",
            response=f"Found {len(formatted)} relevant notes for: {query}",
            data={"results": formatted},
        )

    async def _find_connections(self, params: dict[str, Any]) -> AgentResponse:
        """Find notes related to a topic."""
        topic = params.get("topic", "")
        k = params.get("k", 5)

        # Same as query for now
        return await self._query({"query": topic, "k": k})

    async def _run_garden(self, params: dict[str, Any]) -> AgentResponse:
        """Run garden maintenance: scan, vectorize, connect, synthesize."""
        force = params.get("force", False)
        synthesize = params.get("synthesize", True)  # Generate insights
        graft = params.get("graft", True)  # Append to notes
        start_time = time.time()

        if not self._collection or not self._embedding_model:
            return AgentResponse(status="error", error="Gardener not initialized")

        # Initialize LLM if needed for synthesis
        if synthesize and not self._llm:
            await self._initialize_llm()

        # Load state
        state = self._load_state()

        # Scan for changed notes
        notes_to_process = []
        for md_file in self._vault_path.rglob("*.md"):
            # Skip hidden, trash, syncthing temp files
            if self._should_skip_file(md_file):
                continue

            relative_path = str(md_file.relative_to(self._vault_path))
            content_hash = self._hash_content(md_file)

            # Check if new or changed
            if force or relative_path not in state.processed_notes:
                notes_to_process.append((md_file, relative_path))
            elif state.processed_notes[relative_path] != content_hash:
                notes_to_process.append((md_file, relative_path))

        # Process notes
        processed_count = 0
        for md_file, relative_path in notes_to_process:
            try:
                content = md_file.read_text(encoding="utf-8")
                
                # Extract text for embedding (title + first 500 chars)
                embed_text = self._prepare_embed_text(md_file.stem, content)
                
                # Generate embedding
                embedding = self._embedding_model.encode(embed_text).tolist()
                
                # Upsert to vector DB
                self._collection.upsert(
                    ids=[relative_path],
                    embeddings=[embedding],
                    documents=[embed_text],
                    metadatas=[{
                        "title": md_file.stem,
                        "path": relative_path,
                    }],
                )
                
                # Update state
                state.processed_notes[relative_path] = self._hash_content(md_file)
                processed_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to process {relative_path}: {e}")
                continue

        # Find connections and synthesize insights
        connections_found = 0
        insights_generated = 0
        llm_calls = 0

        if synthesize and processed_count > 0:
            for md_file, relative_path in notes_to_process:
                if llm_calls >= MAX_LLM_CALLS_PER_RUN:
                    logger.warning("Hit max LLM calls per run")
                    break

                try:
                    # Find related notes
                    content = md_file.read_text(encoding="utf-8")
                    embed_text = self._prepare_embed_text(md_file.stem, content)
                    embedding = self._embedding_model.encode(embed_text).tolist()

                    results = self._collection.query(
                        query_embeddings=[embedding],
                        n_results=5,
                    )

                    # Filter to high similarity (exclude self)
                    related = []
                    if results["ids"] and results["ids"][0]:
                        for i, doc_id in enumerate(results["ids"][0]):
                            if doc_id == relative_path:
                                continue
                            similarity = 1 - results["distances"][0][i] if results["distances"] else 0
                            if similarity >= SIMILARITY_THRESHOLD:
                                related.append({
                                    "path": doc_id,
                                    "title": Path(doc_id).stem,
                                    "similarity": similarity,
                                    "snippet": results["documents"][0][i][:300] if results["documents"] else "",
                                })
                                connections_found += 1

                    # Generate insight if we found connections and have LLM
                    if related and self._llm:
                        insight = await self._synthesize_insight(md_file.stem, content[:500], related)
                        llm_calls += 1

                        if insight and graft:
                            await self._graft_insight(md_file, insight, related)
                            insights_generated += 1

                except Exception as e:
                    logger.warning(f"Failed to find connections for {relative_path}: {e}")
                    continue

        # Save state
        state.last_run = datetime.now()
        self._save_state(state)

        duration = time.time() - start_time

        result = GardenRunResult(
            notes_processed=processed_count,
            connections_found=connections_found,
            insights_generated=insights_generated,
            duration_seconds=duration,
        )

        return AgentResponse(
            status="success",
            response=f"Garden run complete: {processed_count} notes processed, {connections_found} connections, {insights_generated} insights in {duration:.1f}s",
            data=result.model_dump(),
        )

    async def _initialize_llm(self) -> None:
        """Initialize LLM for insight synthesis."""
        from pandaemon.config import get_settings
        from pandaemon.kernel.llm import get_llm_client

        settings = get_settings()
        if settings.has_llm_provider():
            self._llm = get_llm_client()
            logger.info("Gardener LLM initialized")

    async def _synthesize_insight(
        self, title: str, content: str, related: list[dict[str, Any]]
    ) -> str | None:
        """Use LLM to synthesize an insight connecting related notes."""
        if not self._llm:
            return None

        from pandaemon.kernel.llm import Message

        # Build context
        related_context = "\n".join([
            f"- {r['title']}: {r['snippet'][:150]}..."
            for r in related[:3]  # Limit to 3 for context window
        ])

        prompt = f"""Given this note and its related notes, write a brief insight (1-2 sentences) about the conceptual connection between them.

Current note: {title}
Content excerpt: {content[:200]}...

Related notes:
{related_context}

Write only the insight, without preamble. Focus on the deeper conceptual relationship, not surface similarities."""

        try:
            response = await self._llm.complete(
                messages=[Message(role="user", content=prompt)],
                system="You are a knowledge synthesizer. Generate brief, insightful observations about connections between ideas.",
                temperature=0.7,
                max_tokens=150,
            )
            return response.content.strip()
        except Exception as e:
            logger.warning(f"Failed to synthesize insight: {e}")
            return None

    async def _graft_insight(
        self, note_path: Path, insight: str, related: list[dict[str, Any]]
    ) -> None:
        """Append an insight to a note as a Pandaemon comment."""
        try:
            content = note_path.read_text(encoding="utf-8")

            # Check if we already have a garden block
            if PANDAEMON_GARDEN_DELIMITER in content:
                # Update existing block
                parts = content.split(PANDAEMON_GARDEN_DELIMITER)
                content = parts[0].rstrip()  # Keep content before delimiter

            # Build garden block
            related_links = ", ".join([f"[[{r['title']}]]" for r in related[:3]])
            timestamp = datetime.now().strftime("%Y-%m-%d")

            garden_block = f"""

{PANDAEMON_GARDEN_DELIMITER}
*Connections discovered {timestamp}*

{insight}

Related: {related_links}
"""

            # Append to note
            note_path.write_text(content + garden_block, encoding="utf-8")
            logger.info(f"Grafted insight to: {note_path.name}")

        except Exception as e:
            logger.warning(f"Failed to graft insight to {note_path}: {e}")

    # ==================== Helper Methods ====================

    def _should_skip_file(self, path: Path) -> bool:
        """Check if a file should be skipped."""
        path_str = str(path)
        
        # Skip hidden files/folders
        if any(part.startswith(".") for part in path.parts):
            return True
        
        # Skip trash
        if ".trash" in path_str.lower():
            return True
        
        # Skip syncthing temp files
        if ".syncthing." in path_str and ".tmp" in path_str:
            return True
        
        # Skip locked files
        if path.with_suffix(path.suffix + ".lock").exists():
            return True
        
        return False

    def _hash_content(self, path: Path) -> str:
        """Generate a hash of file content."""
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()

    def _prepare_embed_text(self, title: str, content: str) -> str:
        """Prepare text for embedding (title + first 500 chars)."""
        # Remove YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        
        # Take first 500 chars
        content = content.strip()[:500]
        
        return f"{title}\n\n{content}"

    def _load_state(self) -> GardenerState:
        """Load gardener state from disk."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text())
                return GardenerState(**data)
            except Exception as e:
                logger.warning(f"Failed to load gardener state: {e}")
        
        return GardenerState(last_run=datetime.now())

    def _save_state(self, state: GardenerState) -> None:
        """Save gardener state to disk."""
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(state.model_dump_json(indent=2))
