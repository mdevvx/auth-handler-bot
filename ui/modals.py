"""
UI Modals for Auth Handler Bot
Includes:
 - LoginModal: For user login
 - CreateUserModal: For admin creating users
 - UpdateUserModal: For admin updating users
"""

import discord
import traceback
from datetime import datetime, timezone

from models.user import UserModel
from ui.embeds import create_error_embed
from utils.logger import logger
from utils.helpers import validate_email, validate_full_name, sanitize_input


# -------------------------------------------------------------
# 🔹 LOGIN MODAL (for users)
# -------------------------------------------------------------
class LoginModal(discord.ui.Modal):
    def __init__(self, user_model: UserModel, guild: discord.Guild, auth_cog):
        super().__init__(title="Login", timeout=300)
        self.user_model = user_model
        self.guild = guild
        self.auth_cog = auth_cog

        self.email_input = discord.ui.TextInput(
            label="Email",
            placeholder="your.email@example.com",
            min_length=5,
            max_length=255,
            required=True,
        )
        self.password_input = discord.ui.TextInput(
            label="Password",
            placeholder="Enter your password",
            min_length=1,
            max_length=255,
            required=True,
            style=discord.TextStyle.short,
        )

        self.add_item(self.email_input)
        self.add_item(self.password_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            email = sanitize_input(self.email_input.value.lower(), 255)
            password = self.password_input.value
            guild = interaction.guild

            if not validate_email(email):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Email", "Please enter a valid email address."
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=True)

            user_data = await self.user_model.authenticate_user(
                guild_id=self.guild.id, email=email, password=password
            )

            if not user_data:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Login Failed",
                        "Invalid email or password. Please check your credentials.\nIf you don't have an account, contact an administrator.",
                    ),
                    ephemeral=True,
                )
                return

            member = self.guild.get_member(interaction.user.id)
            if not member:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error", "Could not find your member information."
                    ),
                    ephemeral=True,
                )
                return

            # 🔒 Bind Discord account on first login
            if user_data["discord_user_id"] == 0:
                await self.user_model.update_user(
                    user_data["id"], {"discord_user_id": member.id}
                )
                user_data["discord_user_id"] = member.id
                logger.info(f"Bound Discord ID {member.id} to user {email}")

            elif user_data["discord_user_id"] != member.id:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Access Denied",
                        "This account is already linked to another Discord user.\nIf this is a mistake, contact an admin.",
                    ),
                    ephemeral=True,
                )
                return

            # 🧩 Assign all roles
            roles_assigned = []
            designations = user_data.get("designation", [])
            if isinstance(designations, str):
                designations = [designations]

            for role_name in designations:
                role = discord.utils.get(self.guild.roles, name=role_name)
                if role:
                    await member.add_roles(role, reason="User login")
                    roles_assigned.append(role)

            if not roles_assigned:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "No Roles Found",
                        "Login successful but no valid roles found for this account.",
                    ),
                    ephemeral=True,
                )
                return

            role_mentions = ", ".join([r.mention for r in roles_assigned])
            embed = discord.Embed(
                title="✅ Login Successful!",
                description=f"Welcome back, **{user_data['full_name']}**!",
                color=discord.Color.green(),
            )
            embed.add_field(name="👔 Your Roles", value=role_mentions, inline=False)
            embed.add_field(
                name="🎉 Access Granted",
                value="Your roles have been assigned successfully!",
                inline=False,
            )
            embed.set_footer(text="Enjoy your stay!")

            await interaction.followup.send(embed=embed, ephemeral=True)

            # Log the login
            log_embed = discord.Embed(
                title="🔓 User Logged In",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc),
            )
            log_embed.add_field(
                name="👤 User", value=f"{member.mention} ({member.id})", inline=False
            )
            log_embed.add_field(name="📧 Email", value=f"`{email}`", inline=True)
            log_embed.add_field(name="👔 Roles", value=role_mentions, inline=True)
            log_embed.set_thumbnail(url=member.display_avatar.url)
            log_embed.set_footer(text=f"User: {member.name} • Guild: {self.guild.name}")

            await self.auth_cog.send_log_message(self.guild, log_embed)

            from models.user import UserModel

            user_model = UserModel()
            # Fetch actual user info
            user_data = await user_model.get_user_by_discord_id(guild.id, member.id)
            email = user_data.get("email") if user_data else None
            user_id = user_data.get("id") if user_data else None

            await user_model.save_login_history(
                guild_id=guild.id,
                user_id=user_id,
                discord_user_id=member.id,
                email=email,
                is_logged_in=True,
            )

        except Exception as e:
            logger.error(f"Error in LoginModal: {e}\n{traceback.format_exc()}")
            await interaction.followup.send(
                embed=create_error_embed("Error", "Unexpected error during login."),
                ephemeral=True,
            )


