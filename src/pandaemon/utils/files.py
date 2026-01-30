"""File utility functions for atomic operations."""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """
    Write content to a file atomically.
    
    Uses temp file + rename pattern to ensure the file is never
    in a partially written state.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in same directory for atomic rename
    fd, temp_path = tempfile.mkstemp(
        suffix=".tmp",
        prefix=".pandaemon_",
        dir=path.parent,
    )
    
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        # Atomic rename
        os.replace(temp_path, path)
    except Exception:
        # Cleanup on failure
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


@contextmanager
def acquire_lock(path: Path, timeout: float = 5.0) -> Generator[bool, None, None]:
    """
    Acquire a lock for a file.
    
    Creates a .lock file and yields True if successful.
    Automatically releases on exit.
    
    Usage:
        with acquire_lock(file_path) as locked:
            if locked:
                # Do work
    """
    lock_path = path.with_suffix(path.suffix + ".lock")
    acquired = False
    
    try:
        # Try to create lock file exclusively
        if not lock_path.exists():
            lock_path.write_text(str(os.getpid()))
            acquired = True
        
        yield acquired
        
    finally:
        if acquired and lock_path.exists():
            lock_path.unlink()


def release_lock(path: Path) -> None:
    """Release a lock for a file."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    if lock_path.exists():
        lock_path.unlink()


def is_syncthing_temp(path: Path) -> bool:
    """Check if a file is a Syncthing temporary file."""
    name = path.name
    return name.startswith(".syncthing.") and name.endswith(".tmp")


def is_locked(path: Path) -> bool:
    """Check if a file has an active lock."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    return lock_path.exists()
