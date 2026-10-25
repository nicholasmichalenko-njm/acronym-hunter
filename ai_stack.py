"""What runs each part of Acronym Hunter (2.12.0): one list behind the AI labels, the ? panels, Help > What runs where,
and the one-page summary for the security team.

Labels:
  none  No AI   fixed rules, counting and file reading; the same input always gives the same output
  ml    ML      a trained model on this PC that recognizes characters or scores rows; outputs letters, boxes or numbers
  gen   Gen AI  a model that writes text; separate add-on, runs in the no-network sandbox

The AI and ML switch (per effort) turns off every ml and gen part. A build test checks that each sidebar section and
labeled feature has an entry here.
"""

LABELS = {"none": "No AI", "ml": "ML", "gen": "Gen AI"}

DIFFERENCE = [
    ("ML (machine learning)", "A trained model that recognizes or scores things: letters in a picture, how likely your team "
                              "keeps a row. It outputs letters, boxes or numbers, never sentences."),
    ("AI (generative AI)", "A model that writes text, like the math reader writing out an equation."),
    ("Where they run", "Both run only on this PC, with no network."),
    ("Why the switch turns off both", "Both give results learned from training data rather than fixed rules. With the switch "
                                      "off, every result comes from rules you can trace."),
    ("With the switch off", "Typed text in Word, PowerPoint, Excel and PDFs is still read everywhere. Text inside pictures "
                            "and scanned pages is not, and the learned compliance suggestions and add-ons are off."),
]

# key: (title, [label classes shown], [(part, job, class)])
FEATURES = {
    "scan": ("Scan", ["none", "ml"], [
        ("python-docx, python-pptx, openpyxl", "Read typed text from Word, PowerPoint and Excel", "none"),
        ("PDFium (pypdfium2)", "Reads typed text from PDFs", "none"),
        ("Rules (regular expressions)", "Find acronyms, abbreviations, units, codes and equations", "none"),
        ("RapidFuzz", "Matches definitions with small spelling differences", "none"),
        ("Context rules", "When a term has several meanings, nearby words, role and document cues, and the long form in "
                          "the same files suggest one; you decide", "none"),
        ("OpenCV", "Cleans up pictures before reading (no model)", "none"),
        ("Tesseract 5 (Google, Apache 2.0)", "Reads text inside pictures and scans with a trained LSTM model; built without "
                                             "network support", "ml"),
        ("docTR via ONNX Runtime (Mindee, Microsoft)", "Second reader for hard diagrams: finds text boxes and reads them", "ml"),
    ]),
    "review": ("Review", ["none"], [
        ("Filters and search", "Show one type or status, or search, over the results already found", "none"),
        ("Customer definitions (pattern rule)", "Matches \"Spelled Out Words (ACR)\" by first letters and reads glossary "
                                                "tables in the customer documents", "none"),
    ]),
    "effort": ("Effort", ["none"], [
        ("openpyxl", "Reads and writes the effort list workbook (atomic saves)", "none"),
        ("Rules", "Approved definitions win; first use, missing, unused and differing definitions in volumes", "none"),
        ("Word writer (built in)", "Writes the volume acronym lists", "none"),
        ("Effort folder", "Saved results, choices and backups for this effort only", "none"),
        ("Effort home and volumes (rules)", "The effort list as home; volumes from the files each term was found in, or "
                                            "your own assignment; Use as definition takes the words you select", "none"),
    ]),
    "compliance": ("Compliance", ["none", "ml"], [
        ("Rules", "Find shall, must, will and instruction sentences; actor, type and strength; cross-references", "none"),
        ("Word matching (IDF)", "Suggests an outline section from section numbers and title words", "none"),
        ("difflib", "Word-level differences between RFP versions", "none"),
        ("Setup Builder", "Places RFP text by the Outline column and section numbers; writes plain Word setup files", "none"),
        ("Naive Bayes (pure Python)", "Learned column: scores Keep or Drop from your team's past decisions. Stores numbered "
                                      "counts only, never RFP words", "ml"),
        ("TF-IDF similarity", "Suggests a section from rows you already mapped", "ml"),
    ]),
    "export": ("Export", ["none"], [
        ("CSV and Excel writers", "Write the results you see, nothing else", "none"),
    ]),
    "more": ("More", ["none", "ml"], [
        ("Add Item, Client Lists", "Your own entries and customer lists, matched by rules", "none"),
        ("Improve Reading (Tesseract training tools)", "Fine-tunes the picture reader on your corrected samples, on this PC",
         "ml"),
        ("docTR Training Kit (PyTorch, separate download)", "Optional; trains the second reader on this PC's GPU, offline",
         "ml"),
    ]),
    "math": ("Math reader add-on", ["gen"], [
        ("Granite-Docling (IBM, Apache 2.0)", "Generative model that writes an equation picture out as text", "gen"),
        ("Windows AppContainer sandbox", "Runs it with no network and no file access beyond its job", "gen"),
        ("Separate download", "Shown only when the add-on is installed; runs only when you click it", "gen"),
    ]),
}

SIDEBAR_SECTIONS = {"SCAN": "scan", "REVIEW": "review", "EFFORT": "effort", "COMPLIANCE": "compliance", "EXPORT": "export",
                    "MORE": "more"}


def classes_of(key):
    return FEATURES[key][1]


def summary_text(version, edition, math_installed, doctr_installed):
    """Plain one-page summary for the security team (Help > What runs where > Save summary)."""
    out = [f"Acronym Hunter {version} ({edition}): what runs each part", "",
           "Everything runs on this PC. The program makes no network connections.", "",
           "Labels", "  No AI   fixed rules, counting and file reading",
           "  ML      trained model that recognizes characters or scores rows; outputs letters, boxes or numbers, never sentences",
           "  Gen AI  model that writes text; separate add-on in the no-network sandbox", "",
           "The AI and ML switch (top bar, per effort, on by default) turns off every ML and Gen AI part. Each change is",
           "recorded in the effort list's History sheet (date, Windows user, setting) and in the usage log (no names).", ""]
    for key, (title, classes, parts) in FEATURES.items():
        if key == "math" and not math_installed:
            out += [f"{title}: not installed", ""]
            continue
        out.append(f"{title}  [{' + '.join(LABELS[c] for c in classes)}]")
        for part, job, cls in parts:
            if "docTR via" in part and not doctr_installed:
                continue
            out.append(f"  - {part} ({LABELS[cls]}): {job}")
        out.append("")
    out += ["AI and ML: the difference"] + [f"  - {a}: {b}" for a, b in DIFFERENCE]
    return "\n".join(out) + "\n"
