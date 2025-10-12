# ✅ Complete Multi-Role Admin Management Cog
# Includes: Create, Update, Read, Read All, Delete, Help
# With Role Mentions, Discord Username Display, and Polished UX

import discord
from discord.ext import commands
from discord import app_commands
import traceback

from models.user import UserModel
from models.allowed_roles import AllowedRolesModel
from ui.embeds import create_error_embed
from utils.logger import logger
from utils.helpers import mask_email, validate_email, validate_full_name, sanitize_input


# -------------------------------------------------------------
# 🔹 Utility: Format roles with mentions
# -------------------------------------------------------------
def format_roles_display(guild: discord.Guild, roles: list) -> str:
    """Return a formatted string of role mentions (or names if not found)."""
    formatted = []
    for role_name in roles:
        role = discord.utils.get(guild.roles, name=role_name)
        formatted.append(role.mention if role else f"`{role_name}`")
    return ", ".join(formatted) if formatted else "❌ No roles assigned"


# -------------------------------------------------------------
# 🔹 Multi-Role Selection View
# -------------------------------------------------------------
class MultiRoleSelectView(discord.ui.View):
    def __init__(
        self,
        user_model: UserModel,
        guild_id: int,
        full_name: str,
        email: str,
        available_roles: list,
        admin_user: discord.User,
        existing_roles=None,
        user_data=None,
    ):
        super().__init__(timeout=180)
        self.user_model = user_model
        self.guild_id = guild_id
        self.full_name = full_name
        self.email = email
        self.available_roles = available_roles
        self.admin_user = admin_user
        self.user_data = user_data

        selected = existing_roles or []

        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                description=f"{role.name} role",
                default=(role.name in selected),
            )
            for role in available_roles[:25]
        ]

        select = discord.ui.Select(
            placeholder="Choose one or more roles...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id="multi_role_select",
        )
        select.callback = self.on_role_selected
        self.add_item(select)

    async def on_role_selected(self, interaction: discord.Interaction):
        try:
            role_ids = [int(r) for r in interaction.data.get("values", [])]
            guild = interaction.guild
            roles = [guild.get_role(rid) for rid in role_ids if guild.get_role(rid)]
            role_names = [r.name for r in roles]

            await interaction.response.defer(ephemeral=True)

            if self.user_data is None:
                # Create new user
                user_data = await self.user_model.create_user(
                    guild_id=self.guild_id,
                    discord_user_id=0,
                    full_name=self.full_name,
                    email=self.email,
                    designation=role_names,
                )

                if not user_data:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Creation Failed",
                            "Email already registered or database error.",
                        ),
                        ephemeral=True,
                    )
                    return

                embed = discord.Embed(
                    title="✅ User Created Successfully", color=discord.Color.green()
                )
                embed.add_field(
                    name="👤 Name", value=f"`{self.full_name}`", inline=False
                )
                embed.add_field(name="📧 Email", value=f"`{self.email}`", inline=False)
                embed.add_field(
                    name="👔 Roles",
                    value=format_roles_display(guild, role_names),
                    inline=False,
                )
                embed.add_field(
                    name="🔑 Password",
                    value=f"```{user_data['generated_password']}```",
                    inline=False,
                )
                embed.set_footer(text=f"Created by {self.admin_user}")

                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(
                    f"Admin {self.admin_user} created user {mask_email(self.email)} with roles {role_names} in guild {self.guild_id}"
                )

            else:
                # Update existing user
                success = await self.user_model.update_user(
                    self.user_data["id"],
                    {
                        "full_name": self.full_name,
                        "email": self.email,
                        "designation": role_names,
                    },
                )

                if success:
                    embed = discord.Embed(
                        title="✅ User Updated Successfully",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="👤 Name", value=f"`{self.full_name}`", inline=False
                    )
                    embed.add_field(
                        name="📧 Email", value=f"`{self.email}`", inline=False
                    )
                    embed.add_field(
                        name="👔 New Roles",
                        value=format_roles_display(guild, role_names),
                        inline=False,
                    )
                    embed.set_footer(text=f"Updated by {self.admin_user}")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    logger.info(
                        f"Admin {self.admin_user} updated user {self.user_data['id']} roles {role_names}"
                    )
                else:
                    await interaction.followup.send(
                        embed=create_error_embed(
                            "Update Failed", "Could not update user."
                        ),
                        ephemeral=True,
                    )

            for item in self.children:
                item.disabled = True

        except Exception as e:
            logger.error(f"Error selecting roles: {e}\n{traceback.format_exc()}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "Unexpected error occurred."),
                ephemeral=True,
            )


