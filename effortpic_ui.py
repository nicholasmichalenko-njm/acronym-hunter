"""The effort's picture on Effort home (2.48.0): a logo, mission patch or cover image that stands for the effort.
Copied into the effort's own folder (effort picture.png in its app data), so effort packages and backups carry it.
Rules only (No AI); nothing leaves the PC."""
import os
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag

NAME = "effort picture.png"
BOX = 96                         # shown at most this tall and wide on Effort home
KEEP = 800                       # stored at most this many pixels on the long side


class EffortPictureMixin:
    def effort_picture_path(self):
        ws = getattr(self, "ws", None)
        return ws.p(NAME) if ws is not None and getattr(self, "effort", None) is not None else ""

    def effort_picture_build(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent"); f.pack(side="left", padx=(0, 14))
        self.ep_label = ctk.CTkLabel(f, text="", width=BOX, height=BOX, fg_color=("#E2E8F0", "#1E293B"), corner_radius=8,
                                     text_color=("#64748B", "#94A3B8"), cursor="hand2")
        self.ep_label.pack()
        self.ep_label.bind("<Button-1>", lambda _e: self.effort_picture_set())
        self.ep_btn = ctk.CTkButton(f, text="Effort picture...", width=BOX, height=22, font=("Segoe UI", 11),
                                    fg_color="transparent", text_color=("#1E3A8A", "#93C5FD"), hover_color=("#E2E8F0", "#334155"),
                                    command=self.effort_picture_menu)
        self.ep_btn.pack(pady=(2, 0))
        self._ep_img = None

    def effort_picture_refresh(self):
        lab = getattr(self, "ep_label", None)
        if lab is None:
            return
        p = self.effort_picture_path()
        if p and os.path.isfile(p):
            try:
                from PIL import Image
                with Image.open(p) as src:            # closed at once: Windows can then replace or remove the file
                    im = src.copy()
                im.thumbnail((BOX, BOX))
                self._ep_img = ctk.CTkImage(light_image=im, dark_image=im, size=im.size)
                lab.configure(image=self._ep_img, text="")
                return
            except Exception:
                diag.swallowed()
        self._ep_img = None
        lab.configure(image=None, text="Add a\npicture")

    def effort_picture_set(self, path=None):
        """Pick a picture (PNG, JPG, GIF, BMP) for the open effort. Returns the stored path or None."""
        if getattr(self, "effort", None) is None:
            messagebox.showinfo("Effort picture", "Open an effort first.")
            return None
        if path is None:
            path = filedialog.askopenfilename(title="Effort picture", filetypes=[("Pictures", "*.png *.jpg *.jpeg *.gif *.bmp")])
            if not path:
                return None
        try:
            from PIL import Image
            with Image.open(path) as src:
                im = src.copy()
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA")
            im.thumbnail((KEEP, KEEP))
            dst = self.effort_picture_path()
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tmp = dst + ".tmp"
            im.save(tmp, "PNG")
            os.replace(tmp, dst)
        except Exception as e:
            diag.swallowed()
            messagebox.showerror("Effort picture", f"That picture could not be used ({type(e).__name__}).")
            return None
        diag.activity("effort_picture_set")
        if hasattr(self, "rec_log"):
            self.rec_log("effort", "Effort picture set")
        self.effort_picture_refresh()
        return dst

    def effort_picture_remove(self):
        p = self.effort_picture_path()
        if p and os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                diag.swallowed()
                return False
            diag.activity("effort_picture_removed")
            if hasattr(self, "rec_log"):
                self.rec_log("effort", "Effort picture removed")
        self.effort_picture_refresh()
        return True

    def effort_picture_menu(self):
        import tkinter as tk
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Choose a picture...", command=self.effort_picture_set)
        has = bool(self.effort_picture_path()) and os.path.isfile(self.effort_picture_path())
        m.add_command(label="Remove the picture", command=self.effort_picture_remove, state="normal" if has else "disabled")
        try:
            m.tk_popup(self.ep_btn.winfo_rootx(), self.ep_btn.winfo_rooty() + self.ep_btn.winfo_height())
        finally:
            m.grab_release()
        return m
