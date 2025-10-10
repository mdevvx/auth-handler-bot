"""
Admin User Management Cog
Handles CRUD operations for users via slash commands
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import traceback

from models.user import UserModel
from models.allowed_roles import AllowedRolesModel
from ui.embeds import create_success_embed, create_error_embed
from utils.logger import logger
from utils.helpers import mask_email, generate_password


class RoleSelectViewForCreate(discord.ui.View):
    """View with role select menu for admin creating user"""

    def __init__(
        self,
        user_model: UserModel,
        guild_id: int,
        full_name: str,
        email: str,
        available_roles: list,
        admin_user: discord.User,
    ):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.user_model = user_model
        self.guild_id = guild_id
        self.full_name = full_name
        self.email = email
        self.admin_user = admin_user

        # Create select menu
        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                description=f"Assign {role.name} role",
                emoji="👤",
            )
            for role in available_roles[:25]  # Discord limit is 25 options
        ]

        select = discord.ui.Select(
            placeholder="Choose user's role/designation...",
            options=options,
            custom_id="role_select_create",
        )
        select.callback = self.role_selected
        self.add_item(select)

    async def role_selected(self, interaction: discord.Interaction):
        """Handle role selection"""
        try:
            role_id = int(interaction.data["values"][0])
            guild = interaction.guild

            # Get the selected role
            role = guild.get_role(role_id)
            if not role:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Role Not Found",
                        "The selected role no longer exists. Please try again.",
                    ),
                    ephemeral=True,
                )
                return

            # Defer response as database operation might take time
            await interaction.response.defer(ephemeral=True)

            # Create user in database WITHOUT Discord user ID (will be 0 as placeholder)
            user_data = await self.user_model.create_user(
                guild_id=self.guild_id,
                discord_user_id=0,  # Placeholder - will be updated on first login
                full_name=self.full_name,
                email=self.email,
                designation=role.name,
            )

            if not user_data:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Creation Failed",
                        "Failed to create user. This email may already be registered.",
                    ),
                    ephemeral=True,
                )
                return

            # Success
            embed = discord.Embed(
                title="✅ User Created Successfully",
                description=f"New user account has been registered in the system.",
                color=discord.Color.green(),
            )

            embed.add_field(name="👤 Name", value=f"`{self.full_name}`", inline=False)
            embed.add_field(name="📧 Email", value=f"`{self.email}`", inline=False)
            embed.add_field(
                name="👔 Role", value=f"{role.mention} - `{role.name}`", inline=False
            )
            embed.add_field(
                name="🔑 Password",
                value=f"```{user_data['generated_password']}```",
                inline=False,
            )
            embed.add_field(
                name="📝 Important",
                value=(
                    "**Share these credentials with the user securely:**\n"
                    "• Send via DM or secure channel\n"
                    "• User can login to receive their role\n"
                    "• Password cannot be recovered if lost"
                ),
                inline=False,
            )

            embed.set_footer(text=f"Created by {self.admin_user}")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(
                f"Admin {self.admin_user} created user {mask_email(self.email)} with role {role.name} in guild {self.guild_id}"
            )

            # Disable the view
            for item in self.children:
                item.disabled = True

        except Exception as e:
            logger.error(f"Error in role selection: {e}\n{traceback.format_exc()}")
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

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


class CreateUserModal(discord.ui.Modal):
    """Modal for creating a new user - simplified version"""

    def __init__(self, user_model: UserModel, available_roles: list, guild_id: int):
        super().__init__(title="Create New User", timeout=300)

        self.user_model = user_model
        self.available_roles = available_roles
        self.guild_id = guild_id

        # Full Name input
        self.full_name_input = discord.ui.TextInput(
            label="Full Name",
            placeholder="Enter user's full name",
            min_length=2,
            max_length=100,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.full_name_input)

        # Email input
        self.email_input = discord.ui.TextInput(
            label="Email",
            placeholder="user@example.com",
            min_length=5,
            max_length=255,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.email_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
            from utils.helpers import validate_email, validate_full_name, sanitize_input

            # Get and sanitize inputs
            full_name = sanitize_input(self.full_name_input.value, 100)
            email = sanitize_input(self.email_input.value.lower(), 255)

            # Validate full name
            if not validate_full_name(full_name):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Name",
                        "Please enter a valid full name (letters, spaces, hyphens, and apostrophes only).",
                    ),
                    ephemeral=True,
                )
                return

            # Validate email
            if not validate_email(email):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Email", "Please enter a valid email address."
                    ),
                    ephemeral=True,
                )
                return

            # Check if email already exists
            existing_email = await self.user_model.get_user_by_email(
                self.guild_id, email
            )
            if existing_email:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Email Already Exists",
                        f"A user with email `{email}` already exists in this server.",
                    ),
                    ephemeral=True,
                )
                return

            # Show role selection view
            view = RoleSelectViewForCreate(
                self.user_model,
                self.guild_id,
                full_name,
                email,
                self.available_roles,
                interaction.user,
            )

            embed = discord.Embed(
                title="📋 Select User's Role",
                description=(
                    f"**Name:** {full_name}\n"
                    f"**Email:** {email}\n\n"
                    "Please select the role/designation for this user:"
                ),
                color=discord.Color.blue(),
            )

            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in CreateUserModal: {e}\n{traceback.format_exc()}")
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed("Error", "An error occurred."),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "An error occurred."),
                    ephemeral=True,
                )


# class UpdateUserModal(discord.ui.Modal):
#     """Modal for updating user information"""

#     def __init__(self, user_model: UserModel, user_data: dict, available_roles: list):
#         super().__init__(title="Update User", timeout=300)

#         self.user_model = user_model
#         self.user_data = user_data
#         self.available_roles = available_roles

#         # Full Name input
#         self.full_name_input = discord.ui.TextInput(
#             label="Full Name",
#             default=user_data["full_name"],
#             min_length=2,
#             max_length=100,
#             required=True,
#             style=discord.TextStyle.short,
#         )
#         self.add_item(self.full_name_input)

#         # Email input
#         self.email_input = discord.ui.TextInput(
#             label="Email",
#             default=user_data["email"],
#             min_length=5,
#             max_length=255,
#             required=True,
#             style=discord.TextStyle.short,
#         )
#         self.add_item(self.email_input)

#         # Role input
#         role_names = ", ".join([role.name for role in available_roles])
#         self.designation_input = discord.ui.TextInput(
#             label="Designation/Role",
#             default=user_data["designation"],
#             placeholder=f"Choose from: {role_names[:100]}",
#             min_length=2,
#             max_length=100,
#             required=True,
#             style=discord.TextStyle.short,
#         )
#         self.add_item(self.designation_input)

#     async def on_submit(self, interaction: discord.Interaction):
#         """Handle form submission"""
#         try:
#             from utils.helpers import validate_email, validate_full_name, sanitize_input

#             # Get and sanitize inputs
#             full_name = sanitize_input(self.full_name_input.value, 100)
#             email = sanitize_input(self.email_input.value.lower(), 255)
#             designation = sanitize_input(self.designation_input.value, 100)

#             # Validate
#             if not validate_full_name(full_name):
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Invalid Name", "Please enter a valid full name."
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             if not validate_email(email):
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Invalid Email", "Please enter a valid email."
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             # Find matching role
#             matching_role = None
#             for role in self.available_roles:
#                 if role.name.lower() == designation.lower():
#                     matching_role = role
#                     break

#             if not matching_role:
#                 await interaction.response.send_message(
#                     embed=create_error_embed(
#                         "Invalid Role", f"Role `{designation}` not found."
#                     ),
#                     ephemeral=True,
#                 )
#                 return

#             # Defer response
#             await interaction.response.defer(ephemeral=True, thinking=True)

#             # Update user
#             update_data = {
#                 "full_name": full_name,
#                 "email": email,
#                 "designation": matching_role.name,
#             }

#             success = await self.user_model.update_user(
#                 self.user_data["id"], update_data
#             )

#             if success:
#                 embed = discord.Embed(
#                     title="✅ User Updated Successfully", color=discord.Color.green()
#                 )
#                 embed.add_field(name="👤 Name", value=f"`{full_name}`", inline=False)
#                 embed.add_field(name="📧 Email", value=f"`{email}`", inline=False)
#                 embed.add_field(
#                     name="👔 Role", value=f"`{matching_role.name}`", inline=False
#                 )

#                 await interaction.followup.send(embed=embed, ephemeral=True)
#                 logger.info(
#                     f"Admin {interaction.user} updated user {self.user_data['id']}"
#                 )
#             else:
#                 await interaction.followup.send(
#                     embed=create_error_embed("Update Failed", "Failed to update user."),
#                     ephemeral=True,
#                 )

#         except Exception as e:
#             logger.error(f"Error in UpdateUserModal: {e}\n{traceback.format_exc()}")


class RoleSelectViewForUpdate(discord.ui.View):
    """View with role select menu for updating user role"""

    def __init__(
        self,
        user_model: UserModel,
        user_data: dict,
        full_name: str,
        email: str,
        available_roles: list,
        admin_user: discord.User,
    ):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.user_model = user_model
        self.user_data = user_data
        self.full_name = full_name
        self.email = email
        self.admin_user = admin_user

        # Create select menu
        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                description=f"Change to {role.name} role",
                emoji="👤",
                default=(
                    role.name == user_data["designation"]
                ),  # Pre-select current role
            )
            for role in available_roles[:25]  # Discord limit is 25 options
        ]

        select = discord.ui.Select(
            placeholder="Choose new role/designation...",
            options=options,
            custom_id="role_select_update",
        )
        select.callback = self.role_selected
        self.add_item(select)

    async def role_selected(self, interaction: discord.Interaction):
        """Handle role selection"""
        try:
            role_id = int(interaction.data["values"][0])
            guild = interaction.guild

            # Get the selected role
            role = guild.get_role(role_id)
            if not role:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Role Not Found",
                        "The selected role no longer exists. Please try again.",
                    ),
                    ephemeral=True,
                )
                return

            # Defer response
            await interaction.response.defer(ephemeral=True)

            # Update user
            update_data = {
                "full_name": self.full_name,
                "email": self.email,
                "designation": role.name,
            }

            success = await self.user_model.update_user(
                self.user_data["id"], update_data
            )

            if success:
                embed = discord.Embed(
                    title="✅ User Updated Successfully", color=discord.Color.green()
                )
                embed.add_field(
                    name="👤 Name", value=f"`{self.full_name}`", inline=False
                )
                embed.add_field(name="📧 Email", value=f"`{self.email}`", inline=False)
                embed.add_field(
                    name="👔 New Role",
                    value=f"{role.mention} - `{role.name}`",
                    inline=False,
                )

                if self.user_data["designation"] != role.name:
                    embed.add_field(
                        name="📝 Previous Role",
                        value=f"`{self.user_data['designation']}`",
                        inline=False,
                    )

                embed.set_footer(text=f"Updated by {self.admin_user}")

                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(
                    f"Admin {self.admin_user} updated user {self.user_data['id']}"
                )
            else:
                await interaction.followup.send(
                    embed=create_error_embed("Update Failed", "Failed to update user."),
                    ephemeral=True,
                )

            # Disable the view
            for item in self.children:
                item.disabled = True

        except Exception as e:
            logger.error(
                f"Error in role selection for update: {e}\n{traceback.format_exc()}"
            )
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed("Error", "An unexpected error occurred."),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "An unexpected error occurred."),
                    ephemeral=True,
                )

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


class UpdateUserModal(discord.ui.Modal):
    """Modal for updating user information - now with dropdown for role"""

    def __init__(self, user_model: UserModel, user_data: dict, available_roles: list):
        super().__init__(title="Update User", timeout=300)

        self.user_model = user_model
        self.user_data = user_data
        self.available_roles = available_roles

        # Full Name input
        self.full_name_input = discord.ui.TextInput(
            label="Full Name",
            default=user_data["full_name"],
            min_length=2,
            max_length=100,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.full_name_input)

        # Email input
        self.email_input = discord.ui.TextInput(
            label="Email",
            default=user_data["email"],
            min_length=5,
            max_length=255,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.email_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
            from utils.helpers import validate_email, validate_full_name, sanitize_input

            # Get and sanitize inputs
            full_name = sanitize_input(self.full_name_input.value, 100)
            email = sanitize_input(self.email_input.value.lower(), 255)

            # Validate
            if not validate_full_name(full_name):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Name", "Please enter a valid full name."
                    ),
                    ephemeral=True,
                )
                return

            if not validate_email(email):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Email", "Please enter a valid email."
                    ),
                    ephemeral=True,
                )
                return

            # Show role selection view
            view = RoleSelectViewForUpdate(
                self.user_model,
                self.user_data,
                full_name,
                email,
                self.available_roles,
                interaction.user,
            )

            embed = discord.Embed(
                title="📋 Select New Role",
                description=(
                    f"**Name:** {full_name}\n"
                    f"**Email:** {email}\n"
                    f"**Current Role:** `{self.user_data['designation']}`\n\n"
                    "Please select the new role for this user:"
                ),
                color=discord.Color.blue(),
            )

            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in UpdateUserModal: {e}\n{traceback.format_exc()}")
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed("Error", "An error occurred."),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Error", "An error occurred."),
                    ephemeral=True,
                )


class DeleteUserConfirmationView(discord.ui.View):
    """View for delete user confirmation"""

    def __init__(self, user_model: UserModel, user_data: dict, guild: discord.Guild):
        super().__init__(timeout=60)  # 60 seconds to confirm
        self.user_model = user_model
        self.user_data = user_data
        self.guild = guild

    @discord.ui.button(
        label="Yes, Delete User", style=discord.ButtonStyle.danger, emoji="✅"
    )
    async def confirm_delete(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle delete confirmation"""
        try:
            await interaction.response.defer(ephemeral=True)

            # Delete user
            success = await self.user_model.delete_user_by_email(
                self.guild.id, self.user_data["email"]
            )

            if success:
                embed = discord.Embed(
                    title="✅ User Deleted",
                    description=f"User **{self.user_data['full_name']}** has been permanently deleted.",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="📧 Email", value=f"`{self.user_data['email']}`", inline=False
                )

                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(
                    f"Admin {interaction.user} deleted user {mask_email(self.user_data['email'])} from guild {self.guild.id}"
                )
            else:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Deletion Failed", "Failed to delete user."
                    ),
                    ephemeral=True,
                )

            # Disable buttons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            logger.error(f"Error in delete confirmation: {e}\n{traceback.format_exc()}")

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handle delete cancellation"""
        try:
            embed = discord.Embed(
                title="❌ Deletion Cancelled",
                description="User was not deleted.",
                color=discord.Color.blue(),
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

            # Disable buttons
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

        except Exception as e:
            logger.error(f"Error in cancel delete: {e}\n{traceback.format_exc()}")

    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True


class AdminUsersCog(commands.Cog):
    """Cog for admin user management"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_model = UserModel()
        self.roles_model = AllowedRolesModel()
        logger.info("AdminUsersCog initialized")

    @app_commands.command(
        name="create_user", description="Create a new user account (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def create_user(self, interaction: discord.Interaction):
        """Create a new user via modal"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            # Get available roles
            roles_data = await self.roles_model.get_all_roles(guild.id)
            if not roles_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles Configured",
                        "Please configure signup roles first using `/add_signup_role`.",
                    ),
                    ephemeral=True,
                )
                return

            # Get role objects
            available_roles = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    available_roles.append(role)

            if not available_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles Available", "Configured roles no longer exist."
                    ),
                    ephemeral=True,
                )
                return

            # Show modal
            modal = CreateUserModal(self.user_model, available_roles, guild.id)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in create_user: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="read_user", description="View user information (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(email="User's email address")
    async def read_user(self, interaction: discord.Interaction, email: str):
        """Read a specific user's information"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get user
            user_data = await self.user_model.get_user_by_email(guild.id, email)

            if not user_data:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "User Not Found", f"No user found with email `{email}`."
                    ),
                    ephemeral=True,
                )
                return

            # Create embed
            embed = discord.Embed(
                title="👤 User Information", color=discord.Color.blue()
            )

            embed.add_field(
                name="Full Name", value=f"`{user_data['full_name']}`", inline=False
            )
            embed.add_field(name="Email", value=f"`{user_data['email']}`", inline=False)
            embed.add_field(
                name="Discord ID",
                value=f"`{user_data['discord_user_id']}`",
                inline=False,
            )
            embed.add_field(
                name="Designation", value=f"`{user_data['designation']}`", inline=False
            )
            embed.add_field(
                name="Password", value=f"```{user_data['password']}```", inline=False
            )

            # Format dates
            from datetime import datetime, timezone

            created = datetime.fromisoformat(
                user_data["created_at"].replace("Z", "+00:00")
            )
            embed.add_field(
                name="Created", value=f"<t:{int(created.timestamp())}:F>", inline=True
            )

            if user_data.get("last_login"):
                last_login = datetime.fromisoformat(
                    user_data["last_login"].replace("Z", "+00:00")
                )
                embed.add_field(
                    name="Last Login",
                    value=f"<t:{int(last_login.timestamp())}:R>",
                    inline=True,
                )

            # embed.set_footer(text=f"User ID: {user_data['id']}")

            # Get Discord member if they've logged in
            if user_data["discord_user_id"] != 0:
                member = guild.get_member(user_data["discord_user_id"])
                if member:
                    embed.set_footer(
                        text=f"Discord User: {member.name} • Guild: {guild.name}"
                    )
                else:
                    embed.set_footer(text=f"Guild: {guild.name}")
            else:
                embed.set_footer(text=f"Guild: {guild.name}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in read_user: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="read_all_users", description="List all registered users (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def read_all_users(self, interaction: discord.Interaction):
        """List all users in the server"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=True)

            # Get all users
            users = await self.user_model.get_all_users_in_guild(guild.id)

            if not users:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "No Users", "No users registered in this server yet."
                    ),
                    ephemeral=True,
                )
                return

            # Create embed
            embed = discord.Embed(
                title="📋 Registered Users",
                description=f"Total: **{len(users)}** user(s)",
                color=discord.Color.blue(),
            )

            # Add users (limit to 25 fields)
            for i, user in enumerate(users[:25]):
                embed.add_field(
                    name=f"{i+1}. {user['full_name']}",
                    value=f"📧 `{user['email']}`\n👔 {user['designation']}",
                    inline=True,
                )

            if len(users) > 25:
                embed.set_footer(
                    text=f"Showing first 25 of {len(users)} users • Guild: {guild.name}"
                )
            else:
                embed.set_footer(text=f"Guild: {guild.name}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in read_all_users: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="update_user", description="Update user information (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(email="User's current email address")
    async def update_user(self, interaction: discord.Interaction, email: str):
        """Update a user's information"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            # Get user
            user_data = await self.user_model.get_user_by_email(guild.id, email)

            if not user_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "User Not Found", f"No user found with email `{email}`."
                    ),
                    ephemeral=True,
                )
                return

            # Get available roles
            roles_data = await self.roles_model.get_all_roles(guild.id)
            available_roles = []
            for role_data in roles_data:
                role = guild.get_role(role_data["role_id"])
                if role:
                    available_roles.append(role)

            if not available_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles Available", "Please configure signup roles first."
                    ),
                    ephemeral=True,
                )
                return

            # Show update modal
            modal = UpdateUserModal(self.user_model, user_data, available_roles)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in update_user: {e}\n{traceback.format_exc()}")

    # @app_commands.command(
    #     name="delete_user", description="Delete a user account (Admin only)"
    # )
    # @app_commands.default_permissions(administrator=True)
    # @app_commands.describe(email="User's email address")
    # async def delete_user(self, interaction: discord.Interaction, email: str):
    #     """Delete a user from the database"""
    #     try:
    #         guild = interaction.guild
    #         if not guild:
    #             await interaction.response.send_message(
    #                 "❌ Must be used in a server!", ephemeral=True
    #             )
    #             return

    #         await interaction.response.defer(ephemeral=True, thinking=True)

    #         # Check if user exists
    #         user_data = await self.user_model.get_user_by_email(guild.id, email)

    #         if not user_data:
    #             await interaction.followup.send(
    #                 embed=create_error_embed(
    #                     "User Not Found", f"No user found with email `{email}`."
    #                 ),
    #                 ephemeral=True,
    #             )
    #             return

    #         # Delete user
    #         success = await self.user_model.delete_user_by_email(guild.id, email)

    #         if success:
    #             embed = discord.Embed(
    #                 title="✅ User Deleted",
    #                 description=f"User **{user_data['full_name']}** (`{email}`) has been deleted.",
    #                 color=discord.Color.green(),
    #             )
    #             await interaction.followup.send(embed=embed, ephemeral=True)
    #             logger.info(
    #                 f"Admin {interaction.user} deleted user {mask_email(email)} from guild {guild.id}"
    #             )
    #         else:
    #             await interaction.followup.send(
    #                 embed=create_error_embed(
    #                     "Deletion Failed", "Failed to delete user."
    #                 ),
    #                 ephemeral=True,
    #             )

    #     except Exception as e:
    #         logger.error(f"Error in delete_user: {e}\n{traceback.format_exc()}")

    @app_commands.command(
        name="delete_user", description="Delete a user account (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(email="User's email address")
    async def delete_user(self, interaction: discord.Interaction, email: str):
        """Delete a user from the database with confirmation"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ Must be used in a server!", ephemeral=True
                )
                return

            # Check if user exists
            user_data = await self.user_model.get_user_by_email(guild.id, email)

            if not user_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "User Not Found", f"No user found with email `{email}`."
                    ),
                    ephemeral=True,
                )
                return

            # Create confirmation view
            view = DeleteUserConfirmationView(self.user_model, user_data, guild)

            # Create confirmation embed
            embed = discord.Embed(
                title="⚠️ Confirm User Deletion",
                description="Are you sure you want to delete this user? This action cannot be undone!",
                color=discord.Color.red(),
            )

            embed.add_field(
                name="👤 Name", value=f"`{user_data['full_name']}`", inline=False
            )
            embed.add_field(
                name="📧 Email", value=f"`{user_data['email']}`", inline=False
            )
            embed.add_field(
                name="👔 Role", value=f"`{user_data['designation']}`", inline=False
            )

            embed.add_field(
                name="⚠️ Warning",
                value="• All user data will be permanently deleted\n• User will lose access immediately\n• This action cannot be undone",
                inline=False,
            )

            embed.set_footer(text="You have 60 seconds to confirm")

            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in delete_user: {e}\n{traceback.format_exc()}")


async def setup(bot: commands.Bot):
    """Required setup function for loading the cog"""
    await bot.add_cog(AdminUsersCog(bot))
    logger.info("AdminUsersCog loaded successfully")
