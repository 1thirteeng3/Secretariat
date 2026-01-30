"""Tests for utility functions."""

import tempfile
from pathlib import Path

from pandaemon.utils.files import atomic_write, acquire_lock, is_syncthing_temp, is_locked
from pandaemon.utils.sanitize import sanitize_for_llm, EMAIL_PATTERN, PHONE_PATTERN


class TestAtomicWrite:
    """Test atomic file writing."""

    def test_atomic_write_creates_file(self) -> None:
        """Test that atomic_write creates file correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            atomic_write(path, "Hello, World!")
            
            assert path.exists()
            assert path.read_text() == "Hello, World!"

    def test_atomic_write_creates_directories(self) -> None:
        """Test that atomic_write creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "dir" / "test.txt"
            atomic_write(path, "Nested content")
            
            assert path.exists()
            assert path.read_text() == "Nested content"

    def test_atomic_write_overwrites(self) -> None:
        """Test that atomic_write overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            atomic_write(path, "First content")
            atomic_write(path, "Second content")
            
            assert path.read_text() == "Second content"


class TestLocking:
    """Test file locking."""

    def test_acquire_and_release_lock(self) -> None:
        """Test basic lock acquire and release."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.touch()
            
            with acquire_lock(path) as locked:
                assert locked
                assert is_locked(path)
            
            assert not is_locked(path)

    def test_lock_prevents_double_acquire(self) -> None:
        """Test that locked files can't be re-locked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.touch()
            
            with acquire_lock(path) as first_lock:
                assert first_lock
                
                with acquire_lock(path) as second_lock:
                    # Second lock should fail
                    assert not second_lock


class TestSyncthingDetection:
    """Test Syncthing temp file detection."""

    def test_syncthing_temp_detection(self) -> None:
        """Test detecting Syncthing temporary files."""
        assert is_syncthing_temp(Path(".syncthing.file.md.tmp"))
        assert not is_syncthing_temp(Path("normal_file.md"))
        assert not is_syncthing_temp(Path(".hidden_file.md"))


class TestSanitization:
    """Test PII sanitization."""

    def test_email_sanitization(self) -> None:
        """Test email redaction."""
        text = "Contact me at john@example.com for more info."
        result = sanitize_for_llm(text)
        assert "[EMAIL_REDACTED]" in result
        assert "john@example.com" not in result

    def test_phone_sanitization(self) -> None:
        """Test phone number redaction."""
        text = "Call me at +1-555-123-4567 or 11 98765-4321."
        result = sanitize_for_llm(text)
        assert "[PHONE_REDACTED]" in result

    def test_ip_sanitization(self) -> None:
        """Test IP address redaction."""
        text = "Server is at 192.168.1.100 on port 8080."
        result = sanitize_for_llm(text)
        assert "[IP_REDACTED]" in result
        assert "192.168.1.100" not in result

    def test_credit_card_sanitization(self) -> None:
        """Test credit card redaction with explicit format."""
        # Note: The phone pattern can also match card-like numbers
        # This test verifies that the card pattern works on its own
        text = "Card: 1234-5678-9012-3456 is valid"
        result = sanitize_for_llm(text, redact_phones=False)
        assert "[CARD_REDACTED]" in result

    def test_ssn_sanitization(self) -> None:
        """Test SSN redaction."""
        text = "SSN: 123-45-6789"
        result = sanitize_for_llm(text)
        assert "[SSN_REDACTED]" in result

    def test_multiple_redactions(self) -> None:
        """Test multiple PII types in same text."""
        text = "Email: test@test.com, IP: 10.0.0.1, SSN: 123-45-6789"
        result = sanitize_for_llm(text)
        assert "[EMAIL_REDACTED]" in result
        assert "[IP_REDACTED]" in result
        assert "[SSN_REDACTED]" in result

    def test_selective_sanitization(self) -> None:
        """Test selective sanitization."""
        text = "Email: test@test.com, IP: 10.0.0.1"
        result = sanitize_for_llm(text, redact_ips=False)
        assert "[EMAIL_REDACTED]" in result
        assert "10.0.0.1" in result  # IP not redacted
