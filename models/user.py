"""
User Model
Handles all database operations related to users
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import traceback

from config.database import get_supabase_client
from utils.logger import logger
from utils.helpers import generate_password, mask_email


class UserModel:
    """Model for user authentication and management"""

    def __init__(self):
        self.table_name = "users"

    async def create_user(
        self,
        guild_id: int,
        discord_user_id: int,
        full_name: str,
        email: str,
        designation: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new user in the database

        Args:
            guild_id: Discord guild ID
            discord_user_id: Discord user ID
            full_name: User's full name
            email: User's email address
            designation: User's role/designation

        Returns:
            Dictionary with user data including generated password, or None if failed
        """
        try:
            supabase = get_supabase_client()

            # Generate secure password
            password = generate_password()

            # Create user data
            user_data = {
                "guild_id": guild_id,
                "discord_user_id": discord_user_id,
                "full_name": full_name.strip(),
                "email": email.strip().lower(),
                "password": password,  # In production, this should be hashed
                "designation": designation.strip(),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Insert into database
            response = supabase.table(self.table_name).insert(user_data).execute()

            if response.data:
                logger.info(
                    f"User created successfully: {mask_email(email)} in guild {guild_id}"
                )

                # Return user data with password
                result = response.data[0]
                result["generated_password"] = password
                return result
            else:
                logger.error(f"Failed to create user: {mask_email(email)}")
                return None

        except Exception as e:
            # Check for unique constraint violations
            if "unique_email_per_guild" in str(e).lower():
                logger.warning(
                    f"User already exists with email {mask_email(email)} in guild {guild_id}"
                )
            elif "unique_user_per_guild" in str(e).lower():
                logger.warning(
                    f"Discord user {discord_user_id} already has an account in guild {guild_id}"
                )
            else:
                logger.error(f"Error creating user: {e}\n{traceback.format_exc()}")
            return None

    async def authenticate_user(
        self, guild_id: int, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with email and password

        Args:
            guild_id: Discord guild ID
            email: User's email address
            password: User's password

        Returns:
            User data if authentication successful, None otherwise
        """
        try:
            supabase = get_supabase_client()

            # Query user by guild_id and email
            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .eq("email", email.strip().lower())
                .execute()
            )

            if not response.data:
                logger.warning(
                    f"Login attempt failed: User not found - {mask_email(email)} in guild {guild_id}"
                )
                return None

            user = response.data[0]

            # Verify password (in production, use hashed password comparison)
            if user["password"] == password:
                # Update last login time
                await self._update_last_login(user["id"])

                logger.info(
                    f"User authenticated successfully: {mask_email(email)} in guild {guild_id}"
                )
                return user
            else:
                logger.warning(
                    f"Login attempt failed: Invalid password for {mask_email(email)} in guild {guild_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Error authenticating user: {e}\n{traceback.format_exc()}")
            return None

    async def get_user_by_email(
        self, guild_id: int, email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by email and guild ID

        Args:
            guild_id: Discord guild ID
            email: User's email address

        Returns:
            User data if found, None otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .eq("email", email.strip().lower())
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting user by email: {e}\n{traceback.format_exc()}")
            return None

    async def get_user_by_discord_id(
        self, guild_id: int, discord_user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by Discord user ID and guild ID

        Args:
            guild_id: Discord guild ID
            discord_user_id: Discord user ID

        Returns:
            User data if found, None otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .eq("discord_user_id", discord_user_id)
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(
                f"Error getting user by Discord ID: {e}\n{traceback.format_exc()}"
            )
            return None

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update user information

        Args:
            user_id: User's UUID
            update_data: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            # Add updated_at timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()

            response = (
                supabase.table(self.table_name)
                .update(update_data)
                .eq("id", user_id)
                .execute()
            )

            if response.data:
                logger.info(f"User updated successfully: {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating user: {e}\n{traceback.format_exc()}")
            return False

    async def delete_user(self, guild_id: int, discord_user_id: int) -> bool:
        """
        Delete a user from the database

        Args:
            guild_id: Discord guild ID
            discord_user_id: Discord user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .delete()
                .eq("guild_id", guild_id)
                .eq("discord_user_id", discord_user_id)
                .execute()
            )

            logger.info(
                f"User deleted: Discord ID {discord_user_id} from guild {guild_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Error deleting user: {e}\n{traceback.format_exc()}")
            return False

    async def get_all_users_in_guild(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Get all users in a specific guild

        Args:
            guild_id: Discord guild ID

        Returns:
            List of user dictionaries
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .select("*")
                .eq("guild_id", guild_id)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting users in guild: {e}\n{traceback.format_exc()}")
            return []

    async def _update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp (internal method)

        Args:
            user_id: User's UUID

        Returns:
            True if successful, False otherwise
        """
        try:
            supabase = get_supabase_client()

            response = (
                supabase.table(self.table_name)
                .update({"last_login": datetime.utcnow().isoformat()})
                .eq("id", user_id)
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False

    async def user_exists(
        self,
        guild_id: int,
        email: Optional[str] = None,
        discord_user_id: Optional[int] = None,
    ) -> bool:
        """
        Check if a user exists by email or Discord ID

        Args:
            guild_id: Discord guild ID
            email: User's email (optional)
            discord_user_id: Discord user ID (optional)

        Returns:
            True if user exists, False otherwise
        """
        try:
            if email:
                user = await self.get_user_by_email(guild_id, email)
                return user is not None

            if discord_user_id:
                user = await self.get_user_by_discord_id(guild_id, discord_user_id)
                return user is not None

            return False

        except Exception as e:
            logger.error(f"Error checking if user exists: {e}")
            return False
