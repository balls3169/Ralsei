"""
Thin async wrapper around Upstash Redis's REST API.

Why REST instead of a normal redis client: Render + Upstash free tier plays
nicest over HTTPS (no persistent TCP connection management to worry about,
works fine from any environment that can make HTTP calls).

Data shape (per our planning):
  user:{discord_id}            -> hash: {"score": int, "last_affection_ts": float, ...}
  guild:{guild_id}:recruits    -> hash: {"rudinn": 3, "werewire": 6, ...}  (shared Castle Town)
  guild:{guild_id}:lost        -> set:  darkner types permanently LOST via violence
  battle:{channel_id}          -> hash/json blob of active battle state (TTL'd)

All values are stored as JSON strings and decoded on read, since Upstash's
REST API is string-in/string-out.
"""

import json
import aiohttp
from bot_config_and_keys import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN


class Storage:
    def __init__(self):
        self.base_url = UPSTASH_REDIS_REST_URL.rstrip("/")
        self.headers = {"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _command(self, *parts: str):
        """
        Send a raw Redis command via Upstash's REST API using a POST with
        a JSON array body, e.g. POST / with body ["SET", "key", "value"].

        We deliberately avoid the GET /command/arg1/arg2 path style here:
        our values are JSON strings full of quotes, braces, spaces, and
        punctuation (Ralsei's dialogue has apostrophes and em-dashes), and
        naively joining those into a URL path without encoding will break
        or silently corrupt requests. POSTing a JSON array sidesteps that
        entirely — no encoding to get wrong.
        """
        session = await self._get_session()
        async with session.post(self.base_url, headers=self.headers, json=list(parts)) as resp:
            data = await resp.json()
            if "error" in data:
                raise RuntimeError(f"Upstash error: {data['error']}")
            return data.get("result")

    # --- Generic JSON get/set (used for most of our data) ---

    async def get_json(self, key: str, default=None):
        raw = await self._command("get", key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    async def set_json(self, key: str, value, ex_seconds: int | None = None):
        payload = json.dumps(value)
        if ex_seconds:
            return await self._command("set", key, payload, "EX", str(ex_seconds))
        return await self._command("set", key, payload)

    async def delete(self, key: str):
        return await self._command("del", key)

    async def keys(self, pattern: str):
        return await self._command("keys", pattern)

    # --- Convenience helpers matching our data model ---

    async def get_user(self, user_id: int) -> dict:
        return await self.get_json(f"user:{user_id}", default={
            "score": 0,
            "last_affection_ts": 0,
        })

    async def set_user(self, user_id: int, data: dict):
        await self.set_json(f"user:{user_id}", data)

    async def get_guild_recruits(self, guild_id: int) -> dict:
        return await self.get_json(f"guild:{guild_id}:recruits", default={})

    async def set_guild_recruits(self, guild_id: int, data: dict):
        await self.set_json(f"guild:{guild_id}:recruits", data)

    async def get_guild_lost(self, guild_id: int) -> list:
        return await self.get_json(f"guild:{guild_id}:lost", default=[])

    async def set_guild_lost(self, guild_id: int, data: list):
        await self.set_json(f"guild:{guild_id}:lost", data)

    async def get_battle(self, channel_id: int):
        return await self.get_json(f"battle:{channel_id}", default=None)

    async def set_battle(self, channel_id: int, data: dict, ttl_seconds: int = 1800):
        # TTL auto-expires abandoned battles (30 min default) so they don't
        # linger forever in Upstash or block !battle from being restarted.
        await self.set_json(f"battle:{channel_id}", data, ex_seconds=ttl_seconds)

    async def clear_battle(self, channel_id: int):
        await self.delete(f"battle:{channel_id}")


# Single shared instance, imported by cogs.
storage = Storage()
