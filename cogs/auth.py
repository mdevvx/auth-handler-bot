# """
# Authentication Cog
# Handles signup and login functionality with modals and button interactions
# Multi-server compatible with dynamic channel configuration
# """

# import discord
# from discord.ext import commands
# from discord import app_commands
# from typing import Optional
# import traceback

# from models.user import UserModel
# from models.server_config import ServerConfigModel
# from ui.views import AuthView
# from ui.embeds import create_auth_embed, create_success_embed, create_error_embed
# from ui.modals import SignupModal, LoginModal
# from utils.logger import logger
# from utils.helpers import mask_email


# class AuthCog(commands.Cog):
#     """Cog for handling authentication (signup/login)"""

#     def __init__(self, bot: commands.Bot):
#         self.bot = bot
#         self.user_model = UserModel()
#         self.config_model = ServerConfigModel()
#         logger.info("AuthCog initialized")

#     @commands.Cog.listener()
#     async def on_ready(self):
#         """Setup persistent views when bot is ready"""
#         # Add persistent view for auth buttons
#         self.bot.add_view(AuthView(self.bot))
#         logger.info("Auth persistent views registered")

#     @app_commands.command(
#         name="set_login_channel",
#         description="Set the login/signup channel (Admin only)",
#     )
#     @app_commands.default_permissions(administrator=True)
#     @app_commands.describe(channel="The channel to use for login and signup")
#     async def set_login_channel(
#         self, interaction: discord.Interaction, channel: discord.TextChannel
#     ):
#         """
#         Set the login/signup channel for this server
#         Only administrators can use this command

#         Args:
#             channel: The text channel to set as login/signup channel
#         """
#         try:
#             guild = interaction.guild
#             if not guild:
#                 await interaction.response.send_message(
#                     "❌ This command can only be used in a server!", ephemeral=True
#                 )
#                 return

#             # Save channel configuration
#             success = await self.config_model.set_login_channel(guild.id, channel.id)

#             if success:
#                 await interaction.response.send_message(
#                     f"✅ Login/Signup channel set to {channel.mention}\n\n"
#                     f"Now use `/setup_auth` in that channel to create the authentication embed.",
#                     ephemeral=True,
#                 )
#                 logger.info(
#                     f"Login channel set to {channel.name} (ID: {channel.id}) in guild {guild.name} (ID: {guild.id}) by {interaction.user}"
#                 )
#             else:
#                 await interaction.response.send_message(
#                     "❌ Failed to save channel configuration. Please try again.",
#                     ephemeral=True,
#                 )
#                 logger.error(f"Failed to set login channel for guild {guild.id}")

#         except Exception as e:
#             logger.error(f"Error in set_login_channel: {e}\n{traceback.format_exc()}")
#             if not interaction.response.is_done():
#                 await interaction.response.send_message(
#                     "❌ An error occurred while setting the login channel.",
#                     ephemeral=True,
#                 )

#     @app_commands.command(
#         name="setup_auth", description="Setup authentication embed (Admin only)"
#     )
#     @app_commands.default_permissions(administrator=True)
#     async def setup_auth(self, interaction: discord.Interaction):
#         """
#         Setup the authentication embed with login/signup buttons
#         Only administrators can use this command
#         Must be used in the configured login/signup channel
#         """
#         try:
#             guild = interaction.guild
#             if not guild:
#                 await interaction.response.send_message(
#                     "❌ This command can only be used in a server!", ephemeral=True
#                 )
#                 return

#             # Get configured login channel
#             login_channel_id = await self.config_model.get_login_channel(guild.id)

#             if not login_channel_id:
#                 await interaction.response.send_message(
#                     "❌ No login/signup channel has been configured for this server!\n\n"
#                     "Please use `/set_login_channel` first to set the login channel.",
#                     ephemeral=True,
#                 )
#                 return

#             # Check if in correct channel
#             if interaction.channel_id != login_channel_id:
#                 channel = guild.get_channel(login_channel_id)
#                 channel_mention = (
#                     channel.mention if channel else f"<#{login_channel_id}>"
#                 )
#                 await interaction.response.send_message(
#                     f"❌ This command can only be used in the configured login channel: {channel_mention}",
#                     ephemeral=True,
#                 )
#                 return

#             # Create embed
#             embed = create_auth_embed()

#             # Create view with buttons
#             view = AuthView(self.bot)

#             # Send embed with buttons
#             await interaction.response.send_message(embed=embed, view=view)

#             logger.info(
#                 f"Auth embed setup by {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id})"
#             )

