"""
Logout Cog
Handles logout functionality with button interactions
Multi-server compatible with dynamic channel configuration
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import traceback

from models.server_config import ServerConfigModel
from ui.views import LogoutView
from ui.embeds import create_logout_embed, create_success_embed, create_error_embed
from utils.logger import logger
from datetime import datetime, timezone


class LogoutCog(commands.Cog):
    """Cog for handling logout functionality"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_model = ServerConfigModel()
        logger.info("LogoutCog initialized")

    # -------------------------------------------------------------
    # 🔹 Helper for recording logout activity (used by LogoutView)
    # -------------------------------------------------------------
    async def record_logout(self, interaction: discord.Interaction):
        """
        Called when a user logs out (button click).
        Records logout in Supabase and logs the event.
        """
        try:
            guild = interaction.guild
            member = interaction.user

            # ✅ Fetch user info from DB
            user_data = await self.user_model.get_user_by_discord_id(
                guild.id, member.id
            )
            if not user_data:
                logger.warning(f"No user found for logout: {member} ({member.id})")
                return

            email = user_data.get("email", "Unknown")

            # ✅ Save logout event
            await self.user_model.save_login_history(
                guild_id=guild.id,
                discord_user_id=member.id,
                email=email,
                success=False,
            )

            logger.info(
                f"Logout recorded for {member} ({member.id}) in guild {guild.id}"
            )

            # ✅ Create audit log embed
            log_embed = discord.Embed(
                title="🔒 User Logged Out",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            log_embed.add_field(
                name="👤 User", value=f"{member.mention} ({member.id})", inline=False
            )
            log_embed.add_field(name="📧 Email", value=f"`{email}`", inline=True)
            log_embed.set_thumbnail(url=member.display_avatar.url)
            log_embed.set_footer(text=f"Guild: {guild.name}")

            # Send to the same logging channel used for login events
            await self.send_log_message(guild, log_embed)

        except Exception as e:
            logger.error(f"Error recording logout: {e}\n{traceback.format_exc()}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Setup persistent views when bot is ready"""
        # Add persistent view for logout button
        self.bot.add_view(LogoutView())
        logger.info("Logout persistent views registered")

    @app_commands.command(
        name="set_logout_channel", description="Set the logout channel (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="The channel to use for logout")
    async def set_logout_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        """
        Set the logout channel for this server
        Only administrators can use this command

        Args:
            channel: The text channel to set as logout channel
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Save channel configuration
            success = await self.config_model.set_logout_channel(guild.id, channel.id)

            if success:
                await interaction.response.send_message(
                    f"✅ Logout channel set to {channel.mention}\n\n"
                    f"Now use `/setup_logout` in that channel to create the logout embed.",
                    ephemeral=True,
                )
                logger.info(
                    f"Logout channel set to {channel.name} (ID: {channel.id}) in guild {guild.name} (ID: {guild.id}) by {interaction.user}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Failed to save channel configuration. Please try again.",
                    ephemeral=True,
                )
                logger.error(f"Failed to set logout channel for guild {guild.id}")

        except Exception as e:
            logger.error(f"Error in set_logout_channel: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while setting the logout channel.",
                    ephemeral=True,
                )

    @app_commands.command(
        name="setup_logout", description="Setup logout embed (Admin only)"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_logout(self, interaction: discord.Interaction):
        """
        Setup the logout embed with logout button
        Only administrators can use this command
        Must be used in the configured logout channel
        """
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server!", ephemeral=True
                )
                return

            # Get configured logout channel
            logout_channel_id = await self.config_model.get_logout_channel(guild.id)

            if not logout_channel_id:
                await interaction.response.send_message(
                    "❌ No logout channel has been configured for this server!\n\n"
                    "Please use `/set_logout_channel` first to set the logout channel.",
                    ephemeral=True,
                )
                return

            # Check if in correct channel
            if interaction.channel_id != logout_channel_id:
                channel = guild.get_channel(logout_channel_id)
                channel_mention = (
                    channel.mention if channel else f"<#{logout_channel_id}>"
                )
                await interaction.response.send_message(
                    f"❌ This command can only be used in the configured logout channel: {channel_mention}",
                    ephemeral=True,
                )
                return

            # Create embed
            embed = create_logout_embed()

            # Create view with button
            view = LogoutView()

            # Send embed with button
            await interaction.response.send_message(embed=embed, view=view)

            logger.info(
                f"Logout embed setup by {interaction.user} (ID: {interaction.user.id}) in guild {guild.name} (ID: {guild.id})"
            )

        except Exception as e:
            logger.error(f"Error in setup_logout: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while setting up logout.", ephemeral=True
                )


async def setup(bot: commands.Bot):
    """Required setup function for loading the cog"""
    await bot.add_cog(LogoutCog(bot))
    logger.info("LogoutCog loaded successfully")
