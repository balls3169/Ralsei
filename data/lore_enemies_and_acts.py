"""
Enemy definitions for !battle.

Each enemy is its own dict — ACT menus are per-enemy, not universal,
per planning (this mirrors how ACT actually works in Deltarune).

Fields:
  name            - display name
  hp              - starting/max HP
  mercy_needed    - % mercy required before SPARE works (100 = must fully fill)
  acts            - list of dicts: {"name": ..., "mercy_gain": int, "flavor": str,
                                     "causes_tired": bool}
  tired_lines     - flavor when this enemy becomes TIRED
  spare_lines     - flavor when successfully spared
  encounter_lines - pool of opening lines when the fight starts
  flirt_sequence  - special-cased list of flirt attempts if this enemy supports
                     X-Flirt (per planning: fails twice, then works)

This is intentionally a small starter roster (2 enemies) to prove out the
system end-to-end. Add more enemies here following the same shape.
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
    },
}
