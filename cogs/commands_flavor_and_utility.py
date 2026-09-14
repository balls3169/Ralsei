"""
Extra flavor/utility commands: !bake, !fortune, !prophecy, !compliment,
!tp, !party, !save, !about.

Deliberately kept separate from commands_affection_pet_hug.py and
commands_battle_system.py so each file stays focused on one theme.
"""

import random
from datetime import datetime, timezone

import discord
from discord.ext import commands

from utils.database_upstash_connection import storage
from utils.relationship_tier_system import get_tier

# --- !bake ---

BAKE_OUTCOMES = [
    "*Ralsei pulls a perfect cake from the oven, practically glowing with pride.* I— I think this might be my best one yet!",
    "*Ralsei checks the oven and winces.* Oh no— it's a little burnt on top. Still tastes alright, I promise!",
    "*Something has gone comically wrong — the cake has risen to nearly twice his height.* Um... I may have added too much of something. Sorry!",
    "*Ralsei carefully frosts a simple, cozy-looking cake.* It's not fancy, but I made it with you in mind.",
    "*The cake collapses slightly in the middle the moment he takes it out.* Oh— that's alright, we'll just call it a very flat cake.",
    "*Ralsei beams, holding up a cake shaped almost perfectly like a heart.* I don't know how that happened, but I'm not complaining!",
]

BAKE_CREATOR_EXTRA = [
    "*Ralsei sets the first slice aside before anyone else can have it.* This one's yours. I insist.",
]

# --- !fortune (once per day per user) ---

FORTUNE_LINES = [
    "The tea leaves settle into a spiral. Something is circling back to you — pay attention when it does.",
    "I see... calm water. Whatever's been weighing on you may ease, soon.",
    "The leaves form a shape like a door. A choice is coming. You'll know it when you see it.",
    "Hm. The pattern is unclear today... perhaps that means today is simply yours to decide.",
    "I see two paths crossing. Someone you haven't spoken to in a while may reappear.",
    "The leaves are unusually still. Sometimes that just means: rest, today.",
    "There's a shape like a key in the cup. Something locked may come open soon.",
    "I see... hm. Actually, I think that's just a leaf. Sorry! Let's call it a fortune of ordinary days.",
]

# --- !prophecy ---
# Deliberately vague/ominous rather than explanatory, per the 4th-wall
# system's philosophy — the unease is the point, not exposition.

PROPHECY_LINES = [
    "\"When the Lightner's shadow falls twice upon the same door, the world will choose which one is real.\"",
    "\"Not all who wear the crown asked to be crowned.\"",
    "\"The one who counts the days does not always live inside them.\"",
    "\"Before the fountain opens, something will have already decided how it closes.\"",
    "\"There is a version of this where you already know how it ends. This may be that version.\"",
    "\"The prophecy does not name a hero. It only names a shape, and hopes someone fits it.\"",
]

# --- !compliment ---

COMPLIMENT_LINES = {
    "CREATOR": [
        "*Ralsei looks at you like it's obvious.* You've always been the one holding this all together, you know. I mean that.",
        "*He smiles warmly, no hesitation at all.* I don't think I say this enough — I'm glad it's you.",
    ],
    "CLOSE": [
        "*Ralsei fidgets, then says it anyway.* I think you're kinder than you give yourself credit for.",
        "*He smiles softly.* You always seem to know what to do. I admire that about you.",
    ],
    "NEUTRAL": [
        "*Ralsei considers for a moment.* You seem like a genuinely thoughtful person. I mean that.",
        "*He offers a polite, sincere smile.* I think you're doing better than you realize.",
    ],
    "SHY": [
        "*Ralsei hesitates, unsure if it's his place to say.* Um— I think you're doing just fine. Sorry, I hope that's alright to say.",
        "*He says it quickly, like he might lose his nerve.* You seem nice. Sorry! I just wanted to say that.",
    ],
}


def _today_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def is_new_day(last_date_str) -> bool:
    """Pure helper — True if last_date_str is missing or not today (UTC)."""
    if not last_date_str:
        return True
    return last_date_str != _today_str()


