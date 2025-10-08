"""
Allowed Roles Model
Handles database operations for roles that users can select during signup
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import traceback

from config.database import get_supabase_client
from utils.logger import logger


class AllowedRolesModel:
    """Model for managing allowed signup roles"""

    def __init__(self):
        self.table_name = "allowed_roles"

    async def add_role(self, guild_id: int, role_id: int, role_name: str) -> bool:
        """
        Add a role to allowed roles list

        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID
            role_name: Role name

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            # Check if role already exists
            existing = await self.get_role(guild_id, role_id)
            if existing:
                logger.warning(
                    f"Role {role_name} already in allowed roles for guild {guild_id}"
                )
                return False

            # Insert role
            role_data = {
                "guild_id": guild_id,
                "role_id": role_id,
                "role_name": role_name,
                "created_at": datetime.utcnow().isoformat(),
            }

            response = supabase.table(self.table_name).insert(role_data).execute()

            if response.data:
                logger.info(
                    f"Added allowed role: {role_name} (ID: {role_id}) in guild {guild_id}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Error adding allowed role: {e}\n{traceback.format_exc()}")
            return False

    async def remove_role(self, guild_id: int, role_id: int) -> bool:
        """
        Remove a role from allowed roles list

        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .delete()
                .eq("guild_id", guild_id)
                .eq("role_id", role_id)
                .execute()
            )

            logger.info(f"Removed allowed role ID {role_id} from guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error removing allowed role: {e}\n{traceback.format_exc()}")
            return False

    async def get_role(self, guild_id: int, role_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific allowed role

        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID

        Returns:
            Role data if found, None otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .eq("role_id", role_id)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting allowed role: {e}\n{traceback.format_exc()}")
            return None

    async def get_all_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Get all allowed roles for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            List of role dictionaries
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .order("role_name")
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting allowed roles: {e}\n{traceback.format_exc()}")
            return []

    async def clear_all_roles(self, guild_id: int) -> bool:
        """
        Remove all allowed roles for a guild

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

            logger.info(f"Cleared all allowed roles for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error clearing allowed roles: {e}\n{traceback.format_exc()}")
            return False

    async def role_exists(self, guild_id: int, role_id: int) -> bool:
        """
        Check if a role is in allowed roles list

        Args:
            guild_id: Discord guild ID
            role_id: Discord role ID

        Returns:
            True if role exists, False otherwise
        """
        role = await self.get_role(guild_id, role_id)
        return role is not None
