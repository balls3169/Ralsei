"""
!battle — the core battle engine.

Flow (per planning, redesigned to match real Deltarune more closely):
  1. !battle <enemy> starts a fight.
  2. Pick an action for EACH of Kris, Susie, and Ralsei (queued, not resolved
     immediately) — mirrors choosing the whole party's moves before the
     turn plays out.
  3. Once all three are chosen, hit "Confirm Turn" — all three actions
     resolve in order (Kris, Susie, Ralsei).
  4. If the fight isn't over, the enemy telegraphs an attack and you must
     pick the safe dodge option within a short time limit. Real bullet-hell
     movement isn't possible over Discord, so this is the turn-based
     equivalent: react to the telegraph, guess/remember the right lane,
     beat the clock. Wrong pick or timeout = you get hit.
  5. Loop back to step 2 for the next turn.

Shared TP pool across the party (per planning). Per-enemy ACT menus and
attack patterns come from data/lore_enemies_and_acts.py — add more enemies
there following the existing shape and everything here will "just work"
for them too.
"""

import random
import discord
from discord.ext import commands

from utils.database_upstash_connection import storage
from utils.battle_image_renderer import render_battle
from data.lore_enemies_and_acts import ENEMIES
from bot_config_and_keys import (
    PACIFY_TP_COST, DUAL_HEAL_TP_COST, TP_GAIN_DEFEND, TP_GAIN_HIT_TAKEN, SHARED_TP_MAX,
    DODGE_TIMEOUT_BASE, DODGE_TIMEOUT_FLOOR, DODGE_TIMEOUT_STEP_PER_TURN,
    GRAZE_DAMAGE_MULTIPLIER_NEAR, GRAZE_DAMAGE_MULTIPLIER_FAR, GRAZE_TP_BONUS, CLEAN_DODGE_TP_BONUS,
    FIGHT_CRIT_CHANCE, FIGHT_CRIT_MULTIPLIER,
)

STARTING_PARTY = {
    "kris": {"hp": 100, "max_hp": 100},
    "susie": {"hp": 140, "max_hp": 140},
    "ralsei": {"hp": 80, "max_hp": 80},
}

CHARACTERS = ["kris", "susie", "ralsei"]

# Generic fallback attack pattern for any enemy that doesn't define its own
# attack_patterns list — keeps the dodge system from crashing on new enemies
# you add later before you've written custom patterns for them.
DEFAULT_ATTACK_PATTERNS = [
    {
        "name": "Lunge",
        "telegraph": "The enemy lunges forward, aiming for one side!",
        "options": ["left", "right"],
        "damage": 12,
    }
]


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
        "pending_actions": {"kris": None, "susie": None, "ralsei": None},
        "turn_number": 0,
        "over": False,
        "won": False,
    }


def _describe_pending(pending):
    if not pending:
        return "choose action"
    if pending["action"] == "act":
        return f"ACT: {pending['act_name']}"
    return pending["action"].upper()


def turn_plan_text(state: dict) -> str:
    lines = [state.get("log_line", "")]
    lines.append("")
    lines.append("Choose an action for each party member, then Confirm Turn:")
    for char in CHARACTERS:
        lines.append(f"  {char.capitalize()}: {_describe_pending(state['pending_actions'].get(char))}")
    return "\n".join(lines)


# --- Turn planning UI (character select -> per-character action -> back to plan) ---

class TurnPlanView(discord.ui.View):
    def __init__(self, channel_id: int, pending_actions: dict):
        super().__init__(timeout=180)
        self.channel_id = channel_id

        styles = {"kris": discord.ButtonStyle.primary, "susie": discord.ButtonStyle.danger, "ralsei": discord.ButtonStyle.success}
        for char in CHARACTERS:
            label = f"{char.capitalize()}: {_describe_pending(pending_actions.get(char))}"
            self.add_item(CharacterPickButton(channel_id, char, label, styles[char]))

        if all(pending_actions.get(c) for c in CHARACTERS):
            self.add_item(ConfirmTurnButton(channel_id))


