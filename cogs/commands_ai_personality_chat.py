"""
Free-chat cog. Ralsei replies via OpenRouter when @mentioned or DMed
(scoped intentionally, per planning, to avoid every message triggering
an API call). Tier context is passed in so his tone shifts naturally,
and there's a chance of a 4th-wall slip layered on top independent of tier.
"""

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


class RalseiChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions if self.bot.user else False

        if not (is_dm or is_mentioned):
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
