"""
Button views for the Discord bot
Handles button interactions for authentication and logout
"""

import discord
import traceback
from discord.ui import Button, View
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from utils.logger import logger
from ui.embeds import create_success_embed, create_error_embed
from models.server_config import ServerConfigModel

if TYPE_CHECKING:
    from discord.ext import commands


class AuthView(View):
    """Persistent view for authentication buttons (Login only - signup removed)"""

    def __init__(self, bot: "commands.Bot"):
        super().__init__(timeout=None)  # Persistent view, no timeout
        self.bot = bot

    @discord.ui.button(
        label="Login",
        style=discord.ButtonStyle.blurple,
        custom_id="auth_login_button",
        emoji="🔑",
    )
    async def login_button(self, interaction: discord.Interaction, button: Button):
        """Handle login button click"""
        try:
            # Get the AuthCog and call handle_login
            auth_cog = self.bot.get_cog("AuthCog")
            if auth_cog:
                await auth_cog.handle_login(interaction)
            else:
                logger.error("AuthCog not found")
                await interaction.response.send_message(
                    "❌ Authentication system is not available. Please contact an administrator.",
                    ephemeral=True,
                )
        except Exception as e:
            logger.error(f"Error in login button: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again later.", ephemeral=True
                )


class LogoutConfirmationView(View):
    """View for logout confirmation with Yes/No buttons"""

    def __init__(self, roles_to_remove: list, bot: "commands.Bot"):
        super().__init__(timeout=60)  # 60 seconds to confirm
        self.roles_to_remove = roles_to_remove
        self.bot = bot
        self.value = None

    async def send_logout_log(
        self, guild: discord.Guild, member: discord.Member, roles_removed: list
    ):
        """Send logout log to logging channel"""
        try:
            config_model = ServerConfigModel()
            logging_channel_id = await config_model.get_logging_channel(guild.id)

            if logging_channel_id:
                channel = guild.get_channel(logging_channel_id)
                if channel:
                    # Create log embed
                    log_embed = discord.Embed(
                        title="🔒 User Logged Out",
                        color=discord.Color.orange(),
                        timestamp=datetime.now(timezone.utc),
                    )

                    log_embed.add_field(
                        name="👤 User",
                        value=f"{member.mention} (`{member.id}`)",
                        inline=False,
                    )
                    log_embed.add_field(
                        name="🗑️ Roles Removed",
                        value="\n".join(
                            [f"• {role.mention}" for role in roles_removed]
                        ),
                        inline=False,
                    )
                    log_embed.set_thumbnail(url=member.display_avatar.url)
                    log_embed.set_footer(
                        text=f"User: {member.name} • Guild: {guild.name}"
                    )
                    # log_embed.set_footer(text=f"User ID: {member.id}")

                    await channel.send(embed=log_embed)
        except Exception as e:
            logger.error(f"Error sending logout log: {e}")

    @discord.ui.button(
        label="Yes, Logout", style=discord.ButtonStyle.danger, emoji="✅"
    )
    async def confirm_logout(self, interaction: discord.Interaction, button: Button):
        """Handle logout confirmation"""
        try:
            guild = interaction.guild
            member = guild.get_member(interaction.user.id)

            if not member:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error", "Could not find your member information."
                    ),
                    ephemeral=True,
                )
                return

            # Store role names for logging
            role_names = [role.name for role in self.roles_to_remove]

            # Remove all roles
            try:
                await member.remove_roles(*self.roles_to_remove, reason="User logout")

                # Send success message
                embed = discord.Embed(
                    title="✅ Logged Out Successfully",
                    description="You have been logged out and your role(s) have been removed.",
                    color=discord.Color.green(),
                )

                embed.add_field(
                    name="🗑️ Removed Roles",
                    value="\n".join([f"• **{name}**" for name in role_names]),
                    inline=False,
                )

                embed.add_field(
                    name="🔑 Login Again",
                    value="You can login again anytime in the login channel to regain access.",
                    inline=False,
                )

                embed.set_footer(text="Your account data remains saved")

                await interaction.response.send_message(embed=embed, ephemeral=True)

                # Send logout log to Discord channel
                await self.send_logout_log(guild, member, self.roles_to_remove)

                logger.info(
                    f"User {member} (ID: {member.id}) logged out from guild {guild.name} (ID: {guild.id}). Removed roles: {role_names}"
                )

                # Disable all buttons after logout
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

            except discord.Forbidden:
                logger.error(
                    f"Missing permissions to remove roles from {member} in guild {guild.name}"
                )
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Permission Error",
                        "I don't have permission to remove your roles. Please contact an administrator.",
                    ),
                    ephemeral=True,
                )
            except Exception as role_error:
                logger.error(f"Error removing roles: {role_error}")
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error",
                        "An error occurred while removing your roles. Please try again or contact an administrator.",
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in logout confirmation: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "An unexpected error occurred."),
                    ephemeral=True,
                )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_logout(self, interaction: discord.Interaction, button: Button):
        """Handle logout cancellation"""
        try:
            embed = discord.Embed(
                title="❌ Logout Cancelled",
                description="You are still logged in. Your roles remain unchanged.",
                color=discord.Color.blue(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"User {interaction.user} cancelled logout in guild {interaction.guild.name}"
            )

            # Disable all buttons after cancellation
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            logger.error(f"Error in logout cancellation: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred.", ephemeral=True
                )

    async def on_timeout(self):
        """Handle timeout - disable all buttons"""
        for item in self.children:
            item.disabled = True


class LogoutView(View):
    """Persistent view for logout button"""

    def __init__(self):
        super().__init__(timeout=None)  # Persistent view, no timeout

    @discord.ui.button(
        label="Logout",
        style=discord.ButtonStyle.red,
        custom_id="logout_button",
        emoji="👋",
    )
    async def logout_button(self, interaction: discord.Interaction, button: Button):
        """Handle logout button click - shows confirmation"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            member = guild.get_member(interaction.user.id)
            if not member:
                await interaction.response.send_message(
                    "❌ Could not find your member information!", ephemeral=True
                )
                return

            # Get all roles except @everyone
            roles_to_remove = [
                role for role in member.roles if role.name != "@everyone"
            ]

            if not roles_to_remove:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Not Logged In",
                        "You don't have any roles to remove. You are not currently logged in.",
                    ),
                    ephemeral=True,
                )
                return

            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm Logout",
                description="Are you sure you want to logout?",
                color=discord.Color.orange(),
            )

            # List roles that will be removed
            role_list = "\n".join([f"• **{role.name}**" for role in roles_to_remove])
            embed.add_field(name="🗑️ Roles to be Removed", value=role_list, inline=False)

            embed.add_field(
                name="ℹ️ What happens when you logout?",
                value=(
                    "• Your roles will be removed\n"
                    "• You will lose access to role-restricted channels\n"
                    "• Your account data will remain saved\n"
                    "• You can login again anytime"
                ),
                inline=False,
            )

            embed.set_footer(text="You have 60 seconds to confirm")

            # Create confirmation view
            view = LogoutConfirmationView(roles_to_remove, interaction.client)

            # Send confirmation message
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

            logger.info(
                f"Logout confirmation shown to {interaction.user} in guild {guild.name}"
            )

        except Exception as e:
            logger.error(f"Error in logout button: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again later.", ephemeral=True
                )


# class LogoutView(discord.ui.View):
#     """View containing the logout button for users"""

#     def __init__(self):
#         super().__init__(timeout=None)

#     @discord.ui.button(
#         label="Logout",
#         style=discord.ButtonStyle.danger,
#         custom_id="persistent_logout_button",
#         emoji="🔒",
#     )
#     async def logout_button(
#         self, interaction: discord.Interaction, button: discord.ui.Button
#     ):
#         """Handles logout button click"""
#         try:
#             guild = interaction.guild
#             member = interaction.user

#             if not guild or not member:
#                 await interaction.response.send_message(
#                     embed=create_error_embed("Error", "Guild or user not found."),
#                     ephemeral=True,
#                 )
#                 return

#             # ✅ Remove all roles except @everyone
#             roles_to_remove = [r for r in member.roles if r.name != "@everyone"]

#             if not roles_to_remove:
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Error", "You don't have any roles to remove."
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             await member.remove_roles(*roles_to_remove, reason="User logout")
#             logger.info(f"Removed roles from {member} in guild {guild.name}")

#             # ✅ Show success message
#             success_embed = create_success_embed(
#                 "Successfully Logged Out",
#                 "All your assigned roles have been removed.\nYou can log in again anytime.",
#             )
#             await interaction.response.send_message(embed=success_embed, ephemeral=True)

#             # ✅ Record logout in database (call LogoutCog helper)
#             logout_cog = interaction.client.get_cog("LogoutCog")
#             if logout_cog:
#                 await logout_cog.record_logout(interaction)
#             else:
#                 logger.warning("LogoutCog not found while attempting to record logout.")

#         except Exception as e:
#             logger.error(f"Error in LogoutView: {e}\n{traceback.format_exc()}")
#             await interaction.response.send_message(
#                 embed=create_error_embed(
#                     "Error", "Unexpected error occurred during logout."
#                 ),
#                 ephemeral=True,
# )
