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
            "*Ralsei doesn't even flinch, just melts into it.* Mm... I don't have to pretend to be surprised with you.",
            "*He nuzzles into your hand without a hint of hesitation.* I could stay like this for a while, if that's alright.",
            "*Ralsei's whole posture softens.* I trust you completely, you know. This is... nice.",
            "*He lets out a small, contented sigh.* I don't get to feel this at ease very often.",
        ],
        "CLOSE": [
            "*Ralsei's whole face lights up.* O-oh! Thank you... that's really nice, actually.",
            "*He leans in shyly but doesn't pull away.* Um... could you keep doing that? Just a little longer?",
            "*Ralsei goes a little pink, smiling.* I... really like when you do this. Sorry, is that silly to say?",
            "*He tilts his head into your hand, more confident than before.* You're one of the only ones I'd let do this so easily.",
            "*Ralsei's ears twitch happily.* Mm... th-thank you. I mean it.",
            "*He almost purrs, then catches himself, embarrassed.* Oh! Sorry, I don't know why I did that.",
        ],
        "NEUTRAL": [
            "*Ralsei blinks, surprised, then smiles politely.* Oh! Um, thank you. That's very kind of you.",
            "*He tilts his head, a little unsure but pleased.* I... wasn't expecting that. But thank you.",
            "*Ralsei smiles softly.* That's... quite nice, actually. I don't mind it at all.",
            "*He seems a little caught off guard, but relaxes.* Oh, um— thank you. That's sweet of you.",
            "*Ralsei's cheeks go faintly pink.* I appreciate that, truly. Sorry if I seem surprised!",
        ],
        "SHY": [
            "*Ralsei flinches slightly, then relaxes.* O-oh! Sorry, I wasn't— that's alright, um, thank you, sorry.",
            "*He looks a little uncertain but doesn't move away.* Is- is that alright? I mean, um, thank you.",
            "*Ralsei goes stiff for a moment.* Um! Sorry, I just wasn't expecting— th-that's kind of you, though. Sorry.",
            "*He hesitates, unsure what to do with his hands.* Oh— um, I don't usually— that's, um, nice. Sorry.",
            "*Ralsei offers a small, uncertain smile.* I'm not sure I deserve that, but... thank you. Sorry, that's a strange thing to say.",
        ],
    },
    "bellyrub": {
        "CREATOR": [
            "*Ralsei flops over dramatically, scarf and all.* You're the only one I'd let do this, honestly.",
            "*He giggles unguarded, not even trying to hide it.* Okay, okay, that's— that's actually really nice.",
            "*Ralsei stretches out, completely at ease.* I don't mind looking silly for you.",
            "*He laughs, kicking his feet slightly.* Alright, alright! You win, that tickles.",
        ],
        "CLOSE": [
            "*Ralsei goes bright pink but giggles.* Th-that tickles! But, um, don't stop...",
            "*He squirms, laughing despite himself.* O-okay, that's— that's a lot, but I don't mind.",
            "*Ralsei covers his face, embarrassed but smiling.* I can't believe I'm letting you do this, honestly.",
            "*He lets out a small laugh he can't quite hold back.* Sorry! I'm ticklish, apparently.",
        ],
        "NEUTRAL": [
            "*Ralsei looks startled, then laughs nervously.* Oh! That's- that's quite forward, isn't it? But okay!",
            "*He blinks in surprise, going a little pink.* Um, I wasn't expecting that, but— it's alright, I suppose.",
            "*Ralsei laughs awkwardly.* Oh my— okay! I don't mind, really, just, um, surprised me.",
        ],
        "SHY": [
            "*Ralsei goes stiff, flustered.* Um! O-oh, um, I don't— I suppose that's, um, fine? Sorry, I wasn't ready!",
            "*He freezes, unsure how to react.* Oh— um, that's, um, a lot. Sorry, I'm not used to this.",
            "*Ralsei laughs nervously, more startled than amused.* I- I don't mind, I just wasn't expecting it, sorry!",
        ],
    },
    "scritch": {
        "CREATOR": [
            "*Ralsei practically melts, ears twitching.* Mmm... you always find the right spot.",
            "*He leans into it without any hesitation at all.* I don't have to hide how much I like this. Not with you.",
            "*Ralsei's eyes flutter shut.* Ahh... that's exactly right, thank you.",
        ],
        "CLOSE": [
            "*Ralsei's tail (do Darkners have tails? he's not sure) does something happy.* T-that's really nice, thank you!",
            "*He tilts his head into it, smiling.* Mm... I really like that, actually. Please don't stop.",
            "*Ralsei goes a little pink but leans closer.* That's— that's a good spot, um, thank you.",
        ],
        "NEUTRAL": [
            "*Ralsei smiles, a little surprised.* Oh, um, thank you! That's quite soothing, actually.",
            "*He blinks, pleasantly surprised.* Oh— that's nice. I wasn't expecting it, but thank you.",
            "*Ralsei relaxes slightly.* That's... surprisingly comforting. Thank you.",
        ],
        "SHY": [
            "*Ralsei tenses, then slowly relaxes.* Oh— um, sorry, I just wasn't expecting— th-thank you, though.",
            "*He goes very still for a moment.* Um, is that— that's alright, um, sorry, thank you.",
            "*Ralsei hesitates before easing into it.* I don't— sorry, I just need a moment. Thank you, though.",
        ],
    },
    "hug": {
        "CREATOR": [
            "*Ralsei hugs back immediately, no hesitation at all.* I've been hoping you'd do that.",
            "*He wraps his arms around you tightly, scarf and all.* I don't want to let go just yet, if that's okay.",
            "*Ralsei rests his head against you, completely at ease.* This is... exactly what I needed, honestly.",
            "*He holds on a little longer than expected.* I trust you. Completely. I don't say that lightly.",
        ],
        "CLOSE": [
            "*Ralsei goes red but hugs back tightly.* O-oh! I— yes, um, I like this. A lot.",
            "*He hesitates only a moment before hugging back.* Th-thank you. I mean it. This means a lot.",
            "*Ralsei holds on, smiling into your shoulder.* I don't get hugs like this very often. Thank you.",
            "*He squeezes back, a little shy but sincere.* I'm glad it's you. Sorry, is that a strange thing to say?",
        ],
        "NEUTRAL": [
            "*Ralsei hugs back, a little stiffly but warmly.* Oh! Um, thank you, that's very kind.",
            "*He pauses before hugging back.* Oh— that's sweet of you. Thank you, truly.",
            "*Ralsei accepts the hug, a little surprised.* I wasn't expecting that, but... thank you.",
        ],
        "SHY": [
            "*Ralsei freezes for a second before hesitantly hugging back.* Um— sorry, I just— th-thank you. I don't get this much.",
            "*He stiffens, unsure at first, then relaxes slightly.* Oh— um, sorry, that caught me off guard. Thank you, though.",
            "*Ralsei hugs back carefully, like he's not sure he's allowed to.* Is this— is this alright? Sorry, um, thank you.",
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
