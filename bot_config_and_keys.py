"""
Central config for Ralsei bot.
Everything sensitive comes from environment variables (Render dashboard / local .env).
Never hardcode tokens or keys here.
"""

import os

# --- Discord ---
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "!")

# --- Creator recognition ---
# Your Discord user ID (as an int). Set this in Render's env vars, not here.
CREATOR_ID = int(os.environ.get("CREATOR_ID", "0"))

# --- OpenRouter (for Ralsei's free-chat dialogue) ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Fallback model chain — tries each in order if one fails/rate-limits.
#
# IMPORTANT: OpenRouter's free-tier model lineup rotates constantly — models
# get delisted or renamed with little to no notice (this is exactly what
# caused the "No endpoints found" error). Rather than chase a moving target
# with hardcoded IDs, we lead with "openrouter/free" — OpenRouter's own
# auto-router, which always resolves to *some* currently-live free model.
# The named models behind it are just extra fallbacks; if they 404 one day,
# that's expected and harmless since openrouter/free (tried first) covers it.
# If you want to pin specific named models instead, check what's currently
# free at https://openrouter.ai/models?max_price=0 before hardcoding one.
OPENROUTER_MODELS = [
    "openrouter/free",
    "meta-llama/llama-4-scout:free",
    "z-ai/glm-4.5-air:free",
]

# --- Upstash Redis (persistent storage) ---
UPSTASH_REDIS_REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_REDIS_REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

# --- Relationship tiers ---
# Thresholds are cumulative "affection points" earned via !pet, !hug, !bake, etc.
TIER_THRESHOLDS = {
    "SHY": 0,        # default/new — anxious, over-apologetic
    "NEUTRAL": 10,    # polite storybook warmth
    "CLOSE": 40,      # flustered-fond, initiates hugs, uses your name warmly
}

# Cooldown (seconds) between affection-command score gains, per user, to prevent farming.
AFFECTION_COOLDOWN_SECONDS = 60

# --- 4th-wall break system ---
FOURTH_WALL_BASE_CHANCE = 0.07  # 7% baseline chance per eligible message/reply
FOURTH_WALL_TOPIC_BOOST = 0.15  # extra chance when topic is mechanics/fate related
FOURTH_WALL_CREATOR_LINGER = True  # creator gets the "lets it sit longer" variant

# --- Battle system ---
SHARED_TP_MAX = 100
TP_GAIN_DEFEND = 16
TP_GAIN_HIT_TAKEN = 8
PACIFY_TP_COST = 16
DUAL_HEAL_TP_COST = 32

# --- Dodge mini-game tuning ---
# Base time (seconds) to pick a dodge option, shrinking slightly each turn
# to build tension as a fight drags on — floors out so it never becomes
# unfairly fast.
DODGE_TIMEOUT_BASE = 12
DODGE_TIMEOUT_FLOOR = 6
DODGE_TIMEOUT_STEP_PER_TURN = 0.5

# For lanes with 3+ options (e.g. left/center/right), picking a lane
# ADJACENT to the safe one is a partial miss ("graze") rather than a full
# hit — mirrors Deltarune's real graze mechanic, where nearly avoiding a
# bullet still earns you something. Binary lanes (e.g. duck/jump) don't
# get partial credit since there's no "adjacent" option — any wrong pick
# there is a full hit, same as before.
GRAZE_DAMAGE_MULTIPLIER_NEAR = 0.4   # picked the lane right next to safe
GRAZE_DAMAGE_MULTIPLIER_FAR = 1.0    # picked the lane furthest from safe
GRAZE_TP_BONUS = 6                   # bonus TP for a close-call graze
CLEAN_DODGE_TP_BONUS = 4             # bonus TP for a fully correct dodge

# --- FIGHT crit chance ---
FIGHT_CRIT_CHANCE = 0.15
FIGHT_CRIT_MULTIPLIER = 1.5