#         except Exception as e:
#             logger.error(f"Error in setup_auth: {e}\n{traceback.format_exc()}")
#             if not interaction.response.is_done():
#                 await interaction.response.send_message(
#                     "❌ An error occurred while setting up authentication.",
#                     ephemeral=True,
#                 )

#     @app_commands.command(
#         name="view_config", description="View current bot configuration (Admin only)"
#     )
#     @app_commands.default_permissions(administrator=True)
#     async def view_config(self, interaction: discord.Interaction):
#         """
#         View the current bot configuration for this server
#         Only administrators can use this command
#         """
#         try:
#             guild = interaction.guild
#             if not guild:
#                 await interaction.response.send_message(
#                     "❌ This command can only be used in a server!", ephemeral=True
#                 )
#                 return

#             # Get configuration
#             login_channel_id = await self.config_model.get_login_channel(guild.id)
#             logout_channel_id = await self.config_model.get_logout_channel(guild.id)

#             # Create embed
#             embed = discord.Embed(
#                 title="🔧 Bot Configuration",
#                 description=f"Current configuration for **{guild.name}**",
#                 color=discord.Color.blue(),
#             )

#             # Login channel
#             if login_channel_id:
#                 channel = guild.get_channel(login_channel_id)
#                 login_text = (
#                     channel.mention
#                     if channel
#                     else f"<#{login_channel_id}> (Channel not found)"
#                 )
#             else:
#                 login_text = "Not configured"
#             embed.add_field(name="Login/Signup Channel", value=login_text, inline=False)

#             # Logout channel
#             if logout_channel_id:
#                 channel = guild.get_channel(logout_channel_id)
#                 logout_text = (
#                     channel.mention
#                     if channel
#                     else f"<#{logout_channel_id}> (Channel not found)"
#                 )
#             else:
#                 logout_text = "Not configured"
#             embed.add_field(name="Logout Channel", value=logout_text, inline=False)

#             # Instructions
#             instructions = []
#             if not login_channel_id:
#                 instructions.append(
#                     "• Use `/set_login_channel` to configure login/signup channel"
#                 )
#             if not logout_channel_id:
#                 instructions.append(
#                     "• Use `/set_logout_channel` to configure logout channel"
#                 )

#             if instructions:
#                 embed.add_field(
#                     name="Next Steps", value="\n".join(instructions), inline=False
#                 )

#             embed.set_footer(text=f"Guild ID: {guild.id}")

#             await interaction.response.send_message(embed=embed, ephemeral=True)

#         except Exception as e:
#             logger.error(f"Error in view_config: {e}\n{traceback.format_exc()}")
#             if not interaction.response.is_done():
#                 await interaction.response.send_message(
#                     "❌ An error occurred while viewing configuration.", ephemeral=True
#                 )

#     async def handle_signup(self, interaction: discord.Interaction):
#         """
#         Handle signup button click - shows signup modal

#         Args:
#             interaction: Discord interaction from button click
#         """
#         try:
#             guild = interaction.guild
#             if not guild:
#                 await interaction.response.send_message(
#                     "❌ This command can only be used in a server!", ephemeral=True
#                 )
#                 return

#             member = guild.get_member(interaction.user.id)
#             if not member:
#                 await interaction.response.send_message(
#                     "❌ Could not find your member information!", ephemeral=True
#                 )
#                 return

#             # Check if user already has a role (already signed up)
#             user_roles = [role for role in member.roles if role.name != "@everyone"]

#             if user_roles:
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Already Registered",
#                         "You already have a role assigned. Please contact an administrator if you need to update your information.",
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             # Get all available roles (excluding @everyone and bot roles)
#             available_roles = [
#                 role
#                 for role in guild.roles
#                 if role.name != "@everyone"
#                 and not role.managed  # Exclude bot roles
#                 and not role.permissions.administrator  # Exclude admin roles
#                 and role.position
#                 < guild.me.top_role.position  # Only roles bot can assign
#             ]

#             if not available_roles:
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "No Roles Available",
#                         "There are no roles available for signup. Please contact an administrator.",
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             # Show signup modal with guild_id
#             modal = SignupModal(self.user_model, available_roles, guild.id)
#             await interaction.response.send_modal(modal)

#             logger.info(
#                 f"Signup modal shown to {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id})"
#             )

#         except Exception as e:
#             logger.error(f"Error in handle_signup: {e}\n{traceback.format_exc()}")
#             if not interaction.response.is_done():
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Error", "An unexpected error occurred. Please try again later."
#                     ),
#                     ephemeral=True,
#                 )

#     async def handle_login(self, interaction: discord.Interaction):
#         """
#         Handle login button click - shows login modal