class CharacterPickButton(discord.ui.Button):
    def __init__(self, channel_id, character, label, style):
        super().__init__(label=label, style=style, row=CHARACTERS.index(character))
        self.channel_id = channel_id
        self.character = character

    async def callback(self, interaction: discord.Interaction):
        state = await storage.get_battle(self.channel_id)
        if not state or state.get("over"):
            await interaction.response.send_message("There's no battle happening right now!", ephemeral=True)
            return
        view = ActionSelectView(self.channel_id, self.character)
        await interaction.response.edit_message(
            content=f"What should **{self.character.capitalize()}** do this turn?",
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
        self.add_item(BackButton(channel_id))


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
            await interaction.response.edit_message(content="Choose an ACT for Kris:", view=view)
            return

        state["pending_actions"][self.character] = {"action": self.action}
        await storage.set_battle(self.channel_id, state)

        view = TurnPlanView(self.channel_id, state["pending_actions"])
        await interaction.response.edit_message(content=turn_plan_text(state), view=view)


class ActMenuView(discord.ui.View):
    def __init__(self, channel_id: int, acts: list):
        super().__init__(timeout=120)
        for act in acts:
            self.add_item(ActButton(channel_id, act))
        self.add_item(BackButton(channel_id))


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

        state["pending_actions"]["kris"] = {"action": "act", "act_name": self.act["name"]}
        await storage.set_battle(self.channel_id, state)

        view = TurnPlanView(self.channel_id, state["pending_actions"])
        await interaction.response.edit_message(content=turn_plan_text(state), view=view)


class BackButton(discord.ui.Button):
    def __init__(self, channel_id):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=4)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        state = await storage.get_battle(self.channel_id)
        if not state or state.get("over"):
            await interaction.response.send_message("There's no battle happening right now!", ephemeral=True)
            return
        view = TurnPlanView(self.channel_id, state["pending_actions"])
        await interaction.response.edit_message(content=turn_plan_text(state), view=view)


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
        await interaction.response.edit_message(
            content=turn_plan_text(state), attachments=[file], view=TurnPlanView(self.channel_id, state["pending_actions"])
        )


# --- Dodge mini-game ---

class DodgeView(discord.ui.View):
    def __init__(self, options: list, timeout: float = 12):
        super().__init__(timeout=timeout)
        self.choice = None
        for opt in options:
            self.add_item(DodgeButton(opt))


class DodgeButton(discord.ui.Button):
    def __init__(self, option: str):
        super().__init__(label=option.capitalize(), style=discord.ButtonStyle.primary)
        self.option = option

    async def callback(self, interaction: discord.Interaction):
        # Acknowledge silently — the real outcome is shown afterward by the
        # code that's waiting on this view via `await dodge_view.wait()`.
        await interaction.response.defer()
        self.view.choice = self.option
        self.view.stop()


def pick_attack_pattern(enemy: dict):
    """Returns a pattern dict (safe option is now picked per-hit, since
    multi-hit patterns need a fresh safe lane for each individual hit)."""
    patterns = enemy.get("attack_patterns") or DEFAULT_ATTACK_PATTERNS
    return random.choice(patterns)


def dodge_timeout_for_turn(turn_number: int) -> float:
    """Dodge windows shrink slightly as a fight drags on, building tension,
    but never go below the floor."""
    return max(DODGE_TIMEOUT_FLOOR, DODGE_TIMEOUT_BASE - turn_number * DODGE_TIMEOUT_STEP_PER_TURN)


def lane_damage_multiplier(options: list, safe_option: str, choice) -> float:
    """
    1.0 = full hit, 0.0 = fully dodged, in between = a "graze" (partial
    miss). Only lanes with 3+ options get partial credit for picking a
    lane ADJACENT to the safe one — binary lanes (e.g. duck/jump) have no
    "adjacent" option, so any wrong pick there is a full hit, same as
    before. This mirrors Deltarune's real graze mechanic, where nearly
    avoiding a bullet still counts for something.
    """
    if choice is None:
        return 1.0  # timeout — no positioning info, treat as a full miss
    if choice == safe_option:
        return 0.0
    if len(options) < 3:
        return 1.0

    safe_idx = options.index(safe_option)
    choice_idx = options.index(choice)
    max_dist = len(options) - 1
    dist = abs(safe_idx - choice_idx)
    frac = dist / max_dist
    # Closest wrong lane -> GRAZE_DAMAGE_MULTIPLIER_NEAR, furthest -> _FAR.
    return GRAZE_DAMAGE_MULTIPLIER_NEAR + (GRAZE_DAMAGE_MULTIPLIER_FAR - GRAZE_DAMAGE_MULTIPLIER_NEAR) * frac


