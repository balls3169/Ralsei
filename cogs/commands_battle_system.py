"""
!battle — the core battle engine.

Flow: !battle <enemy> starts a fight -> character select (Kris/Susie/Ralsei)
-> that character's action set -> resolve -> regenerate image -> repeat.

Shared TP pool across the party (per planning). Per-enemy ACT menus come
from data/enemies.py, not a universal list. SPARE only works once mercy
hits the enemy's threshold; TIRED enemies can only be resolved by Ralsei's
Pacify. X-Flirt follows the canon fail/fail/succeed structure where defined.

This is a working skeleton, not the full 700-enemy roster — add more
enemies in data/enemies.py following the existing shape and everything
here will "just work" for them too.
"""

import random
import discord
from discord.ext import commands

from utils.database_upstash_connection import storage
from utils.battle_image_renderer import render_battle
from data.lore_enemies_and_acts import ENEMIES
from bot_config_and_keys import PACIFY_TP_COST, DUAL_HEAL_TP_COST, TP_GAIN_DEFEND, TP_GAIN_HIT_TAKEN, SHARED_TP_MAX

STARTING_PARTY = {
    "kris": {"hp": 100, "max_hp": 100},
    "susie": {"hp": 140, "max_hp": 140},
    "ralsei": {"hp": 80, "max_hp": 80},
}


def new_battle_state(enemy_key: str) -> dict:
    enemy = ENEMIES[enemy_key]
    return {
        "enemy_key": enemy_key,
        "enemy_name": enemy["name"],
        "enemy_hp": enemy["hp"],
        "enemy_max_hp": enemy["hp"],
        "mercy_percent": 0,
        "mercy_needed": enemy["mercy_needed"],
        "tired": False,
        "tp": 0,
        "tp_max": SHARED_TP_MAX,
        "party": {k: dict(v) for k, v in STARTING_PARTY.items()},
        "log_line": random.choice(enemy["encounter_lines"]),
        "flirt_used": {"susie": False, "ralsei": False},
        "over": False,
        "won": False,
    }


async def send_battle_image(channel: discord.abc.Messageable, state: dict, view: discord.ui.View | None = None):
    buf = render_battle(state)
    file = discord.File(buf, filename="battle.png")
    return await channel.send(file=file, view=view) if view else await channel.send(file=file)


# --- UI Views ---

class CharacterSelectView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=120)
        self.channel_id = channel_id

    @discord.ui.button(label="Kris", style=discord.ButtonStyle.primary)
    async def kris(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, "kris")

    @discord.ui.button(label="Susie", style=discord.ButtonStyle.danger)
    async def susie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, "susie")

    @discord.ui.button(label="Ralsei", style=discord.ButtonStyle.success)
    async def ralsei(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, "ralsei")

    async def _pick(self, interaction: discord.Interaction, character: str):
        state = await storage.get_battle(self.channel_id)
        if not state or state.get("over"):
            await interaction.response.send_message("There's no battle happening right now!", ephemeral=True)
            return
        view = ActionSelectView(self.channel_id, character)
        await interaction.response.edit_message(
            content=f"**{character.capitalize()}** is up. What do you want to do?",
            view=view,
        )


class ActionSelectView(discord.ui.View):
    def __init__(self, channel_id: int, character: str):
        super().__init__(timeout=120)
        self.channel_id = channel_id
        self.character = character

        self.add_item(ActionButton("FIGHT", discord.ButtonStyle.danger, channel_id, character, "fight"))

        if character == "kris":
            self.add_item(ActionButton("ACT", discord.ButtonStyle.primary, channel_id, character, "act"))
            self.add_item(ActionButton("SPARE", discord.ButtonStyle.success, channel_id, character, "spare"))
        else:
            self.add_item(ActionButton("MAGIC", discord.ButtonStyle.primary, channel_id, character, "magic"))
            special_label = "S-Action" if character == "susie" else "R-Action"
            self.add_item(ActionButton(special_label, discord.ButtonStyle.secondary, channel_id, character, "special"))

        self.add_item(ActionButton("ITEM", discord.ButtonStyle.secondary, channel_id, character, "item"))
        self.add_item(ActionButton("DEFEND", discord.ButtonStyle.secondary, channel_id, character, "defend"))


