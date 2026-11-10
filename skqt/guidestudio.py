"""The Guide's Template Studio and Formatting Standards topics (3.66.0), Apply in Word (3.67.0) and Verify (3.84.0), put back in the menu's order by guidetopics. Text only."""
STUDIO = \
("studio", "Production", "Template Studio",
  "One volume's template in one place, read from where its parts live: the profile's cover, headers and footers, table "
  "of contents, fonts, numbering and table looks; this effort's own formatting; the RFP's formatting rules; the parts and "
  "numbering; and the field recipes.",
  "When you set up a volume's template, and before Final Check counts its pages.",
  ["Pick the volume and the profile it is made from. Anatomy lists each part and the library item it uses (a newer "
   "version says so); double-click a row to open the screen that owns it.",
   "Parts and numbering: the volume's parts in order. For each: its page numbers (none, i, I, 1, or A-1 chapter-page with "
   "its chapter style, Heading 7 for appendices), whether they restart, its header and footer, orientation and paper, "
   "and whether its pages count toward the limit (how many pages an 11x17 sheet counts as, whether blank pages count). "
   "Use the usual parts starts from a cover, front matter in i, the response in 1 and appendices in A-1.",
   "Final Check counts pages by this plan when you have not ticked pages out by hand.",
   "Read back: Read a file... reads a template or volume made from this volume's template and sets each part against "
   "its plan (page numbers, restart, chapter style, orientation, paper), the fields against the field recipes and "
   "Heading 7 against Heading 1's list. Word draws each part shows the first page of each part as Word lays it out.",
   "A Customer form part is the customer's own form, kept as it is: name its file and the marking its pages carry. Fix a "
   "Copy and Apply in Word leave it alone; Final Check finds its pages and checks its marking.",
   "Save the part asks where it goes: this effort, every effort of this effort type, or every effort, with how many "
   "efforts would follow it. An effort follows a shared plan until it changes its own.",
   "Field recipes opens Rules > Field recipes: your field codes, which the checks read."],
  ["Nothing here is a second copy: change a style in Formatting Standards, a header in Layout, a pick in Effort Profiles."])

FORMATSTD = \
("formatstd", "Production", "Formatting Standards",
  "The fundamentals every template is built from, as a library: theme and colors, font sets, page setups, pagination schemes, "
  "heading numbering, lists, and paragraph, character and table styles.",
  "When a new template or Word document comes in; when the team changes a style; before building an effort profile.",
  ["Three panes: the categories with their counts; the category's items with their effort types, status, version and where each "
   "came from; the selected item's picture and every value it holds.",
   "Import from a Word file... reads a template or document once (never writing it). Each item lands in its library and category, "
   "New, Same as (Show me) or Differs (what differs). Choose what to do with each: Add, Add as a new version, Keep both (renamed), "
   "Replace, or Do not keep. Take the ticked keeps everything at once or nothing; Undo this import takes it back, and More > Undo "
   "an import takes back an earlier one.",
   "A style shows each property with where it comes from: Set here, or from the style it is based on (the chain is at the top). "
   "Reset puts the base style's value back. Other items show every value as a tree; double-click a plain value to change it. Save "
   "changes keeps the edits in this version; Save as a new version keeps them as the next one (Draft).",
   "Effort types...: the effort types an item is for (Every effort type, or some). The Effort type box shows the items for one "
   "effort type. Status: Draft (just imported), Approved (ready to build with), Retired (kept, not offered).",
   "The first time this page opens, your standards become library items: the global standard's (every effort type), each "
   "profile's and each effort type's changes as new versions labelled with their names. Nothing is deleted; Production Standards "
   "still makes the templates until Effort Profiles arrive. More > Bring in my standards again adds what changed since.",
   "Put in a standard... carries the selected items into the global standard, a profile or an effort type."],
  ["Measuring a Quick Part's pages in Word is a button (Template library > Quick Parts > Measure pages), never automatic.",
   "Quick Parts and Layout get screens of their own in 3.50.0; Effort Profiles and Templates in 3.51.0."])

