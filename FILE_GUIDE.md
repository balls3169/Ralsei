# File Guide — what's what, and where to edit for what

Quick map so you're not hunting through files to find where something lives.

## Root

| File | What it does |
|---|---|
| `main.py` | Entry point. Loads everything, starts the bot, runs the Render keep-alive web server. Run this to start the bot. |
| `bot_config_and_keys.py` | All settings and env var loading — token, OpenRouter key, Upstash creds, tier thresholds, TP costs, 4th-wall chance %. **Edit here to tweak numbers/thresholds. Never put real keys directly in this file — they come from your `.env` / Render dashboard.** |
| `.env.example` | Template for your local `.env` file (or Render's env var dashboard). Copy to `.env` and fill in real values. |
| `requirements.txt` | Python packages needed. |
| `render.yaml` | Render deployment config. |

## `cogs/` — Discord commands (the user-facing stuff)

| File | What it does |
|---|---|
| `commands_affection_pet_hug.py` | `!pet`, `!bellyrub`, `!scritch`, `!hug`. **Edit here to add more affection lines per tier, or add new affection commands.** |
| `commands_ai_personality_chat.py` | Free-chat when Ralsei is @mentioned or DMed. Wires together the tier system + OpenRouter + 4th-wall breaks. **Edit here to change *when* AI chat triggers** (e.g. expand beyond mentions/DMs). |
| `commands_battle_system.py` | `!battle`, `!battle_retry`. The whole battle engine — character select, FIGHT/ACT/MAGIC/ITEM/DEFEND/SPARE, TP, Mercy%, TIRED/Pacify, X-Flirt sequence, enemy counterattack. **This is the biggest file — edit here for battle mechanics/balance changes.** |
| `commands_castle_town_recruits.py` | `!castle_town`, `!checkr`. Shows the shared server-wide recruit roster. **Edit here to change how Castle Town displays.** |

## `utils/` — internal systems, not directly commands

| File | What it does |
|---|---|
| `relationship_tier_system.py` | The CREATOR/CLOSE/NEUTRAL/SHY tier logic — scoring, cooldowns, who counts as "creator." **Edit here to change tier thresholds' *behavior* (thresholds themselves are in config).** |
| `personality_fourth_wall_breaks.py` | The random "Ralsei knows too much" slip-and-catch lines. **Edit here to add more slip/catch lines, or change trigger keywords.** |
| `ai_chat_openrouter_api.py` | Talks to OpenRouter. Contains Ralsei's full **system prompt** (his core personality description for the AI). **Edit here to change how Ralsei's AI-driven voice/personality is described.** |
| `battle_image_renderer.py` | Pillow code that draws the battle screen (HP/TP/Mercy bars, text box) into a PNG. **Edit here for visual/layout changes to the battle screenshot.** |
| `database_upstash_connection.py` | Talks to Upstash Redis for persistent storage (user scores, guild recruits, battle state). **Edit here only if changing how/where data is stored.** |

## `data/` — game content/lore, not code logic

| File | What it does |
|---|---|
| `lore_enemies_and_acts.py` | Every enemy's stats, ACT menu options, encounter lines, spare/tired flavor text, X-Flirt sequences. **This is where you add new enemies — just follow the existing dict shape.** |

## `assets/`

| Folder | What goes here |
|---|---|
| `assets/fonts/` | Drop a free pixel font here (e.g. Press Start 2P) and update `FONT_PATH` in `utils/battle_image_renderer.py`. |
| `assets/sprites/` | Drop your own original character/enemy art here if you want the battle renderer to use real sprites instead of placeholder bars. |

---

### TL;DR — "I want to change X, where do I go?"

- **Ralsei's personality/voice (AI chat)** → `utils/ai_chat_openrouter_api.py` (system prompt)
- **Canned affection replies** → `cogs/commands_affection_pet_hug.py`
- **Add an enemy** → `data/lore_enemies_and_acts.py`
- **Battle rules/balance** → `cogs/commands_battle_system.py`
- **How the battle image looks** → `utils/battle_image_renderer.py`
- **Tier thresholds / TP costs / cooldowns** → `bot_config_and_keys.py`
- **4th-wall-break lines** → `utils/personality_fourth_wall_breaks.py`
- **Castle Town display** → `cogs/commands_castle_town_recruits.py`
- **Keys/tokens** → your `.env` file (never in code)
