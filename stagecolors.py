"""Stage colors (3.12.0): each stage has a color that tints a few accents on the effort's pages (the header's rule,
the stage pill, the current stage on the track), never the whole theme.

A stage's own color (stage["color"], set in Edit stages) wins; otherwise its name picks one (Pink team pink, Red team
red, Gold team gold), and any other stage takes the next color of the palette by its place. Every color reads with
white text and as a line on both the light and the dark theme."""
import re

PALETTE = (("Indigo", "#5B6FD6"), ("Teal", "#1F8A7A"), ("Rose", "#C2507A"), ("Red", "#C0392B"), ("Gold", "#B8860B"),
           ("Blue", "#2F6FB0"), ("Purple", "#7A4FD1"), ("Slate", "#5A6678"), ("Green", "#2F7D4F"), ("Orange", "#C25E1A"))
NAMED = {k: v for k, v in PALETTE}
BY_WORD = ((r"\bpink\b", "Rose"), (r"\bred\b", "Red"), (r"\bgold\b", "Gold"), (r"\bblue\b", "Blue"), (r"\bgreen\b", "Green"),
           (r"\bwhite\b|\bfinal\b|\bproduction\b", "Slate"), (r"submit", "Slate"), (r"\bdraft|\bauthor|\bwrit", "Teal"),
           (r"\bplan|\bkick|\bcapture|\bstart", "Indigo"), (r"\bblack\b|\blessons?\b|\bdebrief", "Purple"))


def is_hex(c):
    return bool(re.fullmatch(r"#?[0-9A-Fa-f]{6}", str(c or "")))


def color_of(stage, index=0):
    """'#RRGGBB' for a stage dict (or a name) at its place in the effort's stages."""
    if isinstance(stage, dict):
        own = stage.get("color", "")
        if own in NAMED:
            return NAMED[own]
        if is_hex(own):
            return "#" + own.lstrip("#").upper()
        name = stage.get("name", "")
    else:
        name = str(stage or "")
    low = name.lower()
    for pat, c in BY_WORD:
        if re.search(pat, low):
            return NAMED[c]
    return PALETTE[index % len(PALETTE)][1]


def soft(hex_color, amount=0.85, base="#FFFFFF"):
    """The color mixed toward base (white for the light theme, the surface for the dark one)."""
    a = [int(hex_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    b = [int(base.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02X}" for x, y in zip(a, b))
