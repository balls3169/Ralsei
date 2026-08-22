"""
Battle screen renderer using Pillow.

IMPORTANT (per planning): this uses ORIGINAL styling only — no ripped
Deltarune sprites, fonts, or backgrounds. It's inspired by the aesthetic
(dark battle box, heart/soul motif, bar-based HP/TP/Mercy) but everything
here is drawn from scratch with basic shapes and a free font.

You'll want to:
  1. Drop a free pixel-style font (e.g. "Press Start 2P" from Google Fonts,
     OFL-licensed) into assets/fonts/ and update FONT_PATH below.
  2. Optionally replace the placeholder circle/rect sprites with your own
     original character art in assets/sprites/.

This renders to bytes (PNG) so it can be sent directly as a discord.File
without touching disk beyond what Pillow needs internally.
"""

import io
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 700, 400
BG_COLOR = (10, 10, 20)
BOX_COLOR = (255, 255, 255)
BAR_BG = (60, 60, 60)
HP_COLOR = (60, 200, 90)
TP_COLOR = (230, 200, 40)
MERCY_COLOR = (240, 240, 130)
TIRED_COLOR = (100, 160, 240)
TEXT_COLOR = (255, 255, 255)

FONT_PATH = "assets/fonts/PressStart2P-Regular.ttf"  # TODO: add this font file
FALLBACK = None  # Pillow's built-in default font, used if FONT_PATH is missing


def _get_font(size: int):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _draw_bar(draw: ImageDraw.ImageDraw, x, y, w, h, pct, color):
    pct = max(0.0, min(1.0, pct))
    draw.rectangle([x, y, x + w, y + h], fill=BAR_BG, outline=BOX_COLOR)
    if pct > 0:
        draw.rectangle([x, y, x + int(w * pct), y + h], fill=color)


def render_battle(state: dict) -> io.BytesIO:
    """
    state expects:
      enemy_name, enemy_hp, enemy_max_hp, mercy_percent, tired (bool)
      tp, tp_max
      party: {"kris": {"hp":.., "max_hp":..}, "susie": {...}, "ralsei": {...}}
      log_line: str (most recent flavor text to show in the text box)
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(14)
    label_font = _get_font(10)
    text_font = _get_font(12)

    # Enemy name + HP bar (top area)
    draw.text((30, 20), state["enemy_name"], font=title_font, fill=TEXT_COLOR)
    enemy_pct = state["enemy_hp"] / max(1, state["enemy_max_hp"])
    _draw_bar(draw, 30, 50, 300, 18, enemy_pct, HP_COLOR)

    mercy_pct = state.get("mercy_percent", 0) / 100
    mercy_color = TIRED_COLOR if state.get("tired") else MERCY_COLOR
    draw.text((30, 78), "MERCY" + (" (TIRED)" if state.get("tired") else ""), font=label_font, fill=TEXT_COLOR)
    _draw_bar(draw, 30, 95, 300, 12, mercy_pct, mercy_color)

    # Shared TP bar
    tp_pct = state["tp"] / max(1, state.get("tp_max", 100))
    draw.text((400, 20), "TP", font=label_font, fill=TEXT_COLOR)
    _draw_bar(draw, 400, 35, 250, 16, tp_pct, TP_COLOR)

    # Party HP (three columns)
    party = state.get("party", {})
    x_positions = {"kris": 30, "susie": 260, "ralsei": 490}
    for char_key, x in x_positions.items():
        char = party.get(char_key, {"hp": 0, "max_hp": 1})
        pct = char["hp"] / max(1, char["max_hp"])
        draw.text((x, 230), char_key.upper(), font=label_font, fill=TEXT_COLOR)
        _draw_bar(draw, x, 250, 180, 14, pct, HP_COLOR)
        draw.text((x, 268), f"{char['hp']}/{char['max_hp']} HP", font=label_font, fill=TEXT_COLOR)

    # Text box for flavor/log line
    draw.rectangle([20, 310, WIDTH - 20, HEIGHT - 20], outline=BOX_COLOR, width=2)
    log_line = state.get("log_line", "")
    # naive wrap
    max_chars = 60
    wrapped = [log_line[i:i + max_chars] for i in range(0, len(log_line), max_chars)] or [""]
    for i, line in enumerate(wrapped[:3]):
        draw.text((35, 325 + i * 18), line, font=text_font, fill=TEXT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