class ActionButton(discord.ui.Button):
    def __init__(self, label, style, channel_id, character, action):
        super().__init__(label=label, style=style)
        self.channel_id = channel_id
        self.character = character
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        state = await storage.get_battle(self.channel_id)
        if not state or state.get("over"):
            await interaction.response.send_message("There's no battle happening right now!", ephemeral=True)
            return

        if self.action == "act" and self.character == "kris":
            enemy = ENEMIES[state["enemy_key"]]
            view = ActMenuView(self.channel_id, enemy["acts"])
            await interaction.response.edit_message(content="Choose an ACT:", view=view)
            return

        guild_id = interaction.guild_id
        result_text = await resolve_action(state, self.character, self.action, guild_id=guild_id)
        if not state["over"]:
            result_text += apply_enemy_turn(state)
        await storage.set_battle(self.channel_id, state)

        if state["over"]:
            view = None
            if not state["won"]:
                view = RetryView(self.channel_id)
        else:
            view = CharacterSelectView(self.channel_id)

        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")
        await interaction.response.edit_message(content=result_text, attachments=[file], view=view)


class ActMenuView(discord.ui.View):
    def __init__(self, channel_id: int, acts: list):
        super().__init__(timeout=120)
        for act in acts:
            self.add_item(ActButton(channel_id, act))


class ActButton(discord.ui.Button):
    def __init__(self, channel_id, act):
        super().__init__(label=act["name"], style=discord.ButtonStyle.primary)
        self.channel_id = channel_id
        self.act = act

    async def callback(self, interaction: discord.Interaction):
        state = await storage.get_battle(self.channel_id)
        if not state or state.get("over"):
            await interaction.response.send_message("There's no battle happening right now!", ephemeral=True)
            return

        result_text = await resolve_act(state, "kris", self.act)
        if not state["over"]:
            result_text += apply_enemy_turn(state)
        await storage.set_battle(self.channel_id, state)

        view = None if state["over"] else CharacterSelectView(self.channel_id)
        if state["over"] and not state["won"]:
            view = RetryView(self.channel_id)

        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")
        await interaction.response.edit_message(content=result_text, attachments=[file], view=view)


