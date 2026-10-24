"""In-app guide: the "?" button (and F1). Short, direct pages with small screenshots of the real tools.

Pictures live in assets\\help\\ (bundled into _internal\\assets\\help by the build). Each page is a list of blocks:
    ("h", "Heading")          section heading
    ("p", "text")             one short paragraph
    ("img", "file.png", w)    screenshot, shown w logical pixels wide (files are stored at 2x for sharp text)
    ("rows", [(label, text)]) label/text pairs: What / When / Why
    ("table", [row, ...])     first row is the header
"""
import os, sys
import diag
import tkinter as tk
import customtkinter as ctk

_win = [None]
_imgs = {}

def _asset(name):
    for base in (getattr(sys, "_MEIPASS", ""), os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))):
        p = os.path.join(base, "assets", "help", name)
        if os.path.isfile(p):
            return p
    return None

def _img(name, w):
    key = (name, w)
    if key not in _imgs:
        p = _asset(name)
        if not p:
            return None
        from PIL import Image
        im = Image.open(p)
        _imgs[key] = ctk.CTkImage(light_image=im, dark_image=im, size=(w, max(1, round(im.height * w / im.width))))
    return _imgs[key]

PAGES = {
"Start here": [
    ("h", "What Acronym Hunter does"),
    ("p", "It reads your files and lists every acronym, abbreviation, unit, designator, symbol and equation, with its "
          "definition and where it appears. It reads typed text and the text inside pictures, scans and diagrams. "
          "Everything runs on this PC. Nothing is sent anywhere."),
    ("h", "Four steps"),
    ("img", "toolbar_left.png", 560),
    ("rows", [("1. Scan", "Select Files or Scan Folder. Word, PowerPoint, Excel, PDF, pictures and drawings. "
                         "Scan Again repeats the last scan after you change a definition or a choice."),
              ("2. Review", "The results table lists every term found, with its status and where it appears."),
              ("3. Resolve", "Click a row. Pick a definition, add it to the database, or exclude it."),
              ("4. Export", "Export CSV gives you the acronym list for the proposal.")]),
    ("h", "Where to get help on each tool"),
    ("p", "Use the tabs above. Each page says what a tool does, when to use it, and why it is worth it."),
],
"Results": [
    ("h", "The results table"),
    ("img", "results.png", 640),
    ("rows", [("Term / Type", "What was found and what kind it is: acronym, abbreviation, unit, symbol, equation."),
              ("Status", "In DB = known. NEW CANDIDATE = not in your database yet. CHOOSE DEFINITION = several meanings."),
              ("First Use", "Whether the document defines the acronym the first time it uses it."),
              ("Locations", "Every file, page, sheet or picture where it appears. Click a row to see it.")]),
    ("h", "Filters"),
    ("img", "filters.png", 560),
    ("p", "Show one type or status, or search. Show Excluded brings back terms you excluded."),
    ("h", "The action bar (bottom)"),
    ("img", "actionbar.png", 560),
    ("rows", [("Apply Choice", "Pick one meaning when a term has several."),
              ("Include in DB", "Type the definition and save it. Every future scan knows it."),
              ("Fix OCR", "The term is a misreading. Type the correct term. See the Fix OCR vs Training tab."),
              ("Exclude", "Not a real term (a heading word, a part number). Hidden from now on.")]),
    ("p", "Fix OCR appears when the Advanced switch (top right) is on."),
],
"Fix OCR vs Training": [
    ("h", "Two ways to fix a misreading"),
    ("p", "A misreading is the scanner reading RFP as RRP, or SE&I as SE8I, inside a picture or scan. "
          "You have two tools. Use both."),
    ("table", [["", "Fix OCR", "Training"],
               ["What it is", "An auto-correct rule", "Lessons that make the reader better"],
               ["What changes", "The label after reading", "How the scanner reads"],
               ["Helps with", "That exact misreading", "Similar letters and words never corrected"],
               ["When it works", "Next scan", "After Improve Reading (20+ lessons)"],
               ["Best for", "Fixing today's results", "Fewer misreads from now on"]]),
    ("h", "Fix OCR: the instant fix"),
    ("img", "fixocr.png", 110),
    ("rows", [("What", "Saves a rule: when the scanner says RRP, it means RFP."),
              ("How", "Click the wrong row, type the correct term in the bottom box, click Fix OCR, then rescan."),
              ("When", "A misreading you see now, or one that keeps coming back."),
              ("Why", "No waiting and no setup. Every later scan, and every teammate with your Knowledge Pack, gets it right."),
              ("Careful", "Exact match only. Add a rule only for a reading that is always wrong.")]),
    ("h", "Correct + Teach: collect lessons"),
    ("img", "teach.png", 300),
    ("rows", [("What", "In the picture preview, fix the reading and click Correct + Teach. It saves the picture line and the right text."),
              ("When", "Any time a picture is misread. It takes two seconds."),
              ("Why", "Each one is a lesson. Lessons are how the reader gets better over time.")]),
    ("h", "Improve Reading: use the lessons"),
    ("img", "improve_btn.png", 150),
    ("img", "improve.png", 560),
    ("rows", [("What", "Trains a new reader from your saved lessons, on this PC, offline, in a few minutes."),
              ("When", "Once you have 20 or more lessons. The button tells you how many you have."),
              ("Why", "The new reader learns your fonts and drawings, so it misreads less, even on words nobody corrected."),
              ("Safe", "It tests the new reader first and keeps it only if it reads better. Put back the previous reader undoes it.")]),
],
"Effort list": [
    ("h", "One list per proposal"),
    ("p", "The effort list is an Excel file that keeps every term found, chosen and approved for one proposal. "
          "It starts on your desktop and can live in a synced SharePoint folder so the team sees the same list."),
    ("img", "effort_setup.png", 460),
    ("img", "effort_line.png", 560),
    ("rows", [("Start", "Effort > New effort. Name it, pick where the list lives, choose the first-use rule, and point to the "
                        "customer documents folder."),
              ("Customer first", "Every scan reads the customer documents' own definitions: \"Spelled Out (ACR)\" and acronym "
                                 "tables. The customer's definition beats the database. Two different ones: you choose."),
              ("Add button", "The teal button at the bottom adds the selected rows:"),
              ("Add", "Select rows and click Add to effort list. A definition typed in the bottom box goes in too."),
              ("Approve", "Right-click > Effort list > Approve. Enter the SS approver; several names are fine, separated by ;."),
              ("Not a term", "Right-click > Effort list > Not a term in this effort. Hidden for this proposal only."),
              ("Scan Again", "Approved definitions win on every later scan. Edits made in Excel are read too."),
              ("Export", "Effort > Export for approvals: sheets for Needs author, Conflicts, Approved and All."),
              ("Excel open", "If the list is open in Excel, the app asks you to close it and keeps your change until it can save.")]),
    ("img", "effort_add.png", 150),
    ("h", "Which definition wins"),
    ("p", "Effort list (approved) > customer documents > client lists > company database."),
],
"Pictures": [
    ("h", "The picture preview (right side)"),
    ("img", "preview.png", 340),
    ("rows", [("Where it was found", "Pick a location. Pictures and PDF pages show boxes; Word, PowerPoint and Excel typed "
                                     "text shows the passage with the term highlighted."),
              ("Find ◀ ▶", "Step through every find of the term, then on to its next location."),
              ("Zoom", "Mouse wheel or + / -. Drag to move around. Whole shows the whole page or picture."),
              ("Enlarge", "Opens the picture in a big window. Click boxes there too."),
              ("Click a box", "Every box is something the scanner read. Click one to check or fix it."),
              ("Correct + Teach", "Fix the spelling and save a lesson (see Fix OCR vs Training)."),
              ("Not text", "A line, arrow or speck read as text. The scanner ignores it from now on."),
              ("Exclude term", "A real reading, but not a term you want listed."),
              ("Undo last save", "Takes back your last save in this panel."),
              ("Open in Trainer", "Draw a box around text the scanner missed completely.")]),
    ("p", "Tools > Show preview pane turns this panel on or off."),
],
"Symbols": [
    ("h", "Symbol picker: no more copy and paste"),
    ("img", "picker.png", 380),
    ("rows", [("Open", "The Ω button next to a text box, Ctrl+Shift+Space, or right-click a text box."),
              ("Insert", "Click a symbol. It goes into the box you were typing in."),
              ("Find", "Search by name: sigma, dot, sub 2, degree, arrow."),
              ("Sub / Sup", "Select text (Isp: select sp) and click Sub to get Iₛₚ. Normal turns it back."),
              ("Accents", "Put the cursor after the letter, then click the accent: m + dot gives ṁ."),
              ("Recent", "Your last 24 symbols, ready to reuse.")]),
],
"Equations": [
    ("h", "Equations and symbols"),
    ("p", "Typed equations are read automatically. Their symbols (Isp, g₀, Δv) are listed as Symbols, with the "
          "definition when the document gives one."),
    ("h", "Math reader (optional add-on)"),
    ("img", "math.png", 440),
    ("rows", [("What", "Reads an equation picture and writes out the whole equation, 96-98% of symbols right."),
              ("How", "Click an Equation (picture) row, then Read this equation with the math reader. "
                      "Select several rows and right-click to read them all."),
              ("When", "Pictures of equations. Without it, the scanner reads them as loose letters."),
              ("Speed", "About 5 seconds per small equation. Results are remembered."),
              ("Install", "Unzip AcronymHunter_MathAddon.zip next to the app. It runs only in the no-network sandbox.")]),
],
"Sharing": [
    ("h", "Work as a team"),
    ("img", "toolbar_right.png", 300),
    ("rows", [("Knowledge Pack", "Tools > Knowledge. Share with team saves your database, OCR fixes, ignore list and "
                                 "trained reader in one file. Teammates install it. Undo puts theirs back."),
              ("Where", "Your approved local SharePoint folder only. Never GitHub, email or USB."),
              ("Client Lists", "Load the client's own acronym list. Its definitions win over the database."),
              ("Projects", "Project > Save. A rescan reads only files that changed."),
              ("Full Text", "Tools > Full Text. All typed and picture text, saved as .txt.")]),
    ("h", "Feedback: bugs, improvements, ideas"),
    ("rows", [("Open", "The Feedback button, or Ctrl+Shift+F."),
              ("Write", "Pick Bug, Improvement or Idea and the feature. Describe the feature, never your documents."),
              ("Guard", "The app will not save text that matches your terms, definitions, file or folder names."),
              ("Export", "Export for Claude shows everything first, then saves one text-only zip."),
              ("Logs", "The app also logs errors and which controls are clicked, by internal name only. "
                       "No file names, terms or document text, ever.")]),
    ("h", "Good team habit"),
    ("p", "One person collects fixes and lessons for a week, runs Improve Reading, and shares a Knowledge Pack. "
          "Everyone installs it. The whole team gets the better reader."),
],
}

