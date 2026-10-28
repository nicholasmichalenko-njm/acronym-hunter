"""What runs each part (2.12.0; 2.55.0 no switch, no generative AI).

- Every sidebar section header shows what runs it: No AI or ML, with a ? that lists the parts and their jobs.
- 2.55.0: the AI and ML switch is gone. Picture reading and the learned suggestions (ML, on this PC) always run; there
  is no generative AI anywhere in the app. The top bar keeps a ? that explains rules and ML.
- A line at the bottom of the window always shows: offline, the effort, no generative AI.
- Help > What runs where lists every part and saves a one-page summary for the security team.
"""
import hashlib, os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import ai_stack as S
import diag

BADGE = {"none": (("#E2E8F0", "#334155"), ("#334155", "#E2E8F0")),
         "ml": (("#DBEAFE", "#1E3A5F"), ("#1D4ED8", "#BFDBFE")),
}


def _eng():
    import app_gui
    return app_gui


def effort_code(name):
    """A number standing for the effort in the usage log, so the log never holds a program name."""
    return int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:6], 16) if name else 0


class AIMixin:
    # ------------------------------------------------------------ building
    def ai_section_header(self, parent, title, show_title=True):
        """Section title with its labels and a ? (the step strip shows the labels without the title, 2.32.0)."""
        row = ctk.CTkFrame(parent, fg_color="transparent", height=24)
        row.pack(fill="x", padx=8, pady=(12, 2) if show_title else 0)
        if show_title:
            ctk.CTkLabel(row, text=title, font=("Segoe UI", 11, "bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(side="left")
        key = S.SIDEBAR_SECTIONS.get(title)
        if not key:
            return row
        if not hasattr(self, "_ai_badges"):
            self._ai_badges = []
        ctk.CTkButton(row, text="?", width=20, height=18, corner_radius=9, font=("Segoe UI", 10, "bold"),
                      fg_color=("#E2E8F0", "#334155"), hover_color=("#CBD5E1", "#475569"), text_color=("#334155", "#E2E8F0"),
                      command=lambda k=key: self.show_stack(k)).pack(side="right", padx=(4, 0))
        for cls in reversed(S.classes_of(key)):
            b = ctk.CTkLabel(row, text=S.LABELS[cls], font=("Segoe UI", 9, "bold"), corner_radius=4, height=16, width=10,
                             fg_color=BADGE[cls][0], text_color=BADGE[cls][1])
            b.pack(side="right", padx=(3, 0))
            self._ai_badges.append((b, cls))
        return row

    def ai_init(self):
        """The ? in the top bar and the always-visible state line at the bottom of the window."""
        bar = self.topbar_right
        ctk.CTkButton(bar, text="?", width=24, height=24, corner_radius=12, font=("Segoe UI", 11, "bold"),
                      fg_color=("#CBD5E1", "#334155"), hover_color=("#94A3B8", "#475569"), text_color=("#0F172A", "#F1F5F9"),
                      command=self.show_ai_difference).pack(side="right", padx=(6, 0), pady=5)
        sb = getattr(self, "statusbar", None)          # one status line (2.32.0): the state sits at its right end
        self.lbl_aistate = ctk.CTkLabel(sb or self.main, text="", font=("Segoe UI", 11), anchor="e", text_color=("#475569", "#94A3B8"))
        if sb is not None:
            self.lbl_aistate.pack(side="right", padx=12, pady=2)
        else:
            self.lbl_aistate.pack(side="bottom", fill="x", padx=10, pady=(0, 3))

    # ------------------------------------------------------------ state
    def ai_load_for_workspace(self):
        """Nothing to switch since 2.55.0; refresh the state line for the open effort."""
        self.ai_state_line()

    def ai_state_line(self):
        who = self.effort.name if getattr(self, "effort", None) is not None else "no effort"
        self.lbl_aistate.configure(text=f"Offline: nothing leaves this PC   |   Effort: {who}   |   No generative AI"
                                        + self._master_bit())

    def _master_bit(self):
        try:
            import master_db
            i = master_db.master_info()
            return (f"   |   Acronyms Master Database v{i['version']}" if i
                    else "   |   No Acronyms, Abbreviations, Units and Symbols Master Database loaded")
        except Exception:
            diag.swallowed()
            return ""

    # ------------------------------------------------------------ panels
    def _panel(self, title, rows, foot=""):
        win = ctk.CTkToplevel(self); win.title(title)
        win.transient(self); win.after(150, win.lift)
        diag.register(win, "ai_panel")
        size = max(11, getattr(self, "font_size", 13) - 1)
        f = ctk.CTkScrollableFrame(win, fg_color="transparent", width=640, height=min(520, 70 + 46 * len(rows)))
        f.pack(fill="both", expand=True, padx=12, pady=(12, 4))
        f.grid_columnconfigure(1, weight=1)
        for i, (a, b, cls) in enumerate(rows):
            ctk.CTkLabel(f, text=a, font=("Segoe UI", size, "bold"), anchor="nw", justify="left", wraplength=230).grid(
                row=i, column=0, sticky="nw", padx=(0, 10), pady=4)
            ctk.CTkLabel(f, text=b, font=("Segoe UI", size), anchor="nw", justify="left", wraplength=330).grid(
                row=i, column=1, sticky="nw", pady=4)
            if cls:
                ctk.CTkLabel(f, text=S.LABELS[cls], font=("Segoe UI", 9, "bold"), corner_radius=4, height=16, width=10,
                             fg_color=BADGE[cls][0], text_color=BADGE[cls][1]).grid(row=i, column=2, sticky="ne", padx=(8, 0), pady=6)
        if foot:
            ctk.CTkLabel(win, text=foot, font=("Segoe UI", size, "bold"), text_color=("#0F766E", "#5EEAD4"), anchor="w").pack(
                fill="x", padx=14, pady=(2, 4))
        ctk.CTkButton(win, text="Close", width=90, command=win.destroy).pack(anchor="e", padx=14, pady=(0, 12))
        return win

    def show_stack(self, key):
        diag.activity("ai_stack_opened")
        eng = _eng()
        title, classes, parts = S.FEATURES[key]
        rows = [(p, j, c) for p, j, c in parts if eng.DOCTR_DIR or "docTR via" not in p]
        foot = "Runs on this PC. No network."
        return self._panel(f"What runs {title}", rows, foot)

    def show_ai_difference(self):
        diag.activity("ai_difference_opened")
        return self._panel("Rules and ML: the difference", [(a, b, "") for a, b in S.DIFFERENCE], "Everything runs only on this PC. No network.")

    COMPONENTS = (("Python", None, "The language the program is written in; its runtime ships inside the program."),
                  ("customtkinter", "customtkinter", "The windows, buttons and lists (on Tcl/Tk, which ships with Python)."),
                  ("openpyxl", "openpyxl", "Reads and writes the Excel files: effort lists, matrices, exports."),
                  ("Pillow", "pillow", "Pictures: page images, screenshots in the Guide."),
                  ("pypdfium2", "pypdfium2", "Reads PDF text and draws PDF pages (PDFium, the engine in Chrome)."),
                  ("Tesseract OCR", None, "Reads text in pictures and scanned pages (ML, an LSTM model, on this PC)."),
                  ("ONNX Runtime", "onnxruntime", "Runs the optional docTR second reader's models (ML, on this PC)."),
                  ("NumPy", "numpy", "Number arrays for the picture readers."),
                  ("darkdetect", "darkdetect", "Follows the Windows light or dark setting."))

    def show_components(self):
        """Help > What it is built on: the main parts, their versions here, and what each does."""
        diag.activity("components_opened")
        import importlib.metadata as md, platform
        rows = []
        for name, dist, what in self.COMPONENTS:
            ver = platform.python_version() if name == "Python" else ""
            if dist:
                try:
                    ver = md.version(dist)
                except Exception:
                    ver = ""
                    if dist == "onnxruntime":
                        continue                     # only with the docTR add-on
            rows.append((f"{name} {ver}".strip(), what, ""))
        rows.append(("Our own code", "Everything else: the rules for acronyms, compliance, submission requirements, the effort "
                                     "record. Written for this program; no AI writes anything, and there is no generative AI.", ""))
        return self._panel("What Stationkeeper is built on", rows,
                           "Every part with its license and fingerprint: the SBOM file published with each release.")

    def show_what_runs(self):
        """Help > What runs where: every part of the app, and a summary to save for the security team."""
        diag.activity("ai_what_runs_opened")
        eng = _eng()
        rows = []
        for key, (title, classes, parts) in S.FEATURES.items():
            for p, j, c in parts:
                if "docTR via" in p and not eng.DOCTR_DIR:
                    continue
                rows.append((f"{title}: {p}", j, c))
        win = self._panel("What runs where", rows, "Everything runs on this PC. The program makes no network connections.")

        def save():
            p = filedialog.asksaveasfilename(parent=win, title="Save the summary for your security team", defaultextension=".txt",
                                             initialfile=f"Acronym_Hunter_{eng.APP_VERSION}_what_runs_where.txt",
                                             filetypes=[("Text", "*.txt")])
            if not p:
                return
            with open(p, "w", encoding="utf-8") as f:
                f.write(S.summary_text(eng.APP_VERSION, eng.EDITION_NAME, bool(eng.DOCTR_DIR)))
            diag.activity("ai_summary_saved")
            messagebox.showinfo("What runs where", f"Saved:\n{p}", parent=win)
        ctk.CTkButton(win, text="Save summary for security...", command=save).pack(anchor="w", padx=14, pady=(0, 12))
        win._save = save
        return win
