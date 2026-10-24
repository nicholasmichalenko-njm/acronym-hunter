"""Symbol picker: Greek letters, subscripts, superscripts, math operators, accents and units, inserted straight into
the field you are typing in. One floating window serves every attached field: it inserts into whichever attached
field had the cursor last, so it can stay open while you correct several readings.

    import symbol_picker as SP
    SP.attach(entry)                       # right-click menu + Ctrl+Shift+Space on that field
    SP.button(parent, entry).pack(...)     # a small "Ω" button that opens the picker for that field
"""
import json, os, unicodedata
import diag
import tkinter as tk
import customtkinter as ctk

SUB = str.maketrans("0123456789+-=()aehijklmnoprstuvxβγρφχ", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓᵦᵧᵨᵩᵪ")
SUP = str.maketrans("0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW",
                    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ")
UNSUB = {v: k for k, v in zip("0123456789+-=()aehijklmnoprstuvxβγρφχ", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓᵦᵧᵨᵩᵪ")}
UNSUP = {v: k for k, v in zip("0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW",
                              "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ")}

# Combining marks: they attach to the letter just before the cursor (m + dot -> ṁ)
ACCENTS = [("̇", "dot above (ṁ, ẋ: rate)"), ("̈", "two dots (ẍ: 2nd derivative)"), ("̄", "bar (x̄: mean)"),
           ("̂", "hat (x̂: unit vector, estimate)"), ("̃", "tilde (x̃)"), ("⃗", "vector arrow (v⃗)"),
           ("̅", "overline (long bar)"), ("̲", "underline"), ("̸", "slash through (negation)"),
           ("′", "prime ′ (not combining)"), ("″", "double prime ″"), ("‴", "triple prime ‴")]
TABS = {
    "Greek": "αβγδεζηθϑικλμνξοπϖρϱσςτυφϕχψω" "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ",
    "x₂ Sub": "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓᵦᵧᵨᵩᵪ",
    "x² Sup": "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ",
    "Math": "±∓×÷·∙∘√∛∜∞∝∂∇∆∫∬∮∑∏∐′″≈≃≅≡≠≤≥≪≫≲≳∼∠∡⊥∥∦⌀°%‰‱⁄",
    "Accents": "".join(c for c, _ in ACCENTS),
    "Units": "µΩ℧Å℃℉㎛㎜㎝㎞㎏㎎㎐㎑㎒㎓㎾㎿ℓ℔№½⅓⅔¼¾⅛⅜⅝⅞⅕",
    "Arrows": "→←↑↓↔↕⇒⇐⇔↦⟶⟹∈∉∋⊂⊃⊆⊇∪∩∅∀∃∄∧∨¬⊕⊗⊙ℝℕℤℚℂℏℓ∴∵",
}
ALIASES = {"ṁ": "m dot mass flow", "Δ": "delta change", "Ω": "ohm omega", "µ": "micro mu", "°": "degree", "√": "root sqrt",
           "∞": "infinity", "∂": "partial derivative", "∇": "nabla gradient del", "∑": "sum sigma", "∫": "integral",
           "±": "plus minus", "×": "times multiply cross", "·": "dot multiply middle", "≈": "approx about", "≠": "not equal",
           "≤": "less equal", "≥": "greater equal", "∝": "proportional", "→": "arrow right yields", "ℓ": "liter script l",
           "Å": "angstrom", "℃": "celsius", "℉": "fahrenheit", "‰": "per mille", "′": "prime minute foot", "″": "double prime second inch"}

_recent_file = [None]
_recent = []
_targets = []           # attached fields, most recently focused first
_win = [None]

def set_storage(path):
    """Where the 'recently used' row is remembered (a small JSON file in the app's config folder)."""
    _recent_file[0] = path
    try:
        _recent[:] = [c for c in json.load(open(path, encoding="utf-8")) if isinstance(c, str) and len(c) == 1][:24]
    except Exception:
        diag.swallowed()
        pass

def _comb(c):
    return len(c) == 1 and unicodedata.combining(c) > 0

def _remember(ch):
    ch = ch.strip()
    if len(ch) != 1:
        return
    if ch in _recent:
        _recent.remove(ch)
    _recent.insert(0, ch)
    del _recent[24:]
    if _recent_file[0]:
        try:
            json.dump(_recent, open(_recent_file[0], "w", encoding="utf-8"), ensure_ascii=False)
        except Exception:
            diag.swallowed()
            pass

def _raw(entry):
    return getattr(entry, "_entry", entry)          # CTkEntry wraps a tk.Entry

def _alive(entry):
    try:
        return bool(_raw(entry).winfo_exists())
    except Exception:
        diag.swallowed()
        return False

def _target():
    for e in list(_targets):
        if _alive(e):
            return e
        _targets.remove(e)
    return None

def insert(ch, entry=None):
    """Insert ch at the cursor (replacing a selection). Accents attach to the letter before the cursor."""
    e = entry or _target()
    if e is None:
        return
    w = _raw(e)
    if str(w.cget("state")) == "disabled":
        return
    try:
        if w.selection_present():
            w.delete("sel.first", "sel.last")
    except tk.TclError:
        pass
    pos = w.index("insert")
    w.insert(pos, ch)
    text = w.get()
    composed = unicodedata.normalize("NFC", text)
    if composed != text:                               # m + combining dot -> ṁ when a precomposed form exists
        before = unicodedata.normalize("NFC", text[:pos + len(ch)])
        w.delete(0, "end"); w.insert(0, composed); w.icursor(len(before))
    w.focus_set()
    _remember(ch)

def convert(kind, entry=None):
    """Selected text (or the character before the cursor) -> subscript / superscript / normal."""
    e = entry or _target()
    if e is None:
        return
    w = _raw(e)
    try:
        a, b = w.index("sel.first"), w.index("sel.last")
    except tk.TclError:
        b = w.index("insert"); a = max(0, b - 1)
    seg = w.get()[a:b]
    if not seg:
        return
    new = seg.translate(SUB) if kind == "sub" else seg.translate(SUP) if kind == "sup" else \
        "".join(UNSUB.get(c, UNSUP.get(c, c)) for c in seg)
    w.delete(a, b); w.insert(a, new); w.icursor(a + len(new)); w.focus_set()

def attach(entry):
    """Make a field a picker target: focus tracking, right-click menu, Ctrl+Shift+Space opens the picker."""
    w = _raw(entry)
    def focused(_e=None):
        if entry in _targets:
            _targets.remove(entry)
        _targets.insert(0, entry)
    w.bind("<FocusIn>", focused, add="+")
    w.bind("<Control-Shift-space>", lambda e: (focused(), open_picker(w)), add="+")
    def menu(ev):
        focused()
        m = tk.Menu(w, tearoff=0)
        m.add_command(label="Symbols... (Ctrl+Shift+Space)", command=lambda: open_picker(w))
        m.add_command(label="Make selection subscript", command=lambda: convert("sub", entry))
        m.add_command(label="Make selection superscript", command=lambda: convert("sup", entry))
        m.add_command(label="Make selection normal text", command=lambda: convert("normal", entry))
        m.add_separator()
        m.add_command(label="Cut", command=lambda: w.event_generate("<<Cut>>"))
        m.add_command(label="Copy", command=lambda: w.event_generate("<<Copy>>"))
        m.add_command(label="Paste", command=lambda: w.event_generate("<<Paste>>"))
        m.tk_popup(ev.x_root, ev.y_root)
    w.bind("<Button-3>", menu, add="+")
    return entry

def button(parent, entry, **kw):
    """A small Ω button that opens the picker for this field."""
    attach(entry)
    def go():
        if entry in _targets:
            _targets.remove(entry)
        _targets.insert(0, entry)
        open_picker(_raw(entry))
    opts = dict(text="Ω", width=30, height=kw.pop("height", 28), fg_color="#4338CA", font=("Cambria", 15))
    opts.update(kw)
    b = ctk.CTkButton(parent, command=go, **opts)
    return b

def _names(ch):
    try:
        n = unicodedata.name(ch).lower()
    except ValueError:
        n = ""
    return n + " " + ALIASES.get(ch, "")

def open_picker(anchor=None):
    if _win[0] is not None and _win[0].winfo_exists():
        _win[0].deiconify(); _win[0].lift(); _win[0].focus_force(); return _win[0]
    root = anchor.winfo_toplevel() if anchor is not None else tk._default_root
    win = ctk.CTkToplevel(root); _win[0] = win
    diag.register(win, "symbols")
    win.title("Symbols"); win.geometry("540x460"); win.resizable(False, True); win.attributes("-topmost", True)
    try:
        # Physical pixels via raw Tk: CTk's geometry() would scale the position again and push it off-screen.
        try:
            sc = ctk.ScalingTracker.get_window_scaling(win)
        except Exception:
            diag.swallowed()
            sc = 1.0
        x = (anchor.winfo_rootx() if anchor else 200) + 20; y = (anchor.winfo_rooty() if anchor else 200) + 40
        x = min(x, win.winfo_screenwidth() - int(540 * sc) - 10)
        y = min(y, win.winfo_screenheight() - int(460 * sc) - 60)
        tk.Wm.wm_geometry(win, f"+{max(0, x)}+{max(0, y)}")
    except Exception:
        diag.swallowed()
        pass
    top = ctk.CTkFrame(win, fg_color="transparent"); top.pack(fill="x", padx=8, pady=(8, 2))
    q = tk.StringVar()
    ctk.CTkEntry(top, textvariable=q, placeholder_text="Search: sigma, dot, sub 2, degree...", width=250).pack(side="left")
    ctk.CTkButton(top, text="x₂ Sub", width=60, height=28, command=lambda: convert("sub")).pack(side="left", padx=(6, 2))
    ctk.CTkButton(top, text="x² Sup", width=60, height=28, command=lambda: convert("sup")).pack(side="left", padx=2)
    ctk.CTkButton(top, text="Normal", width=60, height=28, fg_color="#475569", command=lambda: convert("normal")).pack(side="left", padx=2)
    tabs = ["Recent"] + list(TABS)
    tabvar = tk.StringVar(value="Recent" if _recent else "Greek")
    seg = ctk.CTkSegmentedButton(win, values=tabs, variable=tabvar, command=lambda _v: draw())
    seg.pack(fill="x", padx=8, pady=4)
    hint = ctk.CTkLabel(win, text="Click to insert into the field you were typing in. Accents attach to the letter before the cursor.",
                        wraplength=520, justify="left", anchor="w", text_color=("#475569", "#94A3B8"), font=("Arial", 11))
    hint.pack(fill="x", padx=10)
    grid = ctk.CTkScrollableFrame(win, fg_color="transparent"); grid.pack(fill="both", expand=True, padx=6, pady=4)
    status = ctk.CTkLabel(win, text="", anchor="w", font=("Arial", 11)); status.pack(fill="x", padx=10, pady=(0, 6))
    def chars():
        s = q.get().strip().lower()
        if s:
            pool = "".join(dict.fromkeys("".join(TABS.values())))
            words = s.replace("sub ", "subscript ").replace("sup ", "superscript ").split()
            return [c for c in pool if all(wd in _names(c) for wd in words)]
        t = tabvar.get()
        return list(_recent) if t == "Recent" else list(TABS[t])
    def draw():
        for w in grid.winfo_children():
            w.destroy()
        cs = chars()
        if not cs:
            ctk.CTkLabel(grid, text="Nothing here yet." if not q.get() else "No match.").grid(row=0, column=0, padx=6, pady=6)
            return
        acc = dict(ACCENTS)
        for i, c in enumerate(cs[:240]):
            label = ("◌" + c) if _comb(c) else c
            b = ctk.CTkButton(grid, text=label, width=40, height=36, font=("Cambria", 18), fg_color=("#E0E7FF", "#312E81"),
                              text_color=("#1E1B4B", "#E0E7FF"), hover_color=("#C7D2FE", "#4338CA"),
                              command=lambda ch=c: insert(ch))
            b.grid(row=i // 10, column=i % 10, padx=2, pady=2)
            tip = acc.get(c) or (unicodedata.name(c, "").title() if len(c) == 1 else "")
            b.bind("<Enter>", lambda _e, t=tip, ch=c: status.configure(text=f"{'◌' + ch if _comb(ch) else ch}  {t}"))
    q.trace_add("write", lambda *_: draw())
    win.bind("<Escape>", lambda e: win.withdraw())
    draw()
    return win