# -------------------------------------------------------------
# 🔹 Delete User Confirmation View
# -------------------------------------------------------------
class DeleteUserConfirmationView(discord.ui.View):
    def __init__(self, user_model: UserModel, user_data: dict, guild: discord.Guild):
        super().__init__(timeout=60)
        self.user_model = user_model
        self.user_data = user_data
        self.guild = guild

    @discord.ui.button(label="✅ Yes, Delete User", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            await interaction.response.defer(ephemeral=True)

            success = await self.user_model.delete_user_by_email(
                self.guild.id, self.user_data["email"]
            )

            roles = self.user_data.get("designation", [])
            if isinstance(roles, str):
                roles = [roles]
            roles_display = format_roles_display(self.guild, roles)

            if success:
                embed = discord.Embed(
                    title="✅ User Deleted Successfully",
                    description=f"**{self.user_data['full_name']}** has been permanently deleted.",
                    color=discord.Color.green(),
                )
                embed.add_field(
                    name="📧 Email", value=f"`{self.user_data['email']}`", inline=False
                )
                embed.add_field(name="👔 Roles", value=roles_display, inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(
                    f"Admin {interaction.user} deleted user {mask_email(self.user_data['email'])} ({roles}) from guild {self.guild.id}"
                )
            else:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Deletion Failed", "Unable to delete user."
                    ),
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error deleting user: {e}\n{traceback.format_exc()}")

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Deletion Cancelled",
            description="User was not deleted.",
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# -------------------------------------------------------------
# 🔹 Admin Users Cog
# -------------------------------------------------------------
class AdminUsersCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_model = UserModel()
        self.roles_model = AllowedRolesModel()
        logger.info(
            "AdminUsersCog initialized with complete multi-role and help support"
        )

    # ---------------------------------------------------------
    # /CREATE_USER
    # ---------------------------------------------------------
    @app_commands.command(
        name="create_user", description="Create a new user with multiple roles"
    )
    @app_commands.default_permissions(administrator=True)
    async def create_user(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            roles_data = await self.roles_model.get_all_roles(guild.id)
            available_roles = [
                guild.get_role(r["role_id"])
                for r in roles_data
                if guild.get_role(r["role_id"])
            ]

            if not available_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles", "No available roles configured."
                    ),
                    ephemeral=True,
                )
                return

            from ui.modals import CreateUserModal

            modal = CreateUserModal(self.user_model, available_roles, guild.id)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in create_user: {e}\n{traceback.format_exc()}")

    # ---------------------------------------------------------
    # /UPDATE_USER
    # ---------------------------------------------------------
    @app_commands.command(
        name="update_user", description="Update a user's information and roles"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(email="User's email address")
    async def update_user(self, interaction: discord.Interaction, email: str):
        try:
            guild = interaction.guild
            user_data = await self.user_model.get_user_by_email(guild.id, email)
            if not user_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "User Not Found", f"No user found with `{email}`."
                    ),
                    ephemeral=True,
                )
                return

            roles_data = await self.roles_model.get_all_roles(guild.id)
            available_roles = [
                guild.get_role(r["role_id"])
                for r in roles_data
                if guild.get_role(r["role_id"])
            ]

            if not available_roles:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Roles", "No available roles configured."
                    ),
                    ephemeral=True,
                )
                return

            from ui.modals import UpdateUserModal

            modal = UpdateUserModal(self.user_model, user_data, available_roles)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(f"Error in update_user: {e}\n{traceback.format_exc()}")

    # ---------------------------------------------------------
    # /READ_USER
    # ---------------------------------------------------------
    @app_commands.command(name="read_user", description="View user info (Admin only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(email="User's email address")
    async def read_user(self, interaction: discord.Interaction, email: str):
        try:
            guild = interaction.guild
            user_data = await self.user_model.get_user_by_email(guild.id, email)

            if not user_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "User Not Found", f"No user found with `{email}`."
                    ),
                    ephemeral=True,
                )
                return

            roles = user_data.get("designation", [])
            if isinstance(roles, str):
                roles = [roles]
            roles_display = format_roles_display(guild, roles)

            discord_id = user_data.get("discord_user_id")
            if discord_id and int(discord_id) != 0:
                member = guild.get_member(int(discord_id))
                if member:
                    discord_display = f"{member.name} ({member.mention})"
                else:
                    discord_display = f"Linked but not in server (`{discord_id}`)"
            else:
                discord_display = "❌ Not yet linked (user hasn't logged in)"

            embed = discord.Embed(
                title="👤 User Information", color=discord.Color.blue()
            )
            embed.add_field(
                name="Full Name", value=f"`{user_data['full_name']}`", inline=False
            )
            embed.add_field(name="Email", value=f"`{user_data['email']}`", inline=False)
            embed.add_field(
                name="Password", value=f"```{user_data['password']}```", inline=False
            )
            embed.add_field(name="Roles", value=roles_display, inline=False)
            embed.add_field(name="Discord Account", value=discord_display, inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in read_user: {e}\n{traceback.format_exc()}")

    # ---------------------------------------------------------
    # /READ_ALL_USERS
    # ---------------------------------------------------------
    @app_commands.command(
        name="read_all_users", description="List all registered users (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def read_all_users(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            users = await self.user_model.get_all_users_in_guild(guild.id)
            if not users:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "No Users", "No users registered in this server."
                    ),
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="📋 Registered Users",
                description=f"Total: **{len(users)}**",
                color=discord.Color.blue(),
            )

            for i, user in enumerate(users[:25]):
                roles = user.get("designation", [])
                if isinstance(roles, str):
                    roles = [roles]
                roles_display = format_roles_display(guild, roles)

                discord_id = user.get("discord_user_id")
                if discord_id and int(discord_id) != 0:
                    member = guild.get_member(int(discord_id))
                    if member:
                        discord_display = f"{member.name} ({member.mention})"
                    else:
                        discord_display = "(Linked but not in server)"
                else:
                    discord_display = "❌ Not linked yet"

                embed.add_field(
                    name=f"{i+1}. {user['full_name']}",
                    value=(
                        f"📧 `{user['email']}`\n"
                        f"👔 {roles_display}\n"
                        f"💬 Discord: {discord_display}"
                    ),
                    inline=True,
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in read_all_users: {e}\n{traceback.format_exc()}")

    # ---------------------------------------------------------
    # /DELETE_USER
    # ---------------------------------------------------------
    @app_commands.command(
        name="delete_user", description="Delete a user account (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(email="User's email address")
    async def delete_user(self, interaction: discord.Interaction, email: str):
        try:
            guild = interaction.guild
            user_data = await self.user_model.get_user_by_email(guild.id, email)
            if not user_data:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "User Not Found", f"No user found with `{email}`."
                    ),
                    ephemeral=True,
                )
                return

            roles = user_data.get("designation", [])
            if isinstance(roles, str):
                roles = [roles]
            roles_display = format_roles_display(guild, roles)

            embed = discord.Embed(
                title="⚠️ Confirm User Deletion",
                description="Are you sure you want to delete this user? This action **cannot be undone.**",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="👤 Name", value=f"`{user_data['full_name']}`", inline=False
            )
            embed.add_field(
                name="📧 Email", value=f"`{user_data['email']}`", inline=False
            )
            embed.add_field(name="👔 Roles", value=roles_display, inline=False)
            embed.set_footer(text="You have 60 seconds to confirm.")

            view = DeleteUserConfirmationView(self.user_model, user_data, guild)
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in delete_user: {e}\n{traceback.format_exc()}")

    # ---------------------------------------------------------
    # /HELP
    # ---------------------------------------------------------
    @app_commands.command(name="help", description="Show all available bot commands")
    # @app_commands.default_permissions(administrator=True)
    async def help(self, interaction: discord.Interaction):
        """Display the help menu for all bot commands"""
        try:
            embed = discord.Embed(
                title="🤖 Auth Handler Bot — Help Menu",
                description="A quick overview of available commands and features.",
                color=discord.Color.blurple(),
            )

            embed.add_field(
                name="🔑 User Commands",
                value=(
                    "• `/login` — Log into your account.\n"
                    "• `/logout` — Logout and remove all assigned roles."
                ),
                inline=False,
            )

            embed.add_field(
                name="🛠️ Admin User Management",
                value=(
                    "• `/create_user` — Create a new user with one or more roles.\n"
                    "• `/update_user` — Edit user details or roles.\n"
                    "• `/read_user` — View a specific user's info.\n"
                    "• `/read_all_users` — List all registered users.\n"
                    "• `/delete_user` — Delete a user safely with confirmation."
                ),
                inline=False,
            )

            embed.add_field(
                name="⚙️ Configuration & Setup",
                value=(
                    "• `/set_login_channel` — Set the login channel.\n"
                    "• `/set_logout_channel` — Set the logout channel.\n"
                    "• `/setup_auth` — Post the login/authentication portal.\n"
                    "• `/setup_logout` — Post the logout interface.\n"
                    "• `/view_config` — View current bot configuration."
                ),
                inline=False,
            )

            embed.add_field(
                name="💡 Tips",
                value=(
                    "• First-time users must be created by an admin.\n"
                    "• Users can have **multiple roles**.\n"
                    "• Logout removes roles but keeps user data safe.\n"
                    "• Only administrators can manage user accounts."
                ),
                inline=False,
            )

            embed.set_footer(
                text="Auth Handler Bot v2.0 • Secure Role-Based Authentication"
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in /help command: {e}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Unable to display help menu."),
                ephemeral=True,
            )


# -------------------------------------------------------------
# 🔹 COG SETUP
# -------------------------------------------------------------
async def setup(bot: commands.Bot):
    """Required setup function for loading the cog"""
    await bot.add_cog(AdminUsersCog(bot))
    logger.info("AdminUsersCog loaded successfully")
