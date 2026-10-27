"""Compliance > Export > Compliance matrix (Excel), designed here (2.48.0): pick, order and rename the columns, choose
the roles, see the first rows as they will look, export; or export the matrix and the Response Setup together.
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

    def matrix_design_dialog(self):
        M = self.matrix
        if M is None or not M.items:
            messagebox.showinfo("Compliance matrix", "Read the RFP files first.", parent=self._cwin)
            return None
        design = MD.design_for(M, self._md_config())
        w = ctk.CTkToplevel(self); w.title("Compliance matrix (Excel)"); w.transient(self); w.geometry("1180x760")
        w.after(150, w.lift)
        ctk.CTkLabel(w, text="Design the compliance matrix", font=("Segoe UI", 17, "bold"), anchor="w").pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(w, text="Tick the columns it shows, put them in order and rename them as the customer or the team wants. "
                             "Rows follow the response structure. The design is kept with this effort's matrix.",
                     anchor="w", justify="left", wraplength=1120, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14)
        body = ctk.CTkFrame(w, fg_color="transparent"); body.pack(fill="both", expand=True, padx=14, pady=8)
        left = ctk.CTkFrame(body); left.pack(side="left", fill="y", padx=(0, 10))
        ctk.CTkLabel(left, text="Columns, in order", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        lb = tk.Listbox(left, height=16, width=34, exportselection=False, font=("Segoe UI", max(10, getattr(self, "font_size", 13) - 2)))
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
        ctk.CTkLabel(left, text="Rows", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=10, pady=(12, 2))
        rv = {r: tk.BooleanVar(value=r in design["roles"]) for r, _l in MD.ROLES}

        def roles_changed():
            state["d"]["roles"] = [r for r, _l in MD.ROLES if rv[r].get()] or ["Keep"]
            show()
        for r, lab in MD.ROLES:
            ctk.CTkCheckBox(left, text=lab, variable=rv[r], command=roles_changed).pack(anchor="w", padx=12, pady=1)
        cv = tk.BooleanVar(value=design["customer_sheet"])
        ctk.CTkCheckBox(left, text="A sheet listing the customer's sentences", variable=cv,
                        command=lambda: state["d"].update(customer_sheet=bool(cv.get()))).pack(anchor="w", padx=12, pady=(1, 8))
        right = ctk.CTkFrame(body, fg_color="transparent"); right.pack(side="left", fill="both", expand=True)
        info = ctk.CTkLabel(right, text="", anchor="w"); info.pack(fill="x")
        tf = tk.Frame(right); tf.pack(fill="both", expand=True, pady=4)
        tv = ttk.Treeview(tf, show="headings", height=14)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=tv.xview); tv.configure(xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x"); tv.pack(fill="both", expand=True)

        def show():
            heads, data, n = MD.preview(M, state["d"])
            tv.configure(columns=[f"c{k}" for k in range(len(heads))])
            for k, h in enumerate(heads):
                key = state["d"]["columns"][k]["key"]
                tv.heading(f"c{k}", text=h); tv.column(f"c{k}", width=MD.COLUMNS[key][1] * 7, stretch=key == "text", anchor="w")
            tv.delete(*tv.get_children())
            for r in data:
                tv.insert("", "end", values=[str(v)[:160] for v in r])
            info.configure(text=f"Preview: the first {len(data)} of {n} rows, as they will appear.")

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
                res = MD.export(M, path, state["d"], self._md_effort_name())
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
        w._api = {"state": state, "lb": lb, "toggle": toggle, "move": move, "export": export, "together": together,
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
            res = MD.export_together(M, folder, MD.design_for(M, self._md_config()), self._md_effort_name())
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
