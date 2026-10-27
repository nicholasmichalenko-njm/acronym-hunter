"""The effort record on screen (2.40.0): the countdown in the top bar, Effort details, and on Effort home the stage
track (Move stage..., Edit stages...), the gate goals, tasks, notes and open questions, and the timeline.

Everything is saved in the effort's record.json (effortrec.py) as it happens. The features log to the timeline through
rec_log(): customer document versions, requirement reviews, people and owners, QA/QC checks."""
import datetime, os
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import diag
import effortrec as R

STATE_COLORS = {"done": ("#DCFCE7", "#14532D"), "current": ("#1E3A8A", "#FFFFFF"), "ahead": ("#E2E8F0", "#334155")}
KIND_COLORS = {"customer": "#B45309", "ours": "#1E3A8A", "stage": "#0F766E", "note": "#7C3AED", "task": "#334155",
               "assign": "#0369A1", "requirement": "#B45309", "effort": "#0F766E", "qa": "#15803D", "compliance": "#1D4ED8"}
KIND_WORDS = {"customer": "CUSTOMER", "ours": "OURS", "stage": "STAGE", "note": "NOTE", "task": "TASK", "assign": "PEOPLE",
              "requirement": "REQUIREMENT", "effort": "EFFORT", "qa": "QA/QC", "compliance": "COMPLIANCE"}


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

    def rec_people(self):
        """Everyone named in the effort: section leads and contributors, requirement owners, task owners."""
        names = set()
        M = getattr(self, "matrix", None)
        if M is not None:
            try:
                import setupdoc as SD
                names.update(SD.people(M))
            except Exception:
                diag.swallowed()
        r = self.effrec()
        if r is not None:
            names.update(t["owner"] for t in r.data["tasks"] if t["owner"])
        return sorted(names, key=str.casefold)

    # ------------------------------------------------------------ what the app can check for the gate goals
    def rec_checks(self):
        c = {k: None for k in R.AUTO}
        try:
            lib = self.doclib() if hasattr(self, "doclib") else None
            if lib is not None:
                c["docs_added"] = bool(lib.docs)
                if lib.docs:
                    c["docs_reviewed"] = not lib.counts()["unreviewed"]
            reg = self.subreg() if hasattr(self, "subreg") else None
            rows = reg.rows() if reg is not None else []
            if rows:
                c["reqs_reviewed"] = not any(x["to_review"] for x in rows)
            M = getattr(self, "matrix", None)
            if M is not None and M.items:
                import setupdoc as SD
                cnt = M.counts()
                c["structure_set"] = bool(M.outline)
                c["reqs_placed"] = cnt["Keep"] > 0 and not cnt["needs_home"]
                keeps = [it for it in M.items if it["decision"] == "Keep"]
                c["reqs_owned"] = bool(keeps) and all(SD.owner_of(M, it) for it in keeps)
                tops = [o for o in M.outline if o.get("level", 1) <= 1] if M.outline else []
                if tops:
                    import compliance as C
                    c["sections_led"] = all(SD.section_people(M, C.outline_label(o))["lead"] for o in tops)
                if hasattr(self, "prove_items"):
                    try:
                        c["prove_clear"] = all(not self.prove_items(k) for k in ("unused", "nosection", "ctx", "noowner"))
                    except Exception:
                        diag.swallowed()
            L = getattr(self, "effort", None)
            if L is not None and L.rows:
                c["acr_approved"] = all(x["Status"] in ("Approved", "Rejected") for x in L.rows.values())
            rep = getattr(self, "volume_report", None)
            c["qa_run"] = bool(rep) or None
            if rep:
                s = rep.get("summary", {})
                c["first_use_clean"] = not s.get("first_use_problems")
                if s.get("banned_checked"):
                    c["banned_clean"] = not s.get("banned", {}).get("bad", 0)
                if rep.get("pages"):
                    c["pages_ok"] = not any(p["level"] == "bad" for p in rep["pages"])
            r = self.effrec()
            if r is not None:
                c["tasks_done"] = not r.tasks(stage=r.data["stage"], open_only=True)
        except Exception:
            diag.swallowed()
        return c

    # ------------------------------------------------------------ the countdown in the top bar
    def rec_strip_build(self, strip):
        self.strip_due = ctk.CTkLabel(strip, text="", font=("Segoe UI", 13, "bold"), corner_radius=8, fg_color="transparent",
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
            text = f"{R.countdown_text(r.data['due'])}  to {short}"
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
        w = ctk.CTkToplevel(self); w.title("Effort details"); w.transient(self); w.geometry("640x420")
        ents = {}
        for i, (k, lab, val, hint) in enumerate((("client", "Client", L.client, "USSF SSC"),
                                                  ("sol", "Solicitation or opportunity number", L.solicitation, "FA8810-26-R-0042"),
                                                  ("internal", "Internal number", L.internal_no, ""),
                                                  ("due", "Due date and time", due0, "December 15, 2026, 2:00 p.m. MT"))):
            ctk.CTkLabel(w, text=lab, anchor="w").grid(row=i, column=0, sticky="w", padx=14, pady=(14 if i == 0 else 6, 0))
            e = ctk.CTkEntry(w, width=360, placeholder_text=hint); e.insert(0, val or ""); e.grid(row=i, column=1, sticky="w", padx=8, pady=(14 if i == 0 else 6, 0))
            ents[k] = e
        found = self._rec_rfp_due()
        if found:
            def use():
                ents["due"].delete(0, "end"); ents["due"].insert(0, found)
            ctk.CTkLabel(w, text=f"The customer documents say: {found}", anchor="w", wraplength=560, justify="left",
                         text_color=("#475569", "#94A3B8")).grid(row=4, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 0))
            ctk.CTkButton(w, text="Use it", width=10, command=use).grid(row=5, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkLabel(w, text="The countdown uses this PC's clock; the time zone is shown as written.", anchor="w",
                     text_color=("#475569", "#94A3B8")).grid(row=6, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 0))

        def ok():
            if save({k: e.get() for k, e in ents.items()}):
                w.destroy()
        ctk.CTkButton(w, text="Save", command=ok, fg_color="#1E3A8A").grid(row=7, column=1, sticky="e", padx=14, pady=16)
        w._api = {"entries": ents, "ok": ok}
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
    def rec_build_home(self, P):
        bar = ctk.CTkFrame(P, fg_color="transparent"); bar.pack(fill="x", padx=6, pady=(0, 8))
        B = dict(width=10, height=32)
        ctk.CTkButton(bar, text="Effort details...", command=self.rec_details_dialog, fg_color="#475569", **B).pack(side="left", padx=(0, 6))
        if hasattr(self, "status_export"):
            ctk.CTkButton(bar, text="Effort status (Word)...", command=self.status_export, **B).pack(side="left", padx=6)
        if hasattr(self, "pkg_save_dialog"):
            ctk.CTkButton(bar, text="Save effort package...", command=self.pkg_save_dialog, fg_color="#0F766E", **B).pack(side="left", padx=6)
        self.rec_track = ctk.CTkFrame(P, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1, border_color=("#E2E8F0", "#334155"))
        self.rec_track.pack(fill="x", padx=6, pady=(0, 6))
        grid = ctk.CTkFrame(P, fg_color="transparent"); grid.pack(fill="x", padx=0)
        grid.grid_columnconfigure(0, weight=1, uniform="g"); grid.grid_columnconfigure(1, weight=1, uniform="g")
        cards = {}
        for key, title, col, row in (("goals", "Gate goals", 0, 0), ("tasks", "Tasks", 0, 1), ("notes", "Notes and open questions", 1, 0),
                                     ("timeline", "Timeline", 1, 1)):
            c = ctk.CTkFrame(grid, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1, border_color=("#E2E8F0", "#334155"))
            c.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            head = ctk.CTkFrame(c, fg_color="transparent"); head.pack(fill="x", padx=14, pady=(10, 4))
            lab = ctk.CTkLabel(head, text=title, font=("Segoe UI", 15, "bold"), anchor="w"); lab.pack(side="left")
            body = ctk.CTkFrame(c, fg_color="transparent"); body.pack(fill="x", padx=12, pady=(0, 10))
            cards[key] = (head, lab, body)
        S = dict(width=10, height=28)
        ctk.CTkButton(cards["goals"][0], text="+ Goal", command=self.rec_add_goal_dialog, **S).pack(side="right")
        ctk.CTkButton(cards["tasks"][0], text="+ Task", command=self.rec_task_dialog, **S).pack(side="right")
        self.rec_who = ctk.CTkOptionMenu(cards["tasks"][0], values=["Everyone"], width=150, command=lambda _v: self._rec_force())
        self.rec_who.pack(side="right", padx=6)
        ctk.CTkButton(cards["notes"][0], text="+ Note", command=self.rec_note_dialog, **S).pack(side="right")
        ctk.CTkButton(cards["timeline"][0], text="Full timeline...", command=self.rec_timeline_window, fg_color="#475569", **S).pack(side="right")
        self.rec_cards = cards
        self._rec_sig = None

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
               repr(r.data["notes"]) if r else "", tuple(sorted(checks.items())), self.rec_who.get(), tuple(people))
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
        ref.bind("<Configure>", fit, add="+")

    def _rec_draw_track(self, r):
        t = self.rec_track
        row = ctk.CTkFrame(t, fg_color="transparent"); row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(row, text="STAGE", font=("Segoe UI", 10, "bold"), text_color=("#64748B", "#94A3B8")).pack(side="left", padx=(2, 8))
        pills = ctk.CTkFrame(t, fg_color="transparent"); pills.pack(fill="x", padx=12, pady=(0, 10))
        n = max(1, len(r.stages))
        for i, s in enumerate(r.stages):                # one even row that shrinks with the window; names wrap
            st = r.state_of(s)
            bg, fg = STATE_COLORS[st]
            when = R.short_date(s["started"]) if st != "ahead" else R.short_date(s["planned"]) if s["planned"] else ""
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
        ctk.CTkLabel(line, text=where, text_color=("#64748B", "#94A3B8"), font=("Segoe UI", 11)).pack(side="right", anchor="n")
        txt = g["text"] + (f"   (from {g['from']})" if g.get("from") else "")
        lab = ctk.CTkLabel(line, text=txt, anchor="w", justify="left", wraplength=300)
        lab.pack(side="left", padx=4, fill="x", expand=True)
        self._autowrap(lab, line, pad=110)
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
                reqs = sum(1 for it in M.items if it["decision"] == "Keep" and SD.owner_of(M, it) == who)
            except Exception:
                diag.swallowed()
        ctk.CTkLabel(body, text=f"{who}: {len(secs)} section(s)" + (f" ({', '.join(secs[:4])}{'...' if len(secs) > 4 else ''})" if secs else "")
                     + f", {reqs} compliance requirement(s)", anchor="w", justify="left", wraplength=560,
                     text_color=("#0369A1", "#7DD3FC")).pack(fill="x", pady=(0, 4))

    def _rec_draw_notes(self, r):
        _h, lab, body = self.rec_cards["notes"]
        qs = r.open_questions()
        notes = [n for n in r.notes() if not (n["question"] and not n["resolved"])]
        lab.configure(text=f"Notes and open questions   {len(qs)} open")
        for n in (qs + notes)[:10]:
            line = ctk.CTkFrame(body, fg_color="transparent"); line.pack(fill="x", pady=2)
            q = n["question"] and not n["resolved"]
            kind = "QUESTION" if q else ("ANSWERED" if n["question"] else "NOTE")
            ctk.CTkLabel(line, text=kind, width=86, anchor="w", font=("Segoe UI", 11, "bold"),
                         text_color=("#B45309", "#FBBF24") if q else ("#7C3AED", "#C4B5FD")).pack(side="left", anchor="n")
            if q:
                ctk.CTkButton(line, text="Resolve...", width=10, height=24, fg_color="#B45309",
                              command=lambda nid=n["id"]: self.rec_resolve_dialog(nid)).pack(side="right", padx=4, anchor="n")
            col = ctk.CTkFrame(line, fg_color="transparent"); col.pack(side="left", fill="x", expand=True)
            txt = n["text"] + (f"\nAnswer: {n['answer']}" if n.get("answer") else "")
            lab = ctk.CTkLabel(col, text=txt, anchor="w", justify="left", wraplength=300); lab.pack(fill="x")
            self._autowrap(lab, col)
            meta = " | ".join(x for x in (n["label"], R.short_date(n["at"]), n["who"]) if x)
            ctk.CTkLabel(col, text=meta, font=("Segoe UI", 11), anchor="w", text_color=("#64748B", "#94A3B8")).pack(fill="x")
        if not qs and not notes:
            ctk.CTkLabel(body, text="No notes yet. Notes can go on the effort, a stage, a customer document or a requirement.",
                         anchor="w", justify="left", wraplength=560).pack(fill="x")

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
            ok = r.move_to(to, carry=[g["id"] for g in open_goals] if carry is None else carry, planned=planned)
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
            done = r.move_to(target["id"], carry=[gid for gid, v in vars_ if v.get()], planned=pe.get() or None)
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
        w = ctk.CTkToplevel(self); w.title("Edit stages"); w.transient(self); w.geometry("720x620")
        ctk.CTkLabel(w, text="Stages for this effort", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(w, text="Rename, add, remove or reorder. New stages get the team's default goals when the name matches one.",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16)
        box = ctk.CTkScrollableFrame(w); box.pack(fill="both", expand=True, padx=16, pady=8)
        items = [[s["id"], s["name"], s["planned"]] for s in r.stages]
        widgets = []

        def draw():
            for x in box.winfo_children():
                x.destroy()
            widgets.clear()
            for i, it in enumerate(items):
                line = ctk.CTkFrame(box, fg_color="transparent"); line.pack(fill="x", pady=2)
                ne = ctk.CTkEntry(line, width=280); ne.insert(0, it[1]); ne.pack(side="left")
                pe = ctk.CTkEntry(line, width=130, placeholder_text="planned date"); pe.insert(0, it[2]); pe.pack(side="left", padx=6)
                ctk.CTkButton(line, text="Up", width=44, command=lambda i=i: move(i, -1)).pack(side="left", padx=2)
                ctk.CTkButton(line, text="Down", width=54, command=lambda i=i: move(i, 1)).pack(side="left", padx=2)
                cur = it[0] == r.data["stage"]
                ctk.CTkButton(line, text="Remove", width=70, fg_color="#B91C1C", state="disabled" if cur else "normal",
                              command=lambda i=i: remove(i)).pack(side="left", padx=2)
                if cur:
                    ctk.CTkLabel(line, text="current", text_color=("#1E3A8A", "#BFDBFE")).pack(side="left", padx=4)
                widgets.append((ne, pe))

        def sync():
            for it, (ne, pe) in zip(items, widgets):
                it[1], it[2] = ne.get(), pe.get()

        def move(i, d):
            sync()
            j = i + d
            if 0 <= j < len(items):
                items[i], items[j] = items[j], items[i]
                draw()

        def remove(i):
            sync(); items.pop(i); draw()

        def add():
            sync(); items.append([None, "New stage", ""]); draw()

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
        w._api = {"items": items, "add": add, "move": move, "remove": remove, "ok": ok}
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
    def rec_task_dialog(self, tid=None, values=None):
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
        for i, (k, lab, hint) in enumerate((("title", "Task", "Cut Vol I to 25 pages"), ("owner", "Owner", ", ".join(people[:3]) or "a name"),
                                             ("due", "Due date", "2026-10-30"), ("about", "About (a section, document or deliverable)", ""))):
            ctk.CTkLabel(w, text=lab, anchor="w").grid(row=i, column=0, sticky="w", padx=14, pady=(12 if i == 0 else 4, 0))
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
    def pkg_save_dialog(self, path=None, customer=True, volumes=False):
        """File > Save effort package...: the whole effort in one .ahpkg file for a hand-off."""
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
                                                 initialdir=folder, filetypes=[("Acronym Hunter effort package", "*" + P.EXT)])
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
                         customer=customer, volumes=volumes, stage=stage, app_version=getattr(__import__("app_gui"), "APP_VERSION", ""))
        except (OSError, PermissionError) as e:
            diag.swallowed()
            messagebox.showerror("Save effort package", f"The package could not be written ({type(e).__name__}).")
            return None
        self.rec_log("effort", f"Effort package saved: {os.path.basename(man['path'])} ({stage}, {len(man['files'])} files)")
        diag.activity("package_saved", files=len(man["files"]))
        self.status.configure(text=f"Effort package saved: {os.path.basename(man['path'])}")
        return man

    def pkg_import_dialog(self, path=None, dest=None, mode=None):
        """File > Import effort package...: open a package someone handed over and continue where it was.
        mode when the effort already exists on this PC: "replace" (this PC's saved work is backed up first) or "both"."""
        import effortpkg as P, workspace as W
        from tkinter import filedialog
        if path is None:
            path = filedialog.askopenfilename(title="Import effort package", filetypes=[("Acronym Hunter effort package", "*" + P.EXT)])
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
        P.repoint(got["data"], got["customer_dir"], got["matrix"])
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
    def status_snapshot(self, final=False):
        """Everything the status report shows, gathered from the record and the features (a plain dict: statusdoc.build)."""
        r, L = self.effrec(), self.effort
        checks = self.rec_checks()
        now = datetime.datetime.now()
        snap = {"effort": L.name, "client": L.client, "solicitation": L.solicitation, "internal": L.internal_no,
                "due": R.due_text(r.data["due"], r.data["zone"]), "countdown": R.countdown_text(r.data["due"]),
                "generated": f"{now.strftime('%b')} {now.day}, {now.year}, {now.hour % 12 or 12}:{now.minute:02d} {'a.m.' if now.hour < 12 else 'p.m.'}",
                "who": __import__("getpass").getuser(), "app": getattr(__import__("app_gui"), "APP_VERSION", "")}
        stages = []
        for s in r.stages:
            state = r.state_of(s)
            met = sum(1 for g in s["goals"] if r.goal_done(g, checks))
            dates = (f"{R.short_date(s['started'])} to {R.short_date(s['ended'])}" if state == "done" and s["started"] else
                     f"since {R.short_date(s['started'])}" if state == "current" and s["started"] else
                     (f"planned {R.short_date(s['planned']) or s['planned']}" if s["planned"] else ""))
            stages.append({"name": s["name"], "state": state, "met": met, "goals": len(s["goals"]), "dates": dates,
                           "when": R.short_date(s["started"]) if state != "ahead" else (R.short_date(s["planned"]) or s["planned"]),
                           "open": [g["text"] for g in s["goals"] if not r.goal_done(g, checks)]})
        snap["stages"] = stages
        cur = r.stage()
        met, total = r.goal_progress(checks=checks)
        ts = r.tasks()
        late = [t for t in ts if r.task_overdue(t)]
        stage_name = {s["id"]: s["name"] for s in r.stages}
        reg = self.subreg() if hasattr(self, "subreg") else None
        rows = reg.rows() if reg else []
        lib = self.doclib() if hasattr(self, "doclib") else None
        to_review = (lib.counts()["unreviewed"] if lib and lib.docs else 0) + sum(1 for x in rows if x["to_review"])
        M = getattr(self, "matrix", None)
        tiles = [(f"{met} of {total}", "gate goals met", "1E3A8A")]
        if M is not None and M.items:
            keeps = [it for it in M.items if it["decision"] == "Keep"]
            placed = sum(1 for it in keeps if it.get("map"))
            tiles.append((f"{placed} of {len(keeps)}", "requirements placed", "15803D" if placed == len(keeps) else "B45309"))
        tiles += [(len(r.open_questions()), "open questions", "B45309" if r.open_questions() else "15803D"),
                  (len(late), "tasks late", "B91C1C" if late else "15803D"),
                  (to_review, "changes to review", "B45309" if to_review else "15803D")]
        snap["tiles"] = tiles
        here = [t for t in ts if t["stage"] == cur["id"]]
        snap["current"] = {"name": cur["name"], "since": R.short_date(cur["started"]),
                           "summary": f"{met} of {total} gate goals met" + (f"; {len(late)} task(s) late" if late else ""),
                           "done": [g["text"] for g in cur["goals"] if r.goal_done(g, checks)] + [f"{t['title']} ({t['owner']})" if t["owner"] else t["title"] for t in here if t["status"] == "Done"],
                           "in_progress": [f"{t['title']}" + (f" ({t['owner']}" + (f", due {R.nice_date(t['due'])}" if t["due"] else "") + ")" if t["owner"] else "") for t in here if t["status"] == "In progress"],
                           "left": [g["text"] for g in cur["goals"] if not r.goal_done(g, checks)] + [f"{t['title']}" + (f" ({t['owner']})" if t["owner"] else "") for t in here if t["status"] == "Not started"]}
        snap["questions"] = [{"text": n["text"], "about": n["label"], "when": R.short_date(n["at"]), "who": n["who"]} for n in r.open_questions()]
        others = [n for n in r.notes() if not (n["question"] and not n["resolved"])]
        snap["notes"] = [{"text": n["text"], "about": n["label"], "when": R.short_date(n["at"]), "who": n["who"], "answer": n.get("answer", "")}
                         for n in (others if final else others[:12])]
        snap["projected"] = [{"name": x["name"], "planned": (R.short_date(s["planned"]) or s["planned"]) if s["planned"] else "",
                              "status": {"done": "Done " + R.short_date(s["ended"]), "current": "Now", "ahead": "Ahead"}[x["state"]]}
                             for x, s in zip(stages, r.stages)] + ([{"name": "Submission", "planned": snap["due"], "status": snap["countdown"]}] if snap["due"] else [])
        people = []
        try:
            import setupdoc as SD
            for p in self.rec_people():
                secs = SD.sections_of(M, p) if M is not None else []
                reqs = sum(1 for it in M.items if it["decision"] == "Keep" and SD.owner_of(M, it) == p) if M is not None else 0
                op = [t for t in ts if t["owner"] == p and t["status"] != "Done"]
                people.append({"person": p, "sections": ", ".join(secs[:6]) + ("..." if len(secs) > 6 else ""), "reqs": reqs,
                               "tasks": len(op), "late": sum(1 for t in op if r.task_overdue(t))})
            snap["no_owner"] = sum(1 for it in M.items if it["decision"] == "Keep" and not SD.owner_of(M, it)) if M is not None else 0
        except Exception:
            diag.swallowed()
        snap["people"] = people
        snap["tasks"] = [{"title": t["title"], "owner": t["owner"], "due": R.nice_date(t["due"]), "stage": stage_name.get(t["stage"], ""),
                          "status": t["status"] + (" (late)" if r.task_overdue(t) else ""), "late": r.task_overdue(t)}
                         for t in ts if final or t["status"] != "Done"]
        since = cur["started"] if not final else ""
        kinds = ("customer", "requirement", "stage", "assign", "compliance")
        ev = r.events(since=since or None, kinds=kinds)
        snap["changes_title"] = f"What changed since {cur['name']} began ({R.short_date(cur['started'])})" if since else "What changed"
        snap["changes"] = [] if final else [{"when": R.short_date(e["at"]), "text": e["text"], "who": e["who"]} for e in ev[:40]]
        lines = [x for x in (self.req_summary_text(rows).split("  |  ") if rows and hasattr(self, "req_summary_text") else []) if x]
        snap["requirements"] = {"lines": lines, "to_review": [f"{x['kind']}, {x['subject']}: {x['value']}" for x in rows if x["to_review"]]}
        snap["documents"] = [{"name": dd["name"], "versions": ", ".join(v["label"] for v in dd["versions"]),
                              "latest": f"{dd['versions'][-1]['label']}, {R.short_date(dd['versions'][-1]['added'])}"}
                             for dd in (lib.docs if lib else []) if dd["versions"]]
        if final:
            snap["history"] = [{"when": R.short_date(e["at"]) + (f" {e['at'][:4]}" if e["at"][:4] != str(now.year) else ""),
                                "kind": KIND_WORDS.get(e["kind"], e["kind"].upper()).title(), "text": e["text"], "who": e["who"]}
                               for e in reversed(r.events())]
        return snap

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
