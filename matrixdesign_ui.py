"""Compliance > Export > Compliance matrix (Excel), designed here (2.48.0): pick, order and rename the columns, choose
the roles, see the rows as they will look, export; or export the matrix and the Response Setup together.
2.51.0: every row in the preview, fitted to the window; Context rows under their requirement (indented, lighter);
columns of the team's own (add, rename, remove); Volume, Deliverable, Page limit and Format from the effort.
Rules only (No AI); nothing leaves the PC."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import diag
import matrixdesign as MD


class MatrixDesignMixin:
    def _md_config(self):
        return getattr(__import__("app_gui"), "CONFIG_DIR", "")

    def _md_effort_name(self):
        L = getattr(self, "effort", None)
        return L.name if L is not None else (self.matrix.name if self.matrix is not None else "")

    def _md_ctx(self):
        """What the matrix takes from the effort (2.51.0): each deliverable's name, page limit and format."""
        out = {"deliverables": []}
        try:
            r = self.effrec() if hasattr(self, "effrec") else None
            if r is None:
                return out
            import deliverables as DL
            reg = self.subreg() if hasattr(self, "subreg") else None
            rows = reg.rows() if reg else []
            vols = self.volumes() if hasattr(self, "volumes") else []
            for d in DL.items(r):
                sp = {x["field"]: x["value"] for x in DL.spec(d, rows, vols)}
                fmt = "; ".join(f"{f}: {sp[f]}" for f in ("Font", "Margins", "Page size", "Line spacing", "File format") if sp.get(f))
                out["deliverables"].append({"name": d["name"], "limit": sp.get("Page limit") or d.get("limit", ""),
                                            "format": fmt or d.get("format", "")})
        except Exception:
            diag.swallowed()
        return out

    def md_page_refresh(self):
        """Compliance > Matrix (2.51.0): the matrix design as a step of its own, built fresh each time it opens."""
        win = getattr(self, "_cwin", None)
        fr = getattr(win, "md_page", None) if win is not None else None
        if fr is None or not fr.winfo_exists():
            return None
        for c in fr.winfo_children():
            c.destroy()
        if self.matrix is None or not self.matrix.items:
            ctk.CTkLabel(fr, text="The compliance matrix", font=("Segoe UI", 20, "bold"), anchor="w").pack(fill="x", padx=6, pady=(8, 2))
            ctk.CTkLabel(fr, text="Read the RFP first (Read RFP), then assign requirements and context; the matrix builds from "
                                  "those decisions, in the response structure.", anchor="w").pack(fill="x", padx=6)
            return None
        return self.matrix_design_dialog(parent=fr)

    def matrix_design_dialog(self, parent=None):
        M = self.matrix
        if M is None or not M.items:
            messagebox.showinfo("Compliance matrix", "Read the RFP files first.", parent=self._cwin)
            return None
        design = MD.design_for(M, self._md_config())
        if parent is None:
            w = ctk.CTkToplevel(self); w.title("Compliance matrix (Excel)"); w.transient(self); w.geometry("1180x760")
            w.after(150, w.lift)
        else:
            w = parent
        ctk.CTkLabel(w, text="The compliance matrix", font=("Segoe UI", 17, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(w, text="Built from your decisions as you assign, in the response structure: each requirement with its "
                             "context under it, and every section of the structure. Pick, order, rename and add columns as the "
                             "customer or the team wants; the design is kept with this effort's matrix.",
                     anchor="w", justify="left", wraplength=1120, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14)
        body = ctk.CTkFrame(w, fg_color="transparent"); body.pack(fill="both", expand=True, padx=14, pady=8)
        left = ctk.CTkFrame(body); left.pack(side="left", fill="y", padx=(0, 10))
        ctk.CTkLabel(left, text="Columns, in order", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        lb = tk.Listbox(left, height=18, width=34, exportselection=False, font=("Segoe UI", max(10, getattr(self, "font_size", 13) - 2)))
        lb.pack(padx=10, pady=4)
        state = {"d": design}

        def fill_list(sel=None):
            lb.delete(0, "end")
            on = [c["key"] for c in state["d"]["columns"]]
            for c in state["d"]["columns"]:
                lb.insert("end", f"[x] {c['heading']}")
            for k in MD.COLUMNS:
                if k not in on:
                    lb.insert("end", f"[ ] {MD.COLUMNS[k][0]}")
            if sel is not None and 0 <= sel < lb.size():
                lb.selection_set(sel); lb.see(sel)
            show()

        def keys_in_list():
            on = [c["key"] for c in state["d"]["columns"]]
            return on + [k for k in MD.COLUMNS if k not in on]

        def add_column(name=None):
            """A column of the team's own (2.51.0): blank in the export, filled in Excel."""
            if name is None:
                from tkinter import simpledialog
                name = simpledialog.askstring("Add a column", "Heading for the new column:", parent=w)
            name = " ".join((name or "").split())[:40]
            if not name:
                return None
            key = MD.CUSTOM + name
            if key not in [c["key"] for c in state["d"]["columns"]]:
                state["d"]["columns"].append({"key": key, "heading": name})
            fill_list(len(state["d"]["columns"]) - 1)
            return key

        def picked():
            s = lb.curselection()
            return (s[0], keys_in_list()[s[0]]) if s else (None, None)

        def toggle(_e=None):
            i, k = picked()
            if k is None:
                return
            cols = state["d"]["columns"]
            if any(c["key"] == k for c in cols):
                if len(cols) > 1:
                    state["d"]["columns"] = [c for c in cols if c["key"] != k]
            else:
                cols.append({"key": k, "heading": MD.COLUMNS[k][0]})
            fill_list(min(i, lb.size() - 1))

        def move(d):
            i, k = picked()
            cols = state["d"]["columns"]
            j = next((n for n, c in enumerate(cols) if c["key"] == k), None)
            if j is None or not 0 <= j + d < len(cols):
                return
            cols[j], cols[j + d] = cols[j + d], cols[j]
            fill_list(j + d)

        def rename():
            i, k = picked()
            c = next((c for c in state["d"]["columns"] if c["key"] == k), None)
            if c is None:
                return
            from tkinter import simpledialog
            new = simpledialog.askstring("Column heading", "Heading for this column:", initialvalue=c["heading"], parent=w)
            if new and new.strip():
                c["heading"] = " ".join(new.split())[:60]
                fill_list(i)
        lb.bind("<Double-1>", toggle)
        lb.bind("<space>", lambda _e: (toggle(), "break")[1])
        bb = ctk.CTkFrame(left, fg_color="transparent"); bb.pack(fill="x", padx=10)
        for txt, cmd in (("Show or hide", toggle), ("Up", lambda: move(-1)), ("Down", lambda: move(1)), ("Rename...", rename)):
            ctk.CTkButton(bb, text=txt, width=10, height=28, command=cmd).pack(side="left", padx=(0, 4), pady=2)
        ctk.CTkButton(left, text="Add a column...", height=28, command=add_column).pack(anchor="w", padx=10, pady=(4, 0))
        ctk.CTkLabel(left, text="A column you add is blank in Excel for the team to fill; hiding it removes it.", anchor="w",
                     justify="left", wraplength=250, text_color=("#475569", "#94A3B8"), font=("Segoe UI", 11)).pack(fill="x", padx=10)
        ctk.CTkLabel(left, text="Rows", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=(12, 2))
        rv = {r: tk.BooleanVar(value=r in design["roles"]) for r, _l in MD.ROLES}

        def roles_changed():
            state["d"]["roles"] = [r for r, _l in MD.ROLES if rv[r].get()] or ["Keep"]
            show()
        for r, lab in MD.ROLES:
            ctk.CTkCheckBox(left, text=lab, variable=rv[r], command=roles_changed).pack(anchor="w", padx=12, pady=1)
        ctk.CTkLabel(left, text="Rows in", anchor="w").pack(fill="x", padx=12, pady=(6, 0))       # 2.54.0
        ov = ctk.CTkSegmentedButton(left, values=["RFP order", "Our structure"],
                                    command=lambda v: (state["d"].update(order="rfp" if v == "RFP order" else "structure"), show()))
        ov.set("RFP order" if design.get("order", "rfp") == "rfp" else "Our structure"); ov.pack(anchor="w", padx=12, pady=(0, 4))
        ev = tk.BooleanVar(value=design.get("empty_sections", True))
        ctk.CTkCheckBox(left, text="Proposal sections with nothing assigned yet", variable=ev,
                        command=lambda: (state["d"].update(empty_sections=bool(ev.get())), show())).pack(anchor="w", padx=12, pady=1)
        cv = tk.BooleanVar(value=design["customer_sheet"])
        ctk.CTkCheckBox(left, text="A sheet listing the customer's sentences", variable=cv,
                        command=lambda: state["d"].update(customer_sheet=bool(cv.get()))).pack(anchor="w", padx=12, pady=(1, 8))
        right = ctk.CTkFrame(body, fg_color="transparent"); right.pack(side="left", fill="both", expand=True)
        info = ctk.CTkLabel(right, text="", anchor="w"); info.pack(fill="x")
        tf = tk.Frame(right); tf.pack(fill="both", expand=True, pady=4)
        tv = ttk.Treeview(tf, show="headings", height=14)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=tv.xview)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=tv.yview)
        tv.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        hsb.pack(side="bottom", fill="x"); vsb.pack(side="right", fill="y"); tv.pack(fill="both", expand=True)
        tv.tag_configure("ctx", foreground="#475569", background="#F1F5F9")
        tv.tag_configure("empty", foreground="#94A3B8")
        tv.tag_configure("req", foreground="#0F172A")

        def fit(_e=None):
            """Columns share the preview's width (the requirement wider), so the whole row shows."""
            cols = state["d"]["columns"]
            avail = max(400, tv.winfo_width() - 4)
            weights = [MD.width_of(c["key"]) for c in cols]
            tot = float(sum(weights)) or 1.0
            for k, wt in enumerate(weights):
                tv.column(f"c{k}", width=max(50, int(avail * wt / tot)), stretch=True)
        tv.bind("<Configure>", lambda e: fit())

        def show():
            heads, data, n = MD.preview(M, state["d"], ctx=ctxd)
            items = MD.rows(M, state["d"], ctxd)[0]
            tv.configure(columns=[f"c{k}" for k in range(len(heads))])
            text_k = next((k for k, c in enumerate(state["d"]["columns"]) if c["key"] == "text"), None)
            for k, h in enumerate(heads):
                tv.heading(f"c{k}", text=h); tv.column(f"c{k}", anchor="w")
            fit()
            tv.delete(*tv.get_children())
            for it, r in zip(items, data):
                vals = [str(v)[:200] for v in r]
                kind = it.get("_kind", "req")
                if kind == "ctx" and text_k is not None:
                    vals[text_k] = "      " + vals[text_k]
                tv.insert("", "end", values=vals, tags=(kind,))
            nc = sum(1 for it in items if it.get("_kind") == "ctx")
            ne = sum(1 for it in items if it.get("_kind") == "empty")
            info.configure(text=f"All {n} rows, as they will appear: {n - nc - ne} compliance requirement(s), {nc} context "
                                f"(indented, under the requirement they support)" + (f", {ne} section(s) with nothing assigned yet" if ne else "")
                                + ". Sort on Order in Excel to get this layout back.")
        ctxd = self._md_ctx()

        def remember():
            MD.set_matrix(M, state["d"])
            self._c_changed(refill=False)

        def team_save():
            MD.save_team(self._md_config(), state["d"])
            diag.activity("matrix_design_team_saved")
            info.configure(text="Saved as the team default (new efforts start with it).")

        def team_use():
            t = MD.load_team(self._md_config())
            if t is None:
                info.configure(text="No team default saved yet.")
                return
            state["d"] = t
            for r, _l in MD.ROLES:
                rv[r].set(r in t["roles"])
            cv.set(t["customer_sheet"])
            fill_list(0)

        def export(path=None):
            remember()
            if path is None:
                path = filedialog.asksaveasfilename(parent=w, title="Save the compliance matrix", defaultextension=".xlsx",
                                                    initialfile=f"{self._md_effort_name().replace(' ', '_')}_Compliance_Matrix.xlsx",
                                                    initialdir=os.path.dirname(M.path) or None, filetypes=[("Excel", "*.xlsx")])
                if not path:
                    return None
            try:
                res = MD.export(M, path, state["d"], self._md_effort_name(), ctx=self._md_ctx())
            except PermissionError:
                messagebox.showerror("Compliance matrix", "That file is open in Excel. Close it, then export again.", parent=w)
                return None
            diag.activity("matrix_designed_exported", rows=res["rows"])
            if hasattr(self, "rec_log"):
                self.rec_log("compliance", f"Compliance matrix exported: {os.path.basename(path)} ({res['rows']} rows)")
            info.configure(text=f"Saved {os.path.basename(path)}: {res['rows']} rows" + (f", {res['customer']} customer's" if res["customer"] else "") + ".")
            return res

        def together(folder=None):
            remember()
            return self.compliance_export_together(folder, parent=w)
        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkButton(bar, text="Export the matrix...", fg_color="#0F766E", command=export).pack(side="right")
        ctk.CTkButton(bar, text="Matrix and Response Setup together...", fg_color="#1E3A8A", command=together).pack(side="right", padx=6)
        ctk.CTkButton(bar, text="Save as the team default", fg_color="#475569", command=team_save).pack(side="left")
        ctk.CTkButton(bar, text="Use the team default", fg_color="#475569", command=team_use).pack(side="left", padx=6)
        fill_list(0)
        w._api = {"state": state, "lb": lb, "toggle": toggle, "move": move, "export": export, "together": together, "add": add_column, "order": ov,
                  "roles": rv, "customer": cv, "tree": tv, "team_save": team_save, "team_use": team_use, "info": info}
        return w

    def compliance_export_together(self, folder=None, parent=None):
        """The designed matrix and the Response Setup, from the same decisions, in one dated folder."""
        M = self.matrix
        if M is None or not M.items:
            messagebox.showinfo("Export", "Read the RFP files first.", parent=parent or self._cwin)
            return None
        if folder is None:
            folder = filedialog.askdirectory(parent=parent or self._cwin, title="Folder for the export",
                                             initialdir=os.path.dirname(M.path) or None)
            if not folder:
                return None
        try:
            res = MD.export_together(M, folder, MD.design_for(M, self._md_config()), self._md_effort_name(), ctx=self._md_ctx())
        except PermissionError:
            messagebox.showerror("Export", "A file with that name is open in Excel or Word. Close it, then export again.",
                                 parent=parent or self._cwin)
            return None
        diag.activity("matrix_setup_exported", files=len(res["files"]))
        if hasattr(self, "rec_log"):
            self.rec_log("compliance", f"Compliance matrix and Response Setup exported together ({len(res['files'])} files)")
        if hasattr(self, "_s_fill"):
            try:
                self._c_changed(refill=False); self._s_fill()
            except Exception:
                diag.swallowed()
        messagebox.showinfo("Export", f"Saved in {os.path.basename(res['folder'])}:\n" + "\n".join(os.path.basename(p) for p in res["files"])
                            + ("" if M.outline else "\n\nThe Response Setup needs the response structure first."), parent=parent or self._cwin)
        return res
