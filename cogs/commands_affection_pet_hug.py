"""
Affection commands: !pet, !bellyrub, !scritch, !hug

Each has its own response pool per tier (CREATOR/CLOSE/NEUTRAL/SHY).
Structure mirrors Yarnaby's approach but reworked for Ralsei's voice
(per planning: SHY tier is anxious/over-apologetic, never cold).

These are the response pools worth expanding the most as you playtest —
feel free to add many more lines per tier/command, this is just a
starting set to get the mechanism working end to end.
"""

import discord
from discord.ext import commands

from utils.relationship_tier_system import get_tier, add_affection, cooldown_remaining

# --- Response pools ---
# Structure: RESPONSES[command][tier] -> list[str]

RESPONSES = {
    "pet": {
        "CREATOR": [
            "*Ralsei leans into your hand immediately, ears drooping happily.* Oh— ! I always feel so at ease when it's you.",
            "*He closes his eyes, completely relaxed.* You always know just how I like it.",
        ],
        "CLOSE": [
            "*Ralsei's whole face lights up.* O-oh! Thank you... that's really nice, actually.",
            "*He leans in shyly but doesn't pull away.* Um... could you keep doing that? Just a little longer?",
        ],
        "NEUTRAL": [
            "*Ralsei blinks, surprised, then smiles politely.* Oh! Um, thank you. That's very kind of you.",
            "*He tilts his head, a little unsure but pleased.* I... wasn't expecting that. But thank you.",
        ],
        "SHY": [
            "*Ralsei flinches slightly, then relaxes.* O-oh! Sorry, I wasn't— that's alright, um, thank you, sorry.",
            "*He looks a little uncertain but doesn't move away.* Is- is that alright? I mean, um, thank you.",
        ],
    },
    "bellyrub": {
        "CREATOR": [
            "*Ralsei flops over dramatically, scarf and all.* You're the only one I'd let do this, honestly.",
        ],
        "CLOSE": [
            "*Ralsei goes bright pink but giggles.* Th-that tickles! But, um, don't stop...",
        ],
        "NEUTRAL": [
            "*Ralsei looks startled, then laughs nervously.* Oh! That's- that's quite forward, isn't it? But okay!",
        ],
        "SHY": [
            "*Ralsei goes stiff, flustered.* Um! O-oh, um, I don't— I suppose that's, um, fine? Sorry, I wasn't ready!",
        ],
    },
    "scritch": {
        "CREATOR": [
            "*Ralsei practically melts, ears twitching.* Mmm... you always find the right spot.",
        ],
        "CLOSE": [
            "*Ralsei's tail (do Darkners have tails? he's not sure) does something happy.* T-that's really nice, thank you!",
        ],
        "NEUTRAL": [
            "*Ralsei smiles, a little surprised.* Oh, um, thank you! That's quite soothing, actually.",
        ],
        "SHY": [
            "*Ralsei tenses, then slowly relaxes.* Oh— um, sorry, I just wasn't expecting— th-thank you, though.",
        ],
    },
    "hug": {
        "CREATOR": [
            "*Ralsei hugs back immediately, no hesitation at all.* I've been hoping you'd do that.",
        ],
        "CLOSE": [
            "*Ralsei goes red but hugs back tightly.* O-oh! I— yes, um, I like this. A lot.",
        ],
        "NEUTRAL": [
            "*Ralsei hugs back, a little stiffly but warmly.* Oh! Um, thank you, that's very kind.",
        ],
        "SHY": [
            "*Ralsei freezes for a second before hesitantly hugging back.* Um— sorry, I just— th-thank you. I don't get this much.",
        ],
    },
}


class Affection(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _handle(self, ctx: commands.Context, command_name: str):
        applied, tier = await add_affection(ctx.author.id)
        pool = RESPONSES[command_name][tier]

        import random
        line = random.choice(pool)

        if not applied and tier != "CREATOR":
            remaining = await cooldown_remaining(ctx.author.id)
            line += f"\n\n*(no extra affection gained — try again in {int(remaining)}s)*"

        await ctx.send(line)

    @commands.command(name="pet")
    async def pet(self, ctx: commands.Context):
        """Pet Ralsei on the head."""
        await self._handle(ctx, "pet")

    @commands.command(name="bellyrub")
    async def bellyrub(self, ctx: commands.Context):
        """Give Ralsei a belly rub."""
        await self._handle(ctx, "bellyrub")

    @commands.command(name="scritch")
    async def scritch(self, ctx: commands.Context):
        """Scritch Ralsei behind the ears/horns."""
        await self._handle(ctx, "scritch")

    @commands.command(name="hug")
    async def hug(self, ctx: commands.Context):
        """Hug Ralsei."""
        await self._handle(ctx, "hug")


async def setup(bot: commands.Bot):
    await bot.add_cog(Affection(bot))
