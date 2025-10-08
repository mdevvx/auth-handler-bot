"""
Bot configuration settings
Loads environment variables and provides centralized configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

# Discord Configuration
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is required in .env file")

# Supabase Configuration
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY are required in .env file")

# Bot Configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
PASSWORD_LENGTH: int = int(os.getenv("PASSWORD_LENGTH", "12"))


# Validate configuration
def validate_config() -> bool:
    """
    Validate that all required configuration values are set

    Returns:
        True if valid, raises ValueError if not
    """
    errors = []

    if not DISCORD_TOKEN:
        errors.append("DISCORD_TOKEN is missing")

    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is missing")

    if not SUPABASE_KEY:
        errors.append("SUPABASE_KEY is missing")

    if PASSWORD_LENGTH < 8:
        errors.append("PASSWORD_LENGTH must be at least 8 characters")

    if LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        errors.append(f"Invalid LOG_LEVEL: {LOG_LEVEL}")

    if errors:
        raise ValueError(
            f"Configuration errors:\n" + "\n".join(f"  - {error}" for error in errors)
        )

    return True


# Validate on import
validate_config()

# Export configuration as a dictionary for easy access
CONFIG = {
    "discord_token": DISCORD_TOKEN,
    "supabase_url": SUPABASE_URL,
    "supabase_key": SUPABASE_KEY,
    "log_level": LOG_LEVEL,
    "password_length": PASSWORD_LENGTH,
}


def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a configuration value by key

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    return CONFIG.get(key, default)


def print_config(hide_sensitive: bool = True) -> None:
    """
    Print current configuration (for debugging)

    Args:
        hide_sensitive: Whether to hide sensitive values like tokens and keys
    """
    print("\n" + "=" * 50)
    print("BOT CONFIGURATION")
    print("=" * 50)

    for key, value in CONFIG.items():
        if hide_sensitive and key in ["discord_token", "supabase_key"]:
            # Show only first and last 4 characters
            if value and len(value) > 8:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "****"
            print(f"{key:20s}: {masked}")
        else:
            print(f"{key:20s}: {value}")

    print("=" * 50 + "\n")
