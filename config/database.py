"""
Database connection configuration
Handles Supabase client initialization and connection management
"""

from supabase import create_client, Client
from typing import Optional
import traceback

from config.settings import SUPABASE_URL, SUPABASE_KEY
from utils.logger import logger

# Global Supabase client instance (singleton pattern)
_supabase_client: Optional[Client] = None


def init_database() -> bool:
    """
    Initialize the Supabase database connection

    Returns:
        True if successful, False otherwise
    """
    global _supabase_client

    try:
        if _supabase_client is not None:
            logger.warning("Database already initialized")
            return True

        # Create Supabase client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Test connection by making a simple query
        # This will raise an exception if connection fails
        response = (
            _supabase_client.table("server_config")
            .select("guild_id")
            .limit(1)
            .execute()
        )

        logger.info("✓ Database connection established successfully")
        return True

    except Exception as e:
        logger.error(f"✗ Failed to initialize database connection: {e}")
        logger.error(traceback.format_exc())
        _supabase_client = None
        return False


def get_supabase_client() -> Client:
    """
    Get the Supabase client instance

    Returns:
        Supabase client instance

    Raises:
        RuntimeError: If database not initialized
    """
    global _supabase_client

    if _supabase_client is None:
        logger.error("Database not initialized. Call init_database() first.")
        raise RuntimeError("Database connection not initialized")

    return _supabase_client


def close_database() -> None:
    """
    Close the database connection
    Note: Supabase Python client doesn't require explicit closing,
    but this function is here for completeness and future use
    """
    global _supabase_client

    if _supabase_client is not None:
        logger.info("Closing database connection...")
        _supabase_client = None
        logger.info("✓ Database connection closed")


def test_connection() -> bool:
    """
    Test the database connection

    Returns:
        True if connection is working, False otherwise
    """
    try:
        client = get_supabase_client()

        # Try a simple query
        response = client.table("server_config").select("guild_id").limit(1).execute()

        logger.info("✓ Database connection test successful")
        return True

    except Exception as e:
        logger.error(f"✗ Database connection test failed: {e}")
        return False


def reset_connection() -> bool:
    """
    Reset the database connection (close and reinitialize)
    Useful for handling connection errors

    Returns:
        True if successful, False otherwise
    """
    logger.info("Resetting database connection...")
    close_database()
    return init_database()


# Database health check decorator
def with_db_retry(max_retries: int = 3):
    """
    Decorator to retry database operations on failure

    Args:
        max_retries: Maximum number of retry attempts
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )

                    if attempt < max_retries - 1:
                        # Try to reset connection
                        reset_connection()

            # All retries failed
            logger.error(f"Database operation failed after {max_retries} attempts")
            raise last_exception

        return wrapper

    return decorator


# Context manager for database operations
class DatabaseContext:
    """
    Context manager for database operations with automatic error handling

    Usage:
        async with DatabaseContext() as db:
            result = db.table('users').select('*').execute()
    """

    def __enter__(self):
        return get_supabase_client()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Database operation error: {exc_val}")
        return False  # Don't suppress exceptions
