"""Preview pane in the main window: shows where the selected result came from, with quick fixes.

Pictures (images, diagrams, PDF pages) are read again and drawn with every reading boxed: the selected term in
yellow, other kept readings in green, low-confidence readings in red. On PDF pages, typed matches are outlined in
orange. From the pane: correct a misread line and teach it, mark a reading "Not text", or Exclude the term.
"""
import os
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import ImageTk
import app_gui as eng

PIC_W, PIC_H = 380, 330   # canvas size in pixels; labels wrap a little narrower than the pane

class PreviewPane(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, width=PIC_W + 20)
        self.app = app
        self.term = None
        self.locs = []
        self.sources = {}     # path -> [(label, loader)]
        self.cache = {}       # (path, source label) -> (image, lines, pdf_hits)
        self.img = self.tk_img = None
        self.lines, self.hits, self.sel = [], [], None
        self.scale, self.src_label, self.req = 1.0, "", 0
        self.view = (0, 0, 1, 1)     # part of the picture on screen (x, y, w, h)
        self.zoomed = True           # large pictures open zoomed in on the term

        ctk.CTkLabel(self, text="Where it was found", font=("Arial", 13, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.loc_var = ctk.StringVar(value="")
        self.opt_loc = ctk.CTkOptionMenu(self, variable=self.loc_var, values=["(select a result)"], width=PIC_W,
                                         dynamic_resizing=False, command=self._on_loc)
        self.opt_loc.pack(padx=10, pady=(0, 4))
        self.btn_zoom = ctk.CTkButton(self, text="Show whole picture", width=150, height=24, fg_color="#475569",
                                      command=self._toggle_zoom)
        self.btn_zoom.pack(anchor="e", padx=10, pady=(0, 4))
        self.canvas = tk.Canvas(self, width=PIC_W, height=PIC_H, bg="#3A3F47", highlightthickness=0, cursor="hand2")
        self.canvas.pack(padx=10)
        self.canvas.bind("<Button-1>", self._on_click)
        self.lbl_info = ctk.CTkLabel(self, text="Select a result to see where it came from.", wraplength=PIC_W - 30,
                                     justify="left", anchor="w")
        self.lbl_info.pack(fill="x", padx=10, pady=(6, 2))

        fix = ctk.CTkFrame(self)
        fix.pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkLabel(fix, text="Selected reading (fix the spelling if it is wrong):", anchor="w").pack(fill="x", padx=6, pady=(6, 0))
        self.entry = ctk.CTkEntry(fix)
        self.entry.pack(fill="x", padx=6, pady=4)
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

    # ---------- showing ----------
    def show(self, term):
        d = self.app.results.get(term)
        self.term = term
        self.lbl_msg.configure(text="")
        if not d or d.get("manual") or d.get("file_error"):
            self._blank("Added manually: no location to show." if d and d.get("manual") else "Nothing to show for this row.")
            return
        pics = self.app.picture_locations(term)
        self.locs = pics + [l for l in d.get("locations", []) if l not in pics]
        kind = lambda l: "[page] " if "(p." in l and l.lower().split(" (p.")[0].endswith(".pdf") else "[picture] "
        names = [((kind(l) if l in pics else "[typed text] ") + l)[:90] for l in self.locs] or ["(no location)"]
        self.opt_loc.configure(values=names)
        self.loc_var.set(names[0])
        self._show_location(0)

    def _on_loc(self, choice):
        names = list(self.opt_loc.cget("values"))
        if choice in names:
            self._show_location(names.index(choice))

    def _blank(self, msg):
        self.canvas.delete("all")
        self.img = self.tk_img = None
        self.lines, self.hits, self.sel = [], [], None
        self.lbl_info.configure(text=msg)
        self.entry.delete(0, "end")
        self._set_fix_state(False)

    def _set_fix_state(self, picture_line):
        can_train = eng.trainer_available()
        self.btn_teach.configure(state="normal" if picture_line and can_train else "disabled")
        self.btn_junk.configure(state="normal" if picture_line and can_train else "disabled")
        self.btn_undo.configure(state="normal" if can_train else "disabled")
        self.btn_trainer.configure(state="normal" if can_train and self.img is not None else "disabled")
        self.btn_excl.configure(state="normal" if self.term and self.app.excludable(self.term) else "disabled")

    def _show_location(self, i):
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
            self._blank(f"Could not open {name}: {type(e).__name__}"); return
        srcs = self.sources[path]
        k = tg.match_source([lbl for lbl, _ in srcs], loc)
        if k is None:
            self._blank(f"Found in typed text: {loc}.\n\nTyped text is read exactly from the file, letter for letter, "
                        "so there is nothing to correct. If it is not a real term, Exclude it.")
            return
        label, loader = srcs[k]
        self.src_label = label
        self.req += 1
        req = self.req
        key = (path, label)
        if key in self.cache:
            self._paint(*self.cache[key]); return
        self.canvas.delete("all")
        self.lbl_info.configure(text="Reading the picture...")
        def work():
            try:
                img = loader()
                lines = tg.read_region_lines(img)
                hits = self._pdf_hits(path, loc, img)
                self.cache[key] = (img, lines, hits)
                self.after(0, lambda: req == self.req and self._paint(img, lines, hits))
            except Exception as e:
                eng.log_error("Preview could not read the picture")
                msg = f"Could not read this picture: {type(e).__name__}: {e}"
                self.after(0, lambda: req == self.req and self._blank(msg))
        threading.Thread(target=work, daemon=True).start()

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
            return []

    def _toggle_zoom(self):
        self.zoomed = not self.zoomed
        if self.img is not None:
            self._set_view(); self._repaint()

    def _term_box(self):
        """Where the term itself sits: a typed match on a PDF page, else its share of the selected OCR line."""
        if self.hits:
            return self.hits[0]
        if self.sel is None:
            return None
        (x0, y0, x1, y1), text, _c = self.lines[self.sel]
        k = eng.fold(text).find(eng.fold(self.term or ""))
        if k < 0 or not text:
            return (x0, y0, x1, y1)
        per = (x1 - x0) / max(1, len(text))
        return (x0 + k * per, y0, x0 + (k + len(self.term)) * per, y1)

    def _set_view(self):
        """Whole picture, or (large pictures) a window around the selected reading / typed match."""
        img = self.img
        box = self._term_box()
        big = img.width > PIC_W * 2 or img.height > PIC_H * 2
        if self.zoomed and big and box:
            x0, y0, x1, y1 = box
            vw = min(img.width, max(600.0, (x1 - x0) * 6))
            vh = min(img.height, vw * PIC_H / PIC_W)
            vw = min(img.width, vh * PIC_W / PIC_H)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            vx = min(max(0, cx - vw / 2), img.width - vw)
            vy = min(max(0, cy - vh / 2), img.height - vh)
            self.view = (vx, vy, vw, vh)
            self.btn_zoom.configure(text="Show whole picture", state="normal")
        else:
            self.view = (0, 0, img.width, img.height)
            self.btn_zoom.configure(text="Zoom in on the term" if big and box else "Show whole picture",
                                    state="normal" if big and box else "disabled")
        vx, vy, vw, vh = self.view
        self.scale = min(PIC_W / vw, PIC_H / vh, 3.0)
        crop = img.crop((int(vx), int(vy), int(vx + vw), int(vy + vh)))
        self.tk_img = ImageTk.PhotoImage(crop.resize((max(1, int(vw * self.scale)), max(1, int(vh * self.scale)))))

    def _paint(self, img, lines, hits):
        self.img, self.lines, self.hits = img, lines, hits
        focus = [i for i, (_b, t, _c) in enumerate(lines) if self.term and eng.fold(self.term) in eng.fold(t)]
        self.sel = focus[0] if focus else None
        self.zoomed = True
        self._set_view()
        self._repaint()
        cutoff = eng.ocr_cutoff()
        if self.sel is not None:
            _b, t, c = lines[self.sel]
            state = "kept by the scanner" if c >= cutoff else "below the cutoff, so the scanner ignores it"
            self.lbl_info.configure(text=f"Yellow box = '{self.term}', read from this line as \"{t}\" (confidence {c:.2f}, {state}). "
                                         "Click any box to pick another reading.")
        elif hits:
            self.lbl_info.configure(text=f"Orange = '{self.term}' in the page's typed text ({len(hits)} place(s)). "
                                         "Typed text is exact. Boxes show what OCR read in the page's pictures.")
        else:
            self.lbl_info.configure(text=f"'{self.term}' was not read in this picture just now. Boxes show what was read. "
                                         "Click one to fix it, or open the Trainer and draw a box around missed text.")
        self._fill_entry()

    def _repaint(self):
        self.canvas.delete("all")
        if self.tk_img is None:
            return
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        cutoff, s = eng.ocr_cutoff(), self.scale
        vx, vy = self.view[0], self.view[1]
        X = lambda v: (v - vx) * s
        Y = lambda v: (v - vy) * s
        for x0, y0, x1, y1 in self.hits:
            self.canvas.create_rectangle(X(x0) - 2, Y(y0) - 2, X(x1) + 2, Y(y1) + 2, outline="#F97316", width=3)
        for i, ((x0, y0, x1, y1), _t, c) in enumerate(self.lines):
            color = "#22C55E" if c >= cutoff else "#EF4444"
            width = 1
            if i == self.sel:
                color, width = "#FACC15", 3
            self.canvas.create_rectangle(X(x0), Y(y0), X(x1), Y(y1), outline=color, width=width)

    def _fill_entry(self):
        self.entry.delete(0, "end")
        if self.sel is not None:
            self.entry.insert(0, self.lines[self.sel][1])
        self._set_fix_state(self.sel is not None)

    def _on_click(self, e):
        if not self.lines:
            return
        x, y = e.x / self.scale + self.view[0], e.y / self.scale + self.view[1]
        best = None
        for i, ((x0, y0, x1, y1), _t, _c) in enumerate(self.lines):
            if x0 - 4 <= x <= x1 + 4 and y0 - 4 <= y <= y1 + 4:
                area = (x1 - x0) * (y1 - y0)
                if best is None or area < best[0]:
                    best = (area, i)
        if best:
            self.sel = best[1]
            self._repaint(); self._fill_entry()   # keep the current view; only the selection changes
            _b, t, c = self.lines[self.sel]
            self.lbl_info.configure(text=f"Selected reading: \"{t}\" (confidence {c:.2f}). Fix the spelling and click "
                                         "Correct + Teach, or click Not text.")

    # ---------- quick fixes ----------
    def _crop(self, box, margin=3):
        x0, y0, x1, y1 = box
        return self.img.crop((int(max(0, x0 - margin)), int(max(0, y0 - margin)),
                              int(min(self.img.width, x1 + margin)), int(min(self.img.height, y1 + margin))))

    def teach(self):
        import trainer_gui as tg
        if self.sel is None or self.img is None:
            return
        box, read, conf = self.lines[self.sel]
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
        msg = f"Saved \"{text}\" as a corrected line for teaching the reader."
        if added:
            msg += " Fixed on the next scan right away: " + ", ".join(added) + "."
        self.lbl_msg.configure(text=msg)
        self.app.update_banner()

    def not_text(self):
        import trainer_gui as tg
        if self.sel is None or self.img is None:
            return
        box, read, conf = self.lines[self.sel]
        x0, y0, x1, y1 = box
        pad = max(20, int((y1 - y0) * 2))
        region = (max(0, x0 - pad), max(0, y0 - pad), min(self.img.width, x1 + pad), min(self.img.height, y1 + pad))
        crop = self.img.crop(tuple(int(v) for v in region))
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
