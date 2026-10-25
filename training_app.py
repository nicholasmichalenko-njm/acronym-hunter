"""Acronym Hunter Training (2.15.0): corrections in, a better reader out. Its own program, built from the same code.

Acronym Hunter (the scanner people use every day) only saves corrections: Report misreading and Not text in the
picture preview. People send them as corrections packs to the approved SharePoint folder. This program, run by the
training team:
- Corrections: imports the packs (each file checked against the pack's SHA-256 list first), shows every corrected
  line with its picture, and accepts, rejects or fixes each one. Rejected lines are never taught.
- Teach the reader: the Trainer (box text in pictures, read a region, save lines), Improve Reading (fine-tunes the
  Tesseract reader on this PC's processor, tests it on held-out lines, keeps it only if it reads better), and the
  package for the offline docTR Training Kit.
- Knowledge Pack: exports the better reader, with the database, OCR fixes and ignore list, as a numbered Knowledge
  Pack for the approved SharePoint folder; Acronym Hunter installs it (and can undo it). Loads trained models from
  the Training Kit.

Same engine, sandbox and network guard as Acronym Hunter. Nothing leaves this PC.
"""
import app_gui as eng          # engine first: sandbox, temp redirect, network guard, OCR, config
eng.TRAINING_APP = True
import os, sys, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import customtkinter as ctk
from PIL import Image, ImageTk
import diag
import corrections as C

FILTERS = ["All lines", "Taught (not rejected)", "Rejected", "From packs", "Saved on this PC"]


