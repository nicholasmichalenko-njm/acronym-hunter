"""Stationkeeper Training (2.15.0): corrections in, a better reader out. Its own program, built from the same code.
2.50.0 Training Studio: five steps, 1 Gather, 2 Review, 3 Train, 4 Measure (the scorecard; an area that got worse is
left out automatically), 5 Build the pack (one .skknow file that opens Stationkeeper's install card). See studio.py.

Stationkeeper (the scanner people use every day) only saves corrections: Report misreading and Not text in the
picture preview. People send them as corrections packs to the approved SharePoint folder. This program, run by the
training team:
- Corrections: imports the packs (each file checked against the pack's SHA-256 list first), shows every corrected
  line with its picture, and accepts, rejects or fixes each one. Rejected lines are never taught.
- Teach the reader: the Trainer (box text in pictures, read a region, save lines), Improve Reading (fine-tunes the
  Tesseract reader on this PC's processor, tests it on held-out lines, keeps it only if it reads better), and the
  package for the offline docTR Training Kit.
- Knowledge Pack: exports the better reader, with the database, OCR fixes and ignore list, as a numbered Knowledge
  Pack for the approved SharePoint folder; Stationkeeper installs it (and can undo it). Loads trained models from
  the Training Kit.

Same engine, sandbox and network guard as Stationkeeper. Nothing leaves this PC.
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
import studio as ST

FILTERS = ["All lines", "Taught (not rejected)", "Rejected", "Test set (set aside)", "From packs", "Saved on this PC"]
STEPS = ["1 Gather", "2 Review", "3 Train", "4 Measure", "5 Build the pack"]


class TrainingApp(ctk.CTk):
    # the same windows Stationkeeper used to open, now only here
    open_improve = eng.AcronymAppGUI.open_improve
    open_knowledge = eng.AcronymAppGUI.open_knowledge
    _undo_reader = eng.AcronymAppGUI._undo_reader
    training_state = eng.AcronymAppGUI.training_state
    open_trainer = eng.AcronymAppGUI.open_trainer

    def __init__(self):
        super().__init__()
        eng.ACTIVE_ICON = "trainer.ico"
        eng.apply_window_icon(self)
        self.title(f"Stationkeeper Training {eng.APP_VERSION}: corrections in, a better reader out (100% local)")
        self.geometry("1180x760")
        self.report_callback_exception = lambda et, e, tb: (eng._excepthook(et, e, tb), messagebox.showerror(
            "Error", f"{et.__name__}: {e}\n\nDetails were saved to the logs folder (no file names or document content): Help > Export error logs... saves them for support."))
        self.project, self.queued_files, self._training, self.trainer_win = None, [], False, None
        self._thumb = None
        diag.activity("training_app_started")
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", padx=14, pady=(10, 0))
        ctk.CTkLabel(top, text="Stationkeeper Training", font=("Segoe UI", 18, "bold")).pack(side="left")
        self.lbl_state = ctk.CTkLabel(top, text="", anchor="e", justify="right"); self.lbl_state.pack(side="right")
        # Raw Tk tables are not scaled by CustomTkinter: size their text and rows for the display (2.21.0; rows were
        # clipped at 150-200% display scaling)
        import tkinter.font as tkfont
        sc = max(1.0, float(ctk.ScalingTracker.get_widget_scaling(self)))
        self.table_font = tkfont.Font(family="Segoe UI", size=int(round(11 * sc)))
        self.head_font = tkfont.Font(family="Segoe UI", size=int(round(11 * sc)), weight="bold")
        st = ttk.Style(self); st.theme_use("default")
        st.configure("Treeview", font=self.table_font, rowheight=self.table_font.metrics("linespace") + int(8 * sc))
        st.configure("Treeview.Heading", font=self.head_font, padding=(6, int(4 * sc)))
        self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=12, pady=8)
        self.score_rows = []
        self._gather_tab(self.tabs.add(STEPS[0]))
        self._corrections_tab(self.tabs.add(STEPS[1]))
        self._teach_tab(self.tabs.add(STEPS[2]))
        self._measure_tab(self.tabs.add(STEPS[3]))
        self._build_tab(self.tabs.add(STEPS[4]))
        ctk.CTkLabel(self, text="Offline: nothing leaves this PC. Corrections and Knowledge Packs hold what was learned from "
                                "internal documents: approved SharePoint folder only.", text_color=("#475569", "#94A3B8")).pack(pady=(0, 8))
        self.refresh()

    # ------------------------------------------------------------ corrections
    def _corrections_tab(self, T):
        bar = ctk.CTkFrame(T, fg_color="transparent"); bar.pack(fill="x")
        ctk.CTkButton(bar, text="Import training data...", width=200, fg_color="#0F766E", command=self.import_packs).pack(side="left")
        ctk.CTkLabel(bar, text="Show").pack(side="left", padx=(16, 4))
        self.filter = tk.StringVar(value=FILTERS[0])
        ctk.CTkOptionMenu(bar, variable=self.filter, values=FILTERS, width=190, command=lambda _v: self.fill()).pack(side="left")
        self.search = tk.StringVar(value="")
        e = ctk.CTkEntry(bar, textvariable=self.search, width=200, placeholder_text="Search the text"); e.pack(side="left", padx=8)
        self.search.trace_add("write", lambda *_: self.fill())
        ctk.CTkButton(bar, text="Next: 3 Train >", width=150, command=lambda: self.tabs.set(STEPS[2])).pack(side="right", padx=(8, 0))
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
            if f == "Test set (set aside)" and (s["rejected"] or not ST.in_test_set(s["rel"])):
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
                           values=(s["text"], s["read"], s["conf"], s["source"], s["date"],
                                   "Rejected" if s["rejected"] else "Test set" if ST.in_test_set(s["rel"]) else "Taught"))
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
        if hasattr(self, "lbl_gather"):
            self.gather_refresh()
        if hasattr(self, "lbl_teach"):
            n, new = self.training_state()
            self.lbl_teach.configure(text=f"{n} lines to teach ({new} new since the reader was last improved).")

    def update_banner(self):          # Improve Reading calls this when it starts and ends
        self.refresh()

    def rescan_project(self):         # nothing to rescan here
        pass

    def import_packs(self, paths=None, ask=True):
        """Gather > Import training data... (2.55.0): .sktrain training data packs, each area filed where it belongs;
        older corrections packs (.zip) still import."""
        import trainpack as TP
        paths = paths or filedialog.askopenfilenames(title="Training data (from the approved SharePoint folder)",
                                                     filetypes=[("Training data", "*.sktrain *.zip")])
        done, failed = [], []
        for p in paths or []:
            try:
                if p.lower().endswith(TP.EXT):
                    r = TP.import_pack(p, os.path.join(eng.BASE_DIR, "training_data", "imported"),
                                       os.path.join(eng.CONFIG_DIR, "compliance_learned.json"),
                                       merge_fixes=eng.merge_pack_fixes, merge_ignore=eng.merge_pack_ignore)
                    done.append(f"{os.path.basename(p)}: {r['reading']} misread lines and regions, {r['ocrfix']} OCR fixes, "
                                f"{r['compliance']} compliance decisions ({r['learned']} learned), {r['words']} word choices"
                                + (" (with sentence text)" if r["text"] else "")
                                + (f" ({r['skipped']} already here)" if r["skipped"] else ""))
                    continue
                r = C.import_pack(p)
                done.append(f"{os.path.basename(p)}: {r['lines']} lines, {r['regions']} regions"
                            + (f" ({r['skipped']} already here)" if r["skipped"] else ""))
            except TP.PackError as ex:
                failed.append(f"{os.path.basename(p)}: {ex}")
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
        ctk.CTkLabel(T, text="Step 3. Train: teach the reader", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
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
        ctk.CTkButton(T, text="Next: 4 Measure >", width=200, command=lambda: self.tabs.set(STEPS[3])).pack(anchor="w", padx=8, pady=(20, 8))

    def prepare_package(self):
        import trainer_gui
        rep = trainer_gui.build_training_package()
        messagebox.showinfo("Training package", rep)
        return rep

    # ------------------------------------------------------------ 1 gather
    def _gather_tab(self, T):
        ctk.CTkLabel(T, text="Step 1. Gather what the team learned", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(T, text="Corrections packs from the approved SharePoint folder (misread lines with their pictures), and past "
                             "compliance matrices (their Keep and Drop decisions and where sentences went). The matrices are "
                             "learned as numbered word buckets and counts only, never their words.", wraplength=1000,
                     justify="left", anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)
        bar = ctk.CTkFrame(T, fg_color="transparent"); bar.pack(fill="x", padx=8, pady=10)
        ctk.CTkButton(bar, text="Import training data...", width=230, fg_color="#0F766E", command=self.import_packs).pack(side="left")
        ctk.CTkButton(bar, text="Add past compliance matrices...", width=250, command=self.gather_matrices).pack(side="left", padx=8)
        self.lbl_gather = ctk.CTkLabel(T, text="", anchor="w", justify="left", font=("Segoe UI", 13)); self.lbl_gather.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(T, text="Next: 2 Review >", width=200, command=lambda: self.tabs.set(STEPS[1])).pack(anchor="w", padx=8, pady=8)

    def gather_refresh(self):
        st = ST.load_state(eng.CONFIG_DIR)
        all_ = C.samples()
        train, test = ST.split(all_)
        import complearn
        cs = complearn.Learner(eng.COMPLIANCE_LEARNED_FILE).summary()
        try:
            db, fx = len(eng.read_db_rows()), len(eng.read_ocr_fix_rows())
        except Exception:
            diag.swallowed(); db = fx = 0
        self.lbl_gather.configure(text=(
            f"Corrected lines: {len(all_)} ({len(train)} to teach, {len(test)} set aside as the test set, "
            f"{sum(s['rejected'] for s in all_)} rejected)\n"
            f"Corrections packs imported: {len(C.packs())}\n"
            f"Past compliance matrices gathered: {len(st['matrices'])}  |  compliance decisions learned: {cs['decisions']} "
            f"from {cs['matrices']} matrices\n"
            f"Acronyms database rows: {db}  |  OCR fixes: {fx}"))

    def gather_matrices(self, paths=None):
        paths = paths or filedialog.askopenfilenames(title="Past compliance matrices (Excel)", filetypes=[("Compliance matrix", "*.xlsx")])
        if not paths:
            return []
        res = ST.gather_matrices(list(paths), eng.COMPLIANCE_LEARNED_FILE, eng.CONFIG_DIR)
        diag.activity("studio_matrices_gathered", files=len(res), items=sum(n for _f, n in res))
        self.refresh()
        return res

    # ------------------------------------------------------------ 4 measure
    def _measure_tab(self, T):
        ctk.CTkLabel(T, text="Step 4. Measure: did this training help?", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(T, text="Each area is tested on what it did not learn from. An area that got worse is left out of the pack "
                             "automatically. Double-click a row to leave an area out or put it back.", wraplength=1000,
                     justify="left", anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)
        ctk.CTkButton(T, text="Run the tests", width=200, fg_color="#0F766E", command=self.measure).pack(anchor="w", padx=8, pady=8)
        tf = tk.Frame(T); tf.pack(fill="both", expand=True, padx=8)
        cols = (("title", "Area", 280), ("test", "Test", 330), ("now", "Now", 90), ("after", "After training", 110),
                ("change", "Change", 80), ("pack", "In the pack", 170))
        self.sc = ttk.Treeview(tf, columns=[c[0] for c in cols], show="headings", selectmode="browse")
        for cid, head, w in cols:
            self.sc.heading(cid, text=head); self.sc.column(cid, width=w, stretch=cid in ("title", "test"))
        self.sc.tag_configure("out", foreground="#9CA3AF")
        self.sc.tag_configure("worse", foreground="#B91C1C")
        self.sc.pack(fill="both", expand=True)
        self.sc.bind("<Double-1>", lambda _e: self.toggle_area())
        self.lbl_measure = ctk.CTkLabel(T, text="Run the tests to see the scorecard.", anchor="w"); self.lbl_measure.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(T, text="Next: 5 Build the pack >", width=220, command=lambda: self.tabs.set(STEPS[4])).pack(anchor="w", padx=8, pady=(0, 8))

    def measure(self):
        st = ST.load_state(eng.CONFIG_DIR)
        report = None
        try:
            import json
            with open(os.path.join(eng.TRAIN_DIR, "model", "training_report.json"), encoding="utf-8") as f:
                report = json.load(f)
        except (OSError, ValueError):
            pass
        have = [n for n, _p in eng._knowledge_sources()]
        self.score_rows = ST.scorecard(C.samples(), eng.load_ocr_fixes(), eng.load_ocr_ignore(), report,
                                       ST._matrices(st["matrices"]), have, left_out=st["left_out"])
        diag.activity("studio_measured", rows=len(self.score_rows))
        self.score_fill()
        return self.score_rows

    def score_fill(self):
        self.sc.delete(*self.sc.get_children())
        fmt = lambda v: "-" if v is None else f"{v}%"
        for i, r in enumerate(self.score_rows):
            ch = "" if r["change"] is None else (f"+{r['change']}" if r["change"] >= 0 else str(r["change"]))
            tags = ("worse",) if r["why"] == "Left out: got worse" else ("out",) if not r["include"] else ()
            self.sc.insert("", "end", iid=str(i), tags=tags,
                           values=(r["title"], r["test"] + (f" ({r['n']})" if r.get("n") else ""),
                                   fmt(r["now"]) if r["after"] is not None else "", fmt(r["after"]) if r["after"] is not None else "",
                                   ch, ("Yes" if r["include"] else "No") + ("" if r["why"] == "In the pack" else f": {r['why']}")))
        n_in = len({r["area"] for r in self.score_rows if r["include"]})
        self.lbl_measure.configure(text=f"{n_in} area(s) go in the pack.")

    def toggle_area(self, area=None):
        if area is None:
            sel = self.sc.selection()
            if not sel:
                return None
            area = self.score_rows[int(sel[0])]["area"]
        st = ST.load_state(eng.CONFIG_DIR)
        st["left_out"] = [a for a in st["left_out"] if a != area] if area in st["left_out"] else st["left_out"] + [area]
        ST.save_state(eng.CONFIG_DIR, st)
        self.measure()
        return area not in st["left_out"]

    # ------------------------------------------------------------ 5 build
    def _build_tab(self, T):
        ctk.CTkLabel(T, text="Step 5. Build the pack", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(T, text=("One file (.skknow) with the areas kept and the scorecard. Put it in the approved SharePoint folder. "
                              "People double-click it (or File > Install Knowledge Pack... in Stationkeeper), read one card that "
                              "says what improves, and click Install. Their own corrections, decisions and rows stay; Undo puts "
                              "everything back."), wraplength=1000, justify="left", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)
        ctk.CTkLabel(T, text="Notes for the install card (optional)", anchor="w").pack(fill="x", padx=8, pady=(10, 0))
        self.build_notes = ctk.CTkEntry(T, width=700, placeholder_text="For example: trained on the Kestrel and Osprey corrections")
        self.build_notes.pack(anchor="w", padx=8)
        ctk.CTkButton(T, text="Build the pack...", width=220, height=36, fg_color="#B45309", command=self.build_pack).pack(anchor="w", padx=8, pady=12)
        self.lbl_build = ctk.CTkLabel(T, text="", anchor="w", justify="left", wraplength=1000); self.lbl_build.pack(fill="x", padx=8)
        ctk.CTkLabel(T, text="More", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=8, pady=(16, 2))
        self.lbl_know = ctk.CTkLabel(T, text=eng.knowledge_status(), anchor="w", justify="left", wraplength=900)
        self.lbl_know.pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(T, text="Knowledge Packs: load trained models, export everything, undo...", width=420, height=32,
                      fg_color="#475569", command=self.open_knowledge).pack(anchor="w", padx=8, pady=6)

    def build_pack(self, path=None):
        import datetime
        if not self.score_rows:
            self.measure()
        if not any(r["include"] for r in self.score_rows):
            messagebox.showinfo("Build the pack", "Nothing to ship: every area is left out or empty.", parent=self)
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, title="Save the Knowledge Pack (approved SharePoint folder)",
                                                defaultextension=ST.EXT, initialfile=ST.default_name(datetime.date.today()),
                                                filetypes=[("Knowledge Pack", "*" + ST.EXT)])
            if not path:
                return None
        info = eng.make_knowledge_pack(path, self.build_notes.get(), include=ST.included_files(self.score_rows),
                                       scorecard=self.score_rows)
        diag.activity("studio_pack_built", files=len(info["files"]))
        kept = sorted({r["title"] for r in self.score_rows if r["include"]})
        out = sorted({r["title"] for r in self.score_rows if not r["include"] and r["files"]})
        self.lbl_build.configure(text=f"Built {os.path.basename(path)}.\nIn the pack: {', '.join(kept)}."
                                      + (f"\nLeft out: {', '.join(out)}." if out else "")
                                      + "\nIt holds what was learned from internal documents: approved SharePoint folder only.")
        return info

    # ------------------------------------------------------------ knowledge
    def _knowledge_tab(self, T):
        ctk.CTkLabel(T, text="Ship the better reader", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=8, pady=(8, 2))
        self.lbl_know = ctk.CTkLabel(T, text=eng.knowledge_status(), anchor="w", justify="left", wraplength=900)
        self.lbl_know.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(T, text="Knowledge Packs: export, load trained models, undo...", width=380, height=34,
                      fg_color="#B45309", command=self.open_knowledge).pack(anchor="w", padx=8, pady=8)
        ctk.CTkLabel(T, text=("Export Knowledge Pack writes a numbered pack: the reader trained here, plus the database, OCR fixes "
                              "and ignore list. Put it in the approved SharePoint folder; people install it in Stationkeeper "
                              "(Tools > Knowledge Packs) and can undo it."), wraplength=900, justify="left", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":     # same self-test as Stationkeeper, with training loaded
        eng.run_selftest(sys.argv[2:])
        sys.exit(0)
    try:
        TrainingApp().mainloop()
    except Exception:
        eng.log_error("Stationkeeper Training failed to start")
        raise


if __name__ == "__main__":
    main()