APPLYWORD = \
("applyword", "Production", "Apply in Word (Beta)",
  "Beta: the live step is still being proven in real Word. The team's banned phrases put into a draft as tracked "
  "changes, each with a comment naming the rule, so the author accepts or rejects them in Word.",
  "Before a color review, or when an author asks for the banned phrases fixed in their draft.",
  ["Read a draft... lists every banned or avoided phrase with its sentence. A phrase whose Use instead is a few plain "
   "words is ticked with them; edit Replace with or untick any you keep.",
   "Make the copy with tracked changes writes a dated copy beside the draft: the ticked phrases as tracked changes, the "
   "unticked ones with advice as comments. The draft is only read.",
   "Live in Word: tick Allow changes in a document open in Word for this session, then Read the document open in "
   "Word... and pick it. Put the ticked changes into Word makes them in Word's open window as tracked changes, with a "
   "comment each. You save in Word; Stationkeeper never saves or closes the file. A place whose words changed since "
   "it was read is skipped. Every change is listed under Changes made live in Word.",
   "A fixed copy as tracked changes...: pick a draft and its fixed copy from Fix a Copy; Word compares them and the "
   "fixes reach the author as tracked changes."],
  ["The list is Team References > Banned phrases.", "Allow lasts until Stationkeeper closes."])


CHECKS369 = (   # 3.69.0 and later: lines added to topics in guidetopics by key
    ("rules", "Fix a Copy's checks: graphics, Excel and PowerPoint, and the words Fix a Copy reports and fixes (they were in "
              "Production Standards)."),
    ("formatstd", "Allowed styles...: the styles a finished document may use and the styles the rules read."),
    ("profiles", "Content map, fields and font rules...: every font rule, the content map and the fields, for the picked "
                 "profile in its effort type."),
    ("setups", "Bring in a file... (3.73.0): drop or pick the team's outline Excel. What's in your workbook lists each "
               "kind of text found in each column, as it looks (red text, black italic); say what each one is. Cells, piece "
               "by piece shows a column's cells marked; click a piece to change it. The preview shows the setup as it will "
               "be. Use this structure makes the sections and keeps the picks for the next workbook laid out the same way."),
    ("setups", "Setup styles... (in More): each kind of setup text's style name, font, size, color, bold, italic and hidden. Save for "
               "this effort, Use for every effort, or Put them in this effort's template."),
    ("setups", "Use a template file... (3.72.0): the setup on a Word template your team already made. It starts blank in the "
               "template's look; tick its cover, title page or front matter, any Quick Part, and which parts keep their header "
               "and footer. Headings follow the template's own numbering. The made file is checked before you get it."),
    ("settings", "Our data > Button use on this PC... (3.74.0): which buttons and menu items you press on each screen, "
                 "counted on this PC only (never in a SCIF-ready install), most pressed first. Export it to plan which "
                 "commands stay in view; Clear the count; turn it off."),
    ("setups", "Outline layouts... (in More; 3.73.0): the heading names each column may carry and how mixed text is told apart, set "
               "before you have the workbook. A new version of the outline is compared first; changes in both wait for your "
               "pick. Outline versions... compares any two and writes the workbook back out in its own layout."),
    ("matrix", "Bring the edited matrix back... (3.73.0): the exported matrix as the team filled it in; their values come back "
               "after you look. Merge another copy's matrix... keeps ours unless you take theirs."))

VERIFY = \
("verify", "Shred", "Fix text",
  "4.2.0: a mode inside Shred (F2, or Fix text on its bar) for text that came out wrong: Combine (J), Split (S), Heading, "
  "Set aside (a header, footer or banner; More: every line like it), Add missed text, Suspects (F3) and Page checked "
  "(Ctrl+Enter). A piece the page break joined says Joined across p.N to N+1: keep it, or undo the join. Nothing here holds "
  "the shred up. The page-by-page check below (Fix text > More > Page by page check...) gives each block of a page a role.",
  "Whenever a piece reads wrong in the shred, or before you rely on a document a scanner made.",
  ["Pick the document (Ctrl+O). It opens where you left it.",
   "Look at what is marked: a suggestion the rules were not sure of, a caption to confirm, a scanned line to check.",
   "Click a block (Shift+click or drag for more) and press its key, or pick the role on the bar beside it.",
   "A caption: Confirm what it names, or Pick another and click the figure or table.",
   "Press Enter: the page is verified by you and the next one opens. Next and the strip move on without verifying."],
  ["The reader uses these roles the next time the document is read into Review.",
   "Menu roles... (in More) shows, hides, renames and keys the roles, and adds your own.",
   "A verified page is a record that a person checked it, not a guarantee. Reopen this page... sends one back."])