class TrainingApp(ctk.CTk):
    # the same windows Acronym Hunter used to open, now only here
    open_improve = eng.AcronymAppGUI.open_improve
    open_knowledge = eng.AcronymAppGUI.open_knowledge
    _undo_reader = eng.AcronymAppGUI._undo_reader
    training_state = eng.AcronymAppGUI.training_state
    open_trainer = eng.AcronymAppGUI.open_trainer

    def __init__(self):
        super().__init__()
        eng.ACTIVE_ICON = "trainer.ico"
        eng.apply_window_icon(self)
        self.title(f"Acronym Hunter Training {eng.APP_VERSION}: corrections in, a better reader out (100% local)")
        self.geometry("1180x760")
        self.report_callback_exception = lambda et, e, tb: (eng._excepthook(et, e, tb), messagebox.showerror(
            "Error", f"{et.__name__}: {e}\n\nDetails were saved to the logs folder (no file names or document content)."))
        self.project, self.queued_files, self._training, self.trainer_win = None, [], False, None
        self._thumb = None
        diag.activity("training_app_started")
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(top, text="Acronym Hunter Training", font=("Segoe UI", 18, "bold")).pack(side="left")
        self.lbl_state = ctk.CTkLabel(top, text="", anchor="e", justify="right"); self.lbl_state.pack(side="right")
        self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=12, pady=8)
        self._corrections_tab(self.tabs.add("Corrections"))
        self._teach_tab(self.tabs.add("Teach the reader"))
        self._knowledge_tab(self.tabs.add("Knowledge Pack"))
        ctk.CTkLabel(self, text="Offline: nothing leaves this PC. Corrections and Knowledge Packs hold what was learned from "
                                "internal documents: approved SharePoint folder only.", text_color=("#475569", "#94A3B8")).pack(pady=(0, 8))
        self.refresh()

    # ------------------------------------------------------------ corrections
    def _corrections_tab(self, T):
        bar = ctk.CTkFrame(T, fg_color="transparent"); bar.pack(fill="x")
        ctk.CTkButton(bar, text="Import corrections packs...", width=200, fg_color="#0F766E", command=self.import_packs).pack(side="left")
        ctk.CTkLabel(bar, text="Show").pack(side="left", padx=(16, 4))
        self.filter = tk.StringVar(value=FILTERS[0])
        ctk.CTkOptionMenu(bar, variable=self.filter, values=FILTERS, width=190, command=lambda _v: self.fill()).pack(side="left")
        self.search = tk.StringVar(value="")
        e = ctk.CTkEntry(bar, textvariable=self.search, width=200, placeholder_text="Search the text"); e.pack(side="left", padx=8)
        self.search.trace_add("write", lambda *_: self.fill())
        self.lbl_packs = ctk.CTkLabel(bar, text="", anchor="e"); self.lbl_packs.pack(side="right")
        body = ctk.CTkFrame(T, fg_color="transparent"); body.pack(fill="both", expand=True, pady=6)
        tf = tk.Frame(body); tf.pack(side="left", fill="both", expand=True)
        tf.grid_rowconfigure(0, weight=1); tf.grid_columnconfigure(0, weight=1)
        cols = (("text", "Correct text", 230), ("read", "Read as", 200), ("conf", "Conf.", 60), ("source", "From", 340),
                ("date", "Saved", 120), ("state", "State", 90))
        self.tv = ttk.Treeview(tf, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for cid, head, w in cols:
            self.tv.heading(cid, text=head); self.tv.column(cid, width=w, stretch=cid in ("text", "source"))
        self.tv.tag_configure("rejected", foreground="#9CA3AF")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tv.yview); self.tv.configure(yscrollcommand=vsb.set)
        self.tv.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")
        self.tv.bind("<<TreeviewSelect>>", lambda _e: self.show_picture())
        self.tv.bind("<Double-1>", lambda _e: self.fix_text())
        side = ctk.CTkFrame(body, width=330); side.pack(side="left", fill="y", padx=(8, 0)); side.pack_propagate(False)
        ctk.CTkLabel(side, text="Picture", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.pic = tk.Label(side, bg="#F8FAFC", width=300, height=120); self.pic.pack(padx=10, pady=4, fill="x")
        self.lbl_pic = ctk.CTkLabel(side, text="Select a line.", wraplength=300, justify="left", anchor="w")
        self.lbl_pic.pack(fill="x", padx=10, pady=4)
        for txt, color, fn in (("Accept (teach it)", "#15803D", lambda: self.set_rejected(False)),
                               ("Reject (never teach it)", "#B91C1C", lambda: self.set_rejected(True)),
                               ("Fix the text...", "#1E3A8A", self.fix_text)):
            ctk.CTkButton(side, text=txt, fg_color=color, command=fn).pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(side, text="Every line is taught unless you reject it. Fix the text when the person who sent it spelled it "
                                "wrong. Double-click a row to fix it.", wraplength=300, justify="left",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=10, pady=8)

    def _rows(self):
        f, q = self.filter.get(), self.search.get().strip().casefold()
        out = []
        for s in C.samples():
            if q and q not in s["text"].casefold() and q not in s["read"].casefold():
                continue
            if f == "Taught (not rejected)" and s["rejected"]:
                continue
            if f == "Rejected" and not s["rejected"]:
                continue
            if f == "From packs" and not s["source"].startswith("Pack from"):
                continue
            if f == "Saved on this PC" and s["source"].startswith("Pack from"):
                continue
            out.append(s)
        return out

    def fill(self):
        keep = set(self.tv.selection())
        self.tv.delete(*self.tv.get_children())
        for s in self._rows():
            self.tv.insert("", "end", iid=s["rel"], tags=("rejected",) if s["rejected"] else (),
                           values=(s["text"], s["read"], s["conf"], s["source"], s["date"], "Rejected" if s["rejected"] else "Taught"))
        sel = [k for k in keep if self.tv.exists(k)]
        if sel:
            self.tv.selection_set(sel)

    def refresh(self):
        all_ = C.samples()
        rej = sum(s["rejected"] for s in all_)
        _n, regions, junk, size = C.training_stats()
        ps = C.packs()
        self.lbl_state.configure(text=f"Training set: {len(all_) - rej} lines taught, {rej} rejected, {regions} regions  |  "
                                      f"{size / 1024 / 1024:.1f} MB\n{eng.knowledge_status().splitlines()[0] if eng.knowledge_status() else ''}")
        self.lbl_packs.configure(text=f"Packs imported: {len(ps)}" + (f" (last from {ps[-1]['from']})" if ps else ""))
        self.fill()
        if hasattr(self, "lbl_teach"):
            n, new = self.training_state()
            self.lbl_teach.configure(text=f"{n} lines to teach ({new} new since the reader was last improved).")

    def update_banner(self):          # Improve Reading calls this when it starts and ends
        self.refresh()

    def rescan_project(self):         # nothing to rescan here
        pass

    def import_packs(self, paths=None, ask=True):
        paths = paths or filedialog.askopenfilenames(title="Corrections packs (from the approved SharePoint folder)",
                                                     filetypes=[("Corrections pack", "*.zip")])
        done, failed = [], []
        for p in paths or []:
            try:
                r = C.import_pack(p)
                done.append(f"{os.path.basename(p)}: {r['lines']} lines, {r['regions']} regions"
                            + (f" ({r['skipped']} already here)" if r["skipped"] else ""))
            except C.PackError as ex:
                failed.append(f"{os.path.basename(p)}: {ex}")
            except Exception as ex:
                eng.log_error("Corrections pack import failed")
                failed.append(f"{os.path.basename(p)}: {type(ex).__name__}")
        if done or failed:
            diag.activity("corrections_imported", files=len(done), errors=len(failed))
            self.refresh()
            if ask:
                messagebox.showinfo("Import", ("Imported:\n" + "\n".join(done) if done else "") +
                                    ("\n\nNot imported (nothing copied):\n" + "\n".join(failed) if failed else ""))
        return done, failed

    def selected(self):
        return list(self.tv.selection())

    def set_rejected(self, on, rels=None):
        rels = rels or self.selected()
        if rels:
            C.set_rejected(rels, on)
            if on:
                diag.activity("corrections_rejected", n=len(rels))
            else:
                diag.activity("corrections_accepted", n=len(rels))
            self.refresh()
        return len(rels)

    def fix_text(self, rel=None, text=None):
        rel = rel or (self.selected()[:1] or [None])[0]
        if not rel:
            return False
        cur = self.tv.set(rel, "text") if self.tv.exists(rel) else ""
        if text is None:
            text = simpledialog.askstring("Fix the text", "Correct text for this line:", initialvalue=cur, parent=self)
        if not text or text.strip() == cur:
            return False
        ok = C.set_text(rel, text)
        if ok:
            diag.activity("corrections_fixed")
            self.refresh(); self.show_picture()
        return ok

    def show_picture(self):
        sel = self.selected()
        if len(sel) != 1:
            self.pic.configure(image=""); self.lbl_pic.configure(text=f"{len(sel)} lines selected." if sel else "Select a line.")
            return
        rel = sel[0]
        try:
            img = Image.open(os.path.join(C.TRAIN_DIR, rel.replace("/", os.sep))).convert("RGB")
            img.thumbnail((300, 160))
            self._thumb = ImageTk.PhotoImage(img)
            self.pic.configure(image=self._thumb)
        except Exception:
            diag.swallowed(); self.pic.configure(image="")
        self.lbl_pic.configure(text=f"Correct text: {self.tv.set(rel, 'text')}\nRead as: {self.tv.set(rel, 'read')}")

    # ------------------------------------------------------------ teach
    def _teach_tab(self, T):
        ctk.CTkLabel(T, text="Teach the reader", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
        self.lbl_teach = ctk.CTkLabel(T, text="", anchor="w", font=("Segoe UI", 13)); self.lbl_teach.pack(fill="x", padx=8)
        for title, why, fn in (
                ("Improve Reading...", "Fine-tunes the Tesseract reader on the taught lines, on this PC's processor, offline. "
                                       "It tests the new reader on lines it did not learn from and keeps it only if it reads better.",
                 self.open_improve),
                ("Trainer...", "Open a document or picture, box text the reader missed, read a region, and save lines or "
                               "Not text regions yourself.", self.open_trainer),
                ("Prepare a package for the docTR Training Kit", "Splits the lines and regions into train and check lists the "
                                                                 "offline Training Kit reads (see the Training Kit's guide).",
                 self.prepare_package)):
            ctk.CTkButton(T, text=title, width=320, height=34, command=fn).pack(anchor="w", padx=8, pady=(14, 2))
            ctk.CTkLabel(T, text=why, wraplength=900, justify="left", anchor="w",
                         text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)

    def prepare_package(self):
        import trainer_gui
        rep = trainer_gui.build_training_package()
        messagebox.showinfo("Training package", rep)
        return rep

    # ------------------------------------------------------------ knowledge
    def _knowledge_tab(self, T):
        ctk.CTkLabel(T, text="Ship the better reader", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
        self.lbl_know = ctk.CTkLabel(T, text=eng.knowledge_status(), anchor="w", justify="left", wraplength=900)
        self.lbl_know.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(T, text="Knowledge Packs: export, load trained models, undo...", width=380, height=34,
                      fg_color="#B45309", command=self.open_knowledge).pack(anchor="w", padx=8, pady=8)
        ctk.CTkLabel(T, text=("Export Knowledge Pack writes a numbered pack: the reader trained here, plus the database, OCR fixes "
                              "and ignore list. Put it in the approved SharePoint folder; people install it in Acronym Hunter "
                              "(Tools > Knowledge Packs) and can undo it."), wraplength=900, justify="left", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":     # same self-test as Acronym Hunter, with training loaded
        eng.run_selftest(sys.argv[2:])
        sys.exit(0)
    try:
        TrainingApp().mainloop()
    except Exception:
        eng.log_error("Acronym Hunter Training failed to start")
        raise


if __name__ == "__main__":
    main()
