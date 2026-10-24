"""Preview pane in the main window: shows where the selected result came from, with quick fixes.

Pictures (images, diagrams, PDF pages, slides' pictures) are read again and drawn with every reading boxed: finds of the
selected term in yellow, other kept readings in green, low-confidence readings in red, words only the second reader
(docTR) found in cyan. On PDF pages, typed matches are outlined in orange. Zoom with the mouse wheel or the + / - buttons,
drag to move around, Enlarge for a big window. Find < > steps through every find of the term, across all its locations.
Typed text in Word, PowerPoint and Excel is shown as text with every match highlighted.
From the pane: correct a misread line and teach it, mark a reading "Not text", or Exclude the term.
"""
import os
import diag
import threading
import tkinter as tk
import customtkinter as ctk
import symbol_picker as SP
from PIL import Image, ImageTk
import app_gui as eng

PIC_W, PIC_H = 380, 330   # canvas size in pixels; labels wrap a little narrower than the pane
BIG_W, BIG_H = 1100, 760  # the Enlarge window's canvas
MIN_VIEW = 24             # most zoomed-in view, in picture pixels


class PicView:
    """A zoomable, draggable picture with boxes. Shared by the pane and the Enlarge window."""

    def __init__(self, parent, w, h, on_select):
        self.w, self.h, self.on_select = w, h, on_select
        self.canvas = tk.Canvas(parent, width=w, height=h, bg="#3A3F47", highlightthickness=0, cursor="hand2")
        self.img = self.tk_img = None
        self.lines, self.hits, self.second, self.finds = [], [], set(), []
        self.sel = None
        self.view = (0.0, 0.0, 1.0, 1.0)
        self._drag = None
        c = self.canvas
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._motion)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Double-Button-1>", lambda e: self.zoom(1.6, e.x, e.y))
        c.bind("<MouseWheel>", lambda e: self.zoom(1.25 if e.delta > 0 else 0.8, e.x, e.y))   # Windows
        c.bind("<Button-4>", lambda e: self.zoom(1.25, e.x, e.y))                              # Linux
        c.bind("<Button-5>", lambda e: self.zoom(0.8, e.x, e.y))
        c.bind("<Configure>", self._resized)

    # ----- data
    def set_data(self, img, lines, hits, second, finds, sel):
        self.img, self.lines, self.hits, self.second, self.finds, self.sel = img, lines, hits, second, finds, sel

    def clear(self):
        self.canvas.delete("all")
        self.img = self.tk_img = None
        self.lines, self.hits, self.second, self.finds, self.sel = [], [], set(), [], None

    # ----- view
    @property
    def scale(self):
        return min(self.w / self.view[2], self.h / self.view[3])

    def _resized(self, e):
        if e.width > 10 and e.height > 10 and (e.width, e.height) != (self.w, self.h):
            self.w, self.h = e.width, e.height
            if self.img is not None:
                self._clamp(); self.render()

    def fit(self):
        if self.img is None:
            return
        self.view = (0.0, 0.0, float(self.img.width), float(self.img.height))
        self._clamp(); self.render()

    def focus_box(self, box, context=6.0):
        """Center on a box with some context around it (zoomed in on large pictures)."""
        if self.img is None or not box:
            self.fit(); return
        x0, y0, x1, y1 = box
        iw, ih = self.img.width, self.img.height
        vw = max(MIN_VIEW, (x1 - x0) * context, 300.0)
        vh = vw * self.h / self.w
        if vh < (y1 - y0) * 3:
            vh = (y1 - y0) * 3; vw = vh * self.w / self.h
        if vw >= iw and vh >= ih:
            self.fit(); return
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.view = (cx - vw / 2, cy - vh / 2, vw, vh)
        self._clamp(); self.render()

    def zoom(self, factor, cx=None, cy=None):
        if self.img is None:
            return
        vx, vy, vw, vh = self.view
        cx = self.w / 2 if cx is None else cx
        cy = self.h / 2 if cy is None else cy
        s = self.scale
        px, py = vx + cx / s, vy + cy / s          # the picture point under the cursor stays put
        nw = max(MIN_VIEW, min(vw / factor, self.img.width * 1.0 if factor < 1 and vw / factor > self.img.width else vw / factor))
        nh = nw * vh / vw
        self.view = (px - (px - vx) * nw / vw, py - (py - vy) * nh / vh, nw, nh)
        self._clamp(); self.render()

    def pan(self, dx, dy):
        vx, vy, vw, vh = self.view
        s = self.scale
        self.view = (vx - dx / s, vy - dy / s, vw, vh)
        self._clamp(); self.render(fast=True)

    def _clamp(self):
        iw, ih = self.img.width, self.img.height
        vx, vy, vw, vh = self.view
        r = self.w / self.h                      # keep the canvas shape so nothing stretches
        if vw / vh > r:
            vh = vw / r
        else:
            vw = vh * r
        if vw > iw and vh > ih:                  # zoomed out past the whole picture: fit it
            k = max(iw / vw, ih / vh)
            vw, vh = vw * k, vh * k
        vx = (iw - vw) / 2 if vw >= iw else min(max(0, vx), iw - vw)
        vy = (ih - vh) / 2 if vh >= ih else min(max(0, vy), ih - vh)
        self.view = (vx, vy, vw, vh)

    def zoom_percent(self):
        return int(round(self.scale * 100)) if self.img is not None else 0

    # ----- drawing
    def render(self, fast=False):
        c = self.canvas
        c.delete("all")
        if self.img is None:
            return
        vx, vy, vw, vh = self.view
        s = self.scale
        iw, ih = self.img.width, self.img.height
        x0, y0 = max(0, int(vx)), max(0, int(vy))
        x1, y1 = min(iw, int(vx + vw + 1)), min(ih, int(vy + vh + 1))
        if x1 > x0 and y1 > y0:
            crop = self.img.crop((x0, y0, x1, y1))
            size = (max(1, int((x1 - x0) * s)), max(1, int((y1 - y0) * s)))
            crop = crop.resize(size, Image.BILINEAR if fast or s > 1 else Image.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(crop)
            c.create_image((x0 - vx) * s, (y0 - vy) * s, image=self.tk_img, anchor="nw")
        X = lambda v: (v - vx) * s
        Y = lambda v: (v - vy) * s
        cutoff = eng.ocr_cutoff()
        finds = {f[1] for f in self.finds if f[0] == "line"}
        for i, ((a, b, cc, d), _t, conf) in enumerate(self.lines):
            if i in finds:
                continue
            color = "#22D3EE" if i in self.second else ("#22C55E" if conf >= cutoff else "#EF4444")
            c.create_rectangle(X(a), Y(b), X(cc), Y(d), outline=color, width=1)
        for k, (a, b, cc, d) in enumerate(self.hits):
            cur = self.sel == ("hit", k)
            c.create_rectangle(X(a) - 2, Y(b) - 2, X(cc) + 2, Y(d) + 2, outline="#F97316", width=4 if cur else 2)
        for i in finds:
            (a, b, cc, d), _t, _c = self.lines[i]
            cur = self.sel == ("line", i)
            c.create_rectangle(X(a) - 1, Y(b) - 1, X(cc) + 1, Y(d) + 1, outline="#FACC15", width=4 if cur else 2)
        if self.sel and self.sel[0] == "line" and self.sel[1] not in finds and self.sel[1] < len(self.lines):
            (a, b, cc, d), _t, _c = self.lines[self.sel[1]]
            c.create_rectangle(X(a) - 1, Y(b) - 1, X(cc) + 1, Y(d) + 1, outline="#FACC15", width=3, dash=(4, 2))

    # ----- mouse
    def _press(self, e):
        self._drag = (e.x, e.y, e.x, e.y, False)

    def _motion(self, e):
        if not self._drag:
            return
        sx, sy, lx, ly, moved = self._drag
        if not moved and abs(e.x - sx) + abs(e.y - sy) < 5:
            return
        self.canvas.configure(cursor="fleur")
        self.pan(e.x - lx, e.y - ly)
        self._drag = (sx, sy, e.x, e.y, True)

    def _release(self, e):
        moved = self._drag[4] if self._drag else False
        self._drag = None
        self.canvas.configure(cursor="hand2")
        if moved:
            self.render()
            return
        if self.img is None:
            return
        s = self.scale
        x, y = e.x / s + self.view[0], e.y / s + self.view[1]
        best = None
        for k, (a, b, cc, d) in enumerate(self.hits):
            if a - 4 <= x <= cc + 4 and b - 4 <= y <= d + 4:
                best = (0, ("hit", k))
        for i, ((a, b, cc, d), _t, _c) in enumerate(self.lines):
            if a - 4 <= x <= cc + 4 and b - 4 <= y <= d + 4:
                area = (cc - a) * (d - b)
                if best is None or (best[0] and area < best[0]):
                    best = (area, ("line", i))
        if best:
            self.on_select(best[1])


class PreviewPane(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, width=PIC_W + 20)
        self.app = app
        self.term = None
        self.locs = []
        self.loc_i = 0
        self.sources = {}     # path -> [(label, loader)]
        self.cache = {}       # (path, source label) -> (image, lines, pdf_hits, second-reader line indexes)
        self.typed = {}       # path -> typed chunks [(label, text)]
        self.src_label, self.req = "", 0
        self.big = None       # the Enlarge window
        self.find_i = 0
        self.mode = "none"    # "picture", "typed" or "none"

        ctk.CTkLabel(self, text="Where it was found", font=("Arial", 13, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.loc_var = ctk.StringVar(value="")
        self.opt_loc = ctk.CTkOptionMenu(self, variable=self.loc_var, values=["(select a result)"], width=PIC_W,
                                         dynamic_resizing=False, command=self._on_loc)
        self.opt_loc.pack(padx=10, pady=(0, 4))
        self.lbl_math = ctk.CTkLabel(self, text="", wraplength=PIC_W - 20, justify="left", anchor="w",
                                     fg_color="#E0E7FF", text_color="#312E81", corner_radius=6, font=("Cambria", 14))
        self.btn_math = ctk.CTkButton(self, text="Read this equation with the math reader", height=28, fg_color="#4338CA",
                                      command=lambda: self.term and self.app.read_equations([self.term]))
        # find stepper + view controls
        self.ctl = ctk.CTkFrame(self, fg_color="transparent")
        self.ctl.pack(fill="x", padx=10, pady=(0, 4))
        B = dict(width=30, height=24, fg_color="#475569")
        self.btn_prev = ctk.CTkButton(self.ctl, text="◀", command=lambda: self.step(-1), **B)
        self.btn_prev.pack(side="left")
        self.lbl_find = ctk.CTkLabel(self.ctl, text="", width=92)
        self.lbl_find.pack(side="left", padx=2)
        self.btn_next = ctk.CTkButton(self.ctl, text="▶", command=lambda: self.step(1), **B)
        self.btn_next.pack(side="left")
        self.btn_big = ctk.CTkButton(self.ctl, text="⤢ Enlarge", width=78, height=24, fg_color="#1E3A8A", command=self.enlarge)
        self.btn_big.pack(side="right")
        self.btn_fit = ctk.CTkButton(self.ctl, text="Whole", width=52, height=24, fg_color="#475569", command=self.fit)
        self.btn_fit.pack(side="right", padx=2)
        self.btn_in = ctk.CTkButton(self.ctl, text="+", command=lambda: self.zoom(1.4), **B)
        self.btn_in.pack(side="right", padx=(2, 0))
        self.btn_out = ctk.CTkButton(self.ctl, text="−", command=lambda: self.zoom(1 / 1.4), **B)
        self.btn_out.pack(side="right", padx=(2, 0))
        self.btn_zoom = self.btn_fit        # older code refers to btn_zoom
        self.stage = tk.Frame(self, width=PIC_W, height=PIC_H, bg="#3A3F47")
        self.stage.pack(padx=10)
        self.stage.pack_propagate(False)
        self.pv = PicView(self.stage, PIC_W, PIC_H, self._select)
        self.pv.canvas.pack(fill="both", expand=True)
        self.txt = tk.Text(self.stage, wrap="word", font=("Segoe UI", 10), bg="#F8FAFC", fg="#0F172A", relief="flat",
                           padx=8, pady=6, cursor="arrow")
        self.txt.tag_configure("hit", background="#FDE68A")
        self.txt.tag_configure("cur", background="#F59E0B", foreground="#000000")
        self.txt.tag_configure("dim", foreground="#64748B")
        self.lbl_info = ctk.CTkLabel(self, text="Select a result to see where it came from.", wraplength=PIC_W - 30,
                                     justify="left", anchor="w")
        self.lbl_info.pack(fill="x", padx=10, pady=(6, 2))

        fix = ctk.CTkFrame(self)
        fix.pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkLabel(fix, text="Selected reading (fix the spelling if it is wrong):", anchor="w").pack(fill="x", padx=6, pady=(6, 0))
        erow = ctk.CTkFrame(fix, fg_color="transparent"); erow.pack(fill="x", padx=6, pady=4)
        self.entry = ctk.CTkEntry(erow)
        self.entry.pack(side="left", fill="x", expand=True)
        SP.button(erow, self.entry).pack(side="left", padx=(4, 0))
        row = ctk.CTkFrame(fix, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=(0, 6))
        self.btn_teach = ctk.CTkButton(row, text="Correct + Teach", width=130, height=30, fg_color="#0F766E", command=self.teach)
        self.btn_teach.pack(side="left", padx=2)
        self.btn_junk = ctk.CTkButton(row, text="Not text", width=90, height=30, fg_color="#64748B", command=self.not_text)
        self.btn_junk.pack(side="left", padx=2)
        self.btn_excl = ctk.CTkButton(row, text="Exclude term", width=110, height=30, fg_color="#DC2626", command=self.exclude)
        self.btn_excl.pack(side="left", padx=2)
        row2 = ctk.CTkFrame(fix, fg_color="transparent")
        row2.pack(fill="x", padx=4, pady=(0, 6))
        self.btn_undo = ctk.CTkButton(row2, text="Undo last save", width=120, height=26, fg_color="#475569", command=self.undo)
        self.btn_undo.pack(side="left", padx=2)
        self.btn_trainer = ctk.CTkButton(row2, text="Open in Trainer", width=130, height=26,
                                         fg_color="#1E3A8A", command=self.open_trainer)
        self.btn_trainer.pack(side="left", padx=2)
        self.lbl_msg = ctk.CTkLabel(self, text="", wraplength=PIC_W - 30, justify="left", anchor="w", text_color="#0F766E")
        self.lbl_msg.pack(fill="x", padx=10, pady=(0, 8))
        self._set_fix_state(False)
        self._update_controls()

    # ---------- compatibility with older callers ----------
    @property
    def img(self):
        return self.pv.img

    @property
    def lines(self):
        return self.pv.lines

    @property
    def sel(self):
        s = self.pv.sel
        return s[1] if s and s[0] == "line" else None

    # ---------- showing ----------
    def show(self, term):
        d = self.app.results.get(term)
        self.term = term
        self.lbl_msg.configure(text="")
        if not d or d.get("manual") or d.get("file_error"):
            self._blank("Added manually: no location to show." if d and d.get("manual") else "Nothing to show for this row.")
            self.locs = []
            self._update_controls()
            return
        self._math_info(term, d)
        pics = self.app.picture_locations(term)
        self.locs = pics + [l for l in d.get("locations", []) if l not in pics]
        kind = lambda l: "[page] " if "(p." in l and l.lower().split(" (p.")[0].endswith(".pdf") else "[picture] "
        names = [((kind(l) if l in pics else "[typed text] ") + l)[:90] for l in self.locs] or ["(no location)"]
        self.opt_loc.configure(values=names)
        self.loc_var.set(names[0])
        self._show_location(0)

    def _math_info(self, term, d):
        """Equation and symbol rows: show the equation, its symbols, and which symbols the document never defines."""
        cat = d.get("category", "")
        txt = ""
        if cat == "Equation":
            undefined = [x for x in d.get("symbols", []) if x in self.app.results
                         and str(self.app.results[x].get("status", "")).startswith("\U0001F50D")]
            txt = f"Equation:  {term}\nSymbols:  {', '.join(d.get('symbols', [])) or '(none)'}"
            txt += f"\nNot defined anywhere in the files:  {', '.join(undefined)}" if undefined else "\nEvery symbol is defined."
        elif cat == "Symbol":
            uses = [k for k, v in self.app.results.items() if v.get("category") == "Equation" and term in v.get("symbols", [])]
            meaning = d.get("selected_definition") or "not defined in the files or the database"
            txt = f"Symbol:  {term}\nMeaning:  {meaning}"
            if uses:
                txt += "\nUsed in:  " + "\n          ".join(u[:70] for u in uses[:4]) + (f"\n          (+{len(uses) - 4} more)" if len(uses) > 4 else "")
        elif cat == "Equation (picture)":
            read = d.get("math_read") or {}
            if read:
                txt = "Math reader:\n" + "\n".join(l for v in read.values() for l in v) if any(read.values()) else "Math reader found no equation here."
            elif eng.MATH_DIR:
                txt = ("This picture looks like an equation. The math reader can read it exactly: subscripts, Greek letters "
                       "and fractions. Click below (about 5 s for a small equation).")
            else:
                txt = ("This picture looks like an equation. Check its symbols by eye: the text reader reads letters well "
                       "but can miss subscripts, Greek letters and fraction bars. The math add-on reads equations exactly.")
        if txt:
            self.lbl_math.configure(text=txt)
            self.lbl_math.pack(fill="x", padx=10, pady=(0, 4), before=self.ctl)
        else:
            self.lbl_math.pack_forget()
        if cat == "Equation (picture)" and eng.MATH_DIR and not d.get("math_read"):
            self.btn_math.pack(fill="x", padx=10, pady=(0, 4), before=self.ctl)
        else:
            self.btn_math.pack_forget()

    def _on_loc(self, choice):
        names = list(self.opt_loc.cget("values"))
        if choice in names:
            self._show_location(names.index(choice))

    def _use(self, mode):
        """Swap the stage between the picture canvas and the typed-text view."""
        if mode == self.mode:
            return
        self.mode = mode
        if mode == "typed":
            self.pv.canvas.pack_forget(); self.txt.pack(fill="both", expand=True)
        else:
            self.txt.pack_forget(); self.pv.canvas.pack(fill="both", expand=True)

    def _blank(self, msg):
        self._use("picture")
        self.pv.clear()
        self.lbl_info.configure(text=msg)
        self.entry.delete(0, "end")
        self._set_fix_state(False)
        self._update_controls()

    def _set_fix_state(self, picture_line):
        can_train = eng.trainer_available()
        self.btn_teach.configure(state="normal" if picture_line and can_train else "disabled")
        self.btn_junk.configure(state="normal" if picture_line and can_train else "disabled")
        self.btn_undo.configure(state="normal" if can_train else "disabled")
        self.btn_trainer.configure(state="normal" if can_train and self.pv.img is not None else "disabled")
        self.btn_excl.configure(state="normal" if self.term and self.app.excludable(self.term) else "disabled")

    def _show_location(self, i, find=0):
        self.loc_i = i
        self.find_i = find
        names = list(self.opt_loc.cget("values"))
        if i < len(names):
            self.loc_var.set(names[i])
        if i >= len(self.locs):
            self._blank("No location recorded."); return
        loc = self.locs[i]
        name = eng._file_of(loc)
        path = self.app.path_for(name)
        if not path:
            self._blank(f"{name} is no longer where it was scanned, so it cannot be shown."); return
        import trainer_gui as tg
        try:
            if path not in self.sources:
                self.sources[path] = tg.list_sources(path)
        except Exception as e:
            diag.swallowed()
            self._blank(f"Could not open {name}: {type(e).__name__}"); return
        srcs = self.sources[path]
        k = tg.match_source([lbl for lbl, _ in srcs], loc)
        self.req += 1
        req = self.req
        if k is None:
            self._show_typed(path, loc, req)
            return
        diag.activity("preview_picture")
        label, loader = srcs[k]
        self.src_label = label
        key = (path, label)
        if key in self.cache:
            self._paint(*self.cache[key]); return
        self._use("picture")
        self.pv.clear()
        self.lbl_info.configure(text="Reading the picture...")
        self._update_controls()
        def work():
            try:
                img = loader()
                lines = tg.read_region_lines(img)
                lines, second = self._second_reader(img, lines)
                hits = self._pdf_hits(path, loc, img)
                self.cache[key] = (img, lines, hits, second)
                self.after(0, lambda: req == self.req and self._paint(img, lines, hits, second))
            except Exception as e:
                eng.log_error("Preview could not read the picture")
                msg = f"Could not read this picture: {type(e).__name__}"
                self.after(0, lambda: req == self.req and self._blank(msg))
        threading.Thread(target=work, daemon=True).start()

    def _second_reader(self, img, lines):
        """Add the words only docTR found (as the scanner does), so a term docTR found gets a box too."""
        second = set()
        if not eng.doctr_active():
            return lines, second
        try:
            import numpy as np
            rgb = np.array(img.convert("RGB"))
            extra = eng.get_doctr().read(rgb, extra_passes=bool(int(eng.OCR_CFG.get("doctr_extra_passes", 1))))
        except Exception:
            diag.swallowed()
            return lines, second
        out = list(lines)
        boxes = [b for b, _t, _c in lines]
        for pts, text, conf, *_ in extra or []:
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            b = (min(xs), min(ys), max(xs), max(ys))
            area = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
            covered = any(max(0, min(b[2], o[2]) - max(b[0], o[0])) * max(0, min(b[3], o[3]) - max(b[1], o[1])) > area * 0.5
                          for o in boxes)
            new_term = self.term and eng.fold(self.term) in eng.fold(str(text)) and \
                not any(eng.fold(self.term) in eng.fold(t) for _b, t, _c in lines)
            if not covered or new_term:
                second.add(len(out))
                out.append((b, str(text), float(conf)))
        return out, second

    def _show_typed(self, path, loc, req):
        """Typed text: show the passage with every match of the term highlighted."""
        diag.activity("preview_typed")
        self._use("typed")
        self.pv.clear()
        self.entry.delete(0, "end")
        self._set_fix_state(False)
        if path in self.typed:
            self._paint_typed(loc); return
        self.txt.configure(state="normal"); self.txt.delete("1.0", "end")
        self.txt.insert("1.0", "Reading the typed text...", "dim"); self.txt.configure(state="disabled")
        self._update_controls()
        def work():
            try:
                chunks = eng.typed_chunks(path)
            except Exception:
                diag.swallowed()
                chunks = []
            self.typed[path] = chunks
            self.after(0, lambda: req == self.req and self._paint_typed(loc))
        threading.Thread(target=work, daemon=True).start()

    def _typed_matches(self, text):
        import re
        if not self.term:
            return []
        pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(self.term) + r"s?(?![A-Za-z0-9])", re.I)
        out = [(m.start(), m.end()) for m in pat.finditer(text)]
        if not out:   # the scanner folds look-alike characters: fall back to a folded search
            ft, fterm = eng.fold(text), eng.fold(self.term)
            k = ft.find(fterm)
            while k >= 0 and fterm:
                out.append((k, k + len(fterm))); k = ft.find(fterm, k + 1)
        return out

    def _paint_typed(self, loc):
        chunks = self.typed.get(eng._file_of(loc) and self.app.path_for(eng._file_of(loc)), [])
        want = loc.split(" [OCR fix", 1)[0]
        text = next((t for lbl, t in chunks if lbl == want), None)
        if text is None or not self._typed_matches(text):
            text = next((t for lbl, t in chunks if self._typed_matches(t)), text)
        t = self.txt
        t.configure(state="normal"); t.delete("1.0", "end")
        if not text:
            t.insert("1.0", f"Found in typed text: {loc}\n\nThe passage could not be shown.", "dim")
            t.configure(state="disabled")
            self.lbl_info.configure(text="Typed text is read exactly from the file, letter for letter. If it is not a real term, Exclude it.")
            self._typed_hits = []
            self._update_controls(); return
        t.insert("1.0", text)
        self._typed_hits = self._typed_matches(text)
        for a, b in self._typed_hits:
            t.tag_add("hit", f"1.0+{a}c", f"1.0+{b}c")
        t.configure(state="disabled")
        self.find_i = min(self.find_i, max(0, len(self._typed_hits) - 1)) if self.find_i >= 0 else len(self._typed_hits) - 1
        self._goto_typed()
        n = len(self._typed_hits)
        self.lbl_info.configure(text=f"Typed text: '{self.term}' highlighted ({n} place(s) in this passage). Typed text is exact; "
                                     "if it is not a real term, Exclude it.")

    def _goto_typed(self):
        t = self.txt
        t.tag_remove("cur", "1.0", "end")
        if self._typed_hits:
            a, b = self._typed_hits[self.find_i]
            t.tag_add("cur", f"1.0+{a}c", f"1.0+{b}c")
            t.see(f"1.0+{a}c")
        self._update_controls()

    def _pdf_hits(self, path, loc, img):
        """Typed matches of the term on a PDF page, in picture pixels (PDFium text search)."""
        if not path.lower().endswith(".pdf") or "(p." not in loc or not self.term:
            return []
        try:
            n = int(loc.rsplit("(p.", 1)[1].split(")")[0])
            doc = eng.pdfium.PdfDocument(path)
            try:
                page = doc[n - 1]
                h_pt = page.get_height()
                s = img.height / h_pt
                tp = page.get_textpage()
                out = []
                srch = tp.search(self.term, match_case=True, match_whole_word=True)
                occ = srch.get_next()
                while occ:
                    idx, cnt = occ
                    for r in range(tp.count_rects(idx, cnt)):
                        l, b, rr, t = tp.get_rect(r)
                        out.append((l * s, (h_pt - t) * s, rr * s, (h_pt - b) * s))
                    occ = srch.get_next()
                srch.close(); tp.close(); page.close()
                return out
            finally:
                doc.close()
        except Exception:
            diag.swallowed()
            return []

    # ---------- finds ----------
    def _finds(self, lines, hits):
        f = [("hit", k) for k in range(len(hits))]
        if self.term:
            ft = eng.fold(self.term)
            f += [("line", i) for i, (_b, t, _c) in enumerate(lines) if ft and ft in eng.fold(t)]
        return f

    def _find_box(self, f):
        if f[0] == "hit":
            return self.pv.hits[f[1]]
        (x0, y0, x1, y1), text, _c = self.pv.lines[f[1]]
        k = eng.fold(text).find(eng.fold(self.term or ""))
        if k < 0 or not text:
            return (x0, y0, x1, y1)
        per = (x1 - x0) / max(1, len(text))
        return (x0 + k * per, y0, x0 + (k + len(self.term)) * per, y1)

    def _paint(self, img, lines, hits, second=frozenset()):
        self._use("picture")
        finds = self._finds(lines, hits)
        if self.find_i < 0:
            self.find_i = len(finds) - 1
        self.find_i = max(0, min(self.find_i, len(finds) - 1)) if finds else 0
        sel = finds[self.find_i] if finds else None
        self.pv.set_data(img, lines, hits, set(second), finds, sel)
        if sel:
            self.pv.focus_box(self._find_box(sel))
        else:
            self.pv.fit()
        self._describe()
        self._fill_entry()
        self._update_controls()
        if self.big is not None and self.big.winfo_exists():
            self._sync_big(fit=True)

    def _describe(self):
        cutoff = eng.ocr_cutoff()
        s = self.pv.sel
        if s and s[0] == "line":
            _b, t, c = self.pv.lines[s[1]]
            who = "the second reader" if s[1] in self.pv.second else "the scanner"
            state = "kept" if c >= cutoff or s[1] in self.pv.second else "below the cutoff, so ignored"
            self.lbl_info.configure(text=f"Yellow = '{self.term}', read by {who} as \"{t}\" (confidence {c:.2f}, {state}). "
                                         "Click any box to pick another reading.")
        elif s and s[0] == "hit":
            self.lbl_info.configure(text=f"Orange = '{self.term}' in the page's typed text ({len(self.pv.hits)} place(s)). "
                                         "Typed text is exact. Other boxes show what OCR read in the page's pictures.")
        elif self.pv.img is not None:
            self.lbl_info.configure(text=f"'{self.term}' was not read in this picture just now. Boxes show what was read. "
                                         "Click one to fix it, or open the Trainer and draw a box around missed text.")

    def _total_finds(self):
        if self.mode == "typed":
            return len(getattr(self, "_typed_hits", []))
        return len(self.pv.finds)

    def _update_controls(self):
        n = self._total_finds()
        many_locs = len(self.locs) > 1
        txt = f"Find {self.find_i + 1} of {n}" if n else ("No find here" if self.mode != "none" and self.locs else "")
        self.lbl_find.configure(text=txt)
        can_step = n > 1 or many_locs
        self.btn_prev.configure(state="normal" if can_step else "disabled")
        self.btn_next.configure(state="normal" if can_step else "disabled")
        pic = self.mode == "picture" and self.pv.img is not None
        for b in (self.btn_in, self.btn_out, self.btn_fit, self.btn_big):
            b.configure(state="normal" if pic else "disabled")

    def step(self, d):
        """Next / previous find: within this location first, then on to the next location of the term."""
        n = self._total_finds()
        if 0 <= self.find_i + d < n:
            self.find_i += d
            if self.mode == "typed":
                self._goto_typed()
            else:
                f = self.pv.finds[self.find_i]
                self.pv.sel = f
                self.pv.focus_box(self._find_box(f))
                self._describe(); self._fill_entry(); self._update_controls()
                if self.big is not None and self.big.winfo_exists():
                    self._sync_big()
            return
        if len(self.locs) > 1:
            nxt = (self.loc_i + d) % len(self.locs)
            self._show_location(nxt, find=0 if d > 0 else -1)

    def _select(self, s):
        """A box was clicked (in the pane or the Enlarge window)."""
        self.pv.sel = s
        if s in self.pv.finds:
            self.find_i = self.pv.finds.index(s)
        self.pv.render()
        self._fill_entry(); self._update_controls()
        if s[0] == "line":
            _b, t, c = self.pv.lines[s[1]]
            self.lbl_info.configure(text=f"Selected reading: \"{t}\" (confidence {c:.2f}). Fix the spelling and click "
                                         "Correct + Teach, or click Not text.")
        else:
            self._describe()
        if self.big is not None and self.big.winfo_exists():
            self._sync_big()

    def zoom(self, f):
        self.pv.zoom(f)

    def fit(self):
        self.pv.fit()

    def _toggle_zoom(self):     # kept for older callers
        self.fit()

    # ---------- Enlarge window ----------
    def enlarge(self):
        if self.pv.img is None:
            return
        diag.activity("preview_enlarged")
        if self.big is None or not self.big.winfo_exists():
            win = ctk.CTkToplevel(self.app); self.big = win
            win.title("Preview"); win.geometry(f"{BIG_W + 20}x{BIG_H + 70}"); win.after(150, win.lift)
            bar = ctk.CTkFrame(win, fg_color="transparent"); bar.pack(fill="x", padx=10, pady=6)
            B = dict(width=34, height=28, fg_color="#475569")
            ctk.CTkButton(bar, text="◀ Find", width=70, height=28, fg_color="#475569", command=lambda: self.step(-1)).pack(side="left")
            win._lbl = ctk.CTkLabel(bar, text="", width=110); win._lbl.pack(side="left", padx=4)
            ctk.CTkButton(bar, text="Find ▶", width=70, height=28, fg_color="#475569", command=lambda: self.step(1)).pack(side="left")
            ctk.CTkLabel(bar, text="Wheel: zoom   Drag: move   Click a box: select", text_color=("#475569", "#94A3B8")).pack(side="left", padx=16)
            ctk.CTkButton(bar, text="Close", width=70, height=28, fg_color="#475569", command=win.destroy).pack(side="right")
            ctk.CTkButton(bar, text="Whole", width=60, height=28, fg_color="#475569", command=lambda: win._pv.fit()).pack(side="right", padx=4)
            ctk.CTkButton(bar, text="+", command=lambda: win._pv.zoom(1.4), **B).pack(side="right", padx=2)
            ctk.CTkButton(bar, text="−", command=lambda: win._pv.zoom(1 / 1.4), **B).pack(side="right", padx=2)
            win._pv = PicView(win, BIG_W, BIG_H, self._select)
            diag.register(win, "preview_big"); diag.register(win._pv.canvas, "preview_big.canvas")
            win._pv.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            win.bind("<Escape>", lambda e: win.destroy())
            win.bind("<Right>", lambda e: self.step(1)); win.bind("<Left>", lambda e: self.step(-1))
        self._sync_big(fit=True)
        self.big.lift()

    def _sync_big(self, fit=False):
        win = self.big
        p = win._pv
        p.set_data(self.pv.img, self.pv.lines, self.pv.hits, self.pv.second, self.pv.finds, self.pv.sel)
        if fit or p.view == (0.0, 0.0, 1.0, 1.0):
            s = self.pv.sel
            if s:
                p.focus_box(self._find_box(s), context=10.0)
            else:
                p.fit()
        else:
            p.render()
        win._lbl.configure(text=self.lbl_find.cget("text"))
        win.title(f"Preview: {self.src_label}"[:120])

    # ---------- quick fixes ----------
    def _fill_entry(self):
        self.entry.delete(0, "end")
        if self.sel is not None:
            self.entry.insert(0, self.pv.lines[self.sel][1])
        self._set_fix_state(self.sel is not None)

    def _crop(self, box, margin=3):
        x0, y0, x1, y1 = box
        img = self.pv.img
        return img.crop((int(max(0, x0 - margin)), int(max(0, y0 - margin)),
                         int(min(img.width, x1 + margin)), int(min(img.height, y1 + margin))))

    def teach(self):
        import trainer_gui as tg
        if self.sel is None or self.pv.img is None:
            return
        box, read, conf = self.pv.lines[self.sel]
        text = self.entry.get().strip()
        if not text:
            return
        rel = tg.save_sample(self._crop(box), text, read, conf, self.src_label, box)
        added = []
        pairs = tg.fixes_from_correction(read, text)
        if pairs:
            rows = eng.read_ocr_fix_rows()
            have = {r[0] for r in rows}
            for a, b in pairs:
                if a not in have:
                    rows.append([a, b, "Correct + Teach (preview)"]); have.add(a); added.append(f"{a} > {b}")
            if added:
                eng.write_ocr_fix_rows(rows)
        tg._log_save({"time": tg._now(), "images": [rel], "ignored": [], "summary": f"line '{text}' (preview)"})
        diag.activity("correct_teach_saved")
        msg = f"Saved \"{text}\" as a corrected line for teaching the reader."
        if added:
            msg += " Fixed on the next scan right away: " + ", ".join(added) + "."
        self.lbl_msg.configure(text=msg)
        self.app.update_banner()

    def not_text(self):
        import trainer_gui as tg
        if self.sel is None or self.pv.img is None:
            return
        img = self.pv.img
        box, read, conf = self.pv.lines[self.sel]
        x0, y0, x1, y1 = box
        pad = max(20, int((y1 - y0) * 2))
        region = (max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))
        crop = img.crop(tuple(int(v) for v in region))
        rel_box = (x0 - region[0], y0 - region[1], x1 - region[0], y1 - region[1])
        rel = tg.save_region(crop, [], [], [(rel_box, read, conf)], self.src_label, region)
        added = []
        if conf >= eng.ocr_cutoff():
            rows = eng.read_ocr_ignore_rows()
            have = {eng.fold(r[0]).strip() for r in rows}
            if eng.fold(read).strip() not in have:
                rows.append([read.strip(), f"Not text, preview {tg._now()}, {self.src_label}"])
                eng.write_ocr_ignore_rows(rows); added.append(read.strip())
        tg._log_save({"time": tg._now(), "images": [rel], "ignored": added, "summary": f"not text '{read}' (preview)"})
        diag.activity("not_text_saved")
        self.lbl_msg.configure(text=(f"\"{read}\" marked Not text. The scanner ignores it in pictures from the next scan."
                                     if added else f"\"{read}\" marked Not text (the scanner already ignored it)."))
        self.app.update_banner()

    def exclude(self):
        self.app.exclude_term()

    def undo(self):
        import trainer_gui as tg
        what = tg.remove_last_save()
        self.lbl_msg.configure(text=f"Removed: {what}" if what else "Nothing to undo.")
        self.app.update_banner()

    def open_trainer(self):
        if self.term and self.locs:
            loc = next((l for l in self.locs if l in self.app.picture_locations(self.term)), None)
            if loc:
                self.app.check_in_picture(self.term, loc); return
        self.app.open_trainer()
