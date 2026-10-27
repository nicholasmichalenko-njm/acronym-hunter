"""Install a Knowledge Pack (2.50.0): one card that says what the pack improves and what it adds, then Install or Not
now. Opens from File > Install Knowledge Pack..., or on double-click of a .skknow file. Installing backs up first and
can be undone (Advanced > Knowledge Packs)."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag
import studio as ST


class KnowledgeCardMixin:
    def knowledge_card(self, path=None, answer=None):
        """The install card. answer (tests): "install" or "later" at once. Returns the window, or the result."""
        import app_gui as A
        if path is None:
            path = filedialog.askopenfilename(parent=self, title="Install Knowledge Pack (from the approved SharePoint folder)",
                                              filetypes=[("Knowledge Pack", "*" + ST.EXT + " *.zip")])
            if not path:
                return None
        try:
            info, _data = A.read_knowledge_pack(path)
        except Exception as e:
            diag.swallowed()
            messagebox.showerror("Not a Knowledge Pack", f"{e}\n\nNothing was changed.", parent=self)
            return None
        counts = info.get("counts") or {}
        words = {"database_rows": "acronym database rows (added only when new)", "ocr_fixes": "OCR fixes",
                 "ignored_readings": "ignored readings"}
        adds = [f"{v} {words.get(k, k.replace('_', ' '))}" for k, v in counts.items() if isinstance(v, int) and v]
        tested = ST.card_lines(info)

        def install():
            try:
                rep = A.install_knowledge_pack(path)
            except PermissionError:
                messagebox.showerror("File in use", A.DB_LOCKED_MSG, parent=self)
                return None
            except Exception as e:
                A.log_error("Knowledge Pack install failed")
                messagebox.showerror("Not installed", f"{e}\n\nNothing was changed.", parent=self)
                return None
            diag.activity("knowledge_installed_card")
            return rep
        if answer is not None:
            return install() if answer == "install" else None
        w = ctk.CTkToplevel(self); w.title("Install Knowledge Pack"); w.transient(self); w.geometry("640x520")
        ver = info.get("created", info.get("version", ""))[:10]
        ctk.CTkLabel(w, text=f"Install Knowledge Pack {ver}?", font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=18, pady=(16, 2))
        ctk.CTkLabel(w, text=f"From the training team ({info.get('created_by', '?')}), made {info.get('created', '?')}"
                             + (f" with Stationkeeper {info['app_version']}" if info.get("app_version") else "") + ".",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=18)
        box = ctk.CTkScrollableFrame(w); box.pack(fill="both", expand=True, padx=18, pady=10)
        if tested:
            ctk.CTkLabel(box, text="Tested before release", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", pady=(4, 2))
            for t in tested:
                ctk.CTkLabel(box, text="✓  " + t, anchor="w", justify="left", wraplength=560).pack(fill="x", padx=6)
        left = [r["title"] for r in info.get("scorecard") or [] if not r.get("include") and r.get("files")]
        if left:
            ctk.CTkLabel(box, text="Left out by the training team: " + ", ".join(dict.fromkeys(left)), anchor="w", justify="left",
                         wraplength=560, text_color=("#475569", "#94A3B8")).pack(fill="x", pady=(6, 0))
        if adds:
            ctk.CTkLabel(box, text="Adds", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", pady=(10, 2))
            ctk.CTkLabel(box, text=", ".join(adds), anchor="w", justify="left", wraplength=560).pack(fill="x", padx=6)
        if info.get("notes"):
            ctk.CTkLabel(box, text="Notes: " + info["notes"], anchor="w", justify="left", wraplength=560).pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(w, text="Your own corrections, decisions and database rows stay. A backup is taken first; Advanced > "
                             "Knowledge Packs > Undo puts everything back.", anchor="w", justify="left", wraplength=600,
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=18)
        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", padx=18, pady=12)

        def ok():
            rep = install()
            if rep is not None:
                w.destroy()
                messagebox.showinfo("Knowledge Pack installed", rep, parent=self)
        ctk.CTkButton(bar, text="Install", fg_color="#0F766E", command=ok).pack(side="right")
        ctk.CTkButton(bar, text="Not now", fg_color="#64748B", command=w.destroy).pack(side="right", padx=8)
        w._api = {"tested": tested, "adds": adds, "install": ok, "info": info}
        w.after(100, w.lift)
        return w