#         Args:
#             interaction: Discord interaction from button click
#         """
#         try:
#             guild = interaction.guild
#             if not guild:
#                 await interaction.response.send_message(
#                     "❌ This command can only be used in a server!", ephemeral=True
#                 )
#                 return

#             member = guild.get_member(interaction.user.id)
#             if not member:
#                 await interaction.response.send_message(
#                     "❌ Could not find your member information!", ephemeral=True
#                 )
#                 return

#             # Check if user already has a role (already logged in)
#             user_roles = [role for role in member.roles if role.name != "@everyone"]

#             if user_roles:
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Already Logged In",
#                         f"You are already logged in with the role: **{user_roles[0].name}**\n\nPlease logout first if you want to login again.",
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             # Show login modal with guild
#             modal = LoginModal(self.user_model, guild)
#             await interaction.response.send_modal(modal)

#             logger.info(
#                 f"Login modal shown to {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id})"
#             )

#         except Exception as e:
#             logger.error(f"Error in handle_login: {e}\n{traceback.format_exc()}")
#             if not interaction.response.is_done():
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Error", "An unexpected error occurred. Please try again later."
#                     ),
#                     ephemeral=True,
#                 )


# async def setup(bot: commands.Bot):
#     """Required setup function for loading the cog"""
#     await bot.add_cog(AuthCog(bot))
#     logger.info("AuthCog loaded successfully")


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

