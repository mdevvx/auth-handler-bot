"""
Server Configuration Model
Handles database operations for server-specific configurations
"""

from typing import Optional, Dict, Any
from datetime import datetime
import traceback

from config.database import get_supabase_client
from utils.logger import logger


class ServerConfigModel:
    """Model for server configuration management"""

    def __init__(self):
        self.table_name = "server_config"

    async def get_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific guild

        Args:
            guild_id: Discord guild ID

        Returns:
            Configuration dictionary if found, None otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting server config: {e}\n{traceback.format_exc()}")
            return None

    async def create_or_update_config(
        self, guild_id: int, config_data: Dict[str, Any]
    ) -> bool:
        """
        Create or update server configuration

        Args:
            guild_id: Discord guild ID
            config_data: Configuration data to save

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            # Check if config exists
            existing = await self.get_config(guild_id)

            config_data["updated_at"] = datetime.utcnow().isoformat()

            if existing:
                # Update existing config
                response = (
                    supabase.table(self.table_name)
                    .update(config_data)
                    .eq("guild_id", guild_id)
                    .execute()
                )
            else:
                # Create new config
                config_data["guild_id"] = guild_id
                config_data["created_at"] = datetime.utcnow().isoformat()
                response = supabase.table(self.table_name).insert(config_data).execute()

            if response.data:
                logger.info(f"Server config saved for guild {guild_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error saving server config: {e}\n{traceback.format_exc()}")
            return False

    async def set_login_channel(self, guild_id: int, channel_id: int) -> bool:
        """
        Set the login/signup channel for a guild

        Args:
            guild_id: Discord guild ID
            channel_id: Channel ID to set

        Returns:
            True if successful, False otherwise
        """
        return await self.create_or_update_config(
            guild_id, {"login_channel_id": channel_id}
        )

    async def set_logout_channel(self, guild_id: int, channel_id: int) -> bool:
        """
        Set the logout channel for a guild

        Args:
            guild_id: Discord guild ID
            channel_id: Channel ID to set

        Returns:
            True if successful, False otherwise
        """
        return await self.create_or_update_config(
            guild_id, {"logout_channel_id": channel_id}
        )

    async def get_login_channel(self, guild_id: int) -> Optional[int]:
        """
        Get the login channel ID for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            Channel ID if set, None otherwise
        """
        config = await self.get_config(guild_id)
        return config["login_channel_id"] if config else None

    async def get_logout_channel(self, guild_id: int) -> Optional[int]:
        """
        Get the logout channel ID for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            Channel ID if set, None otherwise
        """
        config = await self.get_config(guild_id)
        return config["logout_channel_id"] if config else None

    async def delete_config(self, guild_id: int) -> bool:
        """
        Delete server configuration (useful when bot leaves a server)

        Args:
            guild_id: Discord guild ID

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .delete()
                .eq("guild_id", guild_id)
                .execute()
            )

            logger.info(f"Server config deleted for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting server config: {e}\n{traceback.format_exc()}")
            return False
