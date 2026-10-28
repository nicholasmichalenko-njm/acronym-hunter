"""The sentence card in Assign (2.58.0): click any sentence and the card beside the page shows everything decided
about it, in one place:
- Source: the file, the page and the paragraph on that page, the RFP reference (its L number, else the heading number,
  else the heading name) and how the response refers to it;
- Decision: compliance requirement (each proposal section it is in, as a chip with x, and + Section), supporting
  context (each requirement it supports with that requirement's section, as a chip with x, and + Requirement), the
  customer's, or not used;
- Author(s): one or more names (the effort's team offered); empty means the section's lead;
- Relationships: what supports it, or what it supports, each with where it is in the RFP, Jump and Unlink;
- Notes.
What the card shows is what the compliance matrix and the Response Setup are built from. Rules only (No AI);
nothing leaves the PC.
"""
import tkinter as tk
import customtkinter as ctk
import diag
import compliance as C
import setupdoc as SD

MUTED = ("#475569", "#94A3B8")
KIND = {"Keep": ("Compliance requirement", "#15803D"), "Context": ("Supporting context", "#1D4ED8"),
        "Customer": ("The customer's (identified, not answered)", "#7E22CE"), "Heading": ("RFP heading", "#334155")}


class AssignCardMixin:
    # ------------------------------------------------------------ building
    def _ac_build(self, card):
        """The card's own parts (the source labels, cp_head, cp_where and cp_ref, are made by the caller)."""
        win = self._cwin
        win.ac_kind = ctk.CTkLabel(card, text="", anchor="w", font=("Segoe UI", 13, "bold"), corner_radius=6,
                                   text_color="#FFFFFF", fg_color="#64748B")
        win.ac_kind.pack(fill="x", padx=8, pady=(6, 2))
        win.ac_dec = ctk.CTkFrame(card, fg_color="transparent")
        win.ac_dec.pack(fill="x", padx=8)
        ctk.CTkLabel(card, text="Author(s)", anchor="w", font=("Segoe UI", 12, "bold")).pack(fill="x", padx=8, pady=(8, 0))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=8)
        win.ac_auth = ctk.CTkEntry(row, placeholder_text="names, separated by commas")
        win.ac_auth.pack(side="left", fill="x", expand=True)
        win.ac_auth.bind("<Return>", lambda _e: self.ac_set_authors(win.ac_auth.get()))
        win.ac_auth.bind("<FocusOut>", lambda _e: self.ac_set_authors(win.ac_auth.get(), quiet=True))
        win.ac_add = ctk.CTkOptionMenu(row, width=80, values=["(no team yet)"], command=self.ac_add_author)
        win.ac_add.set("+ add")
        win.ac_add.pack(side="left", padx=(4, 0))
        win.ac_auth_note = ctk.CTkLabel(card, text="", anchor="w", justify="left", wraplength=320, text_color=MUTED,
                                        font=("Segoe UI", 11))
        win.ac_auth_note.pack(fill="x", padx=8)
        ctk.CTkLabel(card, text="Notes", anchor="w", font=("Segoe UI", 12, "bold")).pack(fill="x", padx=8, pady=(8, 0))
        win.ac_notes = ctk.CTkTextbox(card, height=56, wrap="word")
        win.ac_notes.pack(fill="x", padx=8, pady=(0, 4))
        win.ac_notes.bind("<FocusOut>", lambda _e: self.ac_set_notes(win.ac_notes.get("1.0", "end").strip(), quiet=True))
        win.ac_cur = None

    # ------------------------------------------------------------ showing
    def ac_source_lines(self, it):
        """[(label, value)] for the card's Source part."""
        M = self.matrix
        out = [("File", it.get("file", ""))]
        where = self.ac_where(it)
        if where:
            out.append(("Where", where))
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        if sec:
            out.append(("RFP", sec))
        try:
            ref, _how = SD.ref_of(M, it)
        except Exception:
            diag.swallowed()
            ref = ""
        if ref and ref != it.get("section", ""):
            out.append(("Referenced as", ref))
        return out

    def ac_where(self, it):
        """'p.3, para 2' for a sentence: from its place on the page (the PDF, or the PDF copy Page view uses), else from
        where the reader found it."""
        import matrixdesign as MD
        place = it.get("place", "")
        pv = getattr(self._cwin, "pv", None) or {}
        if not place and pv.get("file") == it.get("file") and it["id"] in (pv.get("placed") or {}):
            place = pv["placed"][it["id"]][0]
        if place:
            pdf = pv.get("pdf", "") if pv.get("file") == it.get("file") else ""
            if not pdf and str(it.get("file", "")).lower().endswith(".pdf"):
                pdf = self.matrix.path_of(it.get("file", ""))
            try:
                import pagesent as PS
                w = PS.where_text(pdf, place)
                if w:
                    return w
            except Exception:
                diag.swallowed()
        return MD._where(it) or ""

    def _ac_show(self, it):
        """Fill the card for the selected sentence."""
        win = self._cwin
        if win is None or not hasattr(win, "ac_kind") or it is None:
            return
        M = self.matrix
        if win.ac_cur and win.ac_cur != it["id"]:        # leaving a sentence keeps what was typed for it
            prev = self._c_item(win.ac_cur)
            if prev is not None:
                self._ac_save_fields(prev)
        win.ac_cur = it["id"]
        d = it.get("decision", "")
        kind = "Heading" if it.get("type") == "Heading" and not d else d
        txt, color = KIND.get(kind, ("Not used (not assigned)", "#64748B"))
        if win.cp_range and len(win.cp_range) > 1:
            txt = f"{txt}   (and {len(win.cp_range) - 1} more selected)"
        win.ac_kind.configure(text="  " + txt, fg_color=color)
        win.cp_where.configure(text="\n".join(f"{k}: {v}" for k, v in self.ac_source_lines(it)))
        for w in win.ac_dec.winfo_children():
            w.destroy()
        S = dict(height=24, width=10, font=("Segoe UI", 11))
        if d == "Keep":
            secs = SD.item_sections(M, it)
            ctk.CTkLabel(win.ac_dec, text="In section" + ("s" if len(secs) != 1 else "") + ":", anchor="w",
                         font=("Segoe UI", 11, "bold")).pack(fill="x")
            for lab in secs:
                self._ac_chip(win.ac_dec, lab, ("#DCFCE7", "#052E16"), lambda l=lab: self.cp_remove_section(it["id"], l))
            if not secs:
                ctk.CTkLabel(win.ac_dec, text="No section yet: click one in the structure below, or + Section.", anchor="w",
                             text_color=MUTED, font=("Segoe UI", 11)).pack(fill="x")
            labs = [C.outline_label(o) for o in M.outline if C.outline_label(o) not in secs]
            if labs:
                add = ctk.CTkOptionMenu(win.ac_dec, values=labs, width=10, height=24, command=lambda v: self.ac_add_section(it["id"], v))
                add.set("+ Section")
                add.pack(anchor="w", pady=(2, 0))
        elif d == "Context":
            ids = C.cf_ids(it.get("context_for", ""))
            ctk.CTkLabel(win.ac_dec, text="Supports:" if ids else ("Support for section " + it["map"] if it.get("map") else
                                                                   "Supports nothing yet: + Requirement."),
                         anchor="w", font=("Segoe UI", 11, "bold")).pack(fill="x")
            for i in ids:
                x = self._c_item(i)
                lab = f"{i}  {x.get('map', '')}".strip() if x else i
                self._ac_chip(win.ac_dec, lab, ("#DBEAFE", "#172554"), lambda b=i: self.cp_unlink(it["id"], b), jump=i)
            ctk.CTkButton(win.ac_dec, text="+ Requirement...", command=lambda: self.cp_support_picker(it["id"]), **S).pack(anchor="w", pady=(2, 0))
        elif d == "Customer":
            ctk.CTkLabel(win.ac_dec, text="Counted, never answered and never put in the response.", anchor="w",
                         text_color=MUTED, font=("Segoe UI", 11)).pack(fill="x")
        else:
            ctk.CTkLabel(win.ac_dec, text="R: compliance requirement.  C: support for the last requirement you clicked.  "
                                          "G: the customer's.", anchor="w", justify="left", wraplength=320, text_color=MUTED,
                         font=("Segoe UI", 11)).pack(fill="x")
        on = d in ("Keep", "Context")
        win.ac_auth.configure(state="normal")
        win.ac_auth.delete(0, "end")
        win.ac_auth.insert(0, ", ".join(SD.split_names(it.get("owner", ""))))
        lead = SD.section_people(M, it.get("map", "")).get("lead", "") if it.get("map") else ""
        win.ac_auth_note.configure(text=("" if it.get("owner") else (f"Empty: the section lead writes it ({lead})." if lead else
                                                                      "Empty: the section's lead, once one is named (People...)."))
                                   if on else "Assign the sentence to give it an author.")
        win.ac_auth.configure(state="normal" if on else "disabled")
        team = self.rec_people() if hasattr(self, "rec_people") else SD.people(M)
        win.ac_add.configure(values=team or ["(no team yet)"])
        win.ac_add.set("+ add")
        win.ac_notes.delete("1.0", "end")
        win.ac_notes.insert("1.0", it.get("notes", ""))

    def _ac_chip(self, parent, text, color, remove, jump=None):
        row = ctk.CTkFrame(parent, fg_color=color, corner_radius=12)
        row.pack(fill="x", pady=1)
        ctk.CTkLabel(row, text=text[:46], anchor="w", font=("Segoe UI", 11)).pack(side="left", padx=(8, 2))
        ctk.CTkButton(row, text="×", width=24, height=22, fg_color="transparent", text_color=("#B91C1C", "#FCA5A5"),
                      hover_color=("#FEE2E2", "#450A0A"), command=remove).pack(side="right", padx=2)
        if jump:
            ctk.CTkButton(row, text="Jump", width=10, height=22, fg_color="transparent", text_color=("#1E3A8A", "#BFDBFE"),
                          hover_color=("#DBEAFE", "#1E3A8A"), command=lambda: self._cp_select(jump)).pack(side="right")
        return row

    # ------------------------------------------------------------ changing
    def _ac_item(self):
        win = self._cwin
        return self._c_item(win.ac_cur) if win is not None and getattr(win, "ac_cur", None) else None

    def _ac_save_fields(self, it):
        win = self._cwin
        if win is None or not hasattr(win, "ac_auth"):
            return
        if it.get("decision") in ("Keep", "Context") and str(win.ac_auth.cget("state")) == "normal":
            self.ac_set_authors(win.ac_auth.get(), it=it, quiet=True)
        self.ac_set_notes(win.ac_notes.get("1.0", "end").strip(), it=it, quiet=True)

    def ac_set_authors(self, text, it=None, quiet=False):
        """The sentence's author(s) (and every other selected sentence's). Returns the names set, or None."""
        it = it or self._ac_item()
        if it is None or it.get("decision") not in ("Keep", "Context"):
            return None
        names = SD.split_names(text)
        value = ", ".join(names)
        rows = [it]
        win = self._cwin
        if win.cp_range and it["id"] in win.cp_range:
            rows = [x for x in (self._c_item(i) for i in win.cp_range) if x and x.get("decision") in ("Keep", "Context")]
        rows = [x for x in rows if (x.get("owner") or "") != value]
        if not rows:
            return names
        for x in rows:
            x["owner"] = value
            self.matrix.log(x["id"], f"author(s): {value or '(section lead)'}")
        if hasattr(self, "rec_log"):
            self.rec_log("assign", (f"{len(rows)} compliance requirements" if len(rows) > 1 else f"Compliance requirement {rows[0]['id']}")
                         + (f" assigned to {value}" if value else " back to the section lead"))
        self.matrix.pending = True
        diag.activity("assign_card_authors", n=len(rows))
        self._c_changed(refill=False)
        if not quiet:
            self._cp_flash(f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' sentences'}: author(s) {value or 'from the section'}")
            self._ac_show(it)
        return names

    def ac_add_author(self, name):
        win = self._cwin
        if not name or name.startswith("("):
            win.ac_add.set("+ add")
            return None
        cur = SD.split_names(win.ac_auth.get())
        if name not in cur:
            cur.append(name)
        win.ac_auth.delete(0, "end")
        win.ac_auth.insert(0, ", ".join(cur))
        win.ac_add.set("+ add")
        return self.ac_set_authors(", ".join(cur))

    def ac_set_notes(self, text, it=None, quiet=False):
        it = it or self._ac_item()
        if it is None:
            return None
        text = text.strip()
        if text == (it.get("notes") or "").strip():
            return text
        it["notes"] = text
        self.matrix.log(it["id"], "notes changed")
        self.matrix.pending = True
        diag.activity("assign_card_notes")
        self._c_changed(refill=False)
        if not quiet:
            self._cp_flash(f"{it['id']}: notes saved")
        return text

    def ac_add_section(self, iid, label):
        """+ Section: the requirement is in this section too (it keeps the others)."""
        it = self._c_item(iid)
        if it is None or not label or label.startswith("+"):
            return 0
        win = self._cwin
        keep_next = win.cp_next_var.get() if hasattr(win, "cp_next_var") else None
        if keep_next is not None:
            win.cp_next_var.set(False)                  # the card stays on this sentence
        try:
            n = self.cp_assign_req([it], label)
        finally:
            if keep_next is not None:
                win.cp_next_var.set(keep_next)
        self._cp_select(iid)
        return n
