"""
Config package initialization
Exports configuration settings and database utilities
"""

from .settings import (
    DISCORD_TOKEN,
    SUPABASE_URL,
    SUPABASE_KEY,
    LOG_LEVEL,
    PASSWORD_LENGTH,
    CONFIG,
    get_config,
    print_config,
    validate_config,
)

from .database import (
    init_database,
    get_supabase_client,
    close_database,
    test_connection,
    reset_connection,
    with_db_retry,
    DatabaseContext,
)

__all__ = [
    # Settings
    "DISCORD_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "LOG_LEVEL",
    "PASSWORD_LENGTH",
    "CONFIG",
    "get_config",
    "print_config",
    "validate_config",
    # Database
    "init_database",
    "get_supabase_client",
    "close_database",
    "test_connection",
    "reset_connection",
    "with_db_retry",
    "DatabaseContext",
]
