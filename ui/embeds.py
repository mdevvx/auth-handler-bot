"""
Embed templates for the Discord bot
Provides consistent, reusable embed creation functions
"""

import discord
from typing import Optional


def create_auth_embed() -> discord.Embed:
    """
    Create the authentication embed for login/signup

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="🔐 Authentication Portal",
        description=(
            "Welcome! Please authenticate to access the server.\n\n"
            "**New User?** Click **Sign Up** to create an account.\n"
            "**Existing User?** Click **Login** to access your account.\n\n"
            "Your credentials will be sent to you privately."
        ),
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="📝 Sign Up",
        value="Create a new account with your information",
        inline=True,
    )

    embed.add_field(
        name="🔑 Login",
        value="Access your account with email and password",
        inline=True,
    )

    embed.set_footer(text="Your privacy is important. All data is securely stored.")

    return embed


def create_logout_embed() -> discord.Embed:
    """
    Create the logout embed

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="👋 Logout",
        description=(
            "Click the button below to logout and remove your role.\n\n"
            "You can login again anytime in the authentication channel."
        ),
        color=discord.Color.orange(),
    )

    embed.set_footer(text="Your account data will remain saved for future logins.")

    return embed


def create_success_embed(title: str, description: str) -> discord.Embed:
    """
    Create a success embed

    Args:
        title: Embed title
        description: Embed description

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"✅ {title}", description=description, color=discord.Color.green()
    )

    return embed


def create_error_embed(title: str, description: str) -> discord.Embed:
    """
    Create an error embed

    Args:
        title: Embed title
        description: Embed description

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"❌ {title}", description=description, color=discord.Color.red()
    )

    return embed


def create_info_embed(title: str, description: str) -> discord.Embed:
    """
    Create an info embed

    Args:
        title: Embed title
        description: Embed description

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"ℹ️ {title}", description=description, color=discord.Color.blue()
    )

    return embed


def create_warning_embed(title: str, description: str) -> discord.Embed:
    """
    Create a warning embed

    Args:
        title: Embed title
        description: Embed description

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"⚠️ {title}", description=description, color=discord.Color.gold()
    )

    return embed


def create_signup_success_embed(
    full_name: str, email: str, designation: str, password: str
) -> discord.Embed:
    """
    Create signup success embed with credentials

    Args:
        full_name: User's full name
        email: User's email
        designation: User's designation/role
        password: Generated password

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="✅ Sign Up Successful!",
        description=f"Welcome, **{full_name}**! Your account has been created successfully.",
        color=discord.Color.green(),
    )

    embed.add_field(name="📧 Email", value=f"`{email}`", inline=False)

    embed.add_field(name="🔑 Password", value=f"```{password}```", inline=False)

    embed.add_field(name="👔 Designation", value=f"`{designation}`", inline=False)

    embed.add_field(
        name="🔐 Next Step",
        value=(
            "**Your account is now registered!**\n\n"
            "To get access to the server, please:\n"
            "1. Go to the login channel\n"
            "2. Click the **Login** button\n"
            "3. Enter your email and password\n"
            "4. You will receive your role automatically"
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

    return embed


def create_login_success_embed(
    full_name: str, designation: str, role_mention: str = None
) -> discord.Embed:
    """
    Create login success embed

    Args:
        full_name: User's full name
        designation: User's designation/role
        role_mention: Role mention (optional)

    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title="✅ Login Successful!",
        description=f"Welcome back, **{full_name}**!",
        color=discord.Color.green(),
    )

    role_display = role_mention if role_mention else f"`{designation}`"

    embed.add_field(name="👔 Your Role", value=f"{role_display}", inline=False)

    embed.add_field(
        name="🎉 Access Granted",
        value="Your role has been assigned successfully! You now have access to the server channels.",
        inline=False,
    )

    embed.set_footer(text="Enjoy your stay!")

    return embed
