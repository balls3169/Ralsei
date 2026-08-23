"""
Enemy definitions for !battle.

Each enemy is its own dict — ACT menus are per-enemy, not universal,
per planning (this mirrors how ACT actually works in Deltarune).

Fields:
  name             - display name
  hp               - starting/max HP
  mercy_needed     - % mercy required before SPARE works (100 = must fully fill)
  acts             - list of dicts: {"name": ..., "mercy_gain": int, "flavor": str,
                                      "causes_tired": bool}
  tired_lines      - flavor when this enemy becomes TIRED
  spare_lines      - flavor when successfully spared
  encounter_lines  - pool of opening lines when the fight starts
  flirt_sequence   - special-cased list of flirt attempts if this enemy supports
                      X-Flirt (per planning: fails twice, then works)
  attack_patterns  - list of dicts describing the enemy's attacks for the
                      dodge mini-game: {"name": ..., "telegraph": ...,
                      "options": [...], "damage": int, "hits": int (optional,
                      default 1)}. One is picked at random each enemy turn;
                      which OPTION is actually safe is randomized at runtime
                      (not stored here) for EACH hit separately, so it can't
                      be memorized — you have to react to the telegraph text
                      and guess/react correctly each time. "hits" > 1 means
                      the attack fires multiple times in a row (e.g. a
                      3-hit feather storm), each needing its own dodge pick.

Roster covers Chapter 1 (Rudinn, Jigsawry, Ponman) and Chapter 2
(Head Hathy, Werewire) enemies, with ACT options/flavor grounded in their
actual canon mechanics (e.g. Jigsawry's Befriend really does instantly
make all Jigsawry spareable in-game; Ponman's Goodnight/Lullaby really do
cause TIRED; Werewire really does turn back into a Plugboy when spared).

Add more enemies here following the same shape.
"""

