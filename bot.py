"""
Discord Authentication Bot
Main entry point for the bot application
"""

import discord
from discord.ext import commands
import asyncio
from config.settings import DISCORD_TOKEN
from utils.logger import setup_logger
from config.database import init_database

# Setup logger
logger = setup_logger()


class AuthBot(commands.Bot):
    """Custom Bot class with setup hook for loading cogs"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        """Load all cogs before bot starts"""
        logger.info("Loading cogs...")

        cogs_to_load = ["cogs.auth", "cogs.logout"]

        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"✓ Loaded {cog}")
            except Exception as e:
                logger.error(f"✗ Failed to load {cog}: {e}")

        logger.info("All cogs loaded successfully!")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # List all guilds
        for guild in self.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id})")

        # Sync commands globally
        try:
            logger.info("Syncing commands globally...")
            synced = await self.tree.sync()
            logger.info(f"✓ Synced {len(synced)} global command(s)")

            # Also sync to each guild individually for instant updates
            for guild in self.guilds:
                try:
                    guild_commands = await self.tree.sync(guild=guild)
                    logger.info(
                        f"✓ Synced {len(guild_commands)} command(s) to guild: {guild.name}"
                    )
                except Exception as e:
                    logger.error(f"✗ Failed to sync to guild {guild.name}: {e}")

        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="for authentication requests"
            )
        )

        logger.info("Bot is ready!")
        logger.info("=" * 50)
        logger.info("Use !sync command to manually sync slash commands")
        logger.info("=" * 50)

    async def on_error(self, event_method: str, *args, **kwargs):
        """Global error handler"""
        logger.error(f"Error in {event_method}", exc_info=True)


async def main():
    """Main function to run the bot"""
    # Initialize database connection
    logger.info("Initializing database connection...")
    if not init_database():
        logger.error("Failed to initialize database. Exiting...")
        return

    logger.info("Database initialized successfully!")

    # Create bot instance
    bot = AuthBot()

    # Add manual sync command
    @bot.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync(ctx: commands.Context):
        """
        Manually sync slash commands to all servers
        Usage: !sync
        """
        try:
            msg = await ctx.send("🔄 Syncing commands...")

            # Sync globally
            synced_global = await bot.tree.sync()

            # Sync to all guilds
            guild_count = 0
            for guild in bot.guilds:
                try:
                    await bot.tree.sync(guild=guild)
                    guild_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync to {guild.name}: {e}")

            await msg.edit(
                content=(
                    f"✅ **Commands Synced Successfully!**\n\n"
                    f"📊 **Global Commands:** {len(synced_global)}\n"
                    f"🌐 **Synced to Guilds:** {guild_count}/{len(bot.guilds)}\n\n"
                    f"Commands should now be available in all servers!"
                )
            )

            logger.info(
                f"Commands manually synced by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}"
            )

        except Exception as e:
            logger.error(f"Error in sync command: {e}")
            await ctx.send(f"❌ **Error syncing commands:**\n```{str(e)}```")

    @sync.error
    async def sync_error(ctx: commands.Context, error):
        """Handle sync command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "❌ You need **Administrator** permission to use this command!"
            )
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logger.error(f"Sync command error: {error}")

    # Add botinfo command
    @bot.command(name="botinfo")
    async def botinfo(ctx: commands.Context):
        """
        Display bot information
        Usage: !botinfo
        """
        try:
            embed = discord.Embed(
                title="🤖 Bot Information",
                description="Discord Authentication Bot",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="Bot",
                value=f"{bot.user.name}#{bot.user.discriminator}",
                inline=True,
            )

            embed.add_field(name="Servers", value=f"{len(bot.guilds)}", inline=True)

            embed.add_field(
                name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True
            )

            # List slash commands
            commands_list = bot.tree.get_commands()
            if commands_list:
                cmd_text = "\n".join([f"• `/{cmd.name}`" for cmd in commands_list])
                embed.add_field(
                    name=f"📋 Slash Commands ({len(commands_list)})",
                    value=(
                        cmd_text if len(cmd_text) <= 1024 else f"{cmd_text[:1020]}..."
                    ),
                    inline=False,
                )

            embed.add_field(
                name="📖 Admin Commands",
                value="• `!sync` - Sync slash commands\n• `!botinfo` - Show this info",
                inline=False,
            )

            embed.set_thumbnail(url=bot.user.display_avatar.url)
            embed.set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in botinfo: {e}")
            await ctx.send(f"❌ Error displaying bot info: {str(e)}")

    # Run bot
    try:
        logger.info("Starting bot...")
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.close()
        logger.info("Bot shut down successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
