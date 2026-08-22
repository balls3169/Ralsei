# Setup Guide — getting Ralsei online

This walks through the exact pipeline: **code on GitHub → Render runs it → Upstash remembers things.**
Same shape as your Yarnaby setup, just written out step by step so nothing gets messy.

---

## 0. Where the token actually goes (the short answer)

You will **never** type your token into any `.py` file. It lives in one place only:
an environment variable called `DISCORD_TOKEN`.

In the code, this happens in `main.py`:

```python
from bot_config_and_keys import DISCORD_TOKEN
...
await bot.start(DISCORD_TOKEN)   # <- this is the bot.run(TOKEN) equivalent
```

And `bot_config_and_keys.py` just reads it from the environment:

```python
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
```

So the token itself goes into:
- **Locally:** a `.env` file you create yourself (never committed — `.gitignore` already blocks it)
- **On Render:** the Environment Variables section of your service dashboard

That's it. If you're ever unsure "where do I paste my token," the answer is always
"an environment variable / Render dashboard field," never a source file.

---

## 1. Create the Discord bot application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Go to the **Bot** tab → **Reset Token** (or copy the existing one). This is your `DISCORD_TOKEN`.
3. On the same Bot tab, scroll to **Privileged Gateway Intents** and turn ON:
   - **Message Content Intent** — required, since the code sets `INTENTS.message_content = True` in `main.py`. Without this toggle, the bot will connect but silently fail to read command text or @mentions.
4. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: at minimum `Send Messages`, `Read Message History`, `Attach Files` (for the battle screenshots), `Embed Links`
   - Copy the generated URL, open it, and invite the bot to your server.

---

## 2. Get your Upstash Redis credentials

1. [upstash.com](https://upstash.com) → create a free Redis database.
2. On the database's page, find the **REST API** section — copy:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`

Keep this tab open, you'll paste these into Render in a minute.

---

## 3. (Optional but recommended) Get an OpenRouter key

1. [openrouter.ai/keys](https://openrouter.ai/keys) → create a key. This is `OPENROUTER_API_KEY`.
2. Without this, `!pet` etc. and battles still work fully (they're canned responses) —
   only free-chat (@mentioning Ralsei / DMing him) needs this.

---

## 4. Test it locally first (strongly recommended before deploying)

1. Copy `.env.example` → rename the copy to `.env`.
2. Fill in the real values in `.env`:
   ```
   DISCORD_TOKEN=your_real_token
   CREATOR_ID=your_discord_user_id
   OPENROUTER_API_KEY=your_key_or_leave_blank
   UPSTASH_REDIS_REST_URL=your_url
   UPSTASH_REDIS_REST_TOKEN=your_token
   ```
   (To get your own Discord user ID: enable Developer Mode in Discord settings →
   right-click your name → Copy User ID.)
3. Install dependencies and run:
   ```
   pip install -r requirements.txt
   python main.py
   ```
4. If it logs `Logged in as <YourBotName>`, it's working. Try `!ralsei_help` in your server.

---

## 5. Push the code to GitHub

```
git init
git add .
git commit -m "Initial Ralsei bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

`.gitignore` already excludes `.env`, so your real secrets won't get pushed —
only `.env.example` (the blank template) goes up.

---

## 6. Deploy on Render

1. [render.com](https://render.com) → **New → Web Service** → connect your GitHub repo.
2. Render should auto-detect the settings from `render.yaml`, but double check:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
3. Under **Environment**, add each of these as a real environment variable
   (same names as your `.env`, real values this time):
   - `DISCORD_TOKEN`
   - `CREATOR_ID`
   - `OPENROUTER_API_KEY`
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`
4. Deploy. Check the **Logs** tab — you should see `Logged in as <YourBotName>`.

### Important free-tier gotcha

Render's **free Web Services spin down after ~15 minutes of no incoming HTTP traffic**,
which would kill your bot's connection to Discord along with it. This is exactly why
`main.py` runs a tiny web server (`start_web_server()`) alongside the bot — it gives
Render something to receive traffic on.

But Render still won't ping itself. You need something external hitting that URL
periodically to keep the service awake. Since you're using **cron-job.org**, here's
the exact setup:

1. Deploy the bot on Render first (steps above) and grab its public URL from the
   Render dashboard — it looks like `https://ralsei-bot.onrender.com`.
2. Go to [cron-job.org](https://cron-job.org) and create a free account.
3. Click **Create cronjob**.
4. Set the **URL** to your Render URL's root (just `https://ralsei-bot.onrender.com`,
   no path needed — that's what `handle_health` in `main.py` responds to).
5. Set the **execution schedule** to every **3–5 minutes** — comfortably under
   Render's 15-minute spin-down window, without being excessive.
6. Save it. No code changes needed; cron-job.org just needs to keep hitting that URL.

You can check it's working by watching Render's **Logs** tab — you should see a steady
trickle of incoming requests to `/` roughly every 3–5 minutes, and the bot should
never show the "spinning back up" delay in Discord.

(Other options like UptimeRobot work the same way if you ever want a backup, but
cron-job.org alone is enough.)

---

## 7. Confirm it's actually persisting data

Run `!pet` a few times (respecting the cooldown), then restart the Render service manually
(Render dashboard → Manual Deploy → Deploy latest commit, or just wait for it to spin down
and back up). If your relationship tier is still remembered afterward, Upstash is working
correctly. If scores reset, double check your `UPSTASH_REDIS_REST_URL`/`TOKEN` are set
correctly in Render's environment variables, not just locally.

---

## Troubleshooting quick list

| Symptom | Likely cause |
|---|---|
| Bot doesn't respond to `!commands` at all | Message Content Intent not enabled in Developer Portal |
| Bot logs in but `@mention` chat doesn't work | Same as above, or `OPENROUTER_API_KEY` missing/blank |
| Bot works, then goes offline after a while | cron-job.org isn't set up yet, or its interval is longer than 15 min (see step 6) |
| Relationship/recruit data resets randomly | Upstash env vars wrong/missing on Render specifically (check Render dashboard, not just `.env`) |
| `RuntimeError: DISCORD_TOKEN environment variable is not set!` | You're running locally without a `.env` file, or forgot to add it in Render's dashboard |
