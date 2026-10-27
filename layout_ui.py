"""Compliance > Original layout (2.45.0): a PDF customer document page as it looks, every review sentence boxed in its
decision's color; click one to work on it in Assign. Text not in the review is boxed in red; click it to add it to the
review. Show page opens this view on the selected sentence's page. Rules only (No AI); nothing leaves the PC."""
import uiquiet as UQ  # 2.47.0: smooth resizing
import os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import diag
import layout as LY


class LayoutMixin:
    def _lay_files(self):
        """{file name: path} of the matrix's PDF files that are still on disk."""
        M = getattr(self, "matrix", None)
        out = {}
        for it in (M.items if M is not None else []):
            f = it.get("file", "")
            if f.lower().endswith(".pdf") and f not in out:
                p = self._c_source_path(it) if hasattr(self, "_c_source_path") else ""
                if p and os.path.isfile(p):
                    out[f] = p
        return out

    def compliance_layout(self, it=None):
        """Open (or raise) the Original layout window, on the given sentence's page when it is in a PDF."""
        files = self._lay_files()
        if not files:
            messagebox.showinfo("Original layout", "The original layout is shown for PDF customer documents. This matrix has no PDF "
                                                   "file on this PC; for Word, Excel and PowerPoint the passage is in the panel and "
                                                   "Open file opens the document.", parent=getattr(self, "_cwin", None))
            return None
        w = getattr(self, "_lay", None)
        if w is None or not w.winfo_exists():
            w = self._lay_build()
        f = it["file"] if it is not None and it.get("file") in files else (w._file if w._file in files else next(iter(files)))
        pg = LY._page_of(it) if it is not None and it.get("file") == f else None
        self.layout_show(f, pg or (w._page if f == w._file else 1), it["id"] if it is not None else w._sel)
        w.after(150, w.lift)
        diag.activity("compliance_layout")
        return w

    def _lay_build(self):
        w = ctk.CTkToplevel(self); w.title("Original layout"); w.geometry("980x900")
        diag.register(w, "original_layout")
        self._lay = w
        w._file, w._page, w._sel, w._map, w._base, w._scale, w._pages = "", 1, "", None, None, 1.0, 1
        top = ctk.CTkFrame(w, fg_color="transparent"); top.pack(fill="x", padx=10, pady=(10, 4))
        w._om = ctk.CTkOptionMenu(top, values=[""], width=300, command=lambda f: self.layout_show(f, 1))
        w._om.pack(side="left")
        ctk.CTkButton(top, text="<", width=34, command=lambda: self.layout_step(-1)).pack(side="left", padx=(12, 2))
        w._pl = ctk.CTkLabel(top, text="", width=110)
        w._pl.pack(side="left")
        ctk.CTkButton(top, text=">", width=34, command=lambda: self.layout_step(1)).pack(side="left", padx=2)
        w._miss = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(top, text="Show text not in the review", variable=w._miss, command=self.layout_redraw).pack(side="right")
        leg = ctk.CTkFrame(w, fg_color="transparent"); leg.pack(fill="x", padx=10, pady=(0, 4))
        for rgb, lab in list(LY.COLORS.values()) + [LY.MISSING]:
            sw = "#%02X%02X%02X" % rgb
            ctk.CTkLabel(leg, text="  ", width=16, fg_color=sw, corner_radius=3).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(leg, text=lab).pack(side="left", padx=(0, 14))
        w._info = ctk.CTkLabel(w, text="", anchor="w", justify="left", wraplength=940, text_color=("#475569", "#94A3B8"))
        w._info.pack(fill="x", padx=12)
        body = tk.Frame(w); body.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        cv = tk.Canvas(body, highlightthickness=0, bg="#E2E8F0", cursor="hand2")
        sb = tk.Scrollbar(body, orient="vertical", command=cv.yview); cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)
        cv.bind("<Button-1>", self._lay_click)
        cv.bind("<Configure>", UQ.debounced(cv, lambda _e: self._lay_fit(), 200))
        cv.bind("<MouseWheel>", lambda e: cv.yview_scroll(int(-e.delta / 120), "units"))
        w.bind("<Prior>", lambda _e: self.layout_step(-1)); w.bind("<Next>", lambda _e: self.layout_step(1))
        w._cv = cv
        w.protocol("WM_DELETE_WINDOW", lambda: (w.destroy(), setattr(self, "_lay", None)))
        return w

    def _lay_items(self, f):
        M = self.matrix
        return [it for it in M.items if it.get("file") == f]

    def layout_show(self, f, page=1, sel=None):
        """Show one page of one PDF file (and mark the selected sentence)."""
        w = getattr(self, "_lay", None)
        files = self._lay_files()
        if w is None or f not in files:
            return None
        path = files[f]
        try:
            n = LY.page_count(path)
        except Exception:
            diag.swallowed()
            messagebox.showerror("Original layout", "The file could not be read.", parent=w)
            return None
        page = max(1, min(int(page or 1), n))
        if (f, page) != (w._file, w._page) or w._map is None:
            M = self.matrix
            try:
                w._map = LY.page_map(path, page, self._lay_items(f), M.headings)
                w._base = None
            except Exception:
                diag.swallowed()
                messagebox.showerror("Original layout", "The page could not be read.", parent=w)
                return None
        w._file, w._page, w._pages = f, page, n
        if sel is not None:
            w._sel = sel
        w._om.configure(values=list(files)); w._om.set(f)
        w._pl.configure(text=f"Page {page} of {n}")
        m = w._map
        nmiss = len(m["missing"])
        w._info.configure(text=f"{len(m['items'])} sentence(s) of the review on this page" +
                          (f"; {nmiss} line(s) of text not in the review (red): click one to add it." if nmiss else
                           "; all its text is in the review.") + " Click a sentence to work on it in Assign.")
        self._lay_fit()
        return m

    def layout_step(self, d):
        w = getattr(self, "_lay", None)
        if w is not None and w._file:
            self.layout_show(w._file, w._page + d)

    def _lay_fit(self):
        """Render the page to the canvas width, then draw the boxes."""
        w = getattr(self, "_lay", None)
        if w is None or not w._file or w._map is None:
            return
        cw = max(400, w._cv.winfo_width() - 4)
        pw = w._map["size"][0]
        scale = round(cw / pw, 3)
        if w._base is None or abs(scale - w._scale) > 0.01:
            try:
                w._base = LY.render(self._lay_files()[w._file], w._page, scale)
            except Exception:
                diag.swallowed()
                return
            w._scale = scale
        self.layout_redraw()

    def layout_redraw(self):
        w = getattr(self, "_lay", None)
        if w is None or w._base is None:
            return
        from PIL import ImageTk
        dec = {it["id"]: it.get("decision", "") for it in self.matrix.items}
        img = LY.overlay(w._base, w._map, dec, w._scale, w._sel, w._miss.get())
        w._photo = ImageTk.PhotoImage(img)
        cv = w._cv
        cv.delete("all")
        cv.create_image(0, 0, image=w._photo, anchor="nw")
        cv.configure(scrollregion=(0, 0, img.width, img.height))
        w._img = img

    def _lay_click(self, e):
        w = self._lay
        cv = w._cv
        x, y = cv.canvasx(e.x) / w._scale, cv.canvasy(e.y) / w._scale
        return self.layout_pick(x, y)

    def layout_pick(self, x, y):
        """A click at a point on the page (PDF points): a sentence opens in Assign; red text is offered for the review."""
        w = self._lay
        h = LY.hit(w._map, x, y, w._miss.get())
        if h is None:
            return None
        if h[0] == "item":
            w._sel = h[1]
            self.layout_redraw()
            if hasattr(self, "shell_go"):
                self.shell_go("compliance", "decide")
            if hasattr(self, "_cp_select"):
                self._cp_select(h[1])
            w.after(100, w.lift)
            diag.activity("layout_pick")
            return h
        m = w._map["missing"][h[1]]
        if messagebox.askyesno("Text not in the review", f"Add this line to the review, to assign it?\n\n\"{m['text'][:300]}\"", parent=w):
            self.layout_add_missing(h[1])
        return h

    def layout_add_missing(self, k):
        """Add one red line to the review (as the text check does), then show it selected."""
        w = self._lay
        m = w._map["missing"][k]
        f, page = w._file, w._page                     # the refresh after adding may move the view: come back here
        added = self.compliance_add_missing([{"file": f, "lines": [(f"p.{page}", m["text"], "missing")]}]) \
            if hasattr(self, "compliance_add_missing") else []
        w._map = None
        w._file = ""
        if added:
            w._sel = added[0]["id"]
            if hasattr(self, "_cp_select"):
                self._cp_select(added[0]["id"])     # Assign shows the new sentence, ready to assign
        self.layout_show(f, page, added[0]["id"] if added else None)
        return added

    def layout_follow(self, it):
        """Assign moved to a sentence: follow it when the window is open (its page, its box)."""
        w = getattr(self, "_lay", None)
        if w is None or not w.winfo_exists() or it is None:
            return
        if it.get("id") == w._sel and it.get("file") == w._file and (LY._page_of(it) or w._page) == w._page:
            return
        if it.get("file") in self._lay_files():
            self.layout_show(it["file"], LY._page_of(it) or w._page, it["id"])