class RetryView(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=300)
        self.channel_id = channel_id

    @discord.ui.button(label="Retry Battle", style=discord.ButtonStyle.danger)
    async def retry(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = await storage.get_battle(self.channel_id)
        if current and not current.get("over"):
            await interaction.response.send_message("A new battle is already in progress in this channel!", ephemeral=True)
            return

        last_key = await storage.get_json(f"battle:{self.channel_id}:last_enemy")
        if not last_key:
            await interaction.response.send_message("Nothing to retry!", ephemeral=True)
            return
        state = new_battle_state(last_key)
        await storage.set_battle(self.channel_id, state)
        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")
        await interaction.response.edit_message(content=state["log_line"], attachments=[file], view=CharacterSelectView(self.channel_id))


# --- Resolution logic ---

async def mark_recruited(guild_id: int, enemy_key: str):
    recruits = await storage.get_guild_recruits(guild_id)
    recruits[enemy_key] = recruits.get(enemy_key, 0) + 1
    await storage.set_guild_recruits(guild_id, recruits)


async def mark_lost(guild_id: int, enemy_key: str):
    lost = await storage.get_guild_lost(guild_id)
    if enemy_key not in lost:
        lost.append(enemy_key)
        await storage.set_guild_lost(guild_id, lost)


def apply_enemy_turn(state: dict) -> str:
    """
    Enemy attacks a random alive party member after the player's action
    resolves. Without this, party HP never changes and a battle can never
    actually be lost — !battle_retry's "you lost" path would be dead code.
    TIRED enemies don't act (they're worn out, per canon flavor).
    """
    if state.get("tired"):
        return ""

    alive = [k for k, v in state["party"].items() if v["hp"] > 0]
    if not alive:
        return ""

    target = random.choice(alive)
    dmg = random.randint(5, 18)
    state["party"][target]["hp"] = max(0, state["party"][target]["hp"] - dmg)
    state["tp"] = min(state["tp_max"], state["tp"] + TP_GAIN_HIT_TAKEN)

    text = f"\n{state['enemy_name']} attacks {target.capitalize()} for {dmg} damage!"

    if all(v["hp"] <= 0 for v in state["party"].values()):
        state["over"] = True
        state["won"] = False
        text += f"\nThe whole party is down... {state['enemy_name']} overwhelms you."

    return text


async def resolve_action(state: dict, character: str, action: str, guild_id: int | None = None) -> str:
    enemy = ENEMIES[state["enemy_key"]]

    if action == "fight":
        dmg = random.randint(15, 30) if character == "susie" else random.randint(5, 15)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        text = f"{character.capitalize()} attacks! {enemy['name']} takes {dmg} damage."
        # Fighting to defeat = violent kill = enemy becomes LOST (per planning, guard-railed elsewhere).
        if state["enemy_hp"] <= 0:
            state["over"] = True
            state["won"] = True
            state["violent"] = True
            if guild_id:
                await mark_lost(guild_id, state["enemy_key"])
            text += f"\n{enemy['name']} is defeated... violently. (This enemy type is now LOST and can't be recruited.)"
        return text

    if action == "defend":
        state["tp"] = min(state["tp_max"], state["tp"] + TP_GAIN_DEFEND)
        return f"{character.capitalize()} defends, building up the party's TP."

    if action == "spare":
        if state["tired"]:
            return f"{enemy['name']} is TIRED — SPARE won't work. Only Ralsei's Pacify can end this peacefully now."
        if state["mercy_percent"] >= state["mercy_needed"]:
            state["over"] = True
            state["won"] = True
            if guild_id:
                await mark_recruited(guild_id, state["enemy_key"])
            return random.choice(enemy["spare_lines"]) + "\n*(Recruited to Castle Town!)*"
        return f"Not yet... {enemy['name']}'s mercy isn't full. Keep using ACT."

    if action == "item":
        return "*(Item system not implemented yet — plug in your item logic here.)*"

    if action == "magic":
        if character == "ralsei":
            if state["tp"] >= PACIFY_TP_COST and state["tired"]:
                state["tp"] -= PACIFY_TP_COST
                state["over"] = True
                state["won"] = True
                if guild_id:
                    await mark_recruited(guild_id, state["enemy_key"])
                return f"Ralsei casts Pacify! {random.choice(enemy['tired_lines'])} " + random.choice(enemy["spare_lines"]) + "\n*(Recruited to Castle Town!)*"
            if state["tp"] >= DUAL_HEAL_TP_COST:
                state["tp"] -= DUAL_HEAL_TP_COST
                for c in state["party"].values():
                    c["hp"] = c["max_hp"]
                return "Ralsei casts Heal Prayer! The whole party feels better."
            return "Not enough TP to cast anything useful right now."
        if character == "susie":
            dmg = random.randint(20, 35)
            state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
            return f"Susie casts Rude Buster! {enemy['name']} takes {dmg} damage."

    if action == "special":
        # S-Action / R-Action placeholders — flavor-only for now.
        if character == "susie":
            return "Susie does her own thing, refusing to wait for permission. (S-Action — customize per enemy!)"
        if character == "ralsei":
            return "Ralsei quietly does something supportive off to the side. (R-Action — customize per enemy!)"

    return "...nothing happens."


async def resolve_act(state: dict, character: str, act: dict) -> str:
    enemy = ENEMIES[state["enemy_key"]]

    if act["name"] == "X-Flirt" and enemy.get("flirt_sequence"):
        seq = enemy["flirt_sequence"]
        # Determine who's "using" it this turn based on prior attempts, per canon order.
        if not state["flirt_used"]["susie"]:
            state["flirt_used"]["susie"] = True
            return seq["susie"]["line"]
        if not state["flirt_used"]["ralsei"]:
            state["flirt_used"]["ralsei"] = True
            return seq["ralsei"]["line"]
        # Kris's attempt succeeds.
        gain = seq["kris"].get("mercy_gain", 50)
        state["mercy_percent"] = min(100, state["mercy_percent"] + gain)
        return seq["kris"]["line"]

    state["mercy_percent"] = min(100, state["mercy_percent"] + act["mercy_gain"])
    text = act["flavor"] or f"{act['name']} doesn't seem to do much here."
    if act.get("causes_tired"):
        state["tired"] = True
        text += " " + random.choice(enemy["tired_lines"])
    return text


class Battle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="battle")
    async def battle(self, ctx: commands.Context, enemy_key: str = "rudinn"):
        """Start a battle. Usage: !battle rudinn"""
        enemy_key = enemy_key.lower()
        if enemy_key not in ENEMIES:
            await ctx.send(f"Unknown enemy `{enemy_key}`. Available: {', '.join(ENEMIES.keys())}")
            return

        existing = await storage.get_battle(ctx.channel.id)
        if existing and not existing.get("over"):
            await ctx.send("There's already a battle in progress in this channel!")
            return

        state = new_battle_state(enemy_key)
        await storage.set_battle(ctx.channel.id, state)
        await storage.set_json(f"battle:{ctx.channel.id}:last_enemy", enemy_key)

        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")
        await ctx.send(content=state["log_line"], file=file, view=CharacterSelectView(ctx.channel.id))

    @commands.command(name="battle_retry")
    async def battle_retry(self, ctx: commands.Context):
        """Retry the last battle in this channel."""
        last_key = await storage.get_json(f"battle:{ctx.channel.id}:last_enemy")
        if not last_key:
            await ctx.send("No previous battle to retry!")
            return
        state = new_battle_state(last_key)
        await storage.set_battle(ctx.channel.id, state)
        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")
        await ctx.send(content=state["log_line"], file=file, view=CharacterSelectView(ctx.channel.id))


async def setup(bot: commands.Bot):
    await bot.add_cog(Battle(bot))
