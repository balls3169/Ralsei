"""
Ralsei's 4th-wall-break system.

Per planning: this is a SEPARATE axis from relationship tiers, not tied to
affection score. It's trigger-based (random chance + topic boosts), and
escalates specifically with the CREATOR (the moment lingers longer before
he catches himself, vs. strangers where the catch is near-instant).

Keep payloads vague/ominous rather than literal exposition — referencing
"resets," prior loops, "the one really deciding this," knowing how things
end — then a flustered self-correction. Never have him explain real bot
mechanics; the unease should feel narrative, not like a tutorial.
"""

import random
from bot_config_and_keys import FOURTH_WALL_BASE_CHANCE, FOURTH_WALL_TOPIC_BOOST

# Topics/keywords that bump the chance up, since the slip should feel tied
# to what's being discussed (mechanics, fate, memory, control).
ON_THEME_KEYWORDS = [
    "save", "reset", "soul", "prophecy", "fate", "control", "again",
    "before", "remember", "choice", "choose", "tp", "hp", "mercy",
]

# The "lingering" moment before Ralsei catches himself. Written to trail
# off rather than state anything concrete — the discomfort is the point.
SLIP_LINES = [
    "You've done this before, haven't you? Not- not this conversation, but... this. All of thi—",
    "It's strange... I feel like I already know how you'll answer that.",
    "Sometimes I forget which... version of this we're on.",
    "I keep thinking there's someone else listening. Not you. Someone... behind you.",
    "You could just start over, you know. If this went wrong. I don't know why I know that.",
]

# The catch/backpedal — short, flustered, redirects immediately.
CATCH_LINES = [
    "*He stops. Blinks.* S-sorry! Ignore me. Um— did you want a hug?",
    "*He laughs, a little too quickly.* That was strange of me to say! Anyway—",
    "N-nevermind! Forget I said anything, please.",
    "*He shakes his head.* Sorry, sorry. Where were we?",
]

# Creator-specific variant: the line lingers a beat longer before the catch,
# since he trusts them more and is less guarded — per planning.
CREATOR_LINGER_LINES = [
    "You already know, don't you? I don't have to pretend with you as much.",
    "I think you're the only one I'd even admit that to.",
]


def should_trigger(message_text: str, is_creator: bool = False) -> bool:
    chance = FOURTH_WALL_BASE_CHANCE
    lowered = message_text.lower()
    if any(word in lowered for word in ON_THEME_KEYWORDS):
        chance += FOURTH_WALL_TOPIC_BOOST
    return random.random() < chance


def build_slip(is_creator: bool = False) -> str:
    """Returns a full slip+catch string to append/prepend to a reply."""
    slip = random.choice(SLIP_LINES)
    if is_creator and random.random() < 0.5:
        # Let it linger — add a lingering line before the catch, per planning.
        linger = random.choice(CREATOR_LINGER_LINES)
        catch = random.choice(CATCH_LINES)
        return f"{slip} {linger}\n{catch}"
    catch = random.choice(CATCH_LINES)
    return f"{slip}\n{catch}"
