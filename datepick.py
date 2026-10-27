"""Date fields with a calendar to pick from (2.52.0): no date formats to remember. A DateField is an entry (typing
still works: 2026-12-15, 12/15/2026, December 15, 2026) with a small calendar button; get() gives 'YYYY-MM-DD' or ''.
Rules only; nothing leaves the PC."""
import calendar, datetime
import customtkinter as ctk
import effortrec as R


def to_iso(text):
    d = R.parse_date((text or "").split(",  ")[0]) or R.parse_date(",".join((text or "").split(",")[:2]))
    return d.isoformat() if d else ""


def nice(iso):
    d = R.parse_date(iso or "")
    return f"{d.strftime('%b')} {d.day}, {d.year}" if d else ""


class DateField(ctk.CTkFrame):
    def __init__(self, master, value="", width=140, placeholder="pick a date", command=None):
        super().__init__(master, fg_color="transparent")
        self.command = command
        self.entry = ctk.CTkEntry(self, width=width, placeholder_text=placeholder)
        self.entry.pack(side="left")
        ctk.CTkButton(self, text="Pick", width=46, command=self.open).pack(side="left", padx=(4, 0))
        self.set(value)
        self.popup = None

    def set(self, value):
        iso = to_iso(value) if value else ""
        self.entry.delete(0, "end")
        if iso:
            self.entry.insert(0, nice(iso))
        elif value:
            self.entry.insert(0, value)

    def get(self):
        t = self.entry.get().strip()
        return to_iso(t) if t else ""

    def open(self):
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.lift()
            return self.popup
        cur = R.parse_date(self.get()) or datetime.date.today()
        self.popup = CalendarPopup(self, cur, self._picked)
        return self.popup

    def _picked(self, d):
        self.set(d.isoformat())
        if self.command:
            self.command(d)


class CalendarPopup(ctk.CTkToplevel):
    def __init__(self, field, start, on_pick):
        super().__init__(field)
        self.title("Pick a date"); self.transient(field.winfo_toplevel()); self.resizable(False, False)
        self.on_pick, self.month, self.chosen = on_pick, start.replace(day=1), start
        bar = ctk.CTkFrame(self, fg_color="transparent"); bar.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkButton(bar, text="<", width=34, command=lambda: self.step(-1)).pack(side="left")
        self.lab = ctk.CTkLabel(bar, text="", font=("Segoe UI", 14, "bold")); self.lab.pack(side="left", expand=True)
        ctk.CTkButton(bar, text=">", width=34, command=lambda: self.step(1)).pack(side="right")
        self.grid_fr = ctk.CTkFrame(self, fg_color="transparent"); self.grid_fr.pack(padx=8, pady=(2, 8))
        ctk.CTkButton(self, text="Today", width=80, fg_color="#475569",
                      command=lambda: self.pick(datetime.date.today())).pack(pady=(0, 8))
        self.draw()
        self.after(100, self.lift)

    def step(self, d):
        m = self.month
        y, mo = m.year + (m.month - 1 + d) // 12, (m.month - 1 + d) % 12 + 1
        self.month = datetime.date(y, mo, 1)
        self.draw()

    def draw(self):
        for w in self.grid_fr.winfo_children():
            w.destroy()
        self.lab.configure(text=self.month.strftime("%B %Y"))
        for i, dn in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
            ctk.CTkLabel(self.grid_fr, text=dn, width=36, font=("Segoe UI", 11, "bold")).grid(row=0, column=i)
        today = datetime.date.today()
        self.buttons = {}
        for wi, week in enumerate(calendar.Calendar(0).monthdatescalendar(self.month.year, self.month.month)):
            for di, d in enumerate(week):
                inm = d.month == self.month.month
                b = ctk.CTkButton(self.grid_fr, text=str(d.day), width=36, height=28,
                                  fg_color="#1E3A8A" if d == self.chosen else ("transparent" if inm else "transparent"),
                                  text_color=("#0F172A", "#F1F5F9") if inm and d != self.chosen else ("#FFFFFF" if d == self.chosen else ("#94A3B8", "#475569")),
                                  border_width=1 if d == today else 0, border_color="#B91C1C",
                                  hover_color=("#E2E8F0", "#334155"), command=lambda d=d: self.pick(d))
                b.grid(row=wi + 1, column=di, padx=1, pady=1)
                self.buttons[d] = b

    def pick(self, d):
        self.on_pick(d)
        self.destroy()
