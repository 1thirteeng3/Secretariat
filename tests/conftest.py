"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_vault() -> Generator[Path, None, None]:
    """Create a temporary Obsidian vault for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "TestVault"
        vault_path.mkdir()
        
        # Create standard folders
        (vault_path / "Inbox").mkdir()
        (vault_path / "Projects").mkdir()
        (vault_path / "Notes").mkdir()
        
        yield vault_path


@pytest.fixture
def temp_vector_db() -> Generator[Path, None, None]:
    """Create a temporary vector database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_note_content() -> str:
    """Sample note content for testing."""
    return """This is a test note about quantum physics and thermodynamics.

The second law of thermodynamics states that entropy always increases.
Quantum entanglement connects particles across space.

Related concepts: energy, matter, physics, science
"""


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set mock environment variables for testing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/test-vault")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
