"""
Modal forms for user input
Handles signup and login form submissions
"""

import discord
from discord.ui import Modal, TextInput, Select, View
from discord import SelectOption
from typing import List
import traceback

from models.user import UserModel
from ui.embeds import (
    create_signup_success_embed,
    create_login_success_embed,
    create_error_embed,
)
from utils.logger import logger
from utils.helpers import validate_email, validate_full_name, sanitize_input


class RoleSelectView(View):
    """View with role select menu for signup"""

    def __init__(
        self,
        user_model: UserModel,
        guild_id: int,
        full_name: str,
        email: str,
        available_roles: List[discord.Role],
    ):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.user_model = user_model
        self.guild_id = guild_id
        self.full_name = full_name
        self.email = email
        self.selected_role = None

        # Create select menu
        options = [
            SelectOption(
                label=role.name,
                value=str(role.id),
                description=f"Select {role.name} role",
                emoji="👤",
            )
            for role in available_roles[:25]  # Discord limit is 25 options
        ]

        select = Select(
            placeholder="Choose your role/designation...",
            options=options,
            custom_id="role_select",
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

            self.selected_role = role

            # Defer response as database operation might take time
            await interaction.response.defer(ephemeral=True)

            # Create user in database WITHOUT assigning role
            user_data = await self.user_model.create_user(
                guild_id=self.guild_id,
                discord_user_id=interaction.user.id,
                full_name=self.full_name,
                email=self.email,
                designation=role.name,
            )

            if not user_data:
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Registration Failed",
                        "Failed to create your account. Please try again later or contact an administrator.",
                    ),
                    ephemeral=True,
                )
                return

            # Send success message with credentials (NO ROLE ASSIGNED YET)
            embed = discord.Embed(
                title="✅ Sign Up Successful!",
                description=f"Welcome, **{self.full_name}**! Your account has been created successfully.",
                color=discord.Color.green(),
            )

            embed.add_field(name="📧 Email", value=f"`{self.email}`", inline=False)

            embed.add_field(
                name="🔑 Password",
                value=f"```{user_data['generated_password']}```",
                inline=False,
            )

            embed.add_field(name="👔 Designation", value=f"`{role.name}`", inline=False)

            embed.add_field(
                name="🔐 Next Step",
                value=(
                    "**Your account is now registered!**\n\n"
                    "To get access to the server, please:\n"
                    "1. Click the **Login** button\n"
                    "2. Enter your email and password\n"
                    "3. You will receive your role automatically"
                ),
                inline=False,
            )

            embed.add_field(
                name="⚠️ Important",
                value=(
                    "**Please save your password securely!**\n"
                    "You will need this password to login.\n"
                    "Keep your credentials safe and never share them with anyone."
                ),
                inline=False,
            )

            embed.set_footer(
                text="Account created successfully • Use login to access the server"
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

            logger.info(
                f"User {interaction.user} (ID: {interaction.user.id}) signed up with designation {role.name} in guild {self.guild_id} (no role assigned yet)"
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
        # Disable all items
        for item in self.children:
            item.disabled = True


class SignupModal(Modal):
    """Modal form for user signup"""

    def __init__(
        self, user_model: UserModel, available_roles: List[discord.Role], guild_id: int
    ):
        super().__init__(title="Sign Up", timeout=300)

        self.user_model = user_model
        self.available_roles = available_roles
        self.guild_id = guild_id

        # Full Name input
        self.full_name_input = TextInput(
            label="Full Name",
            placeholder="Enter your full name",
            min_length=2,
            max_length=100,
            required=True,
            style=discord.TextStyle.short,
        )
        self.add_item(self.full_name_input)

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

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        try:
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

            # Check if user already exists
            existing_user = await self.user_model.get_user_by_discord_id(
                self.guild_id, interaction.user.id
            )

            if existing_user:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Account Already Exists",
                        "You already have an account in this server. Please use the login button instead.",
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
                        "Email Already Registered",
                        "This email is already registered in this server. Please use a different email or contact an administrator.",
                    ),
                    ephemeral=True,
                )
                return

            # Show role selection view
            view = RoleSelectView(
                self.user_model, self.guild_id, full_name, email, self.available_roles
            )

            embed = discord.Embed(
                title="📋 Select Your Role",
                description=(
                    f"**Name:** {full_name}\n"
                    f"**Email:** {email}\n\n"
                    "Please select your role/designation from the dropdown below:"
                ),
                color=discord.Color.blue(),
            )

            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )

        except Exception as e:
            logger.error(f"Error in signup modal: {e}\n{traceback.format_exc()}")
            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=create_error_embed(
                        "Error",
                        "An unexpected error occurred during signup. Please try again later.",
                    ),
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        "Error",
                        "An unexpected error occurred during signup. Please try again later.",
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


class LoginModal(Modal):
    """Modal form for user login"""

    def __init__(self, user_model: UserModel, guild: discord.Guild):
        super().__init__(title="Login", timeout=300)

        self.user_model = user_model
        self.guild = guild

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
                        "If you haven't signed up yet, please use the **Sign Up** button first.",
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
                            f"If you want to logout, go to the logout channel and click the logout button.",
                        ),
                        ephemeral=True,
                    )
                    return

                # Assign the role
                await member.add_roles(role, reason="User login")

                # Send success message
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
                        "The bot may be missing the **Manage Roles** permission, or the role might be higher than the bot's role.",
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