from models.user import UserModel
from models.server_config import ServerConfigModel
from models.allowed_roles import AllowedRolesModel
from ui.views import AuthView
from ui.embeds import create_auth_embed, create_success_embed, create_error_embed
from ui.modals import SignupModal, LoginModal
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

    @commands.Cog.listener()
    async def on_ready(self):
        """Setup persistent views when bot is ready"""
        # Add persistent view for auth buttons
        self.bot.add_view(AuthView(self.bot))
        logger.info("Auth persistent views registered")

    @app_commands.command(
        name="add_signup_role",
        description="Add a role that users can select during signup (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="The role to add to signup options")
    async def add_signup_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        """
        Add a role to the list of roles users can select during signup
        Only administrators can use this command

        Args:
            role: The Discord role to add
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Check if role is @everyone
            if role.name == "@everyone":
                await interaction.response.send_message(
                    "❌ Cannot add @everyone as a signup role!", ephemeral=True
                )
                return

            # Check if role is managed by bot/integration
            if role.managed:
                await interaction.response.send_message(
                    "❌ Cannot add bot/integration managed roles!", ephemeral=True
                )
                return

            # Check if role has admin permissions
            if role.permissions.administrator:
                await interaction.response.send_message(
                    "❌ Cannot add administrator roles as signup options!",
                    ephemeral=True,
                )
                return

            # Check if bot can assign this role
            if role.position >= guild.me.top_role.position:
                await interaction.response.send_message(
                    "❌ This role is higher than or equal to my highest role! Please move my role above it in Server Settings → Roles.",
                    ephemeral=True,
                )
                return

            # Add role to database
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
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while adding the role.", ephemeral=True
                )

    @app_commands.command(
        name="remove_signup_role",
        description="Remove a role from signup options (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="The role to remove from signup options")
    async def remove_signup_role(
        self, interaction: discord.Interaction, role: discord.Role
    ):
        """
        Remove a role from the list of roles users can select during signup
        Only administrators can use this command

        Args:
            role: The Discord role to remove
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Remove role from database
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
                    f"❌ Failed to remove **{role.name}**. Please try again.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in remove_signup_role: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while removing the role.", ephemeral=True
                )

    @app_commands.command(
        name="list_signup_roles",
        description="List all available signup roles (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    async def list_signup_roles(self, interaction: discord.Interaction):
        """
        List all roles that users can select during signup
        Only administrators can use this command
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Get all allowed roles
            roles_data = await self.roles_model.get_all_roles(guild.id)

            if not roles_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Signup Roles Configured",
                        "No roles have been added for signup yet.\n\n"
                        "Use `/add_signup_role` to add roles that users can select during signup.",
                    ),
                    ephemeral=True,
                )
                return

            # Create embed
            embed = discord.Embed(
                title="📋 Available Signup Roles",
                description=f"Users can select from these roles during signup:",
                color=discord.Color.blue(),
            )

            # Add roles to embed
            role_list = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    role_list.append(f"• {role.mention} - `{role.name}`")
                else:
                    # Role deleted from server
                    role_list.append(f"• ~~{role_data['role_name']}~~ (Deleted)")

            embed.add_field(
                name=f"Roles ({len(roles_data)})",
                value="\n".join(role_list) if role_list else "No roles available",
                inline=False,
            )

            embed.set_footer(text=f"Server: {guild.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in list_signup_roles: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while listing roles.", ephemeral=True
                )

    @app_commands.command(
        name="clear_signup_roles", description="Remove all signup roles (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def clear_signup_roles(self, interaction: discord.Interaction):
        """
        Remove all roles from signup options
        Only administrators can use this command
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Get count before clearing
            roles_data = await self.roles_model.get_all_roles(guild.id)
            count = len(roles_data)

            if count == 0:
                await interaction.response.send_message(
                    "❌ There are no signup roles to clear!", ephemeral=True
                )
                return

            # Clear all roles
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
                    "❌ Failed to clear signup roles. Please try again.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in clear_signup_roles: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while clearing roles.", ephemeral=True
                )

    @app_commands.command(
        name="set_login_channel",
        description="Set the login/signup channel (Admin only)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="The channel to use for login and signup")
    async def set_login_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        """
        Set the login/signup channel for this server
        Only administrators can use this command

        Args:
            channel: The text channel to set as login/signup channel
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Save channel configuration
            success = await self.config_model.set_login_channel(guild.id, channel.id)

            if success:
                await interaction.response.send_message(
                    f"✅ Login/Signup channel set to {channel.mention}\n\n"
                    f"📝 **Next steps:**\n"
                    f"1. Add signup roles with `/add_signup_role`\n"
                    f"2. Use `/setup_auth` in {channel.mention} to create the authentication embed",
                    ephemeral=True,
                )
                logger.info(
                    f"Login channel set to {channel.name} (ID: {channel.id}) in guild {guild.name} (ID: {guild.id}) by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to save channel configuration. Please try again.",
                    ephemeral=True,
                )
                logger.error(f"Failed to set login channel for guild {guild.id}")

        except Exception as e:
            logger.error(f"Error in set_login_channel: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while setting the login channel.",
                    ephemeral=True,
                )

    @app_commands.command(
        name="setup_auth", description="Setup authentication embed (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_auth(self, interaction: discord.Interaction):
        """
        Setup the authentication embed with login/signup buttons
        Only administrators can use this command
        Must be used in the configured login/signup channel
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Get configured login channel
            login_channel_id = await self.config_model.get_login_channel(guild.id)

            if not login_channel_id:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Channel Not Configured",
                        "No login/signup channel has been configured for this server!\n\n"
                        "**How to fix:**\n"
                        "Use `/set_login_channel` first to set the login channel.",
                    ),
                    ephemeral=True,
                )
                return

            # Check if in correct channel
            if interaction.channel_id != login_channel_id:
                channel = guild.get_channel(login_channel_id)
                channel_mention = (
                    channel.mention if channel else f"<#{login_channel_id}>"
                )
                await interaction.response.send_message(
                    f"❌ This command can only be used in the configured login channel: {channel_mention}",
                    ephemeral=True,
                )
                return

            # Check if signup roles are configured
            roles_data = await self.roles_model.get_all_roles(guild.id)

            if not roles_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Signup Roles Configured",
                        "You haven't added any roles for users to select during signup!\n\n"
                        "**How to fix:**\n"
                        "1. Use `/add_signup_role @RoleName` to add roles\n"
                        "2. Add at least one role\n"
                        "3. Run `/setup_auth` again\n\n"
                        "**Example:**\n"
                        "`/add_signup_role @Developer`\n"
                        "`/add_signup_role @Designer`",
                    ),
                    ephemeral=True,
                )
                return

            # Verify roles still exist in server
            valid_roles = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    valid_roles.append(role)

            if not valid_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Roles Not Found",
                        "The configured signup roles no longer exist in this server!\n\n"
                        "**How to fix:**\n"
                        "1. Use `/clear_signup_roles` to clear old roles\n"
                        "2. Add new roles with `/add_signup_role`\n"
                        "3. Run `/setup_auth` again",
                    ),
                    ephemeral=True,
                )
                return

            # Create embed
            embed = create_auth_embed()

            # Add available roles to embed
            roles_list = "\n".join([f"• {role.mention}" for role in valid_roles[:10]])
            if len(valid_roles) > 10:
                roles_list += f"\n... and {len(valid_roles) - 10} more"

            embed.add_field(name="📋 Available Roles", value=roles_list, inline=False)

            # Create view with buttons
            view = AuthView(self.bot)

            # Send embed with buttons
            await interaction.response.send_message(embed=embed, view=view)

            logger.info(
                f"Auth embed setup by {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id}) with {len(valid_roles)} roles"
            )

        except Exception as e:
            logger.error(f"Error in setup_auth: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while setting up authentication.",
                    ephemeral=True,
                )

    @app_commands.command(
        name="view_config", description="View current bot configuration (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def view_config(self, interaction: discord.Interaction):
        """
        View the current bot configuration for this server
        Only administrators can use this command
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Get configuration
            login_channel_id = await self.config_model.get_login_channel(guild.id)
            logout_channel_id = await self.config_model.get_logout_channel(guild.id)
            roles_data = await self.roles_model.get_all_roles(guild.id)

            # Create embed
            embed = discord.Embed(
                title="🔧 Bot Configuration",
                description=f"Current configuration for **{guild.name}**",
                color=discord.Color.blue(),
            )

            # Login channel
            if login_channel_id:
                channel = guild.get_channel(login_channel_id)
                login_text = (
                    channel.mention
                    if channel
                    else f"<#{login_channel_id}> (Channel not found)"
                )
            else:
                login_text = "❌ Not configured"
            embed.add_field(
                name="📝 Login/Signup Channel", value=login_text, inline=False
            )

            # Logout channel
            if logout_channel_id:
                channel = guild.get_channel(logout_channel_id)
                logout_text = (
                    channel.mention
                    if channel
                    else f"<#{logout_channel_id}> (Channel not found)"
                )
            else:
                logout_text = "❌ Not configured"
            embed.add_field(name="👋 Logout Channel", value=logout_text, inline=False)

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
                    "• Use `/set_login_channel` to configure login/signup channel"
                )
            if not logout_channel_id:
                instructions.append(
                    "• Use `/set_logout_channel` to configure logout channel"
                )
            if not roles_data:
                instructions.append("• Use `/add_signup_role` to add roles for signup")

            if instructions:
                embed.add_field(
                    name="📝 Next Steps", value="\n".join(instructions), inline=False
                )
            else:
                embed.add_field(
                    name="✅ Status",
                    value="All configured! Use `/setup_auth` and `/setup_logout` in the respective channels.",
                    inline=False,
                )

            embed.set_footer(text=f"Guild ID: {guild.id}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in view_config: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while viewing configuration.", ephemeral=True
                )

    async def handle_signup(self, interaction: discord.Interaction):
        """
        Handle signup button click - shows signup modal

        Args:
            interaction: Discord interaction from button click
        """
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

            # Check if user already has a role (already signed up)
            user_roles = [role for role in member.roles if role.name != "@everyone"]

            if user_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Already Registered",
                        "You already have a role assigned. Please contact an administrator if you need to update your information.",
                    ),
                    ephemeral=True,
                )
                return

            # Get allowed roles from database
            roles_data = await self.roles_model.get_all_roles(guild.id)

            if not roles_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles Available",
                        "Signup roles haven't been configured yet. Please contact an administrator.",
                    ),
                    ephemeral=True,
                )
                return

            # Get actual role objects
            available_roles = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    available_roles.append(role)

            if not available_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles Available",
                        "The configured roles no longer exist. Please contact an administrator.",
                    ),
                    ephemeral=True,
                )
                return

            # Show signup modal with guild_id
            modal = SignupModal(self.user_model, available_roles, guild.id)
            await interaction.response.send_modal(modal)

            logger.info(
                f"Signup modal shown to {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id})"
            )

        except Exception as e:
            logger.error(f"Error in handle_signup: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error", "An unexpected error occurred. Please try again later."
                    ),
                    ephemeral=True,
                )

    async def handle_login(self, interaction: discord.Interaction):
        """
        Handle login button click - shows login modal

        Args:
            interaction: Discord interaction from button click
        """
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

            # Check if user already has a role (already logged in)
            user_roles = [role for role in member.roles if role.name != "@everyone"]

            if user_roles:
                await interaction.response
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Already Logged In",
                        f"You are already logged in with the role: **{user_roles[0].name}**\n\nPlease logout first if you want to login again.",
                    ),
                    ephemeral=True,
                )
                return

            # Show login modal with guild
            modal = LoginModal(self.user_model, guild)
            await interaction.response.send_modal(modal)

            logger.info(
                f"Login modal shown to {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id})"
            )

        except Exception as e:
            logger.error(f"Error in handle_login: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error", "An unexpected error occurred. Please try again later."
                    ),
                    ephemeral=True,
                )


async def setup(bot: commands.Bot):
    """Required setup function for loading the cog"""
    await bot.add_cog(AuthCog(bot))
    logger.info("AuthCog loaded successfully")
