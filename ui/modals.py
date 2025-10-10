"""
Modal forms for user input
Handles signup and login form submissions
"""

import discord
from discord.ui import Modal, TextInput, Select, View
from discord import SelectOption
from typing import List, TYPE_CHECKING
import traceback
from datetime import datetime, timezone

from models.user import UserModel
from ui.embeds import (
    create_signup_success_embed,
    create_login_success_embed,
    create_error_embed,
)
from utils.logger import logger
from utils.helpers import validate_email, validate_full_name, sanitize_input

if TYPE_CHECKING:
    from cogs.auth import AuthCog


class LoginModal(Modal):
    """Modal form for user login"""

    def __init__(
        self, user_model: UserModel, guild: discord.Guild, auth_cog: "AuthCog"
    ):
        super().__init__(title="Login", timeout=300)

        self.user_model = user_model
        self.guild = guild
        self.auth_cog = auth_cog

        # Email input
        self.email_input = TextInput(
            label="Email",
            placeholder="your.email@example.com",
            min_length=5,
            max_length=255,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.email_input)

        # Password input
        self.password_input = TextInput(
            label="Password",
            placeholder="Enter your password",
            min_length=1,
            max_length=255,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.password_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle login form submission"""
        try:
            # Get and sanitize inputs
            email = sanitize_input(self.email_input.value.lower(), 255)
            password = self.password_input.value

            # Validate email format
            if not validate_email(email):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Email", "Please enter a valid email address."
                    ),
                    ephemeral=True,
                )
                return

            # Defer response as database operation might take time
            await interaction.response.defer(ephemeral=True, thinking=True)

            # Authenticate user
            user_data = await self.user_model.authenticate_user(
                guild_id=self.guild.id, email=email, password=password
            )

            if not user_data:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Login Failed",
                        "Invalid email or password. Please check your credentials and try again.\n\n"
                        "If you don't have an account, contact an administrator.",
                    ),
                    ephemeral=True,
                )
                return

            # Find the role in the guild
            designation = user_data["designation"]
            role = discord.utils.get(self.guild.roles, name=designation)

            if not role:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Role Not Found",
                        f"The role `{designation}` no longer exists in this server. Please contact an administrator.",
                    ),
                    ephemeral=True,
                )
                logger.warning(
                    f"Role {designation} not found in guild {self.guild.id} for user {email}"
                )
                return

            # NOW Assign role to user (only on login)
            try:
                member = self.guild.get_member(interaction.user.id)
                if not member:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Error",
                            "Could not find your member information. Please try again.",
                        ),
                        ephemeral=True,
                    )
                    return

                # Check if user already has this role
                if role in member.roles:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Already Logged In",
                            f"You already have the **{role.name}** role assigned!\n\n"
                            f"If you want to logout, go to the logout channel.",
                        ),
                        ephemeral=True,
                    )
                    return

                # Assign the role
                await member.add_roles(role, reason="User login")

                # UPDATE: Set Discord user ID if it's 0 (placeholder from admin creation)
                if user_data["discord_user_id"] == 0:
                    await self.user_model.update_user(
                        user_data["id"], {"discord_user_id": member.id}
                    )
                    logger.info(f"Updated Discord user ID for {email} to {member.id}")

                # Send success message to user
                embed = discord.Embed(
                    title="✅ Login Successful!",
                    description=f"Welcome back, **{user_data['full_name']}**!",
                    color=discord.Color.green(),
                )

                embed.add_field(
                    name="👔 Your Role",
                    value=f"{role.mention} - `{designation}`",
                    inline=False,
                )

                embed.add_field(
                    name="🎉 Access Granted",
                    value="Your role has been assigned successfully! You now have access to the server channels.",
                    inline=False,
                )

                embed.set_footer(text="Enjoy your stay!")

                await interaction.followup.send(embed=embed, ephemeral=True)

                # Log to Discord channel
                log_embed = discord.Embed(
                    title="🔓 User Logged In",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc),
                )

                log_embed.add_field(
                    name="👤 User",
                    value=f"{member.mention} (`{member.id}`)",
                    inline=False,
                )
                log_embed.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                log_embed.add_field(
                    name="👔 Role Assigned", value=role.mention, inline=True
                )
                log_embed.set_thumbnail(url=member.display_avatar.url)
                log_embed.set_footer(
                    text=f"User: {member.name} • Guild: {self.guild.name}"
                )
                # log_embed.set_footer(text=f"User ID: {member.id}")

                await self.auth_cog.send_log_message(self.guild, log_embed)

                logger.info(
                    f"User {interaction.user} (ID: {interaction.user.id}) logged in and received role {role.name} in guild {self.guild.id}"
                )

            except discord.Forbidden:
                logger.error(
                    f"Missing permissions to assign role {role.name} to {interaction.user}"
                )
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Permission Error",
                        "Login successful, but I couldn't assign your role. Please contact an administrator.\n\n"
                        "The bot may be missing the **Manage Roles** permission.",
                    ),
                    ephemeral=True,
                )
            except Exception as role_error:
                logger.error(
                    f"Error assigning role during login: {role_error}\n{traceback.format_exc()}"
                )
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Role Assignment Failed",
                        "Login successful, but there was an error assigning your role. Please contact an administrator.",
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in login modal: {e}\n{traceback.format_exc()}")
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error",
                        "An unexpected error occurred during login. Please try again later.",
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error",
                        "An unexpected error occurred during login. Please try again later.",
                    ),
                    ephemeral=True,
                )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle modal errors"""
        logger.error(f"Modal error: {error}\n{traceback.format_exc()}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error", "An unexpected error occurred. Please try again."
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error", "An unexpected error occurred. Please try again."
                    ),
                    ephemeral=True,
                )
        except:
            pass


# SignupModal removed since signup is now admin-only
# Users are created via /create_user command
