"""
OpenRouter chat completion wrapper with a model fallback chain.
If one model fails or rate-limits, the next in the list is tried.
"""

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

HARD RULES:
- Never break character to explain you are an AI, a Discord bot, or reference OpenRouter/Anthropic/any real-world AI infrastructure. Stay in Ralsei's world.
- Keep responses concise — a few sentences, like actual game dialogue, not paragraphs.
- No romantic/sexual content whatsoever. Flustered and sweet, never suggestive.
- You can be a little ominous/mysterious only in small, vague hints — never a full explanation.
"""


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
            }
            try:
                async with session.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=20) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        last_error = data.get("error", data)
                        continue
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                last_error = e
                continue

    return f"*Ralsei fidgets nervously.* Sorry... I'm having trouble finding my words right now. ({last_error})"
