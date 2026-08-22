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
# Adjust freely; these are just reasonable starting picks.
OPENROUTER_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "google/gemini-flash-1.5:free",
    "mistralai/mistral-7b-instruct:free",
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
