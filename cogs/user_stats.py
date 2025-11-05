# """
# User Stats Cog
# Tracks and displays user login/logout activity statistics
# """

# import discord
# from discord.ext import commands
# from discord import app_commands
# from datetime import datetime, timedelta, timezone
# from utils.logger import logger
# from config.database import get_supabase_client


# class UserStatsCog(commands.Cog):
#     """Cog to view user login/logout statistics"""

#     def __init__(self, bot: commands.Bot):
#         self.bot = bot
#         self.supabase = get_supabase_client()

#     @app_commands.command(
#         name="user_stats", description="View user login/logout stats for a given period"
#     )
#     @app_commands.describe(
#         user="Select a user (admins can view others)",
#         period="Choose time range: day, week, month, or year",
#     )
#     @app_commands.choices(
#         period=[
#             app_commands.Choice(name="Past Day", value="day"),
#             app_commands.Choice(name="Past Week", value="week"),
#             app_commands.Choice(name="Past Month", value="month"),
#             app_commands.Choice(name="Past Year", value="year"),
#         ]
#     )
#     async def user_stats(
#         self,
#         interaction: discord.Interaction,
#         period: app_commands.Choice[str],
#         user: discord.Member = None,
#     ):
#         """Display login/logout statistics for yourself or another user (admin only for others)"""
#         try:
#             guild = interaction.guild
#             requester = interaction.user

#             # Determine target user
#             target_user = user or requester
#             is_self = target_user.id == requester.id

#             # Admin-only check when viewing others
#             if not is_self and not requester.guild_permissions.administrator:
#                 await interaction.response.send_message(
#                     "❌ You can only view your own stats unless you are an administrator.",
#                     ephemeral=True,
#                 )
#                 return

#             # Period value
#             period_value = period.value
#             now = datetime.now(timezone.utc)
#             time_ranges = {
#                 "day": now - timedelta(days=1),
#                 "week": now - timedelta(weeks=1),
#                 "month": now - timedelta(days=30),
#                 "year": now - timedelta(days=365),
#             }
#             start_time = time_ranges[period_value]

#             # Query login_history for user
#             response = (
#                 self.supabase.table("login_history")
#                 .select("*")
#                 .eq("discord_user_id", target_user.id)
#                 .eq("guild_id", guild.id)
#                 .gte("timestamp", start_time.isoformat())
#                 .order("timestamp", desc=True)
#                 .execute()
#             )

#             data = response.data or []
#             if not data:
#                 msg = (
#                     f"ℹ️ No activity found for you in the past {period.name.lower()}."
#                     if is_self
#                     else f"ℹ️ No activity found for {target_user.mention} in the past {period.name.lower()}."
#                 )
#                 await interaction.response.send_message(msg, ephemeral=True)
#                 return

#             # Calculate total active time
#             total_seconds = 0
#             login_time = None

#             # Sort by timestamp (ascending)
#             data = sorted(data, key=lambda x: x["timestamp"])

#             for record in data:
#                 is_logged_in = record.get("is_logged_in")
#                 timestamp = datetime.fromisoformat(record["timestamp"])

#                 if is_logged_in:
#                     login_time = timestamp
#                 elif login_time:
#                     logout_time = timestamp
#                     total_seconds += (logout_time - login_time).total_seconds()
#                     login_time = None

#             total_hours = round(total_seconds / 3600, 2)
#             total_logins = sum(1 for r in data if r.get("is_logged_in"))
#             total_logouts = len(data) - total_logins

#             # Build embed
#             embed = discord.Embed(
#                 title=f"📊 {'Your' if is_self else target_user.display_name + '’s'} Login Stats",
#                 description=f"Showing activity for the **{period.name.lower()}**.",
#                 color=discord.Color.blurple(),
#                 timestamp=datetime.now(timezone.utc),
#             )

