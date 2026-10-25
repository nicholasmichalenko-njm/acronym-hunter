"""AI and ML labels and switch (2.12.0).

- Every sidebar section header shows what runs it: No AI, ML or Gen AI, with a ? that lists the parts and their jobs.
- The top bar holds the AI and ML switch for the open effort (on by default, no restriction). Off turns off every ML and
  Gen AI part: text in pictures (Tesseract, docTR), learned compliance suggestions, Improve Reading, the math reader.
  The model code refuses to run while it is off; buttons are greyed so the state is visible.
- Each change is recorded in the effort list's History sheet and in the usage log (by a number, never the effort name).
- A line at the bottom of the window always shows: offline, the effort, AI and ML on or off.
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
         "gen": (("#EDE9FE", "#3B2A5C"), ("#6D28D9", "#DDD6FE")),
         "off": (("#F1F5F9", "#1E293B"), ("#94A3B8", "#64748B"))}


def _eng():
    import app_gui
    return app_gui


def effort_code(name):
    """A number standing for the effort in the usage log, so the log never holds a program name."""
    return int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:6], 16) if name else 0


class AIMixin:
    # ------------------------------------------------------------ building
    def ai_section_header(self, parent, title):
        """Sidebar section title with its labels and a ? (used by the sidebar's section())."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=(12, 2))
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
        """The switch in the top bar, its ?, and the always-visible state line at the bottom of the window."""
        bar = self.topbar_right
        self.ai_var = tk.BooleanVar(value=True)
        ctk.CTkButton(bar, text="?", width=24, height=24, corner_radius=12, font=("Segoe UI", 11, "bold"),
                      fg_color=("#CBD5E1", "#334155"), hover_color=("#94A3B8", "#475569"), text_color=("#0F172A", "#F1F5F9"),
                      command=self.show_ai_difference).pack(side="right", padx=(6, 0), pady=5)
        self.sw_ai = ctk.CTkSwitch(bar, text="AI and ML on", variable=self.ai_var, command=self.toggle_ai_ml,
                                   onvalue=True, offvalue=False, progress_color="#0F766E")
        self.sw_ai.pack(side="right", pady=5)
        self.lbl_aistate = ctk.CTkLabel(self.main, text="", font=("Segoe UI", 11), anchor="w", text_color=("#475569", "#94A3B8"))
        self.lbl_aistate.pack(side="bottom", fill="x", padx=10, pady=(0, 3))

    # ------------------------------------------------------------ state
    def ai_load_for_workspace(self):
        """Read the open effort's setting (default on) and apply it."""
        on = True
        try:
            on = bool(self.ws.get("ai_ml", True))
        except Exception:
            diag.swallowed()
        self.ai_var.set(on)
        self.ai_apply()

    def toggle_ai_ml(self):
        on = bool(self.ai_var.get())
        try:
            self.ws.set("ai_ml", on)
        except Exception:
            diag.swallowed()
        name = self.effort.name if self.effort is not None else ""
        if on:
            diag.activity("ai_ml_turned_on", effort_code=effort_code(name))
        else:
            diag.activity("ai_ml_turned_off", effort_code=effort_code(name))
        if self.effort is not None:            # the effort list's History sheet: date, Windows user, setting
            self.effort._hist("(setting)", "AI and ML turned " + ("on" if on else "off"))
            self._save_effort_list()
        self.ai_apply()
        self.status.configure(text=("AI and ML are on" if on else "AI and ML are off") +
                              (f" for {name}." if name else " for scans with no effort.") +
                              ("" if on else " Typed text is still read; text inside pictures and scans is not."))

    def ai_apply(self):
        eng = _eng()
        on = bool(self.ai_var.get())
        eng.set_ai_ml(on)
        self.sw_ai.configure(text="AI and ML on" if on else "AI and ML off")
        for b, cls in getattr(self, "_ai_badges", []):
            if cls == "none":
                continue
            look = BADGE["off"] if not on else BADGE[cls]
            b.configure(text=S.LABELS[cls] + ("" if on else " off"), fg_color=look[0], text_color=look[1])
        st = "normal" if on else "disabled"
        for w in (getattr(self, "btn_improve_top", None), getattr(self, "btn_improve", None)):
            if w is not None:
                try:
                    w.configure(state=st)
                except Exception:
                    diag.swallowed()
        cw = getattr(self, "_cwin", None)
        if cw is not None and cw.winfo_exists():
            self._c_ai_state()
            self._c_refresh()
        if getattr(self, "preview", None) is not None and hasattr(self.preview, "ai_state"):
            self.preview.ai_state(on)
        self.ai_state_line()

    def ai_state_line(self):
        eng = _eng()
        on = eng.ai_ml_on()
        who = self.effort.name if getattr(self, "effort", None) is not None else "no effort"
        gen = "math reader add-on installed (runs only when you click it)" if eng.MATH_DIR else "no generative AI installed"
        self.lbl_aistate.configure(text=f"Offline: nothing leaves this PC   |   Effort: {who}   |   AI and ML: "
                                        + ("on" if on else "off (rules only; text in pictures not read)")
                                        + f"   |   {gen}" + self._master_bit())

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
        if not eng.ai_ml_on() and any(c != "none" for c in classes):
            foot += "  AI and ML are off for this effort: the ML and Gen AI parts are not running."
        return self._panel(f"What runs {title}", rows, foot)

    def show_ai_difference(self):
        diag.activity("ai_difference_opened")
        return self._panel("AI and ML: the difference", [(a, b, "") for a, b in S.DIFFERENCE], "Both run only on this PC. No network.")

    def show_what_runs(self):
        """Help > What runs where: every part of the app, and a summary to save for the security team."""
        diag.activity("ai_what_runs_opened")
        eng = _eng()
        rows = []
        for key, (title, classes, parts) in S.FEATURES.items():
            if key == "math" and not eng.MATH_DIR:
                rows.append((title, "Not installed.", "gen"))
                continue
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
                f.write(S.summary_text(eng.APP_VERSION, eng.EDITION_NAME, bool(eng.MATH_DIR), bool(eng.DOCTR_DIR)))
            diag.activity("ai_summary_saved")
            messagebox.showinfo("What runs where", f"Saved:\n{p}", parent=win)
        ctk.CTkButton(win, text="Save summary for security...", command=save).pack(anchor="w", padx=14, pady=(0, 12))
        win._save = save
        return win
