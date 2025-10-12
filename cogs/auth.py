"""
Authentication Cog
Handles signup and login functionality with modals and button interactions
Multi-server compatible with dynamic channel configuration and role management
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import traceback
from datetime import datetime, timezone

from models.user import UserModel
from models.server_config import ServerConfigModel
from models.allowed_roles import AllowedRolesModel
from ui.views import AuthView
from ui.embeds import create_auth_embed, create_success_embed, create_error_embed
from ui.modals import LoginModal
from utils.logger import logger
from utils.helpers import mask_email


class AuthCog(commands.Cog):
    """Cog for handling authentication (signup/login)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_model = UserModel()
        self.config_model = ServerConfigModel()
        self.roles_model = AllowedRolesModel()
        logger.info("AuthCog initialized")

    async def send_log_message(self, guild: discord.Guild, embed: discord.Embed):
        """
        Send a log message to the configured logging channel

        Args:
            guild: Discord guild
            embed: Embed to send
        """
        try:
            logging_channel_id = await self.config_model.get_logging_channel(guild.id)
            if logging_channel_id:
                channel = guild.get_channel(logging_channel_id)
                if channel:
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending log message: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Setup persistent views when bot is ready"""
        # Add persistent view for auth buttons
        self.bot.add_view(AuthView(self.bot))
        logger.info("Auth persistent views registered")

    @app_commands.command(
        name="set_logging_channel",
        description="Set the logging channel for login/logout events (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="The channel for login/logout logs")
    async def set_logging_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        """
        Set the logging channel for authentication events
        Only administrators can use this command

        Args:
            channel: The text channel to use for logs
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Save channel configuration
            success = await self.config_model.set_logging_channel(guild.id, channel.id)

            if success:
                await interaction.response.send_message(
                    f"✅ Logging channel set to {channel.mention}\n\n"
                    f"All login and logout events will be logged here.",
                    ephemeral=True,
                )
                logger.info(
                    f"Logging channel set to {channel.name} (ID: {channel.id}) in guild {guild.name} by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to save channel configuration. Please try again.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in set_logging_channel: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while setting the logging channel.",
                    ephemeral=True,
                )

    @app_commands.command(
        name="add_signup_role",
        description="Add a role that users can select during signup (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="The role to add to signup options")
    async def add_signup_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        """Add a role to signup options"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            if role.name == "@everyone":
                await interaction.response.send_message(
                    "❌ Cannot add @everyone!", ephemeral=True
                )
                return

            if role.managed:
                await interaction.response.send_message(
                    "❌ Cannot add bot/integration managed roles!", ephemeral=True
                )
                return

            if role.permissions.administrator:
                await interaction.response.send_message(
                    "❌ Cannot add administrator roles!", ephemeral=True
                )
                return

            if role.position >= guild.me.top_role.position:
                await interaction.response.send_message(
                    "❌ This role is higher than or equal to my highest role!",
                    ephemeral=True,
                )
                return

            success = await self.roles_model.add_role(guild.id, role.id, role.name)

            if success:
                await interaction.response.send_message(
                    f"✅ Added **{role.name}** to signup role options!", ephemeral=True
                )
                logger.info(
                    f"Role {role.name} added to signup options in guild {guild.name} by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    f"❌ **{role.name}** is already in the signup role list!",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in add_signup_role: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="remove_signup_role",
        description="Remove a role from signup options (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="The role to remove")
    async def remove_signup_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        """Remove a role from signup options"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            success = await self.roles_model.remove_role(guild.id, role.id)

            if success:
                await interaction.response.send_message(
                    f"✅ Removed **{role.name}** from signup role options!",
                    ephemeral=True,
                )
                logger.info(
                    f"Role {role.name} removed from signup options in guild {guild.name} by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    f"❌ Failed to remove **{role.name}**.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in remove_signup_role: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="list_signup_roles",
        description="List all available signup roles (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    async def list_signup_roles(self, interaction: discord.Interaction):
        """List all signup roles"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            roles_data = await self.roles_model.get_all_roles(guild.id)

            if not roles_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Signup Roles Configured",
                        "No roles have been added yet.\n\nUse `/add_signup_role` to add roles.",
                    ),
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="📋 Available Signup Roles",
                description=f"Users can select from these roles:",
                color=discord.Color.blue(),
            )

            role_list = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    role_list.append(f"• {role.mention} - `{role.name}`")
                else:
                    role_list.append(f"• ~~{role_data['role_name']}~~ (Deleted)")

            embed.add_field(
                name=f"Roles ({len(roles_data)})",
                value="\n".join(role_list),
                inline=False,
            )

            embed.set_footer(text=f"Server: {guild.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in list_signup_roles: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="clear_signup_roles", description="Remove all signup roles (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def clear_signup_roles(self, interaction: discord.Interaction):
        """Clear all signup roles"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            roles_data = await self.roles_model.get_all_roles(guild.id)
            count = len(roles_data)

            if count == 0:
                await interaction.response.send_message(
                    "❌ No signup roles to clear!", ephemeral=True
                )
                return

            success = await self.roles_model.clear_all_roles(guild.id)

            if success:
                await interaction.response.send_message(
                    f"✅ Cleared **{count}** signup role(s)!", ephemeral=True
                )
                logger.info(
                    f"All signup roles cleared in guild {guild.name} by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to clear roles.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in clear_signup_roles: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="set_login_channel",
        description="Set the login/signup channel (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="The channel to use for login")
    async def set_login_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        """Set the login channel"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            success = await self.config_model.set_login_channel(guild.id, channel.id)

            if success:
                await interaction.response.send_message(
                    f"✅ Login channel set to {channel.mention}\n\n"
                    f"📝 **Next steps:**\n"
                    f"1. Add signup roles with `/add_signup_role`\n"
                    f"2. Use `/setup_auth` in {channel.mention}",
                    ephemeral=True,
                )
                logger.info(
                    f"Login channel set to {channel.name} in guild {guild.name} by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to save configuration.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in set_login_channel: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="setup_auth", description="Setup authentication embed (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_auth(self, interaction: discord.Interaction):
        """Setup authentication embed - Login only (Signup is now private)"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            login_channel_id = await self.config_model.get_login_channel(guild.id)

            if not login_channel_id:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Channel Not Configured",
                        "Please use `/set_login_channel` first.",
                    ),
                    ephemeral=True,
                )
                return

            if interaction.channel_id != login_channel_id:
                channel = guild.get_channel(login_channel_id)
                channel_mention = (
                    channel.mention if channel else f"<#{login_channel_id}>"
                )
                await interaction.response.send_message(
                    f"❌ This command must be used in {channel_mention}", ephemeral=True
                )
                return

            roles_data = await self.roles_model.get_all_roles(guild.id)

            if not roles_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Signup Roles Configured",
                        "Please add roles with `/add_signup_role` first.",
                    ),
                    ephemeral=True,
                )
                return

            valid_roles = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    valid_roles.append(role)

            if not valid_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Roles Not Found", "Configured roles no longer exist."
                    ),
                    ephemeral=True,
                )
                return

            # Create embed - Login Only
            embed = discord.Embed(
                title="🔐 Authentication Portal",
                description=(
                    "Welcome! Please login to access the server.\n\n"
                    "**Existing User?** Click **Login** to access your account.\n\n"
                    "**New User?** Contact an administrator to create your account."
                ),
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="🔑 Login",
                value="Access your account with email and password",
                inline=False,
            )

            roles_list = "\n".join([f"• {role.mention}" for role in valid_roles[:10]])
            if len(valid_roles) > 10:
                roles_list += f"\n... and {len(valid_roles) - 10} more"

            embed.add_field(name="📋 Available Roles", value=roles_list, inline=False)

            embed.set_footer(
                text="Your privacy is important • All data is securely stored"
            )

            # Create view with only Login button (no signup)
            view = AuthView(self.bot)

            await interaction.response.send_message(embed=embed, view=view)

            logger.info(
                f"Auth embed setup by {interaction.user} in guild {guild.name} with {len(valid_roles)} roles"
            )

        except Exception as e:
            logger.error(f"Error in setup_auth: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="view_config", description="View current bot configuration (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def view_config(self, interaction: discord.Interaction):
        """View bot configuration"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            login_channel_id = await self.config_model.get_login_channel(guild.id)
            logout_channel_id = await self.config_model.get_logout_channel(guild.id)
            logging_channel_id = await self.config_model.get_logging_channel(guild.id)
            roles_data = await self.roles_model.get_all_roles(guild.id)

            embed = discord.Embed(
                title="🔧 Bot Configuration",
                description=f"Current configuration for **{guild.name}**",
                color=discord.Color.blue(),
            )

            # Login channel
            if login_channel_id:
                channel = guild.get_channel(login_channel_id)
                login_text = (
                    channel.mention if channel else f"<#{login_channel_id}> (Not found)"
                )
            else:
                login_text = "❌ Not configured"
            embed.add_field(name="📝 Login Channel", value=login_text, inline=False)

            # Logout channel
            if logout_channel_id:
                channel = guild.get_channel(logout_channel_id)
                logout_text = (
                    channel.mention
                    if channel
                    else f"<#{logout_channel_id}> (Not found)"
                )
            else:
                logout_text = "❌ Not configured"
            embed.add_field(name="👋 Logout Channel", value=logout_text, inline=False)

            # Logging channel
            if logging_channel_id:
                channel = guild.get_channel(logging_channel_id)
                logging_text = (
                    channel.mention
                    if channel
                    else f"<#{logging_channel_id}> (Not found)"
                )
            else:
                logging_text = "❌ Not configured"
            embed.add_field(name="📊 Logging Channel", value=logging_text, inline=False)

            # Signup roles
            if roles_data:
                role_list = []
                for role_data in roles_data[:10]:
                    role = guild.get_role(role_data["role_id"])
                    if role:
                        role_list.append(f"• {role.mention}")
                    else:
                        role_list.append(f"• ~~{role_data['role_name']}~~ (Deleted)")

                if len(roles_data) > 10:
                    role_list.append(f"... and {len(roles_data) - 10} more")

                roles_text = "\n".join(role_list)
            else:
                roles_text = "❌ No roles configured"

            embed.add_field(
                name=f"📋 Signup Roles ({len(roles_data)})",
                value=roles_text,
                inline=False,
            )

            # Instructions
            instructions = []
            if not login_channel_id:
                instructions.append(
                    "• Use `/set_login_channel` to configure login channel"
                )
            if not logout_channel_id:
                instructions.append(
                    "• Use `/set_logout_channel` to configure logout channel"
                )
            if not logging_channel_id:
                instructions.append(
                    "• Use `/set_logging_channel` to configure logging channel"
                )
            if not roles_data:
                instructions.append("• Use `/add_signup_role` to add roles")

            if instructions:
                embed.add_field(
                    name="📝 Next Steps", value="\n".join(instructions), inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="All configured! Use `/setup_auth` and `/setup_logout`.",
                    inline=False,
                )

            # embed.set_footer(text=f"Guild ID: {guild.id}")
            embed.set_footer(text=f"Guild ID: {guild.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in view_config: {e}\n{traceback.format_exc()}")

    async def handle_signup(self, interaction: discord.Interaction):
        """
        Handle signup button click - REMOVED (signup is now admin-only)
        This method is kept for backwards compatibility but shows error
        """
        try:
            await interaction.response.send_message(
                embed=create_error_embed(
                    "Signup Unavailable",
                    "Public signup has been disabled.\n\n"
                    "**To get an account:**\n"
                    "Contact a server administrator. They can create an account for you using `/create_user`.",
                ),
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error in handle_signup: {e}\n{traceback.format_exc()}")

    async def handle_login(self, interaction: discord.Interaction):
        """Handle login button click"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            member = guild.get_member(interaction.user.id)
            if not member:
                await interaction.response.send_message(
                    "❌ Could not find your member information!", ephemeral=True
                )
                return

            user_roles = [role for role in member.roles if role.name != "@everyone"]

            if user_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Already Logged In",
                        f"You already have the **{user_roles[0].name}** role!\n\nNo need to login.",
                    ),
                    ephemeral=True,
                )
                return

            modal = LoginModal(self.user_model, guild, self)
            await interaction.response.send_modal(modal)

            logger.info(
                f"Login modal shown to {interaction.user} in guild {guild.name}"
            )

        except Exception as e:
            logger.error(f"Error in handle_login: {e}\n{traceback.format_exc()}")


async def setup(bot: commands.Bot):
    """Required setup function for loading the cog"""
    await bot.add_cog(AuthCog(bot))
    logger.info("AuthCog loaded successfully")
