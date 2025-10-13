"""
User Stats Cog
Tracks and displays user login/logout activity statistics
"""

import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone
from utils.logger import logger
from config.database import get_supabase_client


class UserStatsCog(commands.Cog):
    """Cog to view user login/logout statistics"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.supabase = get_supabase_client()

    @app_commands.command(
        name="user_stats", description="View user login/logout stats for a given period"
    )
    @app_commands.describe(
        user="Select a user (admins can view others)",
        period="Choose time range: day, week, month, or year",
    )
    @app_commands.choices(
        period=[
            app_commands.Choice(name="Past Day", value="day"),
            app_commands.Choice(name="Past Week", value="week"),
            app_commands.Choice(name="Past Month", value="month"),
            app_commands.Choice(name="Past Year", value="year"),
        ]
    )
    async def user_stats(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str],
        user: discord.Member = None,
    ):
        """Display login/logout statistics for yourself or another user (admin only for others)"""
        try:
            guild = interaction.guild
            requester = interaction.user

            # Determine target user
            target_user = user or requester
            is_self = target_user.id == requester.id

            # Admin-only check when viewing others
            if not is_self and not requester.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You can only view your own stats unless you are an administrator.",
                    ephemeral=True,
                )
                return

            # Period value
            period_value = period.value
            now = datetime.now(timezone.utc)
            time_ranges = {
                "day": now - timedelta(days=1),
                "week": now - timedelta(weeks=1),
                "month": now - timedelta(days=30),
                "year": now - timedelta(days=365),
            }
            start_time = time_ranges[period_value]

            # Query login_history for user
            response = (
                self.supabase.table("login_history")
                .select("*")
                .eq("discord_user_id", target_user.id)
                .eq("guild_id", guild.id)
                .gte("timestamp", start_time.isoformat())
                .order("timestamp", desc=True)
                .execute()
            )

            data = response.data or []
            if not data:
                msg = (
                    f"ℹ️ No activity found for you in the past {period.name.lower()}."
                    if is_self
                    else f"ℹ️ No activity found for {target_user.mention} in the past {period.name.lower()}."
                )
                await interaction.response.send_message(msg, ephemeral=True)
                return

            # Calculate total active time
            total_seconds = 0
            login_time = None

            # Sort by timestamp (ascending)
            data = sorted(data, key=lambda x: x["timestamp"])

            for record in data:
                is_logged_in = record.get("is_logged_in")
                timestamp = datetime.fromisoformat(record["timestamp"])

                if is_logged_in:
                    login_time = timestamp
                elif login_time:
                    logout_time = timestamp
                    total_seconds += (logout_time - login_time).total_seconds()
                    login_time = None

            total_hours = round(total_seconds / 3600, 2)
            total_logins = sum(1 for r in data if r.get("is_logged_in"))
            total_logouts = len(data) - total_logins

            # Build embed
            embed = discord.Embed(
                title=f"📊 {'Your' if is_self else target_user.display_name + '’s'} Login Stats",
                description=f"Showing activity for the **{period.name.lower()}**.",
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc),
            )

            embed.add_field(
                name="🕒 Total Active Hours", value=f"**{total_hours}h**", inline=True
            )
            embed.add_field(name="✅ Logins", value=f"{total_logins}", inline=True)
            embed.add_field(name="🚪 Logouts", value=f"{total_logouts}", inline=True)
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.set_footer(text=f"Guild: {guild.name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"Displayed {period_value} stats for {target_user} (requested by {requester}) in guild {guild.name}"
            )

        except Exception as e:
            logger.error(f"Error in /user_stats: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching statistics.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """Load the UserStatsCog"""
    await bot.add_cog(UserStatsCog(bot))
    logger.info("UserStatsCog loaded successfully")
