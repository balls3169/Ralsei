"""
Entry point. Loads all cogs, starts the bot, and runs a tiny web server
alongside it so Render (as a Web Service) has something to health-check.

If you deploy this as a Render "Background Worker" instead of a "Web
Service", you can delete the keep_alive() call — workers don't need an
open port. Web Services are usually the free-tier-friendly choice though,
hence including this by default (matches the Yarnaby/Render setup).
"""

import asyncio
import logging
import os

import discord
from discord.ext import commands
from aiohttp import web

from bot_config_and_keys import DISCORD_TOKEN, COMMAND_PREFIX
from utils.database_upstash_connection import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ralsei_bot")

# Quiets the routine "GET / HTTP/1.1 200" lines that cron-job.org's keep-alive
# pings generate every few minutes — those are expected and harmless (they're
# literally what keeps Render from spinning down), just noisy in the Logs
# tab. This only silences that specific access-log line; real bot activity
# (cogs loading, errors, "Logged in as...") still logs normally above.
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

INTENTS = discord.Intents.default()
INTENTS.message_content = True  # required to read command text / free-chat mentions

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=INTENTS)

COGS = [
    "cogs.commands_affection_pet_hug",
    "cogs.commands_ai_personality_chat",
    "cogs.commands_battle_system",
    "cogs.commands_castle_town_recruits",
]


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (id: {bot.user.id})")


@bot.command(name="ralsei_help")
async def ralsei_help(ctx: commands.Context):
    """In-character help command."""
    embed = discord.Embed(
        title="Um... need help?",
        description=(
            "Oh! Hello. I suppose I should explain myself a little, sorry.\n\n"
            f"**{COMMAND_PREFIX}pet / {COMMAND_PREFIX}bellyrub / {COMMAND_PREFIX}scritch / {COMMAND_PREFIX}hug** — "
            "affection commands, if you'd like.\n"
            f"**{COMMAND_PREFIX}battle <enemy>** — starts a battle! You can choose who acts each turn.\n"
            f"**{COMMAND_PREFIX}battle_retry** — tries the last battle again, if things went poorly.\n"
            f"**{COMMAND_PREFIX}castle_town** — see who's been recruited to Castle Town so far.\n"
            f"**{COMMAND_PREFIX}checkr <name>** — check information on a Darkner.\n\n"
            "You can also just... talk to me, if you mention me or send a DM. I'll try my best to answer."
        ),
        color=discord.Color.from_rgb(150, 200, 130),
    )
    await ctx.send(embed=embed)


async def load_cogs():
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded {cog}")
        except Exception as e:
            logger.error(f"Failed to load {cog}: {e}")


# --- Tiny keep-alive web server for Render Web Service health checks ---

async def handle_health(request):
    return web.Response(text="Ralsei is awake!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Keep-alive web server running on port {port}")


async def main():
    await load_cogs()
    await start_web_server()
    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        await storage.close()


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set!")
    asyncio.run(main())