class FlavorAndUtility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bake")
    async def bake(self, ctx: commands.Context):
        """Ralsei bakes something for you."""
        tier = await get_tier(ctx.author.id)
        line = random.choice(BAKE_OUTCOMES)
        if tier == "CREATOR" and random.random() < 0.4:
            line += "\n" + random.choice(BAKE_CREATOR_EXTRA)
        await ctx.send(line)

    @commands.command(name="fortune", aliases=["teacup"])
    async def fortune(self, ctx: commands.Context):
        """Get your one-per-day tea leaf reading from Ralsei."""
        user_data = await storage.get_user(ctx.author.id)
        last_fortune_date = user_data.get("last_fortune_date")

        if not is_new_day(last_fortune_date):
            await ctx.send("*Ralsei gently shakes his head.* The leaves already spoke to you today. Come back tomorrow!")
            return

        user_data["last_fortune_date"] = _today_str()
        await storage.set_user(ctx.author.id, user_data)

        line = random.choice(FORTUNE_LINES)
        await ctx.send(f"*Ralsei swirls the tea leaves thoughtfully.* {line}")

    @commands.command(name="prophecy")
    async def prophecy(self, ctx: commands.Context):
        """Hear a cryptic prophecy fragment."""
        line = random.choice(PROPHECY_LINES)
        await ctx.send(f"*Ralsei's voice drops slightly, reciting something half-remembered.* {line}")

    @commands.command(name="compliment")
    async def compliment(self, ctx: commands.Context):
        """Ralsei compliments you, for once."""
        tier = await get_tier(ctx.author.id)
        pool = COMPLIMENT_LINES.get(tier, COMPLIMENT_LINES["NEUTRAL"])
        await ctx.send(random.choice(pool))

    @commands.command(name="tp")
    async def tp(self, ctx: commands.Context):
        """Check the party's shared TP, if a battle is active in this channel."""
        state = await storage.get_battle(ctx.channel.id)
        if not state or state.get("over"):
            await ctx.send("There's no battle happening right now, so there's no TP to check.")
            return
        tp, tp_max = state.get("tp", 0), state.get("tp_max", 100)
        bar_filled = int((tp / max(1, tp_max)) * 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        await ctx.send(f"**Party TP:** `{bar}` {tp}/{tp_max}")

    @commands.command(name="party")
    async def party(self, ctx: commands.Context):
        """Check the party's HP, if a battle is active in this channel."""
        state = await storage.get_battle(ctx.channel.id)
        if not state or state.get("over"):
            await ctx.send("There's no battle happening right now, so there's no party status to check.")
            return

        embed = discord.Embed(title="Party Status", color=discord.Color.from_rgb(150, 200, 130))
        for char, stats in state.get("party", {}).items():
            hp, max_hp = stats["hp"], stats["max_hp"]
            bar_filled = int((hp / max(1, max_hp)) * 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            embed.add_field(name=char.capitalize(), value=f"`{bar}` {hp}/{max_hp} HP", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="save")
    async def save(self, ctx: commands.Context):
        """A meta joke — Ralsei reacts to the idea of 'saving', but nothing actually happens."""
        lines = [
            "*Ralsei glances around, a little unsettled.* Did you feel that? Like... something remembering this moment?",
            "*He smiles, but it doesn't quite reach his eyes.* You don't need to do that here. Not yet, anyway.",
            "*Ralsei tilts his head.* I'm not sure saving works like that outside of... well. Never mind!",
        ]
        await ctx.send(random.choice(lines))

    @commands.command(name="about", aliases=["lore"])
    async def about(self, ctx: commands.Context):
        """A short in-character introduction to who Ralsei is."""
        embed = discord.Embed(
            title="About Ralsei",
            description=(
                "*Ralsei gives a small, formal bow.*\n\n"
                "I'm Ralsei, Prince of the Dark World — well, one of them, anyway. "
                "I try to keep the peace where I can, and I'd much rather talk things out than fight. "
                "I also bake, if that's of any interest to you.\n\n"
                "If you'd like, you can use `!ralsei_help` to see everything I can do here."
            ),
            color=discord.Color.from_rgb(150, 200, 130),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FlavorAndUtility(bot))
