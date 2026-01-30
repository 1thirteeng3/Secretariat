# Pandaemon

A cognitive daemon system that operates as a local-first AI assistant. Built in Python with FastAPI.

## Philosophy

Pandaemon is a **daemon** (not a chatbot) - it lives in your system, operates in the background, and acts as a cognitive extension of your digital workspace. It follows local-first principles: your data stays on your machine, with the server acting only as a processing node.

## Quick Start

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn src.pandaemon.main:app --reload --port 8000
```

## Architecture

- **Kernel (Clawdbot 2.0)**: Central router that classifies intent and dispatches to agents
- **Secretariat**: Manages Obsidian vault - creates, edits, and retrieves notes
- **Gardener**: Ontology daemon that finds semantic connections between notes
- **Remote DJ**: Spotify remote control (Phase 2)
- **Black Ops**: Web automation for hostile environments (Phase 2)

## Configuration

Set these environment variables in `.env`:

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Claude API key | Yes* |
| `GEMINI_API_KEY` | Google Gemini API key | Yes* |
| `OBSIDIAN_VAULT_PATH` | Path to your Obsidian vault | Yes |
| `VECTOR_DB_PATH` | Path for ChromaDB storage | No (default: `./data/vectors`) |

*At least one LLM provider key is required.

## License

MIT
