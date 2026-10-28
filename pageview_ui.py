"""Assign on the real page (2.56.0): the customer document exactly as it looks, every page in one scroll, each review
sentence boxed in its decision's color; click a box to select it, drag across several to select them, and assign with
the usual keys (R, C, X, G, H, S, 1-3). Labels in the left margin say what each sentence is (REQ L.4-02, SUPPORTS
L.4-02, a header's number), and a line runs from the selected sentence to the ones tied to it.

PDFs are shown as they are. Word, Excel and PowerPoint files are shown through a PDF copy that Microsoft Office on this
PC makes (office_pdf.py), kept in the effort's folder. Text view stays one click away. Rules only (No AI); nothing
leaves the PC.
"""
import os, threading
import tkinter as tk
import customtkinter as ctk
import diag
import layout as LY
import docview as DV
import office_pdf as OP

GAP = 18            # between pages
MARGIN = 150        # left margin for the labels
LABEL_FG = {"req": "#15803D", "ctx": "#1D4ED8", "cust": "#7E22CE", "hdr": "#B45309"}


class PageViewMixin:
    # ------------------------------------------------------------ building
    def _pv_build(self, page, text_parts):
        """The Page view / Text view switch and the page canvas (packed when Page view is on)."""
        win = self._cwin
        win.pv = {"on": False, "file": None, "pdf": "", "sizes": [], "tops": [], "scale": 1.0, "maps": {}, "base": {},
                  "photos": {}, "page_of": {}, "sig": None, "busy": False, "msg": "", "drag": None, "conv": set()}
        win.pv_text_parts = text_parts
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", padx=18, pady=(6, 0), before=win.cp_src)
        win.pv_switch = ctk.CTkSegmentedButton(bar, values=["Page view", "Text view"], command=self._pv_switch)
        win.pv_switch.pack(side="left")
        win.pv_note = ctk.CTkLabel(bar, text="", anchor="w", text_color=("#64748B", "#94A3B8"))
        win.pv_note.pack(side="left", padx=10)
        fr = tk.Frame(page, bg="#E2E8F0")
        cv = tk.Canvas(fr, highlightthickness=0, bg="#E2E8F0", cursor="arrow", takefocus=1)
        sb = tk.Scrollbar(fr, orient="vertical", command=lambda *a: (cv.yview(*a), self._pv_soon()))
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        cv.bind("<ButtonPress-1>", self._pv_press)
        cv.bind("<B1-Motion>", self._pv_motion)
        cv.bind("<ButtonRelease-1>", self._pv_release)
        cv.bind("<Key>", self._cp_key)
        cv.bind("<Button-3>", self._pv_menu)
        cv.bind("<Configure>", lambda _e: self._pv_soon(relayout=True))
        cv.bind("<MouseWheel>", lambda e: (cv.yview_scroll(-3 if e.delta > 0 else 3, "units"), self._pv_soon()))
        cv.bind("<Button-4>", lambda _e: (cv.yview_scroll(-3, "units"), self._pv_soon()))
        cv.bind("<Button-5>", lambda _e: (cv.yview_scroll(3, "units"), self._pv_soon()))
        win.pv_frame, win.pv_cv = fr, cv
        want = "Page view"
        try:
            want = self.ws.get("assign_view", "Page view") if getattr(self, "ws", None) is not None else "Page view"
        except Exception:
            diag.swallowed()
        win.pv_switch.set(want)
        win.pv["want"] = want == "Page view"

    def _pv_switch(self, value):
        win = self._cwin
        win.pv["want"] = value == "Page view"
        try:
            self.ws.set("assign_view", value)
        except Exception:
            diag.swallowed()
        if win.pv["want"]:
            diag.activity("assign_page_view")
        else:
            diag.activity("assign_text_view")
        self._pv_refresh(force=True)

    def _pv_show_canvas(self, on):
        win = self._cwin
        if on == win.pv["on"]:
            return
        win.pv["on"] = on
        if on:
            for w in win.pv_text_parts:
                w.pack_forget()
            win.pv_frame.pack(fill="both", expand=True, padx=(8, 4), pady=(4, 8))
        else:
            win.pv_frame.pack_forget()
            for w, opts in zip(win.pv_text_parts, win.pv_text_opts):
                w.pack(**opts)

    # ------------------------------------------------------------ the PDF behind a file
    def _pv_copies_dir(self):
        ws = getattr(self, "ws", None)
        root = getattr(ws, "root", None) if ws is not None else None
        return os.path.join(root or _eng().CONFIG_DIR, "page copies")

    def _pv_pdf_of(self, f):
        """(pdf path or "", why not). Starts the Office copies in the background when they are not made yet."""
        win = self._cwin
        path = self._cp_path(f) if hasattr(self, "_cp_path") else ""
        if not path:
            return "", "the file is not on this PC"
        if path.lower().endswith(".pdf"):
            return path, ""
        if not OP.kind(path):
            return "", "Page view shows PDF, Word, Excel and PowerPoint files"
        try:
            c = OP.copy_path(path, self._pv_copies_dir())
        except OSError:
            return "", "the file could not be read"
        if os.path.isfile(c):
            return c, ""
        err = win.pv.get("err", {}).get(path)
        if err:
            return "", err
        if path not in win.pv["conv"]:
            self._pv_convert_all()
        return "", f"making a PDF copy with Microsoft {OP.kind(path).capitalize()} (once per file; about a minute)"

    def _pv_convert_all(self):
        """Every Word, Excel and PowerPoint file of the review, in one Office session per program, in the background."""
        win = self._cwin
        files = {it.get("file", "") for it in self.matrix.items}
        paths = [p for p in (self._cp_path(f) for f in files) if p and OP.kind(p) and p not in win.pv["conv"]]
        if not paths:
            return
        win.pv["conv"] |= set(paths)
        folder = self._pv_copies_dir()
        diag.activity("page_copies_started", files=len(paths))

        def work():
            try:
                res = OP.make_many(paths, folder)
            except Exception:
                diag.swallowed()
                res = {p: RuntimeError("Office could not save a PDF copy") for p in paths}
            errs = {p: str(r) for p, r in res.items() if isinstance(r, Exception)}

            def done():
                if win.winfo_exists():
                    win.pv.setdefault("err", {}).update(errs)
                    diag.activity("page_copies_done", files=len(res) - len(errs), errors=len(errs))
                    self._pv_refresh(force=True)
            try:
                win.after(0, done)
            except Exception:
                diag.swallowed()
        threading.Thread(target=work, daemon=True).start()

    # ------------------------------------------------------------ layout and drawing
    def _pv_soon(self, relayout=False):
        win = self._cwin
        if win is None or not hasattr(win, "pv") or not win.pv["on"]:
            return
        if relayout:
            win.pv["relayout"] = True
        if win.pv.get("after"):
            try:
                win.after_cancel(win.pv["after"])
            except Exception:
                diag.swallowed()
        win.pv["after"] = win.after(60, self._pv_draw)

    def _pv_refresh(self, force=False):
        """Page view for the current file: on when wanted and a PDF (or Office copy) is there; else the text view with
        the reason. Recomputes the page maps when the review's sentences changed; otherwise redraws the boxes."""
        win = self._cwin
        if win is None or not hasattr(win, "pv"):
            return
        pv = win.pv
        f = win.cp_file
        pdf, why = self._pv_pdf_of(f) if (pv["want"] and f) else ("", "")
        if not pdf:
            self._pv_show_canvas(False)
            win.pv_note.configure(text=(f"Text view: {why}." if pv["want"] and why else ""))
            return
        win.pv_note.configure(text="Click a sentence; drag across several; R, C, X, G, H, S as usual.")
        rows = self._cp_items_of(f)
        sig = (f, pdf, tuple((it["id"], it["text"]) for it in rows))
        if sig != pv["sig"] or force or pdf != pv["pdf"]:
            self._pv_load(f, pdf, rows)
            pv["sig"] = sig
        self._pv_show_canvas(True)
        self._pv_soon(relayout=True)

    def _pv_load(self, f, pdf, rows):
        """Page sizes, which page each sentence is on (laid over the PDF's own words), and fresh page maps."""
        import pypdfium2 as pdfium
        pv = self._cwin.pv
        doc = pdfium.PdfDocument(pdf)
        try:
            pv["sizes"] = [doc[i].get_size() for i in range(len(doc))]
        finally:
            doc.close()
        lines = DV.doc_lines(pdf)
        page_of = {}
        if lines:
            res = DV.align(lines, rows)
            for iid, (a, _b) in res["span"].items():
                where = lines[res["words"][a][1]][0]
                if where.startswith("p."):
                    page_of[iid] = int(where[2:])
        pv.update(file=f, pdf=pdf, page_of=page_of, maps={}, base={}, photos={}, relayout=True)

    def _pv_map(self, n):
        pv = self._cwin.pv
        if n not in pv["maps"]:
            items = [dict(it, page=pv["page_of"].get(it["id"], -99)) for it in self._cp_items_of(pv["file"])]
            try:
                pv["maps"][n] = LY.page_map(pv["pdf"], n, items, self.matrix.headings)
            except Exception:
                diag.swallowed()
                pv["maps"][n] = {"size": pv["sizes"][n - 1], "items": [], "headings": [], "missing": [], "chars": 0}
        return pv["maps"][n]

    def _pv_draw(self):
        """Lay the pages out to the canvas width, render the ones in view (and one either side), draw boxes and labels."""
        win = self._cwin
        pv = win.pv
        pv["after"] = None
        if not pv["on"] or not pv["sizes"]:
            return
        cv = win.pv_cv
        cw = max(500, cv.winfo_width())
        maxw = max(w for w, _h in pv["sizes"])
        scale = round(max(0.4, (cw - MARGIN - 24) / maxw), 3)
        if pv.get("relayout") or abs(scale - pv["scale"]) > 0.01:
            pv["scale"] = scale
            pv["base"], pv["photos"] = {}, {}
            tops, y = [], 10
            for _w, h in pv["sizes"]:
                tops.append(y)
                y += int(h * scale) + GAP
            pv["tops"] = tops
            cv.configure(scrollregion=(0, 0, cw, y))
            pv["relayout"] = False
        top = cv.canvasy(0)
        bot = top + cv.winfo_height()
        vis = [n for n in range(1, len(pv["sizes"]) + 1)
               if pv["tops"][n - 1] < bot + 400 and pv["tops"][n - 1] + pv["sizes"][n - 1][1] * scale > top - 400]
        for n in list(pv["base"]):
            if n not in vis:
                pv["base"].pop(n, None)
        cv.delete("all")
        sel = self._c_selected()
        cur = sel[0]["id"] if sel else ""
        rng = set(win.cp_range or [])
        dec = {it["id"]: it.get("decision", "") for it in self.matrix.items}
        from PIL import ImageTk
        photos = {}
        for n in range(1, len(pv["sizes"]) + 1):
            y0 = pv["tops"][n - 1]
            w, h = pv["sizes"][n - 1]
            if n not in vis:
                cv.create_rectangle(MARGIN, y0, MARGIN + w * scale, y0 + h * scale, fill="#FFFFFF", outline="#CBD5E1")
                continue
            if n not in pv["base"]:
                try:
                    pv["base"][n] = LY.render(pv["pdf"], n, scale)
                except Exception:
                    diag.swallowed()
                    continue
            m = self._pv_map(n)
            img = LY.overlay(pv["base"][n], m, dec, scale, (rng | {cur}) if rng else cur, True)
            photos[n] = ImageTk.PhotoImage(img)
            cv.create_image(MARGIN, y0, image=photos[n], anchor="nw")
            cv.create_text(MARGIN - 8, y0 + 4, text=f"Page {n}", anchor="ne", fill="#64748B", font=("Segoe UI", 9))
            last_y = -100
            for x in sorted(m["items"], key=lambda x: (x["rects"][0][1], x["rects"][0][0]) if x["rects"] else (0, 0)):
                it = self._c_item(x["id"])
                if it is None or not x["rects"]:
                    continue
                kind, txt = self._cp_badge_for(it)
                if not txt or (x.get("part") == "end"):
                    continue
                l, t_, r, b = x["rects"][0]
                ly = max(y0 + t_ * scale, last_y + 13)          # two labels on one line: the second goes under the first
                last_y = ly
                cv.create_text(MARGIN - 8, ly, text=txt.replace(" ", " ").strip(), anchor="ne",
                               fill=LABEL_FG.get(kind, "#334155"), font=("Segoe UI", 9, "bold"), width=MARGIN - 14)
        pv["photos"] = photos
        self._pv_lines(cur)

    def _pv_box(self, iid):
        """(page, first rect) of a sentence on the pages drawn, else None."""
        pv = self._cwin.pv
        n = pv["page_of"].get(iid)
        for p in ([n] if n else []) + [p for p in pv["maps"] if p != n]:
            m = pv["maps"].get(p) or (self._pv_map(p) if p == n else None)
            for x in (m or {}).get("items", []):
                if x["id"] == iid and x["rects"]:
                    return p, x["rects"][0]
        return None

    def _pv_lines(self, cur):
        """A line in the margin from the selected sentence to each sentence tied to it."""
        win = self._cwin
        pv = win.pv
        if not cur:
            return
        try:
            ids, _how = self._cp_related(self._c_item(cur))
        except Exception:
            diag.swallowed()
            return
        a = self._pv_box(cur)
        if a is None:
            return
        cv = win.pv_cv
        s = pv["scale"]
        ya = pv["tops"][a[0] - 1] + (a[1][1] + a[1][3]) / 2 * s
        for i in ids:
            b = self._pv_box(i)
            if b is None:
                continue
            yb = pv["tops"][b[0] - 1] + (b[1][1] + b[1][3]) / 2 * s
            x = MARGIN - 4
            cv.create_line(x, ya, x - 10, ya, x - 10, yb, x, yb, fill="#2563EB", width=2, arrow="last")

    # ------------------------------------------------------------ pointing
    def _pv_at(self, x, y):
        """(page, x, y in PDF points) under a canvas point, or None."""
        pv = self._cwin.pv
        s = pv["scale"]
        for n, t in enumerate(pv["tops"], 1):
            w, h = pv["sizes"][n - 1]
            if t <= y <= t + h * s and MARGIN <= x <= MARGIN + w * s:
                return n, (x - MARGIN) / s, (y - t) / s
        return None

    def _pv_press(self, e):
        win = self._cwin
        cv = win.pv_cv
        cv.focus_set()
        win.pv["drag"] = (cv.canvasx(e.x), cv.canvasy(e.y), bool(e.state & 0x0001))

    def _pv_motion(self, e):
        win = self._cwin
        d = win.pv.get("drag")
        if not d:
            return
        cv = win.pv_cv
        cv.delete("rubber")
        cv.create_rectangle(d[0], d[1], cv.canvasx(e.x), cv.canvasy(e.y), outline="#2563EB", dash=(4, 2), width=2, tags="rubber")

    def _pv_release(self, e):
        win = self._cwin
        cv = win.pv_cv
        d = win.pv.get("drag")
        win.pv["drag"] = None
        cv.delete("rubber")
        x, y = cv.canvasx(e.x), cv.canvasy(e.y)
        if d and abs(x - d[0]) + abs(y - d[1]) > 8:
            return self.pv_select_box(min(d[0], x), min(d[1], y), max(d[0], x), max(d[1], y))
        return self.pv_click(x, y, shift=bool(d and d[2]))

    def pv_click(self, x, y, shift=False):
        """A click at a canvas point: a sentence is selected (Shift adds it to the selected ones; a click on a word of
        the selected sentence is where S splits it); red text not in the review is added to it."""
        win = self._cwin
        at = self._pv_at(x, y)
        if at is None:
            return None
        n, px, py = at
        m = self._pv_map(n)
        h = LY.hit(m, px, py, True)
        if h is None:
            return None
        if h[0] == "missing":
            miss = m["missing"][h[1]]
            added = self.compliance_add_missing([{"file": win.pv["file"], "lines": [(f"p.{n}", miss["text"], "missing")]}]) \
                if hasattr(self, "compliance_add_missing") else []
            if added:
                self._cp_select(added[0]["id"])
            return ("added", added[0]["id"] if added else None)
        iid = h[1]
        if shift:
            rng = list(win.cp_range or [])
            sel = self._c_selected()
            if not rng and sel:
                rng = [sel[0]["id"]]
            rng = [i for i in rng if i != iid] if iid in rng else rng + [iid]
            self.cp_set_range(rng)
            self._pv_soon()
            return ("range", rng)
        sel = self._c_selected()
        if sel and sel[0]["id"] == iid:                 # a click inside the selected sentence: where S splits it
            x_ = next((x for x in m["items"] if x["id"] == iid), None)
            words = (x_ or {}).get("words", [])
            k = next((j for j, (l, t, r, b) in enumerate(words) if l - 1 <= px <= r + 1 and t - 1 <= py <= b + 1), None)
            if k is not None:
                if (x_ or {}).get("part") == "end":
                    k += max(0, len(DV.WORD.findall(sel[0].get("text", ""))) - len(words))
                txt = sel[0].get("text", "")
                ms = list(DV.WORD.finditer(txt))
                self._c_split_at = (0 if k <= 0 else len(txt) if k >= len(ms) else ms[k].start(), None)
                win.pv_note.configure(text=f"S splits {iid} before \"{ms[k].group(0) if 0 < k < len(ms) else ''}\".")
            return ("split_at", k)
        if win.cp_range:
            self.cp_set_range([])
        self._cp_select(iid)
        return ("item", iid)

    def _pv_menu(self, e):
        """Right-click a sentence on the page: the same marks as in the text (header, format, customer's...)."""
        win = self._cwin
        cv = win.pv_cv
        x, y = cv.canvasx(e.x), cv.canvasy(e.y)
        at = self._pv_at(x, y)
        if at is not None:
            h = LY.hit(self._pv_map(at[0]), at[1], at[2], False)
            if h and h[0] == "item" and h[1] not in (win.cp_range or []):
                if win.cp_range:
                    self.cp_set_range([])
                self._cp_select(h[1])
        m = tk.Menu(self, tearoff=0)
        sel = self._c_selected()
        if sel and sel[0].get("decision") in ("Context", "") and hasattr(self, "cp_support_picker"):
            m.add_command(label="Support for... (pick requirements or sections)", command=self.cp_support_picker)
        self.c_mark_entries(m, "")
        m.tk_popup(e.x_root, e.y_root)
        return "break"

    def pv_select_box(self, x0, y0, x1, y1):
        """Drag across sentences: every sentence with a box in the rectangle is selected together."""
        win = self._cwin
        pv = win.pv
        s = pv["scale"]
        ids = []
        for n, t in enumerate(pv["tops"], 1):
            if n not in pv["maps"]:
                continue
            for x in pv["maps"][n]["items"]:
                for l, tt, r, b in x["rects"]:
                    L, T, R, B = MARGIN + l * s, t + tt * s, MARGIN + r * s, t + b * s
                    if L < x1 and R > x0 and T < y1 and B > y0 and x["id"] not in ids:
                        ids.append(x["id"])
        order = {it["id"]: k for k, it in enumerate(self.matrix.items)}
        ids.sort(key=lambda i: order.get(i, 0))
        if not ids:
            return []
        sel = self._c_selected()
        if not sel or sel[0]["id"] not in ids:
            self._cp_select(ids[0])
        self.cp_set_range(ids if len(ids) > 1 else [])
        self._pv_soon()
        return ids

    def pv_follow(self, it):
        """The selected sentence changed: bring its box into view and redraw."""
        win = self._cwin
        if win is None or not hasattr(win, "pv") or not win.pv["on"] or it is None:
            return
        pv = win.pv
        n = pv["page_of"].get(it["id"])
        if n and pv["tops"]:
            m = self._pv_map(n)
            x = next((x for x in m["items"] if x["id"] == it["id"] and x["rects"]), None)
            y = pv["tops"][n - 1] + ((x["rects"][0][1] * pv["scale"]) if x else 0)
            cv = win.pv_cv
            top = cv.canvasy(0)
            if not (top + 40 <= y <= top + cv.winfo_height() - 80):
                total = float(cv.cget("scrollregion").split()[3]) if cv.cget("scrollregion") else 1.0
                cv.yview_moveto(max(0.0, (y - cv.winfo_height() * 0.3) / max(1.0, total)))
        self._pv_soon()


def _eng():
    import app_gui
    return app_gui
