"""Bullet characters as Word stores them and as people see them (3.32.1).

Word keeps most bullets as a character in a symbol font: the round bullet is U+F0B7 (or a middle dot) in Symbol, the
square bullet U+F0A7 (or a section sign) in Wingdings, the arrowhead U+F0D8 in Wingdings, the check U+F0FC. Shown in
any other font those characters are empty boxes. This module turns them into the real characters people see (shown),
compares two bullets by what they show (same), and turns a bullet back into the form Word draws on every PC (word_form):
the character in Symbol or Wingdings, as Word itself writes it. Rules only; nothing leaves the PC."""

SYMBOL = {0xB7: "•", 0xA7: "♣", 0xA8: "♦", 0xA9: "♥", 0xAA: "♠", 0xAE: "→", 0xE0: "◊",
          0x2D: "−", 0xB0: "°", 0xD7: "⋅"}
WINGDINGS = {0xA7: "▪", 0x6C: "●", 0x6E: "■", 0x71: "❑", 0x75: "◆", 0x76: "❖", 0xD8: "➢",
             0xFC: "✓", 0xFB: "✗", 0xA8: "◻", 0xE8: "➔", 0xF0: "⇨", 0x9F: "•", 0x77: "⬥",
             0xAB: "★", 0x6F: "□", 0xA1: "○"}
# the form Word writes for each character people see
WORD = {"•": ("", "Symbol"), "▪": ("", "Wingdings"), "➢": ("", "Wingdings"),
        "✓": ("", "Wingdings"), "✔": ("", "Wingdings"), "❖": ("", "Wingdings"),
        "◆": ("", "Wingdings"), "●": ("", "Wingdings"), "■": ("", "Wingdings"),
        "❑": ("", "Wingdings"), "◻": ("", "Wingdings"), "➔": ("", "Wingdings"),
        "⇨": ("", "Wingdings"), "✗": ("", "Wingdings"), "□": ("", "Wingdings"),
        "○": ("", "Wingdings"), "★": ("", "Wingdings")}


def kind(font):
    """'symbol', 'wingdings' or '' for a font name."""
    f = str(font or "").strip().lower()
    if f == "symbol":
        return "symbol"
    if f.startswith("wingdings"):
        return "wingdings"
    return ""


def is_symbol_font(font):
    return bool(kind(font))


def _char(ch, k):
    o = ord(ch)
    pua = 0xF000 <= o <= 0xF0FF
    if not pua and not k:
        return ch
    code = o - 0xF000 if pua else o
    if code > 0xFF:
        return ch
    if k == "symbol":
        return SYMBOL.get(code, "•" if pua else ch)
    if k == "wingdings":
        return WINGDINGS.get(code, "•" if pua else ch)
    # a symbol character with no font named: Word's round bullet is Symbol's; the others are Wingdings'
    return SYMBOL[code] if code == 0xB7 else WINGDINGS.get(code) or SYMBOL.get(code) or "•"


def shown(text, font=""):
    """What the bullet looks like, as real characters that show in any font."""
    k = kind(font)
    return "".join(_char(c, k) for c in str(text or ""))


def same(a_text, a_font, b_text, b_font):
    """Two bullets that show the same character."""
    return shown(a_text, a_font) == shown(b_text, b_font)


def word_form(text, font=""):
    """(text, font) as Word writes the bullet, so it shows on every PC: a known character in Symbol or Wingdings; a
    symbol character keeps (or gets) its font; anything else stays as it is, in the font given."""
    t = str(text or "")
    k = kind(font)
    if k:
        return t, font
    if any(0xF000 <= ord(c) <= 0xF0FF for c in t):         # a symbol character with no font named: name it
        s = shown(t)
        if s in WORD:
            return WORD[s]
        return t, ("Symbol" if t == "" else "Wingdings")
    if t in WORD and not str(font or "").strip():
        return WORD[t]
    return t, font


def for_display(text, font=""):
    """(text, font) for a person: the real character, and no symbol font named (the text's own font shows it)."""
    return shown(text, font), ("" if is_symbol_font(font) else (font or ""))