DESIGNS = \
("designs", "Team", "Parts",
  "The library of parts built in Word and kept whole: covers, marking (CUI) pages, title pages, front matter (contents, "
  "acronyms, units), back covers and Quick Parts. Each kind is a tab; each part is one row with its versions as tabs and "
  "the part sets it is in. Setup and Make templates pick from here.",
  "When the team adds or changes a cover, a CUI page, a title page, a front matter page or a Quick Part; when you group "
  "parts for a kind of effort.",
  ["Build the page in Word on the team template. Put each piece of text that changes per effort in its own paragraph "
   "and style; give each source a header or footer reads (STYLEREF) its own style.",
   "Bring in from a document... reads a Word file once: its pages (one per Word section, each said to be a cover, a CUI "
   "page, a title page...: change it if the guess is wrong) and its Quick Parts gallery. Tick what you keep and pick its part set.",
   "On the right, What fills it: type the fill-in each styled paragraph takes, or leave it blank to keep the words as written.",
   "To change a page: right-click, Open in Word, save your changes as a new file, then Bring back as a new version... The "
   "version you started from stays; Name this version... says what each one is for.",
   "Drag rows onto a part set on the left. A set holds one version of each part."],
  ["Setups already made keep the copy of the page they used.",
   "A table's sample row repeats once per entry when Setup fills it (an Acronyms table: term, meaning).",
   "A Quick Part's picture, fonts and the pages it fills are on the Quick Parts tab (right-click: Details on the Quick Parts tab)."])

# 3.94.0: the Styles library
STYLES = ("styles", "Team", "Styles", "Every style you keep, one row each, with a preview and the sets it is in.",
  "When a file has styles you want to keep; when you group styles for a kind of effort; when a style needs another look.",
  ["Bring in from a document... reads only a Word file's styles: New, Different from yours (a new version) or Already have it, "
   "side by side; tick what you keep and pick its set. A style's versions are tabs on its row. Drag rows onto a set on the left; "
   "a set holds one version of each style and asks before moving to a newer one. New style makes a simple one; Make a copy to "
   "change (right-click) saves another version."],
  ["Each style keeps Word's own definition exactly as the file had it."])

# 3.96.0: the menu as the effort's path, and Team. 4.0.0: six steps. 4.1.0: Shred's four tabs
PATH = ("path", "Effort", "The effort's path",
  "The menu is the effort's path: the Dashboard, then 1 Documents, 2 Shred, 3 Matrix & Outline, 4 Setup, 5 Drafts and "
  "6 Submit. Each step says what is left on it (done, a count, next, or the due date).",
  "Whenever you are not sure what to do next.",
  ["Documents: the customer's package, complete, current and readable. Click a document to see what has been done to it and "
   "its next thing; Changes shows what a new version changed; Text check reads every page right.",
   "Shred: what every piece of the customer's text is (Requirements, Rules & Dates, Evaluation, Acros & Abs; picking a document "
   "extracts it). See it as shows Our structure, List, Sort, L to M or Coverage. The Q&A button opens the Q&A log beside the page.",
   "Matrix & Outline: what we answer and where (the Matrix). Setup: who writes what, when and how long, and the "
   "setup in Word. Drafts: the team writes in Word; the app reads the drafts back. Submit: the last checks.",
   "The Dashboard is the map: one card per step, Your next step with one button, and this week's dates.",
   "Every page in a step ends with a bar: what is left on this step, and the button to the next step when this one is done.",
   "The effort switcher at the top of the menu holds another effort, All Efforts and Your Tools. Ctrl+K goes to any page or "
   "tool by name."],
  ["Nothing is locked: open any step in any order. A step is done when what it counts is done."])

TEAM = ("team", "Team", "Team",
  "The team's own tools on one page of tiles: Standards, Effort Profiles, Template Studio, Rules, Check a Draft and Team "
  "References, shown to the roles that use them.",
  "When you change what every effort is built from, or check a draft against it.",
  ["Click a tile to open the tool. Its own tabs are under its title, as before."],
  ["A tool for another role is not shown; Settings > Roles and Preview tools says who it is for."])