ENEMIES = {
    "rudinn": {
        "name": "Rudinn",
        "hp": 90,
        "mercy_needed": 100,
        "acts": [
            {"name": "Check", "mercy_gain": 0, "flavor": "A diamond-shaped Darkner. Likes: racing. Dislikes: losing.", "causes_tired": False},
            {"name": "Cheer", "mercy_gain": 30, "flavor": "You cheer Rudinn on. It puffs up proudly!", "causes_tired": False},
            {"name": "Race", "mercy_gain": 40, "flavor": "You challenge Rudinn to a race. It's thrilled!", "causes_tired": False},
        ],
        "tired_lines": ["Rudinn yawns, worn out from all that racing."],
        "spare_lines": ["Rudinn waves happily and heads off toward Castle Town!"],
        "encounter_lines": ["Rudinn blocks the way!", "A Rudinn zooms in, ready to race!"],
        "flirt_sequence": None,
        "attack_patterns": [
            {
                "name": "Straight Charge",
                "telegraph": "Rudinn crouches low, wheels spinning — it's lining up a charge down one lane!",
                "options": ["left", "center", "right"],
                "damage": 18,
            },
            {
                "name": "Wide Sweep",
                "telegraph": "Rudinn winds up for a wide, sweeping charge across the field!",
                "options": ["left", "center", "right"],
                "damage": 12,
                "hits": 2,
            },
        ],
    },
    "head_hathy": {
        "name": "Head Hathy",
        "hp": 70,
        "mercy_needed": 100,
        "acts": [
            {"name": "Check", "mercy_gain": 0, "flavor": "A witch's-hat Darkner. Likes: gossip. Dislikes: being ignored.", "causes_tired": False},
            {"name": "Compliment", "mercy_gain": 25, "flavor": "You compliment Head Hathy's hat. It preens!", "causes_tired": False},
            {"name": "X-Flirt", "mercy_gain": 0, "flavor": None, "causes_tired": False},  # handled specially, see flirt_sequence
        ],
        "tired_lines": ["Head Hathy looks a little worn out."],
        "spare_lines": ["Head Hathy giggles and flies off!"],
        "encounter_lines": ["A group of Head Hathys swoop in!"],
        # Per planning: first attempt (Susie) fails, second (Ralsei) fails,
        # third (Kris) succeeds. Battle cog checks which character used it
        # and how many times, referencing this sequence.
        "flirt_sequence": {
            "susie": {
                "success": False,
                "line": "Susie tries to X-Flirt. It's... incredibly awkward. One Head Hathy just leaves.",
            },
            "ralsei": {
                "success": False,
                "line": "Ralsei attempts to X-Flirt, deeply uncomfortable the entire time. Another Head Hathy leaves, unimpressed.",
            },
            "kris": {
                "success": True,
                "line": "Kris tries X-Flirt. Somehow... it works? All the Head Hathys swoon.",
                "mercy_gain": 50,
            },
        },
        "attack_patterns": [
            {
                "name": "Dive Bomb",
                "telegraph": "A Head Hathy swoops high into the air, ready to dive!",
                "options": ["left", "right"],
                "damage": 14,
            },
            {
                "name": "Feather Storm",
                "telegraph": "The Head Hathys shake loose a storm of feathers!",
                "options": ["duck", "jump"],
                "damage": 10,
                "hits": 3,
            },
        ],
    },
    "jigsawry": {
        "name": "Jigsawry",
        "hp": 50,
        "mercy_needed": 100,
        "acts": [
            {"name": "Check", "mercy_gain": 0, "flavor": "A jigsaw-puzzle-piece Darkner with a beanie. Very sensitive and emotional. Only fighting out of desperation for money.", "causes_tired": False},
            # Per canon: Befriend instantly makes Jigsawry (and any other
            # Jigsawry in the fight) spareable outright.
            {"name": "Befriend", "mercy_gain": 100, "flavor": "You offer to be Jigsawry's friend. It immediately tears up with joy!", "causes_tired": False},
        ],
        "tired_lines": ["Jigsawry looks exhausted, its edges fraying."],
        "spare_lines": ["Jigsawry cries tears of joy, thrilled to have a new boss!"],
        "encounter_lines": ["A Jigsawry piece wobbles into view!", "Two jigsaw pieces snap together as Jigsawry appears!"],
        "flirt_sequence": None,
        "attack_patterns": [
            {
                "name": "Puzzle Snap",
                "telegraph": "Two jigsaw pieces drift out on either side, tracking your movement — they're about to snap together!",
                "options": ["left", "right"],
                "damage": 10,
            },
        ],
    },
    "ponman": {
        "name": "Ponman",
        "hp": 75,
        "mercy_needed": 100,
        "acts": [
            {"name": "Check", "mercy_gain": 0, "flavor": "A white, chess-piece-shaped Darkner. Watches quietly, calculating its next move.", "causes_tired": False},
            # Per canon: Goodnight makes a Ponman TIRED and spareable.
            {"name": "Goodnight", "mercy_gain": 0, "flavor": "You tell Ponman goodnight. It grows drowsy...", "causes_tired": True},
            # Per canon: Lullaby (a Ralsei-assisted ACT) makes ALL Ponmen
            # tired at once, at the cost of also lulling Susie to sleep —
            # kept here as flavor-only since our system doesn't yet model
            # disabling a specific party member mid-fight.
            {"name": "Lullaby", "mercy_gain": 0, "flavor": "Ralsei hums a soft lullaby. All the Ponmen grow drowsy — and Susie yawns right along with them.", "causes_tired": True},
        ],
        "tired_lines": ["Ponman's eyes droop, chess-piece head nodding."],
        "spare_lines": ["Ponman bows quietly and steps aside."],
        "encounter_lines": ["Ponman shuffles forward, chess-piece eyes narrowing."],
        "flirt_sequence": None,
        "attack_patterns": [
            {
                "name": "Diamond Volley",
                "telegraph": "Ponman readies a volley of diamond-shaped shots, aimed down one lane!",
                "options": ["left", "center", "right"],
                "damage": 14,
            },
        ],
    },
    "werewire": {
        "name": "Werewire",
        "hp": 85,
        "mercy_needed": 100,
        "acts": [
            {"name": "Check", "mercy_gain": 0, "flavor": "A feral Darkner tangled in wire — once a friendly Plugboy, gone a bit wild.", "causes_tired": False},
            {"name": "Unplug", "mercy_gain": 50, "flavor": "You carefully unplug Werewire from the wall. It relaxes, wires going slack.", "causes_tired": False},
        ],
        "tired_lines": ["Werewire's cord sparks weakly, worn down."],
        # Per canon: a spared Werewire reverts back into a friendly Plugboy.
        "spare_lines": ["Werewire calms down completely, transforming back into a friendly Plugboy!"],
        "encounter_lines": ["A Werewire lunges out from a wall socket!", "ZZT! A Werewire crackles to life!"],
        "flirt_sequence": None,
        "attack_patterns": [
            {
                "name": "Static Whip",
                "telegraph": "Werewire's cord whips out, crackling with static electricity!",
                "options": ["duck", "jump"],
                "damage": 16,
            },
        ],
    },
}
