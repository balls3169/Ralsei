"""
!castle_town — shows the server's shared Castle Town (per planning: one
collective town per Discord server, not per-user, matching canon where
there's a single town everyone contributes to).

!checkr <darkner> — mirrors the in-game CHECK command, works as a
standalone lookup/encyclopedia entry, not just inside battle.
"""

import discord
from discord.ext import commands

from utils.database_upstash_connection import storage
from data.lore_enemies_and_acts import ENEMIES


class CastleTown(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="castle_town")
    async def castle_town(self, ctx: commands.Context):
        """View the server's shared Castle Town — who's been recruited so far."""
        if not ctx.guild:
            await ctx.send("Castle Town only exists per-server — try this in a server, not a DM!")
            return

        recruits = await storage.get_guild_recruits(ctx.guild.id)
        lost = await storage.get_guild_lost(ctx.guild.id)

        embed = discord.Embed(
            title=f"🏰 {ctx.guild.name}'s Castle Town",
            description="Ralsei's home — populated by everyone this server has spared.",
            color=discord.Color.from_rgb(150, 200, 130),
        )

        if not recruits:
            embed.add_field(name="Residents", value="Just Ralsei, for now... it's a little lonely here.", inline=False)
        else:
            lines = []
            for enemy_key, count in recruits.items():
                display_name = ENEMIES.get(enemy_key, {}).get("name", enemy_key)
                lines.append(f"**{display_name}** — {count} recruited")
            embed.add_field(name="Residents", value="\n".join(lines), inline=False)

        if lost:
            lost_names = [ENEMIES.get(k, {}).get("name", k) for k in lost]
            embed.add_field(name="Lost (defeated violently, unrecruitable)", value=", ".join(lost_names), inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="checkr")
    async def checkr(self, ctx: commands.Context, *, darkner_name: str):
        """Check info on a Darkner by name (works like the in-battle CHECK)."""
        key = darkner_name.lower().replace(" ", "_")
        enemy = ENEMIES.get(key)
        if not enemy:
            await ctx.send(f"No record of a Darkner called `{darkner_name}`.")
            return

        check_act = next((a for a in enemy["acts"] if a["name"] == "Check"), None)
        description = check_act["flavor"] if check_act else "No further details recorded."

        embed = discord.Embed(title=f"CHECK: {enemy['name']}", description=description, color=discord.Color.from_rgb(100, 100, 200))
        embed.add_field(name="HP", value=str(enemy["hp"]))
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CastleTown(bot))
