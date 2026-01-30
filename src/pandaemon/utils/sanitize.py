"""PII sanitization utilities for LLM calls."""

import re
from typing import Callable


# Regex patterns for PII
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.\s]?)?(?:\(?\d{2,3}\)?[-.\s]?)?\d{4,5}[-.\s]?\d{4}\b')
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
# Credit card: exactly 16 digits in 4 groups of 4, separated by dashes or spaces
CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b')


def sanitize_for_llm(
    text: str,
    redact_emails: bool = True,
    redact_phones: bool = True,
    redact_ips: bool = True,
    redact_ssn: bool = True,
    redact_credit_cards: bool = True,
) -> str:
    """
    Sanitize text before sending to external LLM APIs.
    
    Replaces PII with neutral tokens to protect user privacy.
    """
    if redact_emails:
        text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    
    if redact_phones:
        text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    
    if redact_ips:
        text = IP_PATTERN.sub("[IP_REDACTED]", text)
    
    if redact_ssn:
        text = SSN_PATTERN.sub("[SSN_REDACTED]", text)
    
    if redact_credit_cards:
        text = CREDIT_CARD_PATTERN.sub("[CARD_REDACTED]", text)
    
    return text


def create_sanitizer(*patterns: tuple[re.Pattern, str]) -> Callable[[str], str]:
    """
    Create a custom sanitizer with specified patterns.
    
    Args:
        patterns: Tuples of (regex_pattern, replacement_string)
    
    Returns:
        A function that sanitizes text using all patterns
    """
    def sanitize(text: str) -> str:
        for pattern, replacement in patterns:
            text = pattern.sub(replacement, text)
        return text
    
    return sanitize


# Pre-built sanitizer for common use case
default_sanitizer = create_sanitizer(
    (EMAIL_PATTERN, "[EMAIL]"),
    (PHONE_PATTERN, "[PHONE]"),
    (IP_PATTERN, "[IP]"),
    (SSN_PATTERN, "[SSN]"),
    (CREDIT_CARD_PATTERN, "[CARD]"),
)
