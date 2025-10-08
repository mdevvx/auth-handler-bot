"""
Helper utility functions for the Discord bot
Includes password generation, validation, and other common operations
"""

import secrets
import string
import re
from typing import Optional


def generate_password(length: int = 12) -> str:
    """
    Generate a secure random password

    Args:
        length: Password length (default: 12)

    Returns:
        Random password string
    """
    # Ensure password has mix of characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"

    # Generate password
    password = "".join(secrets.choice(alphabet) for _ in range(length))

    # Ensure it has at least one of each type
    if (
        any(c.islower() for c in password)
        and any(c.isupper() for c in password)
        and any(c.isdigit() for c in password)
    ):
        return password
    else:
        # Recursively try again if criteria not met
        return generate_password(length)


def validate_email(email: str) -> bool:
    """
    Validate email format using regex

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False

    # RFC 5322 compliant email regex (simplified)
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    return re.match(pattern, email.strip()) is not None


def validate_full_name(name: str) -> bool:
    """
    Validate full name format

    Args:
        name: Full name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name.strip()) < 2:
        return False

    # Should contain at least letters and spaces
    pattern = r"^[a-zA-Z\s\'-]{2,100}$"

    return re.match(pattern, name.strip()) is not None


def sanitize_input(text: str, max_length: int = 100) -> str:
    """
    Sanitize user input by removing excessive whitespace and limiting length

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove leading/trailing whitespace and limit length
    sanitized = text.strip()[:max_length]

    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)

    return sanitized


def format_role_name(designation: str) -> str:
    """
    Format designation into a consistent role name

    Args:
        designation: User's designation

    Returns:
        Formatted role name
    """
    return sanitize_input(designation).title()


def mask_email(email: str) -> str:
    """
    Mask email for privacy in logs
    Example: john.doe@example.com -> j***e@example.com

    Args:
        email: Email to mask

    Returns:
        Masked email string
    """
    if not email or "@" not in email:
        return "***"

    local, domain = email.split("@", 1)

    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

    return f"{masked_local}@{domain}"


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string to specified length with suffix

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
