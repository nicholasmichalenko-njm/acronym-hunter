"""The effort record on screen (2.40.0): the countdown in the top bar, Effort details, and on Effort home the stage
track (Move stage..., Edit stages...), the gate goals, tasks, notes and open questions, and the timeline.

Everything is saved in the effort's record.json (effortrec.py) as it happens. The features log to the timeline through
rec_log(): customer document versions, requirement reviews, people and owners, QA/QC checks."""
import uiquiet as UQ  # 2.47.0: smooth resizing
import datetime, os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import diag
import effortrec as R

STATE_COLORS = {"done": ("#DCFCE7", "#14532D"), "current": ("#1E3A8A", "#FFFFFF"), "ahead": ("#E2E8F0", "#334155")}
KIND_COLORS = {"customer": "#B45309", "ours": "#1E3A8A", "stage": "#0F766E", "note": "#7C3AED", "task": "#334155",
               "assign": "#0369A1", "requirement": "#B45309", "effort": "#0F766E", "qa": "#15803D", "compliance": "#1D4ED8",
               "deliverable": "#0E7490", "gate": "#B45309", "review": "#7C3AED"}
from effortstate import KIND_WORDS  # noqa: E402  (2.63.0: one list for both programs)


class EffortRecordMixin:
    # ------------------------------------------------------------ the record of the open effort
    def effrec(self):
        ws = getattr(self, "ws", None)
        if ws is None or getattr(self, "effort", None) is None:
            return None
        r = getattr(self, "_effrec", None)
        if r is None or r.folder != ws.root:
            self._effrec = r = R.Record(ws.root)
        return r

    def rec_log(self, kind, text, ref=None):
        """Add one line to the open effort's timeline (the paper trail). Never fails the caller."""
        try:
            r = self.effrec()
            if r is not None:
                r.log(kind, text, ref=ref, save=True)
                self._rec_sig = None
        except Exception:
            diag.swallowed()

    def rec_team_names(self):
        r = self.effrec() if getattr(self, "effort", None) is not None else None
        return [m["name"] for m in r.team()] if r is not None else []

    def rec_pick_person(self, title, prompt, initial="", answer=None):
        """2.52.0: pick a person from the effort's team (a drop-down; typing a new name works too). Returns the name,
        "" for nobody, or None when cancelled. answer (tests): at once."""
        if answer is not None:
            return answer
        people = self.rec_people()
        w = ctk.CTkToplevel(self); w.title(title); w.transient(self); w.geometry("520x220"); w.resizable(False, False)
        ctk.CTkLabel(w, text=prompt, anchor="w", justify="left", wraplength=480).pack(fill="x", padx=16, pady=(14, 6))
        cb = ctk.CTkComboBox(w, values=["(nobody)"] + people, width=360); cb.set(initial or "(nobody)"); cb.pack(anchor="w", padx=16)
        ctk.CTkLabel(w, text="The effort's team is in the list (Effort > Team...); a new name can be typed.", anchor="w",
                     text_color=("#64748B", "#94A3B8")).pack(fill="x", padx=16, pady=4)
        res = {"v": None}

        def ok():
            v = cb.get().strip()
            res["v"] = "" if v == "(nobody)" else v
            w.destroy()
        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", padx=16, pady=10)
        ctk.CTkButton(bar, text="OK", command=ok, fg_color="#1E3A8A").pack(side="right")
        ctk.CTkButton(bar, text="Cancel", command=w.destroy, fg_color="#64748B").pack(side="right", padx=8)
        w.after(100, w.lift); w.grab_set(); self.wait_window(w)
        return res["v"]

    def rec_team_dialog(self, rows=None):
        """Effort > Team... (2.52.0): the people on this effort and their roles. They are offered in every drop-down
        where a lead, contributor, author, owner or assignee is picked. rows (tests): save at once."""
        r = self.effrec()
        if r is None:
            messagebox.showinfo("Team", "Open an effort first.")
            return None
        if rows is not None:
            out = r.set_team(rows)
            self._rec_force() if hasattr(self, "rec_cards") else None
            return out
        w = ctk.CTkToplevel(self); w.title("Team"); w.transient(self); w.geometry("640x560")
        ctk.CTkLabel(w, text="The team for this effort", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(w, text="Names (and a role if you like: Proposal manager, Volume lead, Author, Production...). Everyone here "
                             "is in the drop-downs for section leads, contributors, owners, tasks and questions.", anchor="w",
                     justify="left", wraplength=600, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16)
        box = ctk.CTkScrollableFrame(w); box.pack(fill="both", expand=True, padx=16, pady=8)
        items = [[m["name"], m["role"]] for m in r.team()]
        widgets = []

        def draw():
            for x in box.winfo_children():
                x.destroy()
            widgets.clear()
            for i, it in enumerate(items):
                line = ctk.CTkFrame(box, fg_color="transparent"); line.pack(fill="x", pady=2)
                ne = ctk.CTkEntry(line, width=240, placeholder_text="name"); ne.insert(0, it[0]); ne.pack(side="left")
                re_ = ctk.CTkComboBox(line, width=200, values=["Proposal manager", "Capture lead", "Volume lead", "Author",
                                                                "Reviewer", "Production", "Pricing", "Contracts"])
                re_.set(it[1]); re_.pack(side="left", padx=6)
                ctk.CTkButton(line, text="Remove", width=70, fg_color="#B91C1C", command=lambda i=i: (sync(), items.pop(i), draw())).pack(side="left")
                widgets.append((ne, re_))

        def sync():
            for it, (ne, re_) in zip(items, widgets):
                it[0], it[1] = ne.get(), re_.get()

        def add():
            sync(); items.append(["", ""]); draw()

        def ok():
            sync()
            self.rec_team_dialog(rows=[tuple(it) for it in items])
            w.destroy()
        draw()
        if not items:
            add()
        b = ctk.CTkFrame(w, fg_color="transparent"); b.pack(fill="x", padx=16, pady=10)
        ctk.CTkButton(b, text="+ Add a person", command=add, fg_color="#475569").pack(side="left")
        ctk.CTkButton(b, text="Save", command=ok, fg_color="#1E3A8A").pack(side="right")
        w._api = {"items": items, "add": add, "ok": ok, "sync": sync}
        w.after(100, w.lift)
        return w

    def rec_people(self):
        """Everyone named in the effort: section leads and contributors, requirement owners, task owners."""
        import effortstate as ES
        return ES.people_of(self.effrec(), getattr(self, "matrix", None))

    # ------------------------------------------------------------ what the app can check for the gate goals
    def rec_checks(self):
        """2.62.0: the checks live in effortstate (the Qt edition uses them too)."""
        import effortstate as ES
        try:
            lib = self.doclib() if hasattr(self, "doclib") else None
            reg = self.subreg() if hasattr(self, "subreg") else None
            rows = reg.rows() if reg is not None else []
            vols = self.volumes() if hasattr(self, "volumes") else []
            return ES.checks_of(self.effrec(), getattr(self, "matrix", None), lib, rows, getattr(self, "effort", None),
                                getattr(self, "volume_report", None), vols,
                                prove=self.prove_items if hasattr(self, "prove_items") else None)
        except Exception:
            diag.swallowed()
            return {k: None for k in R.AUTO}

    # ------------------------------------------------------------ the countdown in the top bar
    def rec_strip_build(self, strip):
        self.strip_due = ctk.CTkLabel(strip, text="", font=("Segoe UI", 12, "bold"), corner_radius=8, fg_color="transparent", justify="right",
                                      text_color=("#1E3A8A", "#BFDBFE"), cursor="hand2")
        self.strip_due.pack(side="right", padx=(6, 14))
        self.strip_due.bind("<Button-1>", lambda _e: self.rec_details_dialog())

    def rec_strip_refresh(self):
        if not hasattr(self, "strip_due"):
            return ""
        r = self.effrec()
        text = ""
        if r is not None and r.data["due"]:
            left = R.countdown(r.data["due"])
            dt = R.due_text(r.data["due"], r.data["zone"])
            short = dt.split(",")[0] + (dt[dt.rfind(","):] if dt.count(",") >= 2 else "")       # 'Dec 15, 2:00 p.m. MT'
            text = f"{R.countdown_text(r.data['due'])}\nto {short}"
            color = ("#B91C1C", "#FCA5A5") if left and left[0] < 3 else ("#B45309", "#FBBF24") if left and left[0] < 8 else ("#1E3A8A", "#BFDBFE")
            self.strip_due.configure(text_color=color)
        elif r is not None:
            text = "Set the due date..."
            self.strip_due.configure(text_color=("#64748B", "#94A3B8"))
        if self.strip_due.cget("text") != text:
            self.strip_due.configure(text=text)
        return text

    # ------------------------------------------------------------ Effort details
    def rec_details_dialog(self, values=None):
        """Client, solicitation or opportunity number, internal number, due date and time. values (tests): saves at once."""
        L, r = getattr(self, "effort", None), self.effrec()
        if L is None or r is None:
            messagebox.showinfo("Effort details", "Open an effort first.")
            return None
        due0 = R.due_text(r.data["due"], r.data["zone"]) if r.data["due"] else ""

        def save(v):
            client, sol, internal, due = (" ".join((v.get(k) or "").split()) for k in ("client", "sol", "internal", "due"))
            changed = []
            for attr, val, word in (("client", client, "client"), ("solicitation", sol, "solicitation number"), ("internal_no", internal, "internal number")):
                if getattr(L, attr) != val:
                    setattr(L, attr, val); changed.append(f"{word} {val or '(none)'}")
            if changed:
                try:
                    self.efforts.put(L.name, client=L.client, solicitation=L.solicitation, internal_no=L.internal_no)
                    L.pending = True
                    self._save_effort_list()
                except Exception:
                    diag.swallowed()
                r.log("effort", "Effort details: " + "; ".join(changed), save=True)
            if due != due0:
                iso, zone = R.parse_due_text(due) if due else ("", "")
                if due and not iso:
                    messagebox.showwarning("Effort details", "The due date was not understood. Write it like December 15, 2026, 2:00 p.m. MT.")
                    return False
                r.set_due(iso, zone)
            diag.activity("effort_details_saved", n=len(changed))
            self._rec_sig = None
            self.rec_strip_refresh()
            self.shell_overview_refresh() if hasattr(self, "shell_overview_refresh") else None
            return True

        if values is not None:
            return save(values)
        w = ctk.CTkToplevel(self); w.title("Effort details"); w.transient(self); w.geometry("700x440")
        ents = {}
        for i, (k, lab, val, hint) in enumerate((("client", "Client", L.client, "USSF SSC"),
                                                  ("sol", "Solicitation or opportunity number", L.solicitation, "FA8810-26-R-0042"),
                                                  ("internal", "Internal number", L.internal_no, ""))):
            ctk.CTkLabel(w, text=lab, anchor="w").grid(row=i, column=0, sticky="w", padx=14, pady=(14 if i == 0 else 6, 0))
            e = ctk.CTkEntry(w, width=360, placeholder_text=hint); e.insert(0, val or ""); e.grid(row=i, column=1, sticky="w", padx=8, pady=(14 if i == 0 else 6, 0))
            ents[k] = e
        # 2.52.0: the due date from a calendar, the time and zone beside it (no date format to remember)
        import datepick as DP
        ctk.CTkLabel(w, text="Due date and time", anchor="w").grid(row=3, column=0, sticky="w", padx=14, pady=(6, 0))
        dr = ctk.CTkFrame(w, fg_color="transparent"); dr.grid(row=3, column=1, sticky="w", padx=8, pady=(6, 0))
        due_iso = (r.data.get("due") or "")[:10]
        dd = DP.DateField(dr, due_iso, width=130); dd.pack(side="left")
        hm = (r.data.get("due") or "")[11:16]
        t0 = ""
        if hm[:2].isdigit() and hm[3:5].isdigit():
            h, mi = int(hm[:2]), int(hm[3:5])
            t0 = f"{h % 12 or 12}:{mi:02d} {'a.m.' if h < 12 else 'p.m.'}"
        te = ctk.CTkEntry(dr, width=90, placeholder_text="2:00 p.m."); te.insert(0, t0); te.pack(side="left", padx=6)
        ze = ctk.CTkEntry(dr, width=60, placeholder_text="MT"); ze.insert(0, r.data.get("zone", "")); ze.pack(side="left")

        class _Due:                                   # reads like the old text field for save()
            @staticmethod
            def get():
                d = dd.get()
                if not d:
                    return dd.entry.get().strip()
                return ", ".join(x for x in (DP.nice(d), (te.get().strip() + " " + ze.get().strip()).strip()) if x)

            @staticmethod
            def put(text):
                iso, zone = R.parse_due_text(text)
                if iso:
                    dd.set(iso[:10]); ze.delete(0, "end"); ze.insert(0, zone or "")
                    hm2 = iso[11:16]
                    te.delete(0, "end")
                    if hm2[:2].isdigit():
                        h2, m2 = int(hm2[:2]), int(hm2[3:5])
                        te.insert(0, f"{h2 % 12 or 12}:{m2:02d} {'a.m.' if h2 < 12 else 'p.m.'}")
        ents["due"] = _Due
        found = self._rec_rfp_due()
        if found:
            def use():
                _Due.put(found)
            ctk.CTkLabel(w, text=f"The customer documents say: {found}", anchor="w", wraplength=560, justify="left",
                         text_color=("#475569", "#94A3B8")).grid(row=4, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 0))
            ctk.CTkButton(w, text="Use it", width=10, command=use).grid(row=5, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkLabel(w, text="The countdown uses this PC's clock; the time zone is shown as written.", anchor="w",
                     text_color=("#475569", "#94A3B8")).grid(row=6, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 0))

        def ok():
            if save({k: e.get() for k, e in ents.items()}):
                w.destroy()
        ctk.CTkButton(w, text="Save", command=ok, fg_color="#1E3A8A").grid(row=7, column=1, sticky="e", padx=14, pady=16)
        w._api = {"entries": ents, "ok": ok, "date": dd, "time": te, "zone": ze}
        w.after(100, w.lift)
        return w

    def _rec_rfp_due(self):
        try:
            reg = self.subreg() if hasattr(self, "subreg") else None
            due = next((x for x in (reg.rows() if reg else []) if x["kind"] == "Due"), None)
            return due["value"] if due else ""
        except Exception:
            diag.swallowed()
            return ""

    # ------------------------------------------------------------ Effort home
    HOME_SECTIONS = (("goals", "Gate goals", True), ("compliance", "Compliance matrix", True),     # 2.52.0
                     ("tasks", "Tasks", True), ("notes", "Notes and open questions", True),
                     ("custinfo", "Customer information", True),                    # 2.51.0
                     ("calendar", "Calendar", True), ("timeline", "Timeline", False))

    def rec_build_home(self, P):
        """2.49.0: the effort's working sections, full width, each one opens and closes (remembered): gate goals, tasks,
        notes and open questions, a calendar, the timeline. One Show filter picks a person for tasks and questions."""
        bar = ctk.CTkFrame(P, fg_color="transparent"); bar.pack(fill="x", padx=6, pady=(0, 8))
        B = dict(width=10, height=32)
        ctk.CTkButton(bar, text="Effort details...", command=self.rec_details_dialog, fg_color="#475569", **B).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bar, text="Team...", command=self.rec_team_dialog, fg_color="#475569", **B).pack(side="left", padx=6)
        if hasattr(self, "status_export"):
            ctk.CTkButton(bar, text="Effort status (Word)...", command=self.status_export, **B).pack(side="left", padx=6)
        if hasattr(self, "pkg_save_dialog"):
            ctk.CTkButton(bar, text="Save effort package...", command=self.pkg_save_dialog, fg_color="#0F766E", **B).pack(side="left", padx=6)
        self.rec_who = ctk.CTkOptionMenu(bar, values=["Everyone"], width=170, command=lambda _v: self._rec_force())
        self.rec_who.pack(side="right")
        ctk.CTkLabel(bar, text="Show tasks and questions for").pack(side="right", padx=6)
        self.rec_track = ctk.CTkFrame(P, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1, border_color=("#E2E8F0", "#334155"))
        self.rec_track.pack(fill="x", padx=6, pady=(0, 6))
        cards = {}
        self.rec_open = dict({k: d for k, _t, d in self.HOME_SECTIONS}, **(self.settings.get("home_sections") or {}))
        for key, title, _d in self.HOME_SECTIONS:
            c = ctk.CTkFrame(P, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1, border_color=("#E2E8F0", "#334155"))
            c.pack(fill="x", padx=6, pady=4)
            head = ctk.CTkFrame(c, fg_color="transparent"); head.pack(fill="x", padx=10, pady=(8, 6))
            tog = ctk.CTkButton(head, text="", width=26, height=26, fg_color="transparent", text_color=("#1E3A8A", "#93C5FD"),
                                hover_color=("#E2E8F0", "#334155"), font=("Segoe UI", 14, "bold"),
                                command=lambda k=key: self.rec_toggle(k))
            tog.pack(side="left")
            lab = ctk.CTkLabel(head, text=title, font=("Segoe UI", 15, "bold"), anchor="w", cursor="hand2")
            lab.pack(side="left", padx=(2, 0))
            lab.bind("<Button-1>", lambda _e, k=key: self.rec_toggle(k))
            body = ctk.CTkFrame(c, fg_color="transparent")
            cards[key] = (head, lab, body)
            c._tog, c._body = tog, body
            self.__dict__.setdefault("rec_frames", {})[key] = c
        S = dict(width=10, height=28)
        ctk.CTkButton(cards["goals"][0], text="+ Goal", command=self.rec_add_goal_dialog, **S).pack(side="right")
        ctk.CTkButton(cards["tasks"][0], text="+ Task", command=self.rec_task_dialog, **S).pack(side="right")
        ctk.CTkButton(cards["notes"][0], text="+ Question", command=lambda: self.rec_note_dialog(question=True), fg_color="#B45309",
                      **S).pack(side="right", padx=(6, 0))
        ctk.CTkButton(cards["notes"][0], text="+ Note", command=self.rec_note_dialog, **S).pack(side="right")
        ctk.CTkButton(cards["custinfo"][0], text="+ Add...", command=self.rec_custinfo_dialog, **S).pack(side="right")
        go = lambda st: self.shell_go("compliance", st) if hasattr(self, "shell_go") else None
        ctk.CTkButton(cards["compliance"][0], text="Matrix", command=lambda: go("matrix"), fg_color="#475569", **S).pack(side="right")
        ctk.CTkButton(cards["compliance"][0], text="Assign", command=lambda: go("decide"), **S).pack(side="right", padx=6)
        ctk.CTkButton(cards["compliance"][0], text="Read customer documents...", fg_color="#9A3412", **S,
                      command=lambda: (go("read"), self.compliance_read_docs() if hasattr(self, "compliance_read_docs") else None)).pack(side="right")
        ctk.CTkButton(cards["calendar"][0], text="Next >", command=lambda: self.rec_cal_step(1), fg_color="#475569", **S).pack(side="right")
        ctk.CTkButton(cards["calendar"][0], text="This month", command=lambda: self.rec_cal_step(0), fg_color="#475569", **S).pack(side="right", padx=6)
        ctk.CTkButton(cards["calendar"][0], text="< Previous", command=lambda: self.rec_cal_step(-1), fg_color="#475569", **S).pack(side="right")
        ctk.CTkButton(cards["timeline"][0], text="Full timeline...", command=self.rec_timeline_window, fg_color="#475569", **S).pack(side="right")
        self.rec_cards = cards
        self.rec_cal_month = datetime.date.today().replace(day=1)
        self.rec_cal_day = None
        self._rec_sig = None
        for key in self.rec_open:
            self._rec_apply_open(key)

    def _rec_apply_open(self, key):
        c = self.rec_frames.get(key)
        if c is None:
            return
        on = bool(self.rec_open.get(key, True))
        c._tog.configure(text="\u25be" if on else "\u25b8")        # small triangles (text symbols)
        if on and not c._body.winfo_manager():
            c._body.pack(fill="x", padx=12, pady=(0, 10))
        elif not on and c._body.winfo_manager():
            c._body.pack_forget()

    def rec_toggle(self, key, on=None):
        """Open or close one Effort home section (remembered)."""
        self.rec_open[key] = (not self.rec_open.get(key, True)) if on is None else bool(on)
        self._rec_apply_open(key)
        try:
            self.settings["home_sections"] = dict(self.rec_open)
            __import__("app_gui").save_settings(self.settings)
        except Exception:
            diag.swallowed()
        return self.rec_open[key]

    def rec_cal_step(self, d):
        m = self.rec_cal_month
        if d == 0:
            self.rec_cal_month = datetime.date.today().replace(day=1)
        else:
            y, mo = m.year + (m.month - 1 + d) // 12, (m.month - 1 + d) % 12 + 1
            self.rec_cal_month = datetime.date(y, mo, 1)
        self.rec_cal_day = None
        self._rec_force()
        return self.rec_cal_month

    def _rec_force(self):
        self._rec_sig = None
        self.rec_refresh()

    def rec_refresh(self):
        """Redraw the stage track and the four cards when something changed (cheap to call on every tick)."""
        if not hasattr(self, "rec_cards"):
            return
        r = self.effrec()
        checks = self.rec_checks() if r is not None else {}
        people = self.rec_people() if r is not None else []
        sig = (id(r), len(r.data["timeline"]) if r else 0, repr(r.data["stages"]) if r else "", repr(r.data["tasks"]) if r else "",
               repr(r.data["notes"]) if r else "", tuple(sorted(checks.items())), self.rec_who.get(), tuple(people),
               getattr(self, "rec_cal_month", None), getattr(self, "rec_cal_day", None), r.data.get("due", "") if r else "",
               repr(r.data.get("customer_info")) if r else "", self._rec_comp_sig())
        if sig == getattr(self, "_rec_sig", None):
            return
        self._rec_sig = sig
        for w in self.rec_track.winfo_children():
            w.destroy()
        for _h, _l, body in self.rec_cards.values():
            for w in body.winfo_children():
                w.destroy()
        if r is None:
            return
        self.rec_who.configure(values=["Everyone"] + people)
        if self.rec_who.get() not in ["Everyone"] + people:
            self.rec_who.set("Everyone")
        self._rec_draw_track(r)
        self._rec_draw_goals(r, checks)
        self._rec_draw_tasks(r)
        self._rec_draw_notes(r)
        self._rec_draw_compliance(r)
        self._rec_draw_custinfo(r)
        self._rec_draw_calendar(r)
        self._rec_draw_timeline(r)

    @staticmethod
    def _autowrap(label, ref, pad=8, least=120):
        """Wrap a label's text to the width its row really has (cards are half the window; windows vary)."""
        def fit(e):
            try:
                sc = float(ctk.ScalingTracker.get_widget_scaling(label))
                w = max(least, int(e.width / sc) - pad)
                if label.cget("wraplength") != w:
                    label.configure(wraplength=w)
            except Exception:
                pass
        ref.bind("<Configure>", UQ.debounced(ref, fit, 80), add="+")

    def _rec_draw_track(self, r):
        t = self.rec_track
        row = ctk.CTkFrame(t, fg_color="transparent"); row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(row, text="STAGE", font=("Segoe UI", 10, "bold"), text_color=("#64748B", "#94A3B8")).pack(side="left", padx=(2, 8))
        pills = ctk.CTkFrame(t, fg_color="transparent"); pills.pack(fill="x", padx=12, pady=(0, 10))
        n = max(1, len(r.stages))
        for i, s in enumerate(r.stages):                # one even row that shrinks with the window; names wrap
            st = r.state_of(s)
            bg, fg = STATE_COLORS[st]
            tm = r.stage_timing(s)
            plan = (f"{R.short_date(s['planned'])}-{R.short_date(s['planned_end'])}" if s.get("planned") and s.get("planned_end")
                    else R.short_date(s["planned"]) if s.get("planned") else "")
            when = (R.short_date(s["started"]) if st != "ahead" else plan)
            if st == "current" and tm["end"]:                      # 2.52.0: how long the stage was planned to last
                when = (when + "\n" if when else "") + (f"{tm['left']} day{'s' if tm['left'] != 1 else ''} left" if tm["left"] is not None
                                                         else f"{tm['over']} day{'s' if tm['over'] != 1 else ''} past plan")
            if st == "current" and tm["over"]:
                bg, fg = ("#B45309", "#FFFFFF")                    # past its planned end: amber, nothing else changes
            txt = s["name"] + ("  ✓" if st == "done" else "") + (f"\n{when}" if when else "")
            pills.grid_columnconfigure(i, weight=1, uniform="stage")
            lab = ctk.CTkLabel(pills, text=txt, fg_color=bg, text_color=fg, corner_radius=12, font=("Segoe UI", 12, "bold" if st == "current" else "normal"),
                               padx=4, pady=4, justify="center")
            lab.grid(row=0, column=i, sticky="nsew", padx=2)
            self._autowrap(lab, lab, pad=10, least=50)
        B = dict(width=10, height=30)
        ctk.CTkButton(row, text="Edit stages...", command=self.rec_stages_dialog, fg_color="#475569", **B).pack(side="right", padx=(6, 0))
        nxt = r.index() + 1
        ctk.CTkButton(row, text=(f"Move to {r.stages[nxt]['name']}..." if nxt < len(r.stages) else "Move stage..."),
                      command=self.rec_move_dialog, **B).pack(side="right", padx=6)

    def _rec_goal_row(self, parent, r, s, g, checks, carry_var=None):
        done = r.goal_done(g, checks)
        auto_known = bool(g.get("auto")) and checks.get(g["auto"]) is not None
        line = ctk.CTkFrame(parent, fg_color="transparent"); line.pack(fill="x", pady=1)
        if auto_known:
            ctk.CTkLabel(line, text="✓" if done else "✗", width=24, font=("Segoe UI", 14, "bold"),
                         text_color=("#15803D", "#86EFAC") if done else ("#B91C1C", "#FCA5A5")).pack(side="left")
        else:
            var = tk.BooleanVar(value=done)
            ctk.CTkCheckBox(line, text="", variable=var, width=24, checkbox_width=18, checkbox_height=18,
                            command=lambda: (r.set_goal(s["id"], g["id"], var.get()), self._rec_force())).pack(side="left")
        where = "by the app" if auto_known else ("by hand" + (f": {g['by']}" if g.get("by") and done else ""))
        if carry_var is None:
            X = dict(width=10, height=22, fg_color="transparent", text_color=("#475569", "#94A3B8"), hover_color=("#E2E8F0", "#334155"),
                     font=("Segoe UI", 11))
            ctk.CTkButton(line, text="Remove", command=lambda: self.rec_goal_remove(s["id"], g["id"]), **X).pack(side="right", anchor="n")
            if not g.get("auto"):
                ctk.CTkButton(line, text="Edit", command=lambda: self.rec_goal_edit(s["id"], g["id"]), **X).pack(side="right", anchor="n")
        ctk.CTkLabel(line, text=where, text_color=("#64748B", "#94A3B8"), font=("Segoe UI", 11)).pack(side="right", anchor="n", padx=(0, 4))
        txt = g["text"] + (f"   (from {g['from']})" if g.get("from") else "")
        lab = ctk.CTkLabel(line, text=txt, anchor="w", justify="left", wraplength=300)
        lab.pack(side="left", padx=4, fill="x", expand=True)
        self._autowrap(lab, line, pad=200)
        return line

    def _rec_draw_goals(self, r, checks):
        head, lab, body = self.rec_cards["goals"]
        s = r.stage()
        n, total = r.goal_progress(checks=checks)
        lab.configure(text=f"{s['name']}: gate goals   {n} of {total}")
        bar = ctk.CTkProgressBar(body, height=8); bar.pack(fill="x", pady=(0, 6)); bar.set(n / total if total else 0)
        if not s["goals"]:
            ctk.CTkLabel(body, text="No goals for this stage yet. + Goal adds one.", anchor="w").pack(fill="x")
        for g in s["goals"]:
            self._rec_goal_row(body, r, s, g, checks)

    def _rec_draw_tasks(self, r):
        _h, lab, body = self.rec_cards["tasks"]
        who = self.rec_who.get()
        ts = r.tasks(owner=None if who == "Everyone" else who)
        open_n = sum(1 for t in ts if t["status"] != "Done")
        lab.configure(text=f"Tasks   {open_n} open")
        if who != "Everyone":
            self._rec_person_summary(body, who)
        if not ts:
            ctk.CTkLabel(body, text="No tasks." if who == "Everyone" else f"No tasks for {who}.", anchor="w").pack(fill="x")
        for t in ts[:12]:
            line = ctk.CTkFrame(body, fg_color="transparent"); line.pack(fill="x", pady=1)
            done = t["status"] == "Done"
            late = r.task_overdue(t)
            col = ("#15803D", "#86EFAC") if done else ("#B91C1C", "#FCA5A5") if late else ("#1E3A8A", "#BFDBFE") if t["status"] == "In progress" else ("#475569", "#94A3B8")
            ctk.CTkLabel(line, text=t["status"] + (" (late)" if late else ""), width=120, anchor="w", text_color=col,
                         font=("Segoe UI", 12, "bold")).pack(side="left")
            ctk.CTkLabel(line, text=" | ".join(x for x in (t["owner"], ("due " + R.nice_date(t["due"])) if t["due"] else "") if x),
                         text_color=("#475569", "#94A3B8"), font=("Segoe UI", 11)).pack(side="right")
            b = ctk.CTkButton(line, text=t["title"][:48] + ("..." if len(t["title"]) > 48 else ""), anchor="w", fg_color="transparent",
                              text_color=("#0F172A", "#F1F5F9"), hover_color=("#E2E8F0", "#334155"), height=26, width=40,
                              command=lambda tid=t["id"]: self.rec_task_dialog(tid))
            b.pack(side="left", fill="x", expand=True)
        if len(ts) > 12:
            ctk.CTkLabel(body, text=f"and {len(ts) - 12} more", anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x")

    def _rec_person_summary(self, body, who):
        """What one person owns: sections, compliance requirements, tasks."""
        M = getattr(self, "matrix", None)
        secs, reqs = [], 0
        if M is not None:
            try:
                import setupdoc as SD
                secs = SD.sections_of(M, who)
                reqs = sum(1 for it in M.items if it["decision"] == "Keep" and who in SD.owners_list(M, it))
            except Exception:
                diag.swallowed()
        ctk.CTkLabel(body, text=f"{who}: {len(secs)} section(s)" + (f" ({', '.join(secs[:4])}{'...' if len(secs) > 4 else ''})" if secs else "")
                     + f", {reqs} compliance requirement(s)", anchor="w", justify="left", wraplength=560,
                     text_color=("#0369A1", "#7DD3FC")).pack(fill="x", pady=(0, 4))

    def _rec_draw_notes(self, r):
        _h, lab, body = self.rec_cards["notes"]
        who = self.rec_who.get()
        qs = r.open_questions(assignee=None if who == "Everyone" else who)
        notes = [n for n in r.notes() if not (n["question"] and not n["resolved"])] if who == "Everyone" else []
        lab.configure(text=f"Notes and open questions   {len(qs)} open" + ("" if who == "Everyone" else f" for {who}"))
        X = dict(width=10, height=24, fg_color="transparent", text_color=("#1E3A8A", "#93C5FD"), hover_color=("#E2E8F0", "#334155"),
                 font=("Segoe UI", 11))
        for n in (qs + notes)[:14]:
            line = ctk.CTkFrame(body, fg_color="transparent"); line.pack(fill="x", pady=2)
            q = n["question"] and not n["resolved"]
            kind = "QUESTION" if q else ("ANSWERED" if n["question"] else "NOTE")
            ctk.CTkLabel(line, text=kind, width=86, anchor="w", font=("Segoe UI", 11, "bold"),
                         text_color=("#B45309", "#FBBF24") if q else ("#7C3AED", "#C4B5FD")).pack(side="left", anchor="n")
            ctk.CTkButton(line, text="Remove", command=lambda nid=n["id"]: self.rec_note_remove(nid), **X).pack(side="right", anchor="n")
            ctk.CTkButton(line, text="Edit", command=lambda nid=n["id"]: self.rec_note_edit_dialog(nid), **X).pack(side="right", anchor="n")
            if q:
                ctk.CTkButton(line, text="Resolve...", width=10, height=24, fg_color="#B45309",
                              command=lambda nid=n["id"]: self.rec_resolve_dialog(nid)).pack(side="right", padx=4, anchor="n")
                ctk.CTkButton(line, text="Assign...", width=10, height=24, fg_color="#475569",
                              command=lambda nid=n["id"]: self.rec_note_edit_dialog(nid, focus="assignee")).pack(side="right", padx=(4, 0), anchor="n")
            col = ctk.CTkFrame(line, fg_color="transparent"); col.pack(side="left", fill="x", expand=True)
            txt = n["text"] + (f"\nAnswer: {n['answer']}" if n.get("answer") else "")
            tl = ctk.CTkLabel(col, text=txt, anchor="w", justify="left", wraplength=300); tl.pack(fill="x")
            self._autowrap(tl, col)
            meta = " | ".join(x for x in (n["label"], R.short_date(n["at"]), n["who"],
                                          ("assigned to " + n["assignee"]) if n.get("assignee") else "") if x)
            ctk.CTkLabel(col, text=meta, font=("Segoe UI", 11), anchor="w", text_color=("#64748B", "#94A3B8")).pack(fill="x")
        if len(qs) + len(notes) > 14:
            ctk.CTkLabel(body, text=f"and {len(qs) + len(notes) - 14} more", anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x")
        if not qs and not notes:
            ctk.CTkLabel(body, text=("No notes yet. Notes can go on the effort, a stage, a customer document or a requirement."
                                     if who == "Everyone" else f"No open questions for {who}."),
                         anchor="w", justify="left", wraplength=560).pack(fill="x")

    # ------------------------------------------------------------ the compliance matrix on Effort home (2.52.0)
    def rec_matrix(self):
        """The effort's compliance matrix: the open one, else read from its file (kept until the file changes)."""
        M = getattr(self, "matrix", None)
        if M is not None:
            return M
        ws = getattr(self, "ws", None)
        p = ws.get("compliance_path", "") if ws is not None else ""
        if not p or not os.path.isfile(p):
            return None
        key = (p, os.path.getmtime(p))
        if getattr(self, "_rec_mx", (None, None))[0] != key:
            try:
                import compliance as CM
                self._rec_mx = (key, CM.Matrix(p).load())
            except Exception:
                diag.swallowed()
                self._rec_mx = (key, None)
        return self._rec_mx[1]

    def _rec_comp_sig(self):
        M = self.rec_matrix()
        if M is None:
            return None
        return (len(M.items), sum(1 for it in M.items if it.get("decision")), sum(1 for it in M.items if it.get("map")))

    def _rec_draw_compliance(self, r):
        _h, lab, body = self.rec_cards["compliance"]
        M = self.rec_matrix()
        if M is None or not M.items:
            lab.configure(text="Compliance matrix   not started")
            ctk.CTkLabel(body, text="Read the customer documents into the compliance review (Read customer documents...), then "
                                    "assign each sentence. Progress shows here at every stage.", anchor="w", justify="left",
                         wraplength=900, text_color=("#475569", "#94A3B8")).pack(fill="x")
            return
        import compliance as CM
        pg = CM.progress(M.items)
        lab.configure(text=f"Compliance matrix   {pg['pct']}% reviewed")
        bar = ctk.CTkProgressBar(body, height=10); bar.pack(fill="x", pady=(0, 6)); bar.set(pg["pct"] / 100.0)
        ctk.CTkLabel(body, text=(f"{pg['decided']} of {pg['total']} sentences reviewed: {pg['Keep']} compliance requirement(s), "
                                 f"{pg['Context']} support, {pg.get('Customer', 0)} the customer's, {pg['Drop']} not used"
                                 + (f";  {pg['needs_home']} still need a proposal section" if pg["needs_home"] else "") + "."),
                     anchor="w", justify="left", wraplength=900).pack(fill="x")
        for f in pg["files"]:
            line = ctk.CTkFrame(body, fg_color="transparent"); line.pack(fill="x", pady=1)
            done = f["decided"] == f["total"]
            ctk.CTkLabel(line, text=("✓ " if done else "") + f"{f['pct']}%", width=60, anchor="w", font=("Segoe UI", 12, "bold"),
                         text_color=("#15803D", "#86EFAC") if done else ("#B45309", "#FBBF24")).pack(side="left")
            ctk.CTkLabel(line, text=f"{f['file']}   {f['decided']} of {f['total']}", anchor="w").pack(side="left", fill="x", expand=True)
        added = sum(1 for it in M.items if it.get("new") == "Added by the text check")
        tc = ("The text check runs after every read and adds any line of the customer documents the reader missed"
              + (f" ({added} added so far)." if added else "."))
        ctk.CTkLabel(body, text=tc, anchor="w", text_color=("#475569", "#94A3B8"), font=("Segoe UI", 11)).pack(fill="x", pady=(4, 0))

    # ------------------------------------------------------------ customer information (2.51.0)
    def _rec_draw_custinfo(self, r):
        _h, lab, body = self.rec_cards["custinfo"]
        info = r.customer_info()
        lab.configure(text=f"Customer information   {len(info)}")
        if not info:
            ctk.CTkLabel(body, text="Names, e-mails, phone numbers and addresses from the customer documents. In Compliance, select "
                                    "them and right-click, Customer information; or + Add....", anchor="w", justify="left",
                         wraplength=900, text_color=("#475569", "#94A3B8")).pack(fill="x")
            return
        X = dict(width=10, height=22, fg_color="transparent", text_color=("#475569", "#94A3B8"), hover_color=("#E2E8F0", "#334155"),
                 font=("Segoe UI", 11))
        import effortrec as RR
        for kind in RR.INFO_KINDS:
            for c in [c for c in info if c["kind"] == kind]:
                line = ctk.CTkFrame(body, fg_color="transparent"); line.pack(fill="x", pady=1)
                ctk.CTkLabel(line, text=kind.upper(), width=110, anchor="w", font=("Segoe UI", 11, "bold"),
                             text_color=("#0369A1", "#7DD3FC")).pack(side="left", anchor="n")
                ctk.CTkButton(line, text="Remove", command=lambda cid=c["id"]: self.rec_custinfo_remove(cid), **X).pack(side="right")
                if c.get("source"):
                    ctk.CTkLabel(line, text=c["source"], font=("Segoe UI", 11), text_color=("#64748B", "#94A3B8")).pack(side="right", padx=6)
                ctk.CTkLabel(line, text=c["value"], anchor="w", justify="left", wraplength=600).pack(side="left", fill="x", expand=True)

    def rec_custinfo_dialog(self, text=None):
        r = self.effrec()
        if r is None:
            return None
        if text is None:
            from tkinter import simpledialog
            text = simpledialog.askstring("Customer information", "Name, e-mail, phone number or address (several are fine):", parent=self)
            if not text:
                return None
        added = r.add_customer_info(text, source="typed in")
        self._rec_force()
        return added

    def rec_custinfo_remove(self, cid):
        r = self.effrec()
        ok = r.remove_customer_info(cid) if r is not None else False
        self._rec_force()
        return ok

    # ------------------------------------------------------------ calendar
    CAL_COLORS = {"due": ("#B91C1C", "#FCA5A5"), "stage": ("#1E3A8A", "#93C5FD"), "task": ("#B45309", "#FBBF24"),
                  "done": ("#15803D", "#86EFAC"), "event": ("#475569", "#94A3B8"), "questions": ("#7C3AED", "#C4B5FD")}

    def rec_cal_extra(self):
        """Dates from the customer documents: questions due, and the due date when the effort has none of its own."""
        import effortstate as ES
        try:
            reg = self.subreg() if hasattr(self, "subreg") else None
            return ES.cal_extra_of(self.effrec(), reg.rows() if reg is not None else [])
        except Exception:
            diag.swallowed()
            return []

    def rec_cal_days(self, month=None):
        """{date: [(kind, text)]} for one month (Effort home, the status export)."""
        import calendar as CAL
        r = self.effrec()
        m = month or getattr(self, "rec_cal_month", None) or datetime.date.today().replace(day=1)
        last = m.replace(day=CAL.monthrange(m.year, m.month)[1])
        return r.calendar(first=m, last=last, extra=self.rec_cal_extra()) if r is not None else {}

    def _rec_draw_calendar(self, r):
        import calendar as CAL
        head, lab, body = self.rec_cards["calendar"]
        m = self.rec_cal_month
        days = self.rec_cal_days(m)
        lab.configure(text=f"Calendar   {m.strftime('%B %Y')}")
        grid = ctk.CTkFrame(body, fg_color="transparent"); grid.pack(fill="x")
        for i, dn in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            grid.grid_columnconfigure(i, weight=1, uniform="cal")
            ctk.CTkLabel(grid, text=dn, font=("Segoe UI", 11, "bold"), text_color=("#64748B", "#94A3B8")).grid(row=0, column=i, sticky="ew")
        today = datetime.date.today()
        self.rec_cal_cells = {}
        for wi, week in enumerate(CAL.Calendar(0).monthdatescalendar(m.year, m.month)):
            for di, d in enumerate(week):
                inm = d.month == m.month
                items = days.get(d, []) if inm else []
                sel = d == self.rec_cal_day
                cell = ctk.CTkFrame(grid, corner_radius=6, height=64, border_width=2 if (d == today or sel) else 1,
                                    border_color=("#1E3A8A", "#93C5FD") if sel else ("#B91C1C", "#FCA5A5") if d == today else ("#E2E8F0", "#334155"),
                                    fg_color=("#FFFFFF", "#1F2937") if inm else ("#F8FAFC", "#111827"))
                cell.grid(row=wi + 1, column=di, sticky="nsew", padx=1, pady=1)
                cell.grid_propagate(False)
                ctk.CTkLabel(cell, text=str(d.day), font=("Segoe UI", 11, "bold" if d == today else "normal"), height=16,
                             text_color=("#0F172A", "#F1F5F9") if inm else ("#CBD5E1", "#475569")).pack(anchor="nw", padx=4)
                for kind, text in items[:2]:
                    ctk.CTkLabel(cell, text=text[:22], font=("Segoe UI", 10), height=14, anchor="w",
                                 text_color=self.CAL_COLORS.get(kind, ("#334155", "#CBD5E1"))).pack(fill="x", padx=4)
                if len(items) > 2:
                    ctk.CTkLabel(cell, text=f"+{len(items) - 2} more", font=("Segoe UI", 10), height=14, anchor="w",
                                 text_color=("#64748B", "#94A3B8")).pack(fill="x", padx=4)
                if inm:
                    for w in [cell] + list(cell.winfo_children()):
                        w.bind("<Button-1>", lambda _e=None, d=d: self.rec_cal_pick(d))
                    self.rec_cal_cells[d] = cell
        legend = ctk.CTkFrame(body, fg_color="transparent"); legend.pack(fill="x", pady=(6, 0))
        for kind, word in (("due", "Due"), ("questions", "Questions due"), ("stage", "Stages"), ("task", "Tasks due"),
                           ("done", "Tasks done"), ("event", "What happened")):
            ctk.CTkLabel(legend, text="■ " + word, font=("Segoe UI", 11), text_color=self.CAL_COLORS[kind]).pack(side="left", padx=(0, 12))
        d = self.rec_cal_day
        if d is not None:
            box = ctk.CTkFrame(body, fg_color=("#F1F5F9", "#0F172A"), corner_radius=8); box.pack(fill="x", pady=(8, 0))
            ctk.CTkLabel(box, text=d.strftime("%A, %B %d, %Y").replace(" 0", " "), font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=(6, 2))
            for kind, text in days.get(d, []) or [("event", "Nothing on this day.")]:
                ctk.CTkLabel(box, text=text, anchor="w", justify="left", wraplength=900,
                             text_color=self.CAL_COLORS.get(kind, ("#334155", "#CBD5E1"))).pack(fill="x", padx=16)
            ctk.CTkButton(box, text="+ Task due this day", width=10, height=26,
                          command=lambda: self.rec_task_dialog(due=d.isoformat())).pack(anchor="w", padx=10, pady=6)

    def rec_cal_pick(self, d):
        self.rec_cal_day = None if d == self.rec_cal_day else d
        self._rec_force()
        return self.rec_cal_day

    def _rec_draw_timeline(self, r):
        _h, _lab, body = self.rec_cards["timeline"]
        for e in r.events(limit=12):
            self._rec_event_row(body, e)
        if not r.data["timeline"]:
            ctk.CTkLabel(body, text="Nothing yet: documents added, stage moves, notes and assignments show here.", anchor="w").pack(fill="x")

    def _rec_event_row(self, body, e, wrap=470):
        line = ctk.CTkFrame(body, fg_color="transparent"); line.pack(fill="x", pady=1)
        ctk.CTkLabel(line, text=R.short_date(e["at"]), width=56, anchor="w", text_color=("#64748B", "#94A3B8")).pack(side="left", anchor="n")
        ctk.CTkLabel(line, text=KIND_WORDS.get(e["kind"], e["kind"].upper()), width=104, anchor="w", font=("Segoe UI", 11, "bold"),
                     text_color=KIND_COLORS.get(e["kind"], "#334155")).pack(side="left", anchor="n")
        lab = ctk.CTkLabel(line, text=e["text"] + (f"  ({e['who']})" if e.get("who") else ""), anchor="w", justify="left",
                           wraplength=min(wrap, 300))
        lab.pack(side="left", fill="x", expand=True)
        self._autowrap(lab, line, pad=170)

    def rec_timeline_window(self, kinds=None):
        r = self.effrec()
        if r is None:
            return None
        w = ctk.CTkToplevel(self); w.title("Timeline"); w.transient(self); w.geometry("980x700")
        top = ctk.CTkFrame(w, fg_color="transparent"); top.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(top, text=f"{self.effort.name}: everything that happened, newest first", font=("Segoe UI", 16, "bold")).pack(side="left")
        f = ctk.CTkScrollableFrame(w); f.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        evs = r.events(kinds=kinds)
        for e in evs:
            self._rec_event_row(f, e, wrap=760)
        w._api = {"events": evs}
        w.after(100, w.lift)
        return w

    # ------------------------------------------------------------ stages
    def rec_move_dialog(self, to=None, carry=None, planned=None):
        """The proposal manager moves the stage. to/carry (tests): move at once."""
        r = self.effrec()
        if r is None:
            return None
        cur = r.stage()
        checks = self.rec_checks()
        open_goals = [g for g in cur["goals"] if not r.goal_done(g, checks)]
        if to is not None:
            try:
                ok = r.move_to(to, carry=[g["id"] for g in open_goals] if carry is None else carry, planned=planned, checks=checks)
            except R.GateClosed as e:                          # 2.63.0: a hard gate set in Stationkeeper (Qt)
                self.status.configure(text=str(e))
                return False
            if ok:
                diag.activity("stage_moved")
                self._rec_force(); self.shell_overview_refresh() if hasattr(self, "shell_overview_refresh") else None
            return ok
        w = ctk.CTkToplevel(self); w.title("Move stage"); w.transient(self); w.geometry("760x560")
        names = [s["name"] for s in r.stages]
        nxt = min(r.index() + 1, len(names) - 1)
        ctk.CTkLabel(w, text=f"{self.effort.name} is in {cur['name']}.", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        row = ctk.CTkFrame(w, fg_color="transparent"); row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(row, text="Move to").pack(side="left")
        om = ctk.CTkOptionMenu(row, values=[n for n in names if n != cur["name"]] or [""], width=240)
        om.set(names[nxt] if names[nxt] != cur["name"] else (names[0] if names[0] != cur["name"] else ""))
        om.pack(side="left", padx=8)
        ctk.CTkLabel(row, text="Review date").pack(side="left", padx=(12, 0))
        pe = ctk.CTkEntry(row, width=140, placeholder_text="2026-11-30"); pe.pack(side="left", padx=8)
        n, total = r.goal_progress(checks=checks)
        ctk.CTkLabel(w, text=f"Leaving {cur['name']}: {n} of {total} goals met." + (" Tick the open ones to carry over:" if open_goals else ""),
                     anchor="w").pack(fill="x", padx=16, pady=(8, 2))
        box = ctk.CTkScrollableFrame(w, height=220); box.pack(fill="both", expand=True, padx=16)
        vars_ = []
        for g in open_goals:
            v = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(box, text=g["text"], variable=v).pack(anchor="w", pady=2)
            vars_.append((g["id"], v))
        ctk.CTkLabel(w, text="Only the proposal manager moves the stage. Effort home and the gate goals follow; the timeline records who and when.",
                     anchor="w", justify="left", wraplength=700, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16, pady=8)

        def ok():
            target = next((s for s in r.stages if s["name"] == om.get()), None)
            if target is None:
                return False
            try:
                done = r.move_to(target["id"], carry=[gid for gid, v in vars_ if v.get()], planned=pe.get() or None, checks=checks)
            except R.GateClosed as e:                          # 2.63.0: the proposal manager may override with a reason
                from tkinter import simpledialog
                why = simpledialog.askstring("Hard gate", f"{e}\n\nReason to override the gate (kept in the timeline):", parent=w)
                if not why:
                    return False
                done = r.move_to(target["id"], carry=[gid for gid, v in vars_ if v.get()], planned=pe.get() or None, reason=why,
                                 checks=checks)
            if done:
                diag.activity("stage_moved")
                w.destroy()
                self._rec_force()
            return done
        ctk.CTkButton(w, text="Move", command=ok, fg_color="#1E3A8A").pack(side="right", padx=16, pady=12)
        w._api = {"to": om, "planned": pe, "carry": vars_, "ok": ok}
        w.after(100, w.lift)
        return w

    def rec_stages_dialog(self, rows=None):
        """Rename, add, remove and reorder the stages, each with a planned date. rows (tests): save at once."""
        r = self.effrec()
        if r is None:
            return None
        if rows is not None:
            try:
                r.edit_stages(rows)
            except ValueError as e:
                messagebox.showwarning("Edit stages", str(e))
                return False
            diag.activity("stages_edited", n=len(r.stages))
            self._rec_force()
            return True
        w = ctk.CTkToplevel(self); w.title("Edit stages"); w.transient(self); w.geometry("900x620")
        ctk.CTkLabel(w, text="Stages for this effort", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(w, text="Rename, add, remove or reorder; a planned start and end for each (Pick opens a calendar). New stages "
                             "get the team's default goals when the name matches one. The stage moves only when you move it.",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16)
        box = ctk.CTkScrollableFrame(w); box.pack(fill="both", expand=True, padx=16, pady=8)
        items = [[s["id"], s["name"], s["planned"], s.get("planned_end", "")] for s in r.stages]
        import datepick as DP
        widgets = []

        def draw():
            for x in box.winfo_children():
                x.destroy()
            widgets.clear()
            for i, it in enumerate(items):
                line = ctk.CTkFrame(box, fg_color="transparent"); line.pack(fill="x", pady=2)
                ne = ctk.CTkEntry(line, width=200); ne.insert(0, it[1]); ne.pack(side="left")
                pe = DP.DateField(line, it[2], width=110, placeholder="start"); pe.pack(side="left", padx=(6, 2))
                ee = DP.DateField(line, it[3], width=110, placeholder="end"); ee.pack(side="left", padx=(2, 6))
                ctk.CTkButton(line, text="Up", width=44, command=lambda i=i: move(i, -1)).pack(side="left", padx=2)
                ctk.CTkButton(line, text="Down", width=54, command=lambda i=i: move(i, 1)).pack(side="left", padx=2)
                cur = it[0] == r.data["stage"]
                ctk.CTkButton(line, text="Remove", width=70, fg_color="#B91C1C", state="disabled" if cur else "normal",
                              command=lambda i=i: remove(i)).pack(side="left", padx=2)
                if cur:
                    ctk.CTkLabel(line, text="current", text_color=("#1E3A8A", "#BFDBFE")).pack(side="left", padx=4)
                widgets.append((ne, pe, ee))

        def sync():
            for it, (ne, pe, ee) in zip(items, widgets):
                it[1], it[2], it[3] = ne.get(), pe.get(), ee.get()

        def move(i, d):
            sync()
            j = i + d
            if 0 <= j < len(items):
                items[i], items[j] = items[j], items[i]
                draw()

        def remove(i):
            sync(); items.pop(i); draw()

        def add():
            sync(); items.append([None, "New stage", "", ""]); draw()

        def ok():
            sync()
            if self.rec_stages_dialog(rows=[tuple(it) for it in items]):
                w.destroy()
                return True
            return False
        draw()
        b = ctk.CTkFrame(w, fg_color="transparent"); b.pack(fill="x", padx=16, pady=10)
        ctk.CTkButton(b, text="+ Add a stage", command=add, fg_color="#475569").pack(side="left")
        ctk.CTkButton(b, text="Save", command=ok, fg_color="#1E3A8A").pack(side="right")
        w._api = {"items": items, "add": add, "move": move, "remove": remove, "ok": ok, "widgets": widgets}
        w.after(100, w.lift)
        return w

    def rec_add_goal_dialog(self, text=None, auto=""):
        r = self.effrec()
        if r is None:
            return None
        if text is None and not auto:
            w = ctk.CTkToplevel(self); w.title("Add a goal"); w.transient(self); w.geometry("620x260")
            ctk.CTkLabel(w, text=f"A goal for {r.stage()['name']}", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 4))
            e = ctk.CTkEntry(w, width=560, placeholder_text="Write a goal, or pick one the app checks"); e.pack(padx=16)
            labels = ["(written goal)"] + list(R.AUTO.values())
            om = ctk.CTkOptionMenu(w, values=labels, width=560); om.pack(padx=16, pady=8)

            def ok():
                key = next((k for k, v in R.AUTO.items() if v == om.get()), "")
                if r.add_goal(r.data["stage"], e.get(), auto=key):
                    w.destroy(); self._rec_force()
            ctk.CTkButton(w, text="Add", command=ok).pack(side="right", padx=16, pady=10)
            w._api = {"text": e, "auto": om, "ok": ok}
            return w
        gid = r.add_goal(r.data["stage"], text or "", auto=auto)
        self._rec_force()
        return gid

    def rec_goal_edit(self, sid, gid, text=None):
        r = self.effrec()
        if r is None:
            return False
        if text is None:
            from tkinter import simpledialog
            s = r.stage(sid); g = next((x for x in s["goals"] if x["id"] == gid), None) if s else None
            if g is None:
                return False
            text = simpledialog.askstring("Edit goal", "The goal:", initialvalue=g["text"], parent=self)
            if text is None:
                return False
        ok = r.edit_goal(sid, gid, text)
        self._rec_force()
        return ok

    def rec_goal_remove(self, sid, gid, confirm=True):
        r = self.effrec()
        if r is None or (confirm and not messagebox.askyesno("Remove goal", "Remove this goal from the stage?", parent=self)):
            return False
        s = r.stage(sid)
        g = next((x for x in s["goals"] if x["id"] == gid), None) if s else None
        ok = r.remove_goal(sid, gid)
        if ok:
            r.log("stage", f"Goal removed from {s['name']}: {g['text']}", save=True)
        self._rec_force()
        return ok

    def rec_note_remove(self, nid, confirm=True):
        r = self.effrec()
        if r is None or (confirm and not messagebox.askyesno("Remove", "Remove this note or question?", parent=self)):
            return False
        ok = r.remove_note(nid)
        self._rec_force()
        return ok

    def rec_note_edit_dialog(self, nid, focus="text", values=None):
        """Edit a note or question: its words, note or question, and who it is assigned to."""
        r = self.effrec()
        n = next((x for x in r.data["notes"] if x["id"] == nid), None) if r is not None else None
        if n is None:
            return None
        if values is not None:
            ok = r.update_note(nid, **values)
            if ok and values.get("assignee"):
                diag.activity("question_assigned")
            self._rec_force()
            return ok
        w = ctk.CTkToplevel(self); w.title("Edit note or question"); w.transient(self); w.geometry("640x400")
        tb = ctk.CTkTextbox(w, height=150); tb.pack(fill="both", expand=True, padx=16, pady=(14, 8)); tb.insert("1.0", n["text"])
        qv = tk.BooleanVar(value=n["question"])
        ctk.CTkCheckBox(w, text="Open question (stays open until resolved)", variable=qv).pack(anchor="w", padx=16)
        row = ctk.CTkFrame(w, fg_color="transparent"); row.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(row, text="Assigned to").pack(side="left")
        people = ["(nobody)"] + sorted(set(self.rec_people()) | ({n["assignee"]} if n.get("assignee") else set()), key=str.casefold)
        cb = ctk.CTkComboBox(row, values=people, width=300); cb.set(n.get("assignee") or "(nobody)"); cb.pack(side="left", padx=8)
        ctk.CTkLabel(w, text="Pick a person or type a name.", anchor="w", text_color=("#64748B", "#94A3B8")).pack(fill="x", padx=16)

        def ok():
            who = cb.get().strip()
            vals = {"text": tb.get("1.0", "end"), "question": qv.get(), "assignee": "" if who == "(nobody)" else who}
            if r.update_note(nid, **vals) and vals["assignee"]:
                diag.activity("question_assigned")
            w.destroy(); self._rec_force()
        ctk.CTkButton(w, text="Save", command=ok, fg_color="#1E3A8A").pack(side="right", padx=16, pady=10)
        w._api = {"text": tb, "question": qv, "assignee": cb, "ok": ok}
        w.after(100, w.lift); w.after(150, (cb if focus == "assignee" else tb).focus_set)
        return w

    # ------------------------------------------------------------ notes
    def rec_note_dialog(self, on="effort", on_id="", label="", text=None, question=False):
        """A note or an open question on the effort, a stage, a document version, a requirement, a task..."""
        r = self.effrec()
        if r is None:
            messagebox.showinfo("Note", "Open an effort first.")
            return None
        if text is not None:
            nid = r.add_note(text, on=on, on_id=on_id, label=label, question=question)
            if nid:
                diag.activity("note_added")
                self._rec_force()
            return nid
        w = ctk.CTkToplevel(self); w.title("Note"); w.transient(self); w.geometry("640x380")
        about = {"effort": [("effort", "", "The effort")], "stage": []}
        choices = [("effort", "", "The effort"), ("stage", r.data["stage"], f"Stage: {r.stage()['name']}")]
        if on not in ("effort", "stage") or label:
            choices.insert(0, (on, on_id, label or on))
        ctk.CTkLabel(w, text="About", anchor="w").pack(fill="x", padx=16, pady=(14, 0))
        om = ctk.CTkOptionMenu(w, values=[c[2] for c in choices], width=420); om.set(choices[0][2]); om.pack(anchor="w", padx=16)
        tb = ctk.CTkTextbox(w, height=150); tb.pack(fill="both", expand=True, padx=16, pady=8)
        qv = tk.BooleanVar(value=question)
        ctk.CTkCheckBox(w, text="Open question (stays open until resolved)", variable=qv).pack(anchor="w", padx=16)

        def ok():
            c = next(x for x in choices if x[2] == om.get())
            label_ = "" if c[0] == "effort" else c[2].replace("Stage: ", "")
            if r.add_note(tb.get("1.0", "end"), on=c[0], on_id=c[1], label=label_, question=qv.get()):
                diag.activity("note_added")
                w.destroy(); self._rec_force()
                self._rec_after_note() if hasattr(self, "_rec_after_note") else None
        ctk.CTkButton(w, text="Save", command=ok, fg_color="#1E3A8A").pack(side="right", padx=16, pady=10)
        w._api = {"about": om, "text": tb, "question": qv, "ok": ok}
        w.after(100, w.lift); w.after(150, tb.focus_set)
        return w

    def rec_resolve_dialog(self, nid, answer=None):
        r = self.effrec()
        if r is None:
            return False
        if answer is None:
            from tkinter import simpledialog
            answer = simpledialog.askstring("Resolve", "The answer (optional):", parent=self)
            if answer is None:
                return False
        ok = r.resolve_note(nid, answer)
        self._rec_force()
        return ok

    # ------------------------------------------------------------ tasks
    def rec_task_dialog(self, tid=None, values=None, due=""):
        """Add or edit a task: title, owner, due date, stage, status, about, notes. values (tests): save at once."""
        r = self.effrec()
        if r is None:
            messagebox.showinfo("Task", "Open an effort first.")
            return None
        t = r.task(tid) if tid else None
        stage_names = [s["name"] for s in r.stages]

        def save(v):
            sid = next((s["id"] for s in r.stages if s["name"] == v.get("stage")), r.data["stage"])
            if t is None:
                new = r.add_task(v.get("title", ""), owner=v.get("owner", ""), due=v.get("due", ""), stage=sid,
                                 about=v.get("about", ""), notes=v.get("notes", ""))
                if new and v.get("status") and v["status"] != "Not started":
                    r.update_task(new, status=v["status"])
                res = new
            else:
                r.update_task(t["id"], title=v.get("title", t["title"]), owner=v.get("owner", t["owner"]), due=v.get("due", t["due"]),
                              stage=sid, about=v.get("about", t["about"]), notes=v.get("notes", t["notes"]), status=v.get("status", t["status"]))
                res = t["id"]
            diag.activity("task_saved")
            self._rec_force()
            return res

        if values is not None:
            return save(values)
        w = ctk.CTkToplevel(self); w.title("Task" if t else "New task"); w.transient(self); w.geometry("640x520")
        ents = {}
        people = self.rec_people()
        import datepick as DP
        for i, (k, lab, hint) in enumerate((("title", "Task", "Cut Vol I to 25 pages"), ("owner", "Owner", ", ".join(people[:3]) or "a name"),
                                             ("due", "Due date", "2026-10-30"), ("about", "About (a section, document or deliverable)", ""))):
            ctk.CTkLabel(w, text=lab, anchor="w").grid(row=i, column=0, sticky="w", padx=14, pady=(12 if i == 0 else 4, 0))
            if k == "owner":                                   # 2.52.0: the team in a drop-down
                e = ctk.CTkComboBox(w, width=380, values=people or [""])
                e.set(t[k] if t else "")
            elif k == "due":                                   # 2.52.0: a calendar
                e = DP.DateField(w, (t[k] if t else due) or "", width=150)
            else:
                e = ctk.CTkEntry(w, width=380, placeholder_text=hint)
                if t:
                    e.insert(0, t[k])
            e.grid(row=i, column=1, sticky="w", padx=8, pady=(12 if i == 0 else 4, 0))
            ents[k] = e
        ctk.CTkLabel(w, text="Stage", anchor="w").grid(row=4, column=0, sticky="w", padx=14, pady=4)
        so = ctk.CTkOptionMenu(w, values=stage_names, width=240)
        so.set(next((s["name"] for s in r.stages if s["id"] == (t["stage"] if t else r.data["stage"])), stage_names[0]))
        so.grid(row=4, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkLabel(w, text="Status", anchor="w").grid(row=5, column=0, sticky="w", padx=14, pady=4)
        st = ctk.CTkOptionMenu(w, values=list(R.TASK_STATUS), width=240); st.set(t["status"] if t else "Not started")
        st.grid(row=5, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkLabel(w, text="Notes", anchor="w").grid(row=6, column=0, sticky="nw", padx=14, pady=4)
        nb = ctk.CTkTextbox(w, width=380, height=110); nb.grid(row=6, column=1, sticky="w", padx=8, pady=4)
        if t:
            nb.insert("1.0", t["notes"])

        def ok():
            if save({**{k: e.get() for k, e in ents.items()}, "stage": so.get(), "status": st.get(), "notes": nb.get("1.0", "end")}):
                w.destroy()
        bb = ctk.CTkFrame(w, fg_color="transparent"); bb.grid(row=7, column=0, columnspan=2, sticky="ew", padx=14, pady=12)
        if t:
            def rm():
                r.remove_task(t["id"]); w.destroy(); self._rec_force()
            ctk.CTkButton(bb, text="Remove", fg_color="#B91C1C", command=rm).pack(side="left")
        ctk.CTkButton(bb, text="Save", command=ok, fg_color="#1E3A8A").pack(side="right")
        w._api = {"entries": ents, "stage": so, "status": st, "notes": nb, "ok": ok}
        w.after(100, w.lift)
        return w

    # ------------------------------------------------------------ effort package (save and import)
    def pkg_save_dialog(self, path=None, customer=True, volumes=True):
        """File > Save effort package...: the whole effort in one .skpkg file for a hand-off."""
        import effortpkg as P, workspace as W
        L, ws = getattr(self, "effort", None), getattr(self, "ws", None)
        if L is None or ws is None:
            messagebox.showinfo("Save effort package", "Open an effort first.")
            return None
        info = dict(self.efforts.get(L.name) or {})
        try:                                                    # what is on screen goes in the package
            if L.pending:
                self._save_effort_list()
            M = getattr(self, "matrix", None)
            if M is not None and getattr(M, "pending", False) and hasattr(self, "_c_save_now"):
                self._c_save_now()
        except Exception:
            diag.swallowed()
        r = self.effrec()
        stage = r.stage()["name"] if r else ""
        mpath = ws.get("compliance_path", "") or ""
        if path is None:
            from tkinter import filedialog
            w = ctk.CTkToplevel(self); w.title("Save effort package"); w.transient(self); w.geometry("620x320")
            ctk.CTkLabel(w, text="Save effort package", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
            ctk.CTkLabel(w, text="One file with the effort as it is now: stage, goals, notes, tasks, timeline, customer document "
                                 "versions, submission requirements, the compliance matrix and the acronym list. Someone else "
                                 "opens it with File > Import effort package... and continues where you are.", anchor="w",
                         justify="left", wraplength=580).pack(fill="x", padx=16)
            cv, vv = tk.BooleanVar(value=customer), tk.BooleanVar(value=volumes)
            _items, size_c = P.plan(L.path, ws.root, mpath, info.get("customer_dir", ""), "", True, False)
            _items, size_0 = P.plan(L.path, ws.root, mpath, "", "", False, False)
            _items, size_v = P.plan(L.path, ws.root, "", "", info.get("volumes_dir", ""), False, True)
            mb = lambda b: f"{b / 1e6:.1f} MB"
            ctk.CTkCheckBox(w, text=f"Include the customer files themselves ({mb(size_c - size_0)})", variable=cv).pack(anchor="w", padx=16, pady=(12, 2))
            ctk.CTkCheckBox(w, text=f"Include our Word volumes ({mb(max(0, size_v - size_0 + 0))})", variable=vv).pack(anchor="w", padx=16, pady=2)
            ctk.CTkLabel(w, text="Save it on this PC or in the approved SharePoint folder only.", anchor="w",
                         text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16, pady=(10, 0))

            def ok():
                stamp = datetime.date.today().isoformat()
                fname = "_".join(x for x in (L.name, stage, stamp) if x).replace(" ", "_") + P.EXT
                folder = os.path.dirname(info.get("customer_dir", "") or L.path)
                p = filedialog.asksaveasfilename(parent=w, title="Save effort package", defaultextension=P.EXT, initialfile=fname,
                                                 initialdir=folder, filetypes=[("Stationkeeper effort package", " ".join("*" + e for e in P.EXTS))])
                if p:
                    w.destroy()
                    self.pkg_save_dialog(path=p, customer=cv.get(), volumes=vv.get())
            ctk.CTkButton(w, text="Save...", command=ok, fg_color="#0F766E").pack(side="right", padx=16, pady=14)
            w._api = {"customer": cv, "volumes": vv, "ok": ok}
            w.after(100, w.lift)
            return w
        try:
            man = P.save(path, L.name, L.path, ws.root, info={**info, "name": L.name, "client": L.client, "solicitation": L.solicitation,
                                                             "internal_no": L.internal_no, "first_use": L.first_use},
                         matrix_path=mpath, customer_dir=info.get("customer_dir", ""), volumes_dir=info.get("volumes_dir", ""),
                         customer=customer, volumes=volumes, stage=stage, app_version=getattr(__import__("app_gui"), "APP_VERSION", ""),
                         extra_files=[dl.get("file") for dl in (r.data.get("deliverables", []) if r else []) if dl.get("file")],
                         readable_dir=(self.readable_write_now() or "") if hasattr(self, "readable_write_now") else "")
        except (OSError, PermissionError) as e:
            diag.swallowed()
            messagebox.showerror("Save effort package", f"The package could not be written ({type(e).__name__}).")
            return None
        self.rec_log("effort", f"Effort package saved: {os.path.basename(man['path'])} ({stage}, {len(man['files'])} files)")
        diag.activity("package_saved", files=len(man["files"]))
        self.status.configure(text=f"Effort package saved: {os.path.basename(man['path'])}")
        return man

    def pkg_efforts(self):
        """The efforts that can be saved: not archived, their list on this PC."""
        out = []
        for n in self.efforts.names():
            inf = self.efforts.get(n) or {}
            if not inf.get("archived") and inf.get("path") and os.path.isfile(inf["path"]):
                out.append(n)
        return out

    def pkg_save_all(self, folder=None, customer=True, volumes=True):
        """File > Save all efforts (2.52.0): one effort package per effort, in one folder: everything to carry to a new
        PC or a new version of Stationkeeper. Returns the paths written."""
        import effortpkg as P, workspace as W
        names = self.pkg_efforts()
        if not names:
            messagebox.showinfo("Save all efforts", "No efforts to save.")
            return []
        if folder is None:
            from tkinter import filedialog
            folder = filedialog.askdirectory(title="Folder for the effort packages (one file per effort)")
            if not folder:
                return []
        stamp = datetime.date.today().isoformat()
        out, failed = [], []
        app_v = getattr(__import__("app_gui"), "APP_VERSION", "")
        for n in names:
            inf = dict(self.efforts.get(n) or {})
            p = os.path.join(folder, f"{n.replace(' ', '_')}_{stamp}{P.EXT}")
            try:
                if self.effort is not None and self.effort.name == n:
                    man = self.pkg_save_dialog(path=p, customer=customer, volumes=volumes)
                else:
                    dd = W.data_dir_for(inf["path"])
                    st = W.read_json(os.path.join(dd, "settings.json"), None) or {}
                    rec = W.read_json(os.path.join(dd, "record.json"), None) or {}
                    stg = next((x.get("name", "") for x in rec.get("stages", []) if x.get("id") == rec.get("stage")), "")
                    man = P.save(p, n, inf["path"], dd, info={**inf, "name": n}, matrix_path=st.get("compliance_path", "") or "",
                                 customer_dir=inf.get("customer_dir", ""), volumes_dir=inf.get("volumes_dir", ""), customer=customer,
                                 volumes=volumes, stage=stg, app_version=app_v,
                                 extra_files=[dl.get("file") for dl in rec.get("deliverables", []) if dl.get("file")])
                if man:
                    out.append(man["path"])
            except Exception:
                diag.swallowed()
                failed.append(n)
        diag.activity("packages_saved_all", files=len(out), errors=len(failed))
        messagebox.showinfo("Save all efforts", f"{len(out)} effort package(s) saved in {folder}."
                            + (f"\n\nNot saved: {', '.join(failed)}" if failed else "")
                            + "\n\nOn a new PC or a new version: File > Import effort package... for each one.")
        return out

    def pkg_import_dialog(self, path=None, dest=None, mode=None):
        """File > Import effort package...: open a package someone handed over and continue where it was.
        mode when the effort already exists on this PC: "replace" (this PC's saved work is backed up first) or "both"."""
        import effortpkg as P, workspace as W
        from tkinter import filedialog
        if path is None:
            path = filedialog.askopenfilename(title="Import effort package", filetypes=[("Stationkeeper effort package", " ".join("*" + e for e in P.EXTS))])
            if not path:
                return None
        try:
            man = P.read_manifest(path)
        except P.PackageError as e:
            messagebox.showerror("Import effort package", str(e))
            return None
        name = man.get("effort") or "Effort"
        desc = (f"{name}\nSaved by {man.get('saved_by', '?')} on {man.get('saved_at', '').replace('T', ' ')}"
                + (f"\nStage: {man['stage']}" if man.get("stage") else "") + f"\n{len(man.get('files', {}))} files")
        exists = name in self.efforts.names()
        if mode is None and exists:
            ans = messagebox.askyesnocancel("Import effort package", desc + f"\n\n'{name}' is already on this PC.\n\n"
                                            "Yes: use the package (this PC's copy is backed up first).\nNo: keep both (the package "
                                            "opens as a second effort).")
            if ans is None:
                return None
            mode = "replace" if ans else "both"
        elif mode is None and dest is None and not messagebox.askyesno("Import effort package", desc + "\n\nImport it?"):
            return None
        new_name = name
        if exists and mode == "both":
            base = f"{name} (from {man.get('saved_by', 'package')})"
            new_name, k = base, 2
            while new_name in self.efforts.names():
                new_name, k = f"{base} {k}", k + 1
        if dest is None:
            dest = filedialog.askdirectory(title="Where should the effort's files go?")
            if not dest:
                return None
        folder = os.path.join(dest, new_name)
        if exists and mode == "replace":
            old = self.efforts.get(name) or {}
            try:
                if self.effort is not None and self.effort.name == name:
                    self.leave_workspace() if hasattr(self, "leave_workspace") else None
                    self.effort = None
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                od = W.data_dir_for(old.get("path", "")) if old.get("path") else ""
                if od and os.path.isdir(od):
                    P.backup_folder(od, os.path.join(os.path.dirname(od), f"{name} - before import {stamp}.zip"))
            except Exception:
                diag.swallowed()
        try:
            got = P.unpack(path, folder, W.data_dir_for)
        except (P.PackageError, OSError) as e:
            diag.swallowed()
            messagebox.showerror("Import effort package", str(e) if isinstance(e, P.PackageError) else f"The package could not be unpacked ({type(e).__name__}).")
            return None
        P.repoint(got["data"], got["customer_dir"], got["matrix"], got.get("moved"))
        inf = man.get("info", {})
        put = {k: inf.get(k) for k in ("first_use", "client", "solicitation", "internal_no", "list_format") if inf.get(k) is not None}
        self.efforts.put(new_name, path=got["list"], customer_dir=got["customer_dir"] or os.path.join(folder, "Customer documents"),
                         volumes_dir=got["volumes_dir"] or "", **put)
        os.makedirs(os.path.join(folder, "Customer documents"), exist_ok=True)
        diag.activity("package_imported", files=len(man.get("files", {})))
        if not self.open_effort(new_name):
            return got
        if self.effort is not None and self.effort.name != new_name:      # keep both: the list says its new name too
            try:
                self.effort.name = new_name
                self.effort.pending = True
                self._save_effort_list()
            except Exception:
                diag.swallowed()
        self.rec_log("effort", f"Effort package imported: saved by {man.get('saved_by', '?')} on {man.get('saved_at', '').replace('T', ' ')}"
                               + (f" at {man['stage']}" if man.get("stage") else ""))
        if hasattr(self, "shell_go"):
            self.shell_go("home")
        got["name"] = new_name
        return got

    # ------------------------------------------------------------ effort status report (2.40.0)
    def _es_state(self):
        """2.63.0: the open effort as effortstate sees it, from what this window holds."""
        import effortstate as ES
        reg = self.subreg() if hasattr(self, "subreg") else None
        return ES.State(self.ws, getattr(self.effort, "path", ""), getattr(self, "matrix", None), rec=self.effrec(),
                        lib=self.doclib() if hasattr(self, "doclib") else None, rows=reg.rows() if reg is not None else [],
                        L=self.effort, report=getattr(self, "volume_report", None),
                        volumes=self.volumes() if hasattr(self, "volumes") else [])

    def status_snapshot(self, final=False):
        """Everything the status report shows (2.63.0: effortstate.status_snapshot, shared with the Qt edition)."""
        import effortstate as ES
        return ES.status_snapshot(self._es_state(), final=final, app_version=getattr(__import__("app_gui"), "APP_VERSION", ""))

    def status_calendar(self, most=3):
        """2.49.0: months for the status report: this month through the due month (at most `most`)."""
        import effortstate as ES
        return ES.status_calendar(self._es_state(), most)

    def status_export(self, path=None, final=False):
        """File > Effort status (Word)...: where the effort stands, for leadership. final: the effort summary with the
        complete history."""
        import statusdoc as SDOC
        L = getattr(self, "effort", None)
        if L is None or self.effrec() is None:
            messagebox.showinfo("Effort status", "Open an effort first.")
            return None
        if path is None:
            from tkinter import filedialog
            r = self.effrec()
            kind = "Effort_Summary" if final else "Effort_Status"
            fname = f"{L.name}_{kind}_{datetime.date.today().isoformat()}.docx".replace(" ", "_")
            path = filedialog.asksaveasfilename(parent=self, title="Save the effort summary" if final else "Save the effort status",
                                                defaultextension=".docx", initialfile=fname,
                                                initialdir=os.path.dirname(L.path), filetypes=[("Word", "*.docx")])
            if not path:
                return None
        try:
            SDOC.build(self.status_snapshot(final=final), path, final=final)
        except PermissionError:
            messagebox.showerror("Effort status", "That file is open in Word. Close it, then save again.")
            return None
        diag.activity("status_exported", n=1 if final else 0)
        self.rec_log("effort", ("Effort summary" if final else "Effort status") + f" exported: {os.path.basename(path)}")
        self.status.configure(text=("Effort summary" if final else "Effort status") + " written.")
        return path

    def pkg_associate(self, confirm=True):
        """Advanced (2.41.0): double-clicking an effort package (.skpkg, or .ahpkg from before 2.44.0) opens it in this copy of Stationkeeper. Written for this
        Windows user only (HKEY_CURRENT_USER\\Software\\Classes): no admin rights, nothing for other users or the system."""
        import sys
        if os.name != "nt" or not getattr(sys, "frozen", False):
            messagebox.showinfo("Effort packages", "This works in the installed program on Windows. Use File > Import effort package... here.")
            return False
        exe = os.path.abspath(sys.executable)
        if confirm and not messagebox.askyesno("Effort packages", "Make effort packages (.skpkg, and .ahpkg from Acronym Hunter) and Knowledge Packs (.skknow) open in Stationkeeper when you double-click "
                                               f"them?\n\nProgram: {exe}\n\nThis is set for your Windows user only. If you move the "
                                               "Stationkeeper folder, do this again."):
            return False
        try:
            import winreg
            import effortpkg
            P_EXTS = effortpkg.EXTS
            base = r"Software\Classes"
            prog = "Stationkeeper.EffortPackage"
            for ext in P_EXTS:                       # 2.44.0: the new type and the old one both open here
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + ext) as k:
                    winreg.SetValueEx(k, "", 0, winreg.REG_SZ, prog)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + prog) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Stationkeeper effort package")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + prog + r"\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}",0')
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + prog + r"\shell\open\command") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}" "%1"')
            kprog = "Stationkeeper.KnowledgePack"         # 2.50.0: Knowledge Packs open the install card
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\.skknow") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, kprog)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + kprog) as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Stationkeeper Knowledge Pack")
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + kprog + r"\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}",0')
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + "\\" + kprog + r"\shell\open\command") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}" "%1"')
        except OSError as e:
            diag.swallowed()
            messagebox.showerror("Effort packages", f"Windows did not accept the setting ({type(e).__name__}). Use File > Import effort package... instead.")
            return False
        diag.activity("package_associated")
        messagebox.showinfo("Effort packages", "Done. Double-click an effort package (.skpkg or .ahpkg) to open it here, or a Knowledge Pack (.skknow) to see its install card.")
        return True