def apply_single_hit(state: dict, pattern: dict, safe_option: str, choice, hit_label: str = "") -> str:
    """
    Mutates state (damage/TP/over/won) based on one hit's dodge result.
    choice=None means the player didn't answer in time (timeout).
    Pure logic, no Discord objects involved, so this is unit-testable.
    Returns the outcome text for this single hit.
    """
    enemy_name = state["enemy_name"]
    multiplier = lane_damage_multiplier(pattern["options"], safe_option, choice)
    label = f" ({hit_label})" if hit_label else ""

    if multiplier <= 0.0:
        state["tp"] = min(state["tp_max"], state["tp"] + CLEAN_DODGE_TP_BONUS)
        return f"You dodge {enemy_name}'s {pattern['name']}{label} perfectly!"

    if choice is None:
        outcome = f"You hesitated too long! {enemy_name}'s {pattern['name']}{label} connects!"
    elif multiplier < 1.0:
        # A graze — nearly dodged it. Reward TP for the close call, like
        # Deltarune's real graze mechanic, even though some damage lands.
        outcome = f"Close! You almost dodge {enemy_name}'s {pattern['name']}{label} — just grazed."
        state["tp"] = min(state["tp_max"], state["tp"] + GRAZE_TP_BONUS)
    else:
        outcome = f"Wrong way! {enemy_name}'s {pattern['name']}{label} hits!"

    alive = [k for k, v in state["party"].items() if v["hp"] > 0]
    if not alive:
        return outcome

    target = random.choice(alive)
    dmg = max(1, round(pattern["damage"] * multiplier))
    state["party"][target]["hp"] = max(0, state["party"][target]["hp"] - dmg)
    state["tp"] = min(state["tp_max"], state["tp"] + TP_GAIN_HIT_TAKEN)
    outcome += f"\n{target.capitalize()} takes {dmg} damage!"

    if all(v["hp"] <= 0 for v in state["party"].values()):
        state["over"] = True
        state["won"] = False
        outcome += f"\nThe whole party is down... {enemy_name} overwhelms you."

    return outcome


class ConfirmTurnButton(discord.ui.Button):
    def __init__(self, channel_id):
        super().__init__(label="Confirm Turn", style=discord.ButtonStyle.success, row=3)
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        state = await storage.get_battle(self.channel_id)
        if not state or state.get("over"):
            await interaction.response.send_message("There's no battle happening right now!", ephemeral=True)
            return

        state["turn_number"] = state.get("turn_number", 0) + 1

        guild_id = interaction.guild_id
        party_text = await resolve_full_party_turn(state, guild_id)
        await storage.set_battle(self.channel_id, state)

        # Case 1: the party's own actions already ended the fight (enemy
        # defeated or spared) — no enemy counterattack needed.
        if state["over"]:
            view = None if state["won"] else RetryView(self.channel_id)
            buf = render_battle(state)
            file = discord.File(buf, filename="battle.png")
            await interaction.response.edit_message(content=party_text, attachments=[file], view=view)
            return

        # Case 2: enemy is TIRED and skips its turn entirely.
        if state.get("tired"):
            await storage.set_battle(self.channel_id, state)
            buf = render_battle(state)
            file = discord.File(buf, filename="battle.png")
            await interaction.response.edit_message(
                content=party_text, attachments=[file], view=TurnPlanView(self.channel_id, state["pending_actions"])
            )
            return

        # Case 3: enemy attacks — show the telegraph + dodge buttons, wait
        # for the player's pick (or timeout), then apply the outcome.
        # Patterns with "hits" > 1 fire multiple times in a row, each
        # needing its own dodge pick with a freshly randomized safe lane.
        enemy = ENEMIES[state["enemy_key"]]
        pattern = pick_attack_pattern(enemy)
        total_hits = pattern.get("hits", 1)
        timeout = dodge_timeout_for_turn(state["turn_number"])

        outcome_texts = []
        responded = False  # tracks whether interaction.response has been used yet

        for hit_index in range(total_hits):
            if state["over"]:
                break

            safe_option = random.choice(pattern["options"])
            dodge_view = DodgeView(pattern["options"], timeout=timeout)

            hit_label = f"hit {hit_index + 1}/{total_hits}" if total_hits > 1 else ""
            countdown = int(timeout)
            telegraph_text = (
                party_text + ("\n\n" + "\n\n".join(outcome_texts) if outcome_texts else "")
                + "\n\n" + pattern["telegraph"]
                + (f" ({hit_label})" if hit_label else "")
                + f"\n**Choose where to dodge!** ({countdown} seconds)"
            )

            buf = render_battle(state)
            file = discord.File(buf, filename="battle.png")

            if not responded:
                await interaction.response.edit_message(content=telegraph_text, attachments=[file], view=dodge_view)
                responded = True
            else:
                msg = await interaction.original_response()
                await msg.edit(content=telegraph_text, attachments=[file], view=dodge_view)

            await dodge_view.wait()

            outcome_texts.append(apply_single_hit(state, pattern, safe_option, dodge_view.choice, hit_label))
            await storage.set_battle(self.channel_id, state)

        final_view = None
        if state["over"]:
            if not state["won"]:
                final_view = RetryView(self.channel_id)
        else:
            final_view = TurnPlanView(self.channel_id, state["pending_actions"])

        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")

        final_text = party_text + "\n\n" + "\n\n".join(outcome_texts)
        msg = await interaction.original_response()
        await msg.edit(content=final_text, attachments=[file], view=final_view)


