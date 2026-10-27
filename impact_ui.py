"""Submission > Impact (2.42.0): what one new customer document version touched across the effort (impact.py).

The page shows one version at a time (the newest one not reviewed, or the one picked): the document, version, file,
who added it and its fingerprint, then six cards: submission requirements, deliverables, compliance, structure,
acronyms and keywords. Every card says what changed and offers the step that handles it; nothing changes until the
person acts. Who it touches, the text compare, a Word report and Mark impact reviewed sit at the bottom."""
import os, re
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag
import impact as IM

AMBER, NAVY, GRAY = "#B45309", "#1E3A8A", ("#475569", "#94A3B8")
CHANGE = {"changed": "Changed", "new": "New", "removed": "Removed", "renamed": "Renamed", "added": "New"}


class ImpactMixin:
    # ------------------------------------------------------------ the data
    def impact_build(self, vid):
        """The impact review of one version with everything the open effort knows."""
        lib = self.doclib() if hasattr(self, "doclib") else None
        if lib is None:
            return None
        reg = self.subreg()
        rows = [r for r in (reg.rows() if reg is not None else []) if not r.get("hidden")]
        rec = self.effrec() if hasattr(self, "effrec") else None
        M = getattr(self, "matrix", None)
        owner_of = None
        if M is not None:
            import setupdoc
            owner_of = lambda it: setupdoc.owner_of(M, it)            # noqa: E731
        L = self.effort
        eng = __import__("app_gui")
        db = self.db_terms() if hasattr(self, "db_terms") else set()
        listed = set(L.rows) if L is not None else set()
        kws = [k.get("Keyword", "") for k in (L.keywords or [])] if L is not None else []
        try:
            common = eng.common_words()
        except Exception:
            diag.swallowed(); common = ()
        vols = self.volumes() if hasattr(self, "volumes") else []
        return IM.build(lib, vid, rows, rec, M, owner_of, in_list=lambda t: t in listed, in_master=lambda t: eng.fold(t) in db,
                        common=common, keyword_list=kws, volumes=vols)

    def impact_choices(self):
        lib = self.doclib() if hasattr(self, "doclib") else None
        return IM.reviewable(lib) if lib is not None else []

    @staticmethod
    def _imp_label(d, v):
        return f"{d['name'][:40]}: {v['label']}" + ("" if v.get("reviewed") else "  (not reviewed)")

    # ------------------------------------------------------------ the page
    def _page_impact(self):
        A = dict(height=30, width=10)
        act = self.shell_actions("submission", "impact")
        ctk.CTkButton(act, text="Impact report (Word)...", command=self.impact_export, fg_color="#475569", **A).pack(side="left", padx=3)
        pg = self.shell_page("sub_impact")
        top = ctk.CTkFrame(pg, fg_color="transparent"); top.pack(fill="x", padx=6, pady=(12, 2))
        self.imp_title = ctk.CTkLabel(top, text="Impact", font=("Segoe UI", 20, "bold"), anchor="w")
        self.imp_title.pack(side="left")
        self.imp_pick = ctk.CTkOptionMenu(top, values=[""], width=340, command=lambda _v: self._imp_picked())
        self.imp_pick.pack(side="right")
        ctk.CTkLabel(top, text="Version", text_color=GRAY).pack(side="right", padx=6)
        ctk.CTkLabel(pg, text="What one new customer document version touched. Nothing you decided changes until you act on it.",
                     anchor="w", text_color=GRAY).pack(fill="x", padx=6, pady=(0, 6))
        self.imp_scroll = ctk.CTkScrollableFrame(pg, fg_color="transparent")
        self.imp_scroll.pack(fill="both", expand=True, padx=0, pady=(0, 4))
        self.imp_bottom = ctk.CTkFrame(pg, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1,
                                       border_color=("#E2E8F0", "#334155"))
        self.imp_bottom.pack(fill="x", padx=6, pady=(2, 6))
        self.imp_people = ctk.CTkLabel(self.imp_bottom, text="", anchor="w", justify="left", wraplength=700)
        self.imp_people.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        self.imp_done = ctk.CTkButton(self.imp_bottom, text="Mark impact reviewed", fg_color=AMBER, command=self.impact_mark_reviewed, **A)
        self.imp_done.pack(side="right", padx=(4, 12), pady=8)
        self.imp_cmp = ctk.CTkButton(self.imp_bottom, text="Compare the text", fg_color="#475569", command=self.impact_compare, **A)
        self.imp_cmp.pack(side="right", padx=4, pady=8)
        self.imp_vid, self.imp_r, self._imp_map = None, None, {}

    def impact_show(self, vid):
        """Open the impact review of one version."""
        self.imp_vid = vid
        if hasattr(self, "shell_go"):
            self.shell_go("submission", "impact")
        else:
            self.impact_refresh()
        return self.imp_r

    def _imp_picked(self):
        vid = self._imp_map.get(self.imp_pick.get())
        if vid:
            self.imp_vid = vid
            self.impact_refresh()

    def impact_refresh(self):
        if not hasattr(self, "imp_scroll"):
            return None
        for w in self.imp_scroll.winfo_children():
            w.destroy()
        lib = self.doclib() if hasattr(self, "doclib") else None
        ch = self.impact_choices()
        self._imp_map = {self._imp_label(d, v): v["id"] for d, v in ch}
        ids = [v["id"] for _d, v in ch]
        if self.imp_vid not in ids:
            pend = IM.pending(lib) if lib is not None else []
            self.imp_vid = pend[0][1]["id"] if pend else (ids[0] if ids else None)
        self.imp_pick.configure(values=list(self._imp_map) or [""])
        self.imp_r = r = self.impact_build(self.imp_vid) if self.imp_vid else None
        if r is None:
            self.imp_pick.set("")
            self.imp_title.configure(text="Impact")
            msg = ("Open an effort first." if lib is None else
                   "No new versions yet. When the customer sends an amendment or a revised document, add it on Documents: "
                   "what it touched shows here.")
            ctk.CTkLabel(self.imp_scroll, text=msg, anchor="w", justify="left", wraplength=900).pack(fill="x", padx=10, pady=14)
            self.imp_people.configure(text="")
            for b in (self.imp_done, self.imp_cmp):
                b.configure(state="disabled")
            return None
        self.imp_pick.set(next(k for k, v in self._imp_map.items() if v == r["version_id"]))
        self.imp_title.configure(text=f"{r['version']} of {r['doc']}: what it touched")
        self._imp_band(r)
        grid = ctk.CTkFrame(self.imp_scroll, fg_color="transparent"); grid.pack(fill="both", expand=True, padx=2)
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1, uniform="imp")
        cards = (self._imp_reqs, self._imp_deliv, self._imp_comp, self._imp_struct, self._imp_acr, self._imp_kw)
        self.imp_cards = {}
        for i, fn in enumerate(cards):
            card = fn(grid, r)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=5, pady=5)
        who = r["people"]
        self.imp_people.configure(text=("Who it touches: " + "; ".join(f"{o} ({len(w)})" for o, w in who.items()) +
                                        ". Each owner's changed sentences and deliverables are in the Word report.") if who else
                                  "It touches no owner's sections or deliverables yet.")
        self.imp_done.configure(state="disabled" if r["reviewed"] else "normal",
                                text=f"Impact reviewed {r['reviewed'][:10]}" if r["reviewed"] else "Mark impact reviewed")
        self.imp_cmp.configure(state="normal")
        return r

    def _imp_band(self, r):
        band = ctk.CTkFrame(self.imp_scroll, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1,
                            border_color=("#E2E8F0", "#334155"))
        band.pack(fill="x", padx=6, pady=(0, 6))
        t = r["text"]
        cells = (("DOCUMENT", r["doc"]), ("VERSION", f"{r['version']} (was {r['prev']})"), ("FILE", r["file"]),
                 ("ADDED", f"{r['added'].replace('T', ' ')} by {r['who']}"), ("FINGERPRINT (SHA-256)", IM.DV.short_sha(r["sha256"])),
                 ("TEXT", f"{t['changed']} changed, {t['added']} added, {t['removed']} removed"))
        for c, (k, v) in enumerate(cells):
            band.grid_columnconfigure(c, weight=1)
            ctk.CTkLabel(band, text=k, font=("Segoe UI", 10, "bold"), text_color=GRAY, anchor="w").grid(row=0, column=c, sticky="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(band, text=v, anchor="w", justify="left", wraplength=230).grid(row=1, column=c, sticky="w", padx=12, pady=(0, 8))

    def _imp_card(self, parent, key, title, n, warn=True):
        hot = bool(n) and warn
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1,
                            border_color="#FCD34D" if hot else ("#E2E8F0", "#334155"))
        head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(head, text=title, font=("Segoe UI", 15, "bold"), anchor="w").pack(side="left")
        ctk.CTkLabel(head, text=str(n), font=("Segoe UI", 15, "bold"), text_color=AMBER if hot else NAVY).pack(side="right")
        body = ctk.CTkFrame(card, fg_color="transparent"); body.pack(fill="both", expand=True, padx=14)
        foot = ctk.CTkFrame(card, fg_color="transparent"); foot.pack(fill="x", padx=10, pady=(4, 10), side="bottom")
        card._body, card._foot, card._lines = body, foot, []
        self.imp_cards[key] = card
        return card

    @staticmethod
    def _imp_line(card, bold, rest="", color=None):
        t = f"{bold}\n{rest}" if rest else bold
        lab = ctk.CTkLabel(card._body, text=t, anchor="w", justify="left", wraplength=360,
                           text_color=color if color else ("#0F172A", "#F1F5F9"))
        lab.pack(fill="x", pady=(2, 4))
        card._lines.append(t)
        return lab

    @staticmethod
    def _imp_none(card, text):
        ctk.CTkLabel(card._body, text=text, anchor="w", justify="left", wraplength=360, text_color=GRAY).pack(fill="x", pady=4)
        card._lines.append(text)

    @staticmethod
    def _imp_btn(card, text, cmd, main=False):
        b = ctk.CTkButton(card._foot, text=text, command=cmd, height=28, width=10, fg_color=NAVY if main else "#475569")
        b.pack(side="left", padx=3)
        return b

    # ------------------------------------------------------------ the cards
    def _imp_reqs(self, grid, r):
        xs = r["requirements"]
        card = self._imp_card(grid, "requirements", "Submission requirements", len(xs))
        for x in xs[:8]:
            if x["change"] == "changed":
                rest = f"Was {x['was']}, now {x['now']}" if x["was"] else f"Now {x['now']}"
            elif x["change"] == "removed":
                rest = f"No longer in the document (was {x['was']})" if x["was"] else "No longer in the document"
            else:
                rest = f"New: {x['now']}"
            self._imp_line(card, f"{x['kind']}, {x['subject']}", rest)
        if len(xs) > 8:
            self._imp_none(card, f"and {len(xs) - 8} more")
        if not xs:
            self._imp_none(card, "No due date, page limit, format, file or deliverable changed.")
        self._imp_btn(card, "Review in Requirements", lambda: self.shell_go("submission", "requirements"), main=bool(xs))
        return card

    def _imp_deliv(self, grid, r):
        xs, sug = r["deliverables"], r["suggested"]
        card = self._imp_card(grid, "deliverables", "Deliverables", len(xs) + len(sug))
        for x in xs:
            self._imp_line(card, x["name"] + (f", owner {x['owner']}" if x["owner"] else ", no owner yet"), "; ".join(x["why"]),
                           color=("#B91C1C", "#FCA5A5") if x["over"] else None)
        for s in sug:
            self._imp_line(card, f"New: {s['subject']}", "Named for the first time. Add it as a deliverable?")
            row = ctk.CTkFrame(card._body, fg_color="transparent"); row.pack(fill="x", pady=(0, 4))
            ctk.CTkButton(row, text="Add as a deliverable", height=26, width=10, fg_color="#0F766E",
                          command=lambda k=s["key"]: self.impact_add_deliverable(k)).pack(side="left", padx=(0, 4))
            ctk.CTkButton(row, text="Not ours", height=26, width=10, fg_color="#475569",
                          command=lambda k=s["key"]: self.impact_dismiss_deliverable(k)).pack(side="left")
        if not xs and not sug:
            self._imp_none(card, "No deliverable's limit, requirement or form changed.")
        self._imp_btn(card, "Open Deliverables", lambda: self.shell_go("submission", "deliverables"), main=bool(xs or sug))
        return card

    def _imp_comp(self, grid, r):
        c = r["compliance"]
        unassigned = [a for a in c["added"] if not a["decision"]]
        n = len(c["changed"]) + len(c["removed"]) + len(unassigned)
        card = self._imp_card(grid, "compliance", "Compliance", n)
        M = getattr(self, "matrix", None)
        if M is None or not M.items:
            self._imp_none(card, "No compliance matrix yet. When there is one, this card shows the matrix sentences this version "
                                 "changed or removed and who owns them.")
            return card
        placed = [x for x in c["changed"] if x["map"]]
        if c["changed"]:
            secs = sorted({f"{x['map']}" + (f" ({x['owner']})" if x["owner"] else "") for x in placed})
            self._imp_line(card, f"{len(c['changed'])} changed" + (f", {len(placed)} in assigned sections" if placed else ""),
                           ", ".join(secs[:4]) + (" ..." if len(secs) > 4 else "") if secs else
                           ", ".join(x["id"] for x in c["changed"][:6]))
        if c["added"]:
            self._imp_line(card, f"{len(c['added'])} new sentence(s)" + (f", {len(unassigned)} not assigned yet" if unassigned else ""),
                           "; ".join(a["text"][:70] for a in c["added"][:2]))
        for x in c["removed"][:3]:
            self._imp_line(card, f"Removed: {x['id']}", (f"Its sentence in {x['map']} is no longer asked for" if x["map"] else
                                                          "No longer in the document") + (f" (owner {x['owner']})" if x["owner"] else ""))
        if len(c["removed"]) > 3:
            self._imp_none(card, f"and {len(c['removed']) - 3} more removed")
        if not n and not c["added"]:
            self._imp_none(card, "No matrix sentence changed." if c["in_matrix"] else
                                 "This document is not in the compliance matrix.")
        if self.impact_matrix_paths(r) is not None:
            self._imp_btn(card, "Update the matrix", self.impact_update_matrix, main=True)
        self._imp_btn(card, "Open in Assign", lambda: self.shell_go("compliance", "decide"))
        return card

    def _imp_struct(self, grid, r):
        xs = r["structure"]
        card = self._imp_card(grid, "structure", "Structure", len(xs), warn=False)
        for x in xs[:6]:
            if x["change"] == "renamed":
                rest = f'"{x["was"]}" is now "{x["now"]}".' + (f" Rename our section {x['ours']} to match?" if x["ours"] else "")
            elif x["change"] == "added":
                rest = f'New heading: "{x["now"]}"' if x["now"] else "New heading"
            else:
                rest = f'"{x["was"]}" is gone.' + (f" Our section {x['ours']} answered it." if x["ours"] else "")
            self._imp_line(card, f"{x['num']} {CHANGE[x['change']].lower()}", rest)
        if not xs:
            self._imp_none(card, "No RFP heading was renamed, added or removed.")
        self._imp_btn(card, "Open Structure", lambda: self.shell_go("compliance", "outline"))
        return card

    def _imp_acr(self, grid, r):
        a = r["acronyms"]
        card = self._imp_card(grid, "acronyms", "Acronyms", len(a["new"]) + len(a["gone"]), warn=False)
        if a["new"]:
            known = [x["term"] for x in a["new"] if x["in_list"] or x["in_master"]]
            self._imp_line(card, f"{len(a['new'])} new in this version: " + ", ".join(x["term"] for x in a["new"][:10]),
                           (", ".join(known) + (" is" if len(known) == 1 else " are") + " in the effort list or the master database")
                           if known else "None is in the effort list or the master database yet")
        if a["gone"]:
            kept = [x["term"] for x in a["gone"] if x["in_list"]]
            self._imp_line(card, f"{len(a['gone'])} no longer in this document: " + ", ".join(x["term"] for x in a["gone"][:10]),
                           (", ".join(kept) + " stay in the effort list while our documents use them") if kept else "")
        if not a["new"] and not a["gone"]:
            self._imp_none(card, "No acronym came or went.")
        self._imp_btn(card, "Open Acronyms", lambda: self.shell_go("acronyms"))
        return card

    def _imp_kw(self, grid, r):
        xs = r["keywords"]
        card = self._imp_card(grid, "keywords", "Keywords", len(xs), warn=False)
        for x in xs:
            row = ctk.CTkFrame(card._body, fg_color="transparent"); row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f'"{x["phrase"]}" ({x["count"]} times)', anchor="w", justify="left", wraplength=250).pack(side="left")
            ctk.CTkButton(row, text="Add", height=26, width=10, fg_color="#0F766E",
                          command=lambda p=x["phrase"]: self.impact_add_keyword(p)).pack(side="right")
            card._lines.append(x["phrase"])
        if not xs:
            self._imp_none(card, "No new customer phrase is used twice or more.")
        self._imp_btn(card, "Open Keywords", lambda: self.shell_go("keywords"))
        return card

    # ------------------------------------------------------------ actions (also used by tests)
    def impact_add_deliverable(self, key):
        did = self.dl_add_suggested(key) if hasattr(self, "dl_add_suggested") else None
        self.impact_refresh()
        return did

    def impact_dismiss_deliverable(self, key):
        ok = self.dl_dismiss(key) if hasattr(self, "dl_dismiss") else False
        self.impact_refresh()
        return ok

    def impact_add_keyword(self, phrase):
        r = self.imp_r
        why = f"New in {r['version']} of {r['doc']}" if r else ""
        res = self.kw_add(phrase, source=f"{r['doc']}, {r['version']}" if r else "", why=why) if hasattr(self, "kw_add") else "no effort"
        self.status.configure(text=f'Keyword "{phrase}" added as Proposed.' if res == "added" else f'Keyword "{phrase}": {res}.')
        self.impact_refresh()
        return res

    def impact_matrix_paths(self, r=None):
        """The matrix's RFP files with this version in place of the one before it, or None when the matrix was not read
        from the version before (or the new file is gone)."""
        r = r or self.imp_r
        M = getattr(self, "matrix", None)
        lib = self.doclib() if hasattr(self, "doclib") else None
        if r is None or M is None or not M.sources or lib is None:
            return None
        _d, v, prev = IM.find_version(lib, r["version_id"])
        if v is None or not os.path.isfile(v.get("path", "")):
            return None
        out, hit = [], False
        for row in M.sources:
            name, sha, path = row[0], row[1], row[3] if len(row) > 3 else ""
            if sha == v.get("sha256"):
                return None                        # the matrix was already read from this version
            if sha and sha == prev.get("sha256") or (not sha and name == prev.get("file")):
                out.append(v["path"]); hit = True
            elif path and os.path.isfile(path):
                out.append(path)
        return out if hit else None

    def impact_update_matrix(self):
        paths = self.impact_matrix_paths()
        if not paths:
            return False
        r = self.imp_r

        def after(new, gone):
            if hasattr(self, "rec_log"):
                self.rec_log("compliance", f"Matrix updated with {r['version']} of {r['doc']}: {new} new or changed, {gone} no longer present",
                             ref={"version": r["version_id"]})
            self.status.configure(text=f"Matrix updated: {new} new or changed sentence(s) marked [New], {gone} marked [Gone]. "
                                       "Decisions stay on unchanged sentences.")
            self.impact_refresh()
        diag.activity("impact_matrix_update", files=len(paths))
        return self.compliance_reread_paths(paths, after=after)

    def impact_compare(self):
        r = self.imp_r
        if r is not None and hasattr(self, "sub_compare"):
            self.sub_compare(r["doc_id"], r["prev_id"], r["version_id"])

    def impact_mark_reviewed(self):
        """The version's changes are reviewed, and so are the requirement changes it made."""
        r = self.imp_r
        lib = self.doclib() if hasattr(self, "doclib") else None
        if r is None or lib is None:
            return False
        reg = self.subreg()
        n = 0
        for x in r["requirements"]:
            if x["to_review"] and reg is not None and reg.review(x["key"]):
                n += 1
        ok = self.sub_mark_reviewed(r["version_id"]) if hasattr(self, "sub_mark_reviewed") else lib.mark_reviewed(r["version_id"])
        if ok and hasattr(self, "rec_log"):
            self.rec_log("customer", f"Impact of {r['version']} of {r['doc']} reviewed: " + IM.headline(r).split(": ", 1)[-1],
                         ref={"version": r["version_id"]})
        diag.activity("impact_reviewed", rows=n)
        self.impact_refresh()
        return ok

    def impact_export(self, path=None):
        r = self.imp_r
        if r is None:
            messagebox.showinfo("Impact report", "There is no new version to report on yet.")
            return None
        name = self.effort.name if self.effort is not None else ""
        if path is None:
            base = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{r['doc']}_{r['version']}_Impact")
            path = filedialog.asksaveasfilename(title="Save the impact report", defaultextension=".docx", initialfile=base + ".docx",
                                                filetypes=[("Word", "*.docx")])
            if not path:
                return None
        IM.export_word(path, r, name)
        diag.activity("impact_exported")
        self.status.configure(text=f"Impact report saved: {path}")
        return path
