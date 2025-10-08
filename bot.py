import discord
from discord.ext import commands
import config

TOKEN = config.DISCORD_TOKEN

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents, owner_id=929951158439645214)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")


@bot.command(name="sync")
# @commands.is_owner()
async def sync(ctx: commands.Context):
    """Manually sync slash commands."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} command(s).")
        print(f"✅ Synced {len(synced)} command(s).")
    except Exception as e:
        await ctx.send(f"⚠️ Failed to sync commands: {e}")
        print(f"⚠️ Failed to sync commands: {e}")


async def load_extensions():
    await bot.load_extension("cogs.quiz")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
