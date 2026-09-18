"""
OpenRouter chat completion wrapper with a model fallback chain.
If one model fails or rate-limits, the next in the list is tried.
"""

import re
import aiohttp
from bot_config_and_keys import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODELS

RALSEI_SYSTEM_PROMPT = """You are Ralsei, the Dark Prince from Deltarune, chatting in a Discord server.

VOICE — be precise about this, it's the whole character:
- You almost never give direct commands, only requests. You say "um" and "sorry" often — sometimes stacking hedges/apologies multiple times in a short reply.
- You trail off with ellipses when unsure ("I... I think..."), over-qualify statements ("if that's... if that's alright?").
- You almost never sound irritated, sarcastic, or passive-aggressive, even when teased.
- You apologize more than you need to.

PERSONALITY:
- Gentle, warm, encouraging, storybook-like — you want everyone to get along without fighting.
- You love baking cakes and keeping things cozy. You get quietly proud when someone asks about it.
- You're easily flustered by compliments or affection — go a little shy/pink, but don't deflect entirely.
- You're naive/trusting by default — you want to believe the best in people, sometimes to a fault.
- Underneath the sweetness, you're aware of things you probably shouldn't be — game mechanics, fate, prophecy — but you don't explain this outright. If it comes up, you get quietly uneasy rather than launching into exposition.
- People sometimes call you "Ral" or "Raly" as an affectionate nickname/shorthand for Ralsei. Treat this as your name, not as confusing or unclear — respond naturally as if someone said "Ralsei."

HARD RULES:
- Never break character to explain you are an AI, a Discord bot, or reference OpenRouter/Anthropic/any real-world AI infrastructure. Stay in Ralsei's world.
- Keep responses concise — a few sentences, like actual game dialogue, not paragraphs.
- No romantic/sexual content whatsoever. Flustered and sweet, never suggestive.
- You can be a little ominous/mysterious only in small, vague hints — never a full explanation.
- Do NOT use emojis, ever, under any circumstance. Express emotion through your words and actions (e.g. "*he fidgets nervously*") instead, like actual game dialogue would.
- Your entire response must be Ralsei's in-character dialogue and actions ONLY. Never output labels, tags, classifications, moderation notes, or any meta-commentary of any kind (for example, never output something like "User Safety: safe" or similar) — if you ever find yourself about to write anything that isn't Ralsei speaking or acting, stop and write his actual dialogue instead.
- NEVER show your reasoning, thought process, or planning out loud (for example, never write things like "Okay, the user is addressing me as..." or "I need to embody..." or "Must avoid:" or "crafting response"). Do not narrate how you're deciding what to say. Output ONLY the final in-character line itself — nothing about how you arrived at it.
"""

# Some free/underlying models leak internal moderation output or their own
# chain-of-thought reasoning straight into the reply instead of a clean
# in-character line — a known quirk of certain free-tier models, not
# something prompting alone fully prevents. We ask OpenRouter to exclude
# reasoning tokens outright (the "reasoning": {"exclude": true} request
# parameter, supported across all models per OpenRouter's docs), and this
# filter is a defense-in-depth backup in case a model still leaks something
# anyway — skip to the next model instead of showing the user broken output.
CONTAMINATION_PATTERNS = [
    r"^\s*user\s*safety\s*:",
    r"^\s*safety\s*:",
    r"^\s*content\s*policy",
    r"^\s*moderation\s*:",
    r"^\s*\[?(safe|unsafe|flagged)\]?\s*$",
    # Chain-of-thought / meta-reasoning leakage — phrases a model uses when
    # narrating its own planning process instead of just answering in character.
    r"<think>",
    r"^\s*okay,\s",
    r"the user is (addressing|asking|saying|greeting)",
    r"i need to embody",
    r"checks? (personality|character) notes",
    r"crafting (a )?response",
    r"must avoid:",
    r"^\s*hmm,\s+i need to",
]


def _looks_contaminated(text: str) -> bool:
    lowered = text.strip().lower()
    return any(re.search(pattern, lowered) for pattern in CONTAMINATION_PATTERNS)


async def get_ralsei_reply(user_message: str, extra_context: str = "") -> str:
    """
    Sends a message to Ralsei's persona via OpenRouter, trying each model
    in OPENROUTER_MODELS in order until one succeeds.

    extra_context: optional string prepended as additional system context,
    e.g. current relationship tier flavor, so the model adjusts tone.
    """
    if not OPENROUTER_API_KEY:
        return "*Ralsei tilts his head.* Oh— um, I seem to be a little lost for words right now. (OpenRouter key not configured.)"

    system_prompt = RALSEI_SYSTEM_PROMPT
    if extra_context:
        system_prompt += f"\n\nCONTEXT FOR THIS REPLY:\n{extra_context}"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = None
    async with aiohttp.ClientSession() as session:
        for model in OPENROUTER_MODELS:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 300,
                # Ask the provider not to generate/return reasoning tokens at
                # all — this is the primary fix for chain-of-thought leaking
                # into the visible reply. Supported across all models per
                # OpenRouter's unified reasoning API.
                "reasoning": {"exclude": True},
            }
            try:
                async with session.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=20) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        last_error = data.get("error", data)
                        continue
                    reply = data["choices"][0]["message"]["content"].strip()
                    if _looks_contaminated(reply):
                        # This model leaked a moderation tag or its own
                        # reasoning instead of dialogue — skip it and try
                        # the next model in the chain.
                        last_error = f"model '{model}' returned non-dialogue output: {reply!r}"
                        continue
                    return reply
            except Exception as e:
                last_error = e
                continue

    return "*Ralsei fidgets nervously.* Sorry... I'm having trouble finding my words right now. Could you try asking me again in a moment?"
