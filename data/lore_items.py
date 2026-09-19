"""
Consumable items usable via ITEM during !battle.

Grounded in real Deltarune items and their actual documented effects:
  - Butterscotch Pie: fully heals the user
  - TV Dinner: heals 100 HP
  - Choco Diamond: heals 80 HP, canonically Kris-specific
  - Hearts Donut: heals 80 HP, canonically Susie-specific
  - Revive Mint: revives a downed party member to full HP

Fields:
  name           - display name
  heal_amount    - int, or None for a full heal
  target         - "self" (heals whoever used it) or "revive" (heals/revives
                    a downed ally instead — see resolve_item in the battle cog)
  restricted_to  - a character key (e.g. "kris") if only that character can
                    use it, or None if anyone can
  starting_count - how many the party starts a battle with
  flavor_use     - flavor text shown when used

Each battle's inventory is independent (resets to starting_count at the
start of every !battle), since there's no persistent overworld/shop system
here — this keeps the item system self-contained within a single fight.
"""

ITEMS = {
    "butterscotch_pie": {
        "name": "Butterscotch Pie",
        "heal_amount": None,  # None = full heal
        "target": "self",
        "restricted_to": None,
        "starting_count": 1,
        "flavor_use": "is fully healed by the warmth of the pie",
    },
    "tv_dinner": {
        "name": "TV Dinner",
        "heal_amount": 100,
        "target": "self",
        "restricted_to": None,
        "starting_count": 2,
        "flavor_use": "wolfs down the TV Dinner",
    },
    "choco_diamond": {
        "name": "Choco Diamond",
        "heal_amount": 80,
        "target": "self",
        "restricted_to": "kris",
        "starting_count": 1,
        "flavor_use": "eats the Choco Diamond",
    },
    "hearts_donut": {
        "name": "Hearts Donut",
        "heal_amount": 80,
        "target": "self",
        "restricted_to": "susie",
        "starting_count": 1,
        "flavor_use": "devours the Hearts Donut in one bite",
    },
    "revive_mint": {
        "name": "Revive Mint",
        "heal_amount": None,  # None = full heal on revive
        "target": "revive",
        "restricted_to": None,
        "starting_count": 1,
        "flavor_use": "uses the Revive Mint",
    },
}
