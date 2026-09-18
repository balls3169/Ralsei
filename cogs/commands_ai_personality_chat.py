"""
Free-chat cog. Ralsei replies via OpenRouter when @mentioned, DMed, or
when his name/nickname is used directly in a server message (e.g. "ralsei",
"ral", "raly") — the name-trigger is what makes this work reliably in
servers without requiring an explicit @ping every time, since this is
meant to be a server bot people talk to naturally, not just via DM.

IMPORTANT: this listener must ignore messages that are actual bot commands
(e.g. "!bake", "!battle"). discord.py dispatches on_message to every
registered listener AND separately runs command processing on the same
message — without an explicit check, both would fire, so typing "!bake"
in a DM (where every message is eligible) would both run the real !bake
command AND make free-chat treat "bake" as something you said in
conversation. We check whether the message resolves to a valid command
first and bail out immediately if so, letting the real command handle it
exclusively.

Tier context is passed in so his tone shifts naturally, and there's a
chance of a 4th-wall slip layered on top independent of tier.
"""

import re

import discord
from discord.ext import commands

from utils.relationship_tier_system import get_tier
from utils.ai_chat_openrouter_api import get_ralsei_reply
from utils.personality_fourth_wall_breaks import should_trigger, build_slip
from bot_config_and_keys import CREATOR_ID

TIER_CONTEXT = {
    "CREATOR": "You are talking to someone you trust completely — you're warmer and a little more open with them than with anyone else, occasionally letting your guard down.",
    "CLOSE": "You are talking to a close friend. You're comfortable, warm, a little more prone to blushing/flustered affection.",
    "NEUTRAL": "You are talking to someone you know but aren't deeply close with yet. Polite, warm, a little formal.",
    "SHY": "You are talking to someone you don't know very well yet. You're more anxious than usual — over-apologizing, hedging more, second-guessing yourself.",
}

# Word-boundary match so this doesn't false-trigger on words that merely
# contain these letters (e.g. "general", "mineral") — only whole-word uses
# of his name/nicknames count.
NAME_TRIGGER_PATTERN = re.compile(r"\b(ralsei|ral|raly)\b", re.IGNORECASE)


class RalseiChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Bail out entirely if this message is an actual bot command (e.g.
        # "!bake", "!battle rudinn") — otherwise free-chat would ALSO react
        # to it as if it were something you said in conversation, on top of
        # the real command running. get_context + ctx.valid is the correct
        # discord.py way to check this (respects the real command prefix,
        # aliases, etc. rather than a hardcoded string check).
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions if self.bot.user else False
        is_name_called = bool(NAME_TRIGGER_PATTERN.search(message.content))

        if not (is_dm or is_mentioned or is_name_called):
            return

        # Strip the mention out of the message so it's not confusing the model.
        content = message.content
        if self.bot.user:
            content = content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()

        if not content:
            return

        async with message.channel.typing():
            tier = await get_tier(message.author.id)
            context = TIER_CONTEXT.get(tier, TIER_CONTEXT["NEUTRAL"])

            reply = await get_ralsei_reply(content, extra_context=context)

            is_creator = CREATOR_ID and message.author.id == CREATOR_ID
            if should_trigger(content, is_creator=is_creator):
                reply += "\n\n" + build_slip(is_creator=is_creator)

        await message.reply(reply, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(RalseiChat(bot))
