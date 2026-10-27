"""Help > Coming soon (2.46.0): what is planned but not built yet, in a few bullets each, so the team sees what is
built and what is next. Edit PLANNED to add an idea; nothing here does anything."""
import customtkinter as ctk

PLANNED = [
    ("Custom dictionaries", [
        "Keep several custom dictionaries in Stationkeeper and see every word in them.",
        "Import an existing Word custom dictionary (.dic).",
        "Add, edit and remove words; build a dictionary from an effort's approved acronyms and terms.",
        "Export a .dic for Word, named with the date (and the effort name if you choose).",
        "Dictionaries are kept in the backups and every export is kept, dated, like other exports.",
    ]),
    ("Teams and owners", [
        "Editable teams (Proposal manager, Production, and any you add), each with an optional named person.",
        "An owner (team and/or person) for each part of an effort; everyone still sees everything.",
        "A small \"Since you last looked: changed or added by ...\" note: what others changed since you last opened "
        "the effort, and who changed it. Mark each one noted.",
        "Works with the effort folder in a OneDrive-synced SharePoint folder and the existing one-editor lock.",
    ]),
]


def text():
    out = []
    for title, bullets in PLANNED:
        out.append(title.upper())
        out += [f"  - {b}" for b in bullets]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def open_window(app):
    w = ctk.CTkToplevel(app); w.title("Coming soon"); w.transient(app); w.geometry("720x520")
    ctk.CTkLabel(w, text="Coming soon", font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 0))
    ctk.CTkLabel(w, text="Planned for coming versions, not built yet. Ideas and requests: Help > Submit an idea or report a problem.",
                 anchor="w", justify="left", wraplength=680, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16, pady=(2, 8))
    box = ctk.CTkScrollableFrame(w); box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
    for title, bullets in PLANNED:
        ctk.CTkLabel(box, text=title, font=("Segoe UI", 14, "bold"), anchor="w").pack(fill="x", pady=(8, 2))
        for b in bullets:
            ctk.CTkLabel(box, text="•  " + b, anchor="w", justify="left", wraplength=640).pack(fill="x", padx=(10, 0), pady=1)
    ctk.CTkButton(w, text="Close", command=w.destroy, fg_color="#64748B").pack(side="right", padx=16, pady=12)
    w.after(100, w.lift)
    return w
