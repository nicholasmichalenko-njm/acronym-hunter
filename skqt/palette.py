"""The app's colors by choice (4.29.1; Nicholas 2026-11-13 answer 19): Station navy (the tokens as they are), Slate and
teal, or My colors: an accent, a menu color and a page color typed as hex values in Settings > Appearance. The values
are kept in this PC's settings ("palette", "brand_colors"), never in the code. Every other token is worked out from the
three, so a palette is three colors and nothing else. warn() says, in plain words, where text would be hard to read; it
never stops a choice. No Qt here. Rules only (No AI); nothing leaves the PC."""
import re

NAVY, SLATE, MINE = "navy", "slate", "mine"
CHOICES = ((NAVY, "Station navy"), (SLATE, "Slate and teal"), (MINE, "My colors"))
NAMED = {SLATE: {"accent": "#0F6F6A", "menu": "#0E2230", "page": "#F1F4F3"}}
FIELDS = (("accent", "Accent", "Buttons, links and what is picked"), ("menu", "Menu", "The menu down the left side"),
          ("page", "Page", "The background behind the cards (light only)"))
_HEX = re.compile(r"^#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$")
INK, WHITE = "#0E1A2B", "#FFFFFF"


def clean(v):
    """A hex color as #RRGGBB, or "" when it is not one (#abc reads as #AABBCC)."""
    m = _HEX.match(str(v or "").strip())
    if not m:
        return ""
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h.upper()


def _rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, part):
    """a over b: part of a (0 to 1), the rest b."""
    x, y = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x[i] * part + y[i] * (1 - part)):02X}" for i in range(3))


def lum(h):
    out = []
    for c in _rgb(h):
        c /= 255
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable(color, on, want=4.5, toward=WHITE):
    """color, moved toward white (or ink) a step at a time until it reads on its background."""
    c = color
    for _i in range(20):
        if contrast(c, on) >= want:
            break
        c = mix(toward, c, 0.12)
    return c


def colors_of(settings):
    """The three colors chosen, or {} for Station navy. Bad or missing values of My colors fall back one by one."""
    s = settings or {}
    key = s.get("palette") or NAVY
    if key == SLATE:
        return dict(NAMED[SLATE])
    if key != MINE:
        return {}
    got = {k: clean((s.get("brand_colors") or {}).get(k)) for k, _n, _w in FIELDS}
    return {k: v for k, v in got.items() if v}


def tokens(base, colors, dark):
    """base (design.LIGHT or DARK) with the chosen colors worked in. colors: {"accent", "menu", "page"}, any missing."""
    t = dict(base)
    c = {k: clean(v) for k, v in (colors or {}).items()}
    acc, menu, page = c.get("accent"), c.get("menu"), c.get("page")
    if page and not dark:
        t["bg"] = page
        t["surface2"] = mix(page, WHITE, 0.5)
    if acc:
        a = readable(acc, t["surface"], 6.5, WHITE) if dark else acc
        t["accent"] = a
        t["accent_fg"] = WHITE if contrast(a, WHITE) >= contrast(a, "#06101F") else "#06101F"
        t["accent_hover"] = mix(WHITE, a, 0.14) if dark else mix("#000000", a, 0.16)
        t["accent_soft"] = mix(a, t["surface"], 0.16 if dark else 0.12)
        t["accent_line"] = mix(a, t["surface"], 0.45)
        t["accent_tint"] = mix(a, t["surface"], 0.10 if dark else 0.05)
        t["focus"] = mix(WHITE, a, 0.15) if dark else mix(WHITE, a, 0.10)
    if menu:
        fg = WHITE if lum(menu) < 0.35 else INK
        t["rail"] = menu
        t["rail_text"] = mix(fg, menu, 0.80)
        t["rail_group"] = mix(fg, menu, 0.62)
        t["rail_rule"] = mix(fg, menu, 0.13)
        t["rail_card"] = mix(fg, menu, 0.05)
        t["rail_ring"] = mix(fg, menu, 0.28)
        t["rail_dim"] = mix(fg, menu, 0.52)
    if acc or menu:                                  # what is picked in the menu follows the accent, readable on the menu
        rail = t["rail"]
        on = readable(acc or t["rail_sel_bar"], rail, 3.0, WHITE if lum(rail) < 0.35 else INK)
        t["rail_sel_bar"] = on
        t["rail_sel_bg"] = mix(on, rail, 0.28)
        t["rail_active"] = on
        t["rail_active_text"] = WHITE if contrast(on, WHITE) >= contrast(on, "#06101F") else "#06101F"
    return t


PAIRS = (("accent_fg", "accent", 4.5, "The words on a main button are hard to read on the accent"),
         ("accent", "surface", 3.0, "Links and what is picked are hard to see on a card: the accent is too close to the card's color"),
         ("rail_text", "rail", 4.5, "The menu's words are hard to read on the menu color"),
         ("text", "bg", 7.0, "The page color is too dark for the text on it"))


def warn(t):
    """Plain sentences for the pairs that fall short, each with its ratio. [] when every pair reads well."""
    out = []
    for fg, bg, want, say in PAIRS:
        r = contrast(t[fg], t[bg])
        if r < want:
            out.append(f"{say} ({r:.1f} to 1; {want:g} to 1 reads well).")
    return out