# --- Resolution logic (per-character actions) ---

async def mark_recruited(guild_id: int, enemy_key: str):
    recruits = await storage.get_guild_recruits(guild_id)
    recruits[enemy_key] = recruits.get(enemy_key, 0) + 1
    await storage.set_guild_recruits(guild_id, recruits)


async def mark_lost(guild_id: int, enemy_key: str):
    lost = await storage.get_guild_lost(guild_id)
    if enemy_key not in lost:
        lost.append(enemy_key)
        await storage.set_guild_lost(guild_id, lost)


async def resolve_full_party_turn(state: dict, guild_id=None) -> str:
    """
    Resolves all three characters' queued actions in order (Kris, Susie,
    Ralsei), stopping early if the battle ends partway through (e.g. Kris's
    action already defeats/spares the enemy — Susie and Ralsei don't get
    to act on a fight that's already over). Clears pending_actions for the
    next turn regardless of outcome.
    """
    texts = []
    enemy = ENEMIES[state["enemy_key"]]

    for character in CHARACTERS:
        if state["over"]:
            break
        pending = state["pending_actions"].get(character)
        if not pending:
            continue  # shouldn't happen (Confirm Turn only shows once all 3 are set)

        if pending["action"] == "act":
            act = next((a for a in enemy["acts"] if a["name"] == pending["act_name"]), None)
            if act:
                texts.append(await resolve_act(state, character, act))
        else:
            texts.append(await resolve_action(state, character, pending["action"], guild_id=guild_id))

    state["pending_actions"] = {"kris": None, "susie": None, "ralsei": None}
    return "\n".join(texts)


async def resolve_action(state: dict, character: str, action: str, guild_id=None) -> str:
    enemy = ENEMIES[state["enemy_key"]]

    if action == "fight":
        dmg = random.randint(15, 30) if character == "susie" else random.randint(5, 15)
        is_crit = random.random() < FIGHT_CRIT_CHANCE
        if is_crit:
            dmg = round(dmg * FIGHT_CRIT_MULTIPLIER)
        state["enemy_hp"] = max(0, state["enemy_hp"] - dmg)
        text = f"{character.capitalize()} attacks! {enemy['name']} takes {dmg} damage."
        if is_crit:
            text += " Critical hit!"
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
        await ctx.send(content=turn_plan_text(state), file=file, view=TurnPlanView(ctx.channel.id, state["pending_actions"]))

    @commands.command(name="battle_retry")
    async def battle_retry(self, ctx: commands.Context):
        """Retry the last battle in this channel."""
        existing = await storage.get_battle(ctx.channel.id)
        if existing and not existing.get("over"):
            await ctx.send("There's already a battle in progress in this channel!")
            return

        last_key = await storage.get_json(f"battle:{ctx.channel.id}:last_enemy")
        if not last_key:
            await ctx.send("No previous battle to retry!")
            return
        state = new_battle_state(last_key)
        await storage.set_battle(ctx.channel.id, state)
        buf = render_battle(state)
        file = discord.File(buf, filename="battle.png")
        await ctx.send(content=turn_plan_text(state), file=file, view=TurnPlanView(ctx.channel.id, state["pending_actions"]))


async def setup(bot: commands.Bot):
    await bot.add_cog(Battle(bot))