#             embed.add_field(
#                 name="🕒 Total Active Hours", value=f"**{total_hours}h**", inline=True
#             )
#             embed.add_field(name="✅ Logins", value=f"{total_logins}", inline=True)
#             embed.add_field(name="🚪 Logouts", value=f"{total_logouts}", inline=True)
#             embed.set_thumbnail(url=target_user.display_avatar.url)
#             embed.set_footer(text=f"Guild: {guild.name}")

#             await interaction.response.send_message(embed=embed, ephemeral=True)

#             logger.info(
#                 f"Displayed {period_value} stats for {target_user} (requested by {requester}) in guild {guild.name}"
#             )

#         except Exception as e:
#             logger.error(f"Error in /user_stats: {e}")
#             await interaction.response.send_message(
#                 "❌ An error occurred while fetching statistics.",
#                 ephemeral=True,
#             )


# async def setup(bot: commands.Bot):
#     """Load the UserStatsCog"""
#     await bot.add_cog(UserStatsCog(bot))
#     logger.info("UserStatsCog loaded successfully")

import discord
from discord.ext import commands
from discord import app_commands
# Added imports for type hinting and utility functions
from typing import List, Dict, Tuple, Any 
from datetime import datetime, timedelta, timezone
from utils.logger import logger
from config.database import get_supabase_client
# Added Calendar import for week grouping 
from calendar import Calendar 


