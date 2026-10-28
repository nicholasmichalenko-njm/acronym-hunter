"""File > Send training data to the training team... (2.55.0): one .sktrain pack, replacing Send corrections.

The window lists each area with how much is waiting (new since the last send, or everything), a box for the sentence
text (off until ticked), the responsibility warning, and a box to acknowledge it: Save stays greyed until it is ticked.
"""
import datetime, getpass, json, os, re
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag
import trainpack as TP


def _eng():
    import app_gui
    return app_gui


class TrainPackMixin:
    # ------------------------------------------------------------ what is on this PC
    def tp_matrices(self):
        """Every effort's compliance matrix on this PC (the open one as it is now)."""
        import compliance as C, workspace as W
        out, seen = [], set()
        cur = getattr(self, "matrix", None)
        if cur is not None:
            out.append(cur); seen.add(os.path.abspath(cur.path).lower())
        reg = getattr(self, "efforts", None)
        for n in (reg.names() if reg is not None else []):
            inf = reg.get(n) or {}
            if not inf.get("path"):
                continue
            st = W.read_json(os.path.join(W.data_dir_for(inf["path"]), "settings.json"), None) or {}
            p = st.get("compliance_path") or ""
            if not p or not os.path.isfile(p) or os.path.abspath(p).lower() in seen:
                continue
            try:
                out.append(C.Matrix(p).load()); seen.add(os.path.abspath(p).lower())
            except Exception:
                diag.swallowed()
        return out

    def tp_words(self):
        eng = _eng()
        import cwords, keywords, workspace as W
        w = {"cwords_added": [], "cwords_removed": [], "choices": {}, "keywords": {}, "banned": []}
        try:
            cfg = cwords.load(eng.CONFIG_DIR)
            w["cwords_added"] = cwords.added(cfg)
            w["cwords_removed"] = [x for x in cwords.DEFAULT_WORDS if x not in cfg["words"]]
        except Exception:
            diag.swallowed()
        try:
            w["keywords"] = keywords.learning()
        except Exception:
            diag.swallowed()
        try:
            rows = eng.read_csv_rows(os.path.join(eng.CONFIG_DIR, "banned_words.csv"))
            w["banned"] = [next(iter(r.values()), "").strip() for r in rows if r and next(iter(r.values()), "").strip()]
        except Exception:
            diag.swallowed()
        files = [eng.CHOICES_FILE]
        reg = getattr(self, "efforts", None)
        for n in (reg.names() if reg is not None else []):
            inf = reg.get(n) or {}
            if inf.get("path"):
                files.append(os.path.join(W.data_dir_for(inf["path"]), "choices.json"))
        for f in files:
            d = W.read_json(f, None)
            if isinstance(d, dict):
                for t, c in d.items():
                    w["choices"].setdefault(t, c)
        return w

    def tp_args(self, areas=None, everything=False, text=False):
        eng = _eng()
        return dict(matrices=self.tp_matrices(), areas=areas, everything=everything, text=text,
                    ocr_fixes=eng.read_ocr_fix_rows(), ocr_ignore=eng.read_ocr_ignore_rows(), words=self.tp_words())

    def tp_waiting(self):
        """How many items are waiting to be sent (new since the last send), for the banner and the menu."""
        try:
            return sum(TP.gather(config_dir=_eng().CONFIG_DIR, **self.tp_args())["counts"].values())
        except Exception:
            diag.swallowed()
            return 0

    # ------------------------------------------------------------ the window
    def send_training_data(self, path=None):
        """The window. Returns it (tests drive win._api)."""
        eng = _eng()
        diag.activity("training_data_opened")
        win = ctk.CTkToplevel(self); win.title("Send training data to the training team")
        win.transient(self); win.after(150, win.lift)
        diag.register(win, "trainpack")
        ctk.CTkLabel(win, text="Send training data to the training team", font=("Segoe UI", 18, "bold"), anchor="w").pack(
            fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(win, text="What this PC taught, in one file for Stationkeeper Training. The next Knowledge Pack brings "
                               "it back to everyone.", anchor="w", justify="left", wraplength=620,
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16, pady=(0, 8))
        fr = ctk.CTkFrame(win, fg_color="transparent"); fr.pack(fill="x", padx=16)
        av = {a: tk.BooleanVar(value=True) for a, _ in TP.AREAS}
        labs = {}
        for a, title in TP.AREAS:
            row = ctk.CTkFrame(fr, fg_color="transparent"); row.pack(fill="x", pady=1)
            ctk.CTkCheckBox(row, text=title, variable=av[a], command=lambda: refresh()).pack(side="left")
            labs[a] = ctk.CTkLabel(row, text="", width=90, anchor="e", font=("Segoe UI", 12, "bold"))
            labs[a].pack(side="right")
        ev = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(win, text="Everything, not only what is new since the last send", variable=ev,
                        command=lambda: refresh()).pack(anchor="w", padx=16, pady=(8, 2))
        tv = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(win, text="Include the sentence text (RFP sentences and section titles)", variable=tv,
                        command=lambda: refresh()).pack(anchor="w", padx=16, pady=2)
        ctk.CTkLabel(win, text="Left out always: Customer information, team names, file paths, user and PC names.",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16, pady=(2, 8))
        warn = ctk.CTkFrame(win, fg_color=("#FEF3C7", "#422006"), corner_radius=6); warn.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(warn, text=TP.WARNING, wraplength=600, justify="left", anchor="w",
                     text_color=("#78350F", "#FDE68A")).pack(fill="x", padx=10, pady=8)
        ack = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(win, text="I have read this. I am responsible for what this pack holds.", variable=ack,
                        command=lambda: refresh()).pack(anchor="w", padx=16, pady=(6, 4))
        lbl = ctk.CTkLabel(win, text="", anchor="w"); lbl.pack(fill="x", padx=16)
        bar = ctk.CTkFrame(win, fg_color="transparent"); bar.pack(fill="x", padx=16, pady=(6, 14))
        btn = ctk.CTkButton(bar, text="Save the pack...", width=150, fg_color="#15803D", command=lambda: save())
        btn.pack(side="right")
        ctk.CTkButton(bar, text="Cancel", width=90, fg_color="#475569", command=win.destroy).pack(side="right", padx=8)
        state = {"counts": {}}

        def chosen():
            return [a for a, _ in TP.AREAS if av[a].get()]

        def refresh():
            try:
                g = TP.gather(config_dir=eng.CONFIG_DIR, **self.tp_args(chosen(), ev.get(), tv.get()))
                state["counts"] = g["counts"]
            except Exception:
                diag.swallowed()
                state["counts"] = {}
            for a, _t in TP.AREAS:
                n = state["counts"].get(a, 0)
                labs[a].configure(text=(f"{n} waiting" if av[a].get() else "left out"))
            total = sum(state["counts"].get(a, 0) for a in chosen())
            lbl.configure(text=("Nothing new to send." if not total else f"{total} item(s) to send.")
                          + ("" if ack.get() else "  Tick the box above to save."))
            btn.configure(state="normal" if ack.get() and total else "disabled")

        def save(out=None):
            if not ack.get():
                return None
            out = out or path
            if out is None:
                name = (f"Stationkeeper_Training_Data_{re.sub(r'[^A-Za-z0-9]+', '', getpass.getuser()) or 'user'}_"
                        f"{datetime.datetime.now():%Y.%m.%d-%H%M}{TP.EXT}")
                out = filedialog.asksaveasfilename(parent=win, title="Save to the APPROVED SHAREPOINT folder only",
                                                   initialfile=name, defaultextension=TP.EXT,
                                                   filetypes=[("Training data", "*" + TP.EXT)])
                if not out:
                    return None
            r = TP.build(out, eng.CONFIG_DIR, app_version=eng.APP_VERSION, acknowledged=True,
                         **self.tp_args(chosen(), ev.get(), tv.get()))
            c = r["counts"]
            diag.activity("training_data_sent", n=sum(c.values()), items=1 if tv.get() else 0)
            if not r["path"]:
                messagebox.showinfo("Send training data", "Nothing new to send.", parent=win)
                return r
            messagebox.showinfo("Send training data", f"Saved {os.path.basename(out)}: "
                                + ", ".join(f"{c.get(a, 0)} {a}" for a in chosen() if c.get(a)) + ".\n\n"
                                "The training team imports it in Stationkeeper Training (Gather > Import training "
                                "data); what it teaches comes back to you in a Knowledge Pack.", parent=win)
            try:
                self.update_banner()
            except Exception:
                diag.swallowed()
            win.destroy()
            return r

        win._api = {"areas": av, "everything": ev, "text": tv, "ack": ack, "save": save, "refresh": refresh,
                    "button": btn, "labels": labs, "state": state}
        refresh()
        return win