# -------------------------------------------------------------
# 🔹 CREATE USER MODAL (for admins)
# -------------------------------------------------------------
class CreateUserModal(discord.ui.Modal):
    def __init__(self, user_model, available_roles, guild_id: int):
        super().__init__(title="Create New User", timeout=300)
        self.user_model = user_model
        self.available_roles = available_roles
        self.guild_id = guild_id

        self.full_name_input = discord.ui.TextInput(
            label="Full Name",
            placeholder="Enter full name",
            min_length=2,
            max_length=100,
        )
        self.email_input = discord.ui.TextInput(
            label="Email", placeholder="user@example.com", min_length=5, max_length=255
        )

        self.add_item(self.full_name_input)
        self.add_item(self.email_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            from cogs.admin_users import (
                MultiRoleSelectView,
            )  # Lazy import to prevent circular dependency

            full_name = sanitize_input(self.full_name_input.value, 100)
            email = sanitize_input(self.email_input.value.lower(), 255)

            if not validate_full_name(full_name):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Name", "Enter a valid full name."
                    ),
                    ephemeral=True,
                )
                return
            if not validate_email(email):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Email", "Enter a valid email address."
                    ),
                    ephemeral=True,
                )
                return

            existing = await self.user_model.get_user_by_email(self.guild_id, email)
            if existing:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Email Exists",
                        f"User with `{email}` already exists in this server.",
                    ),
                    ephemeral=True,
                )
                return

            view = MultiRoleSelectView(
                self.user_model,
                self.guild_id,
                full_name,
                email,
                self.available_roles,
                interaction.user,
            )

            embed = discord.Embed(
                title="📋 Select Role(s)",
                description=f"**Name:** {full_name}\n**Email:** {email}\nSelect one or more roles for this user:",
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in CreateUserModal: {e}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Unexpected error occurred."),
                ephemeral=True,
            )


# -------------------------------------------------------------
# 🔹 UPDATE USER MODAL (for admins)
# -------------------------------------------------------------
class UpdateUserModal(discord.ui.Modal):
    def __init__(self, user_model, user_data: dict, available_roles: list):
        super().__init__(title="Update User", timeout=300)
        self.user_model = user_model
        self.user_data = user_data
        self.available_roles = available_roles

        self.full_name_input = discord.ui.TextInput(
            label="Full Name",
            default=user_data["full_name"],
            min_length=2,
            max_length=100,
        )
        self.email_input = discord.ui.TextInput(
            label="Email",
            default=user_data["email"],
            min_length=5,
            max_length=255,
        )

        self.add_item(self.full_name_input)
        self.add_item(self.email_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            from cogs.admin_users import MultiRoleSelectView

            full_name = sanitize_input(self.full_name_input.value, 100)
            email = sanitize_input(self.email_input.value.lower(), 255)

            if not validate_full_name(full_name) or not validate_email(email):
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Invalid Input", "Enter valid name and email."
                    ),
                    ephemeral=True,
                )
                return

            existing_roles = self.user_data.get("designation", [])
            if isinstance(existing_roles, str):
                existing_roles = [existing_roles]

            view = MultiRoleSelectView(
                self.user_model,
                interaction.guild.id,
                full_name,
                email,
                self.available_roles,
                interaction.user,
                existing_roles,
                self.user_data,
            )

            embed = discord.Embed(
                title="📋 Update User Roles",
                description=f"**Current Roles:** {', '.join(existing_roles)}\nSelect new roles:",
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in UpdateUserModal: {e}\n{traceback.format_exc()}")
            await interaction.response.send_message(
                embed=create_error_embed("Error", "Unexpected error occurred."),
                ephemeral=True,
            )