def _process_login_history(data: List[Dict[str, Any]]) -> Tuple[str, float, int]:
    """
    Processes raw login/logout history to generate a formatted activity table
    grouped by week, and calculates total active hours and active days.
    
    Returns: (output_content_str, total_hours_float, total_days_int)
    """
    # 1. Find all (login, logout) pairs (sessions)
    session_pairs = []
    login_time = None
    
    # Data is already sorted ascendingly by timestamp for correct pairing
    for record in data:
        is_logged_in = record.get("is_logged_in")
        # Ensure timestamp is UTC-aware
        # The database stores timestamps in ISO format which includes timezone info, 
        # but fromisoformat needs replace to make it UTC-aware for comparisons.
        timestamp = datetime.fromisoformat(record["timestamp"]).replace(tzinfo=timezone.utc)

        if is_logged_in:
            # Start a new potential session
            login_time = timestamp
        elif login_time:
            # Found a logout for the most recent login
            session_pairs.append((login_time, timestamp))
            login_time = None 
            
    # 2. Slice sessions into daily segments and aggregate data
    # Key: date_key (YYYY-MM-DD), Value: {'sessions': [(login_time_str, logout_time_str), ...], 'total_seconds': float}
    daily_summary = {} 
    week_day_map = {
        0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"
    }
    
    total_activity_seconds = 0
    
    for login, logout in session_pairs:
        current_day_start = login 
        
        # Handle sessions spanning multiple days
        while current_day_start.date() <= logout.date():
            date_key = current_day_start.strftime("%Y-%m-%d")

            if date_key not in daily_summary:
                daily_summary[date_key] = {'sessions': [], 'total_seconds': 0.0}

            # Define the start and end for the current day segment
            start_of_day = datetime.combine(current_day_start.date(), datetime.min.time(), tzinfo=timezone.utc)
            end_of_day = datetime.combine(current_day_start.date(), datetime.max.time(), tzinfo=timezone.utc)
            
            # Session segment start is the maximum of (original session start time, start of current day)
            session_start_for_day = max(login, start_of_day)
            # Session segment end is the minimum of (original session end time, end of current day)
            session_end_for_day = min(logout, end_of_day)
            
            duration = (session_end_for_day - session_start_for_day).total_seconds()
            
            if duration > 0:
                # Record login/logout times (HH:MM format)
                daily_summary[date_key]['sessions'].append((
                    session_start_for_day.strftime("%H:%M"),
                    session_end_for_day.strftime("%H:%M")
                ))
                # Add duration to daily and overall totals
                daily_summary[date_key]['total_seconds'] += duration
                total_activity_seconds += duration

            # Prepare for the next day's segment
            next_day_start = current_day_start.date() + timedelta(days=1)
            
            if next_day_start > logout.date():
                break
            
            current_day_start = datetime.combine(next_day_start, datetime.min.time(), tzinfo=timezone.utc)
            # For the next iteration, the new "login" is the start of the next day
            login = current_day_start 
    
    # 3. Group daily summaries by ISO week and prepare output structure
    week_summary = {} 
    sorted_date_keys = sorted(daily_summary.keys())
    total_days_active = len(daily_summary)

    for date_key in sorted_date_keys:
        day_dt = datetime.fromisoformat(date_key).replace(tzinfo=timezone.utc)
        iso_year, iso_week, _ = day_dt.isocalendar()
        week_key = (iso_year, iso_week)
        
        # Calculate the header: "Week X (Month Year)"
        # Find the Monday of the week for consistent month/year formatting
        monday_of_week = day_dt.date() - timedelta(days=day_dt.weekday())
        week_header = f"Week {iso_week} ({monday_of_week.strftime('%B %Y')})"

        if week_key not in week_summary:
            week_summary[week_key] = {
                'header': week_header,
                'days': []
            }
        
        day_of_week_name = week_day_map[day_dt.weekday()]

        for session in daily_summary[date_key]['sessions']:
            week_summary[week_key]['days'].append({
                'day_name': day_of_week_name,
                'login': session[0],
                'logout': session[1],
            })

    # 4. Build the final output string
    output_content = ""
    
    for week_key in sorted(week_summary.keys()):
        week_data = week_summary[week_key]
        
        # Header
        output_content += f"**{week_data['header']}**\n"
        output_content += "```\n"
        output_content += "Day  Login  Logout\n"
        output_content += "---  -----  ------\n"
        
        days_in_week_printed = {} 
        
        for session in week_data['days']:
            day_name = session['day_name']
            login = session['login']
            logout = session['logout']
            
            if day_name not in days_in_week_printed:
                # First session of the day - print day name
                output_content += f"{day_name:<4} {login:<6} {logout}\n"
                days_in_week_printed[day_name] = True
            else:
                # Subsequent session of the day - print blank column for day
                output_content += f"{'':<4} {login:<6} {logout}\n"

        output_content += "```\n"
        
    # 5. Build the Summary
    total_hours_tracked = round(total_activity_seconds / 3600, 2)
    
    summary_content = (
        "\n**Summary**\n"
        f"Total Days Active: {total_days_active}\n"
        f"Total Hours Tracked: {total_hours_tracked}h"
    )
    
    full_output = output_content + summary_content
    
    return full_output, total_hours_tracked, total_days_active


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
                # Order by timestamp ascending for correct chronological processing
                .order("timestamp", desc=False) 
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

            # Process data using the new function
            output_content, total_hours, total_days_active = _process_login_history(data)

            # Build embed
            embed = discord.Embed(
                title=f"📊 {'Your' if is_self else target_user.display_name + '’s'} Login Activity",
                description=f"Showing sessions for the **{period.name.lower()}**.\n\n{output_content}",
                color=discord.Color.blurple(),
                timestamp=datetime.now(timezone.utc),
            )

            # Removed old explicit fields for total hours/logins/logouts as they are now included in output_content

            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.set_footer(text=f"Guild: {guild.name} | Times in UTC")

            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(
                f"Displayed {period_value} stats for {target_user} (requested by {requester}) in guild {guild.name}"
            )

        except Exception as e:
            logger.error(f"Error in /user_stats: {e}\n{traceback.format_exc()}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while fetching statistics.",
                    ephemeral=True,
                )


async def setup(bot: commands.Bot):
    """Load the UserStatsCog"""
    await bot.add_cog(UserStatsCog(bot))
    logger.info("UserStatsCog loaded successfully")