"""The Guide's Template Studio and Formatting Standards topics (3.66.0) and Apply in Word (3.67.0), put back in the menu's order by guidetopics. Text only."""
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
