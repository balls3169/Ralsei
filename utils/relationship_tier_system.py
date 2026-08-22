"""
Relationship tier system — inspired by Yarnaby's social_matrix approach,
reshaped to fit Ralsei's personality (per our planning: no "cold" tier,
the low end is anxious/over-apologetic rather than withdrawn).

Tiers:
  CREATOR  - hardcoded ID match, unconditional, checked first, overrides score
  CLOSE    - high score, flustered-fond
  NEUTRAL  - default warmth, a little formal
  SHY      - low score, over-apologetic/anxious (NOT cold)
"""

import time
from bot_config_and_keys import CREATOR_ID, TIER_THRESHOLDS, AFFECTION_COOLDOWN_SECONDS
from utils.database_upstash_connection import storage


def get_tier_from_score(score: int) -> str:
    if score >= TIER_THRESHOLDS["CLOSE"]:
        return "CLOSE"
    if score >= TIER_THRESHOLDS["NEUTRAL"]:
        return "NEUTRAL"
    return "SHY"


async def get_tier(user_id: int) -> str:
    """The main entry point cogs should call to decide which response pool to use."""
    if CREATOR_ID and user_id == CREATOR_ID:
        return "CREATOR"
    user_data = await storage.get_user(user_id)
    return get_tier_from_score(user_data.get("score", 0))


async def add_affection(user_id: int, amount: int = 1) -> tuple[bool, str]:
    """
    Adds affection score for a user, respecting the cooldown.
    Returns (applied: bool, tier_after: str).
    CREATOR always "applies" for flavor purposes but doesn't need real score.
    """
    if CREATOR_ID and user_id == CREATOR_ID:
        return True, "CREATOR"

    user_data = await storage.get_user(user_id)
    now = time.time()
    last = user_data.get("last_affection_ts", 0)

    if now - last < AFFECTION_COOLDOWN_SECONDS:
        # Still on cooldown — no score change, just report current tier.
        return False, get_tier_from_score(user_data.get("score", 0))

    user_data["score"] = user_data.get("score", 0) + amount
    user_data["last_affection_ts"] = now
    await storage.set_user(user_id, user_data)

    return True, get_tier_from_score(user_data["score"])


async def cooldown_remaining(user_id: int) -> float:
    """Seconds left before this user can gain affection again. 0 if ready."""
    user_data = await storage.get_user(user_id)
    last = user_data.get("last_affection_ts", 0)
    remaining = AFFECTION_COOLDOWN_SECONDS - (time.time() - last)
    return max(0.0, remaining)