def open_guide(parent, page=None):
    if _win[0] is not None and _win[0].winfo_exists():
        w = _win[0]
        w.deiconify(); w.lift(); w.focus_force()
        if page:
            w._show(page)
        return w
    win = ctk.CTkToplevel(parent); _win[0] = win
    win.title("How Acronym Hunter works"); win.geometry("820x680"); win.minsize(640, 420)
    win.transient(parent); win.after(150, win.lift)
    head = ctk.CTkFrame(win, fg_color="transparent"); head.pack(fill="x", padx=12, pady=(10, 4))
    ctk.CTkLabel(head, text="How Acronym Hunter works", font=("Arial", 17, "bold")).pack(side="left")
    ctk.CTkButton(head, text="Close", width=80, fg_color="#475569", command=win.withdraw).pack(side="right")
    tab = tk.StringVar(value=page or "Start here")
    seg = ctk.CTkSegmentedButton(win, values=list(PAGES), variable=tab, command=lambda v: show(v))
    seg.pack(fill="x", padx=12, pady=4)
    body = ctk.CTkScrollableFrame(win, fg_color=("#F8FAFC", "#1E1E1E")); body.pack(fill="both", expand=True, padx=12, pady=(4, 12))
    WRAP = 740

    def show(name):
        tab.set(name)
        for c in body.winfo_children():
            c.destroy()
        for blk in PAGES[name]:
            kind = blk[0]
            if kind == "h":
                ctk.CTkLabel(body, text=blk[1], font=("Arial", 15, "bold"), anchor="w").pack(fill="x", padx=10, pady=(14, 4))
            elif kind == "p":
                ctk.CTkLabel(body, text=blk[1], font=("Arial", 13), anchor="w", justify="left", wraplength=WRAP).pack(fill="x", padx=10, pady=2)
            elif kind == "img":
                im = _img(blk[1], blk[2])
                if im is not None:
                    ctk.CTkLabel(body, text="", image=im, anchor="w").pack(anchor="w", padx=10, pady=6)
            elif kind == "rows":
                g = ctk.CTkFrame(body, fg_color="transparent"); g.pack(fill="x", padx=10, pady=2)
                g.grid_columnconfigure(1, weight=1)
                for r, (lab, txt) in enumerate(blk[1]):
                    ctk.CTkLabel(g, text=lab, font=("Arial", 13, "bold"), anchor="w", width=150, justify="left",
                                 wraplength=150).grid(row=r, column=0, sticky="w", pady=3)
                    ctk.CTkLabel(g, text=txt, font=("Arial", 13), anchor="w", justify="left",
                                 wraplength=WRAP - 170).grid(row=r, column=1, sticky="w", padx=(8, 0), pady=3)
            elif kind == "table":
                t = ctk.CTkFrame(body, fg_color=("#E2E8F0", "#2B2B2B"), corner_radius=8); t.pack(fill="x", padx=10, pady=6)
                for c in range(len(blk[1][0])):
                    t.grid_columnconfigure(c, weight=1 if c else 0)
                for r, row in enumerate(blk[1]):
                    for c, cell in enumerate(row):
                        bold = r == 0 or c == 0
                        ctk.CTkLabel(t, text=cell, font=("Arial", 13, "bold" if bold else "normal"), anchor="w", justify="left",
                                     wraplength=250).grid(row=r, column=c, sticky="w", padx=10, pady=4)
        try:
            body._parent_canvas.yview_moveto(0)
        except Exception:
            diag.swallowed()
            pass
    win._show = show
    diag.register(win, "guide")
    diag.register(seg, "guide.tabs")
    win.bind("<Escape>", lambda e: win.withdraw())
    show(tab.get())
    return win
