# Making Acronym Hunter More Accurate Over Time

This guide covers every way to improve results beyond adding rows to `acronym_database.csv`,
from a two-second fix to training your own OCR model. Every step ends the same way:
**measure with `tools\evaluate.py`, keep what scores better, undo what scores worse.**

---

## 1. Where errors actually come from

The app reads a file in three layers. Each layer fails differently and has different fixes.

| Layer | What it does | How accurate | How to tell it caused an error |
|---|---|---|---|
| Extraction | Pulls typed text out of PDF, Word, PowerPoint, Excel | Exact. Typed text is never misread | Location shows a page, slide, section, sheet, header, notes, chart |
| OCR | Reads text inside pictures, scanned pages, photos | Good, not perfect | Location contains `image`, `(Image)`, or a scanned PDF page |
| Matching | Decides which words are acronyms, units, abbreviations | Rule-based; source of most noise | Wrong term reported from typed text, or real term missed from typed text |

**Rule of thumb:** if the Location does not mention an image, OCR is not the problem.
Fix it with the database, the corrections file, or matching rules (sections 4, 5, 10).

Current score on `test_samples` (v1.0.1): **92.5% of expected terms found, 6 of 8 known noise words still reported.**
The 3 misses and 6 false alarms break down as: 2 matching-rule gaps, 1 OCR miss, 6 matching-rule noise.
Matching rules are the biggest remaining lever.

---

## 2. The levers, cheapest first

| # | Lever | Effort | Fixes | File or place |
|---|---|---|---|---|
| 4 | Database | Seconds | Unknown terms, definitions, noise words | `acronym_database.csv`, Include / Exclude buttons |
| 5 | OCR corrections | Seconds | A specific misread that keeps happening (RFF for RFP) | `config\ocr_corrections.csv`, **Fix OCR** button |
| 6 | OCR settings | Minutes | Whole classes of OCR misses (small text, scans, photos) | `config\ocr_settings.json` |
| 7 | Swap OCR models | 30 minutes | Systematic OCR weakness | `config\models\` (drop-in files) |
| 8 | Train your own OCR model | Days | OCR on a recurring style it never reads well | Separate PC, then `config\models\` |
| 9 | Better source files | Varies | Linked pictures, vector diagrams, low-quality scans | How documents are authored |
| 10 | Matching rules | Code change | Missed DoD, MIL-STD-882E; heading noise | `app_gui.py` |

Sections 4 to 10 below match the numbers in this table.

---

## 3. The improvement loop (do this after each real project)

1. **Scan** the project's files.
2. **Status filter > "Needs choice"**: pick the right definition for each. Add the context-correct one to the database if it recurs.
3. **Status filter > "New candidates"**, sort by **Count**, work top-down:
   - Real acronym: type its definition, click **Include in DB**.
   - Noise (heading word, sentence end): click **Exclude**.
   - OCR misread of a real term: type the correct term, click **Fix OCR**.
4. **Status filter > "Errors / not scanned"**: fix the source where you can (section 9).
5. **Add the misses you found to a ground-truth file** (section 11), so the next change is measured against them.
6. **Run the scorer**, then **copy changed files back** to the project folder and rebuild (section 12).

Ten minutes per project compounds: the database and corrections file grow with your real vocabulary.

---

## 4. Database (`acronym_database.csv`)

You already use this. Three habits make it work harder:

- **Add every confirmed term**, even obvious ones. A term in the database is matched exactly in typed text
  and becomes a target for OCR repair (0/O, 1/I, 5/S, 8/B swaps and fuzzy matching only repair toward database terms).
- **Exclude noise aggressively.** Each Exclude permanently removes that word from future candidate lists.
- **Keep multiple definitions** (CDR = Critical Design Review / Call Detail Record). The app flags them for a choice instead of guessing.

---

## 5. OCR corrections (`config\ocr_corrections.csv`)

For a misread that repeats. Format:

```
Misread,Correct,Note
RFF,RFP,F/P misread seen in test samples
C0PV,COPV,zero read for letter O
```

**From the app (fastest):**
1. Select the misread row (for example `RFF`).
2. Type the correct term (`RFP`) in the box.
3. Click **Fix OCR**. The row turns to "OCR fix saved".
4. Rescan. The term is reported under `RFP`, and its location is tagged `[OCR fix: RFF]`.

**By hand:** open the CSV in Notepad or Excel, add a line, save, rescan. No restart needed.

Rules:
- Matching is exact and case-sensitive, one word per line (`RFF`, not `the RFF`).
- If `Correct` is in the database, the hit resolves with that definition; if it is excluded, it stays hidden; otherwise it appears as a new candidate under the corrected spelling.
- Do not add a pair whose misread is also a real term in your documents.
- 0/O, 1/I, 5/S, 8/B swaps for database terms are already automatic. Add pairs only for other confusions.

---

## 6. OCR settings (`config\ocr_settings.json`)

Plain numbers that control image cleanup and the OCR engine. Edit, save, restart the app.
Delete the file to return to built-in defaults.

| Setting | Default | Raise it when | Lower it when | Cost of raising |
|---|---|---|---|---|
| `pdf_scan_dpi` | 300 | Scanned PDFs miss small or faint lines | Scans are slow, text is large | Slower scans, more memory |
| `scanned_page_max_chars` | 40 | Scanned pages with headers/Bates stamps skip OCR | Typed pages get OCR'd needlessly | Slower on typed pages |
| `min_confidence` | 0.5 | OCR returns garbage words | Real words in images are dropped | Fewer junk candidates, more misses |
| `upscale_below_px` | 1200 | Small screenshots/diagrams read badly | Large images are slow | Slower |
| `upscale_factor` | 2.0 | Tiny text in small images | Rarely | Slower, more memory |
| `contrast_clip` | 2.0 | Faded scans, light gray text | Clean images get speckled; 0 turns it off | Can amplify noise |
| `denoise_strength` | 10 | Phone photos, grainy scans | Clean screenshots blur; 0 turns it off | Slower; blurs thin fonts |
| `detect_side_len` | 736 | Very small text on large pages | Rarely | Slower; tested worse here |
| `detect_box_thresh` | 0.5 | Faint text boxes missed (try 0.4) | Specks read as text | More noise |
| `detect_unclip_ratio` | 1.6 | Words cut off at the edges | Neighboring lines merge | Merged lines |
| `fuzzy_min_score` | 80 | Wrong "OCR fix" matches appear | Close misreads of long DB terms are missed | Fewer repairs |

**Step by step:**
1. Run the scorer for a baseline:
   `.\venv\Scripts\python.exe tools\evaluate.py --note "baseline"`
2. Change **one** number in `config\ocr_settings.json`.
3. Run the scorer again with a note describing the change.
4. Compare RECALL and FALSE ALARMS in the output or in `tools\eval_history.csv`.
5. Keep it if recall rose and false alarms did not; otherwise put the number back.
6. Re-check on a folder of your real documents (section 11) before adopting it.

**Measured on test_samples (2026-10-20):**

| Change | Recall | Result |
|---|---|---|
| Defaults with `pdf_scan_dpi` 200 | 90.0% | Old baseline |
| `pdf_scan_dpi` 300 | **92.5%** | Adopted as the new default |
| `detect_side_len` 1280 | 87.5% | Rejected |
| dpi 300 + detect 1280 + `denoise_strength` 0 | 85.0% | Rejected: lost words in the whiteboard photo |

---

## 7. Swap OCR models (`config\models\`)

The OCR engine uses three model files. The app ships with PP-OCRv4 models and loads replacements from
`config\models\` by exact file name:

| File name | Job | When to swap |
|---|---|---|
| `rec.onnx` | Recognition: reads the characters in each text box | Characters are misread (most common) |
| `det.onnx` | Detection: finds where text is | Whole words or lines are skipped |
| `cls.onnx` | Orientation: flips upside-down text | Rarely |
| `rec_keys.txt` | Character list for `rec.onnx` | Only if the model does not carry its own |

Only PaddleOCR-family models converted to ONNX (RapidOCR format) work.
If a model fails to load, the app falls back to the built-in models and writes `logs\error.log`.

**Step by step:**
1. On a PC with internet access, open https://huggingface.co/SWHL/RapidOCR and download a candidate:

   | File in the repository | Size | Notes |
   |---|---|---|
   | `PP-OCRv3/en_PP-OCRv3_rec_infer.onnx` | 8.6 MB | English-only recognition. Character list embedded |
   | `PP-OCRv4/ch_PP-OCRv4_rec_server_infer.onnx` | 86 MB | Larger recognition model. Character list embedded |
   | `PP-OCRv4/ch_PP-OCRv4_det_server_infer.onnx` | 113 MB | Larger detection model (not yet tested) |
   | `PP-OCRv4/en_PP-OCRv3_det_infer.onnx` | 2.4 MB | English detection model (not yet tested) |

2. Record its fingerprint: `Get-FileHash .\downloaded_file.onnx` (keep it in the score note).
3. Rename it to the role name (`rec.onnx` or `det.onnx`) and copy it into `config\models\`.
4. Score it: `.\venv\Scripts\python.exe tools\evaluate.py --note "en_PP-OCRv3 rec"`.
   The output line `OCR models: custom rec.onnx` confirms it loaded.
5. Score it on your real-document folder too (section 11).
6. Better on both: keep it, rebuild (the build copies `config\` into the zip). Worse: delete it from `config\models\`.

**Measured on test_samples (2026-10-20):**

| Recognition model | Recall | Result |
|---|---|---|
| Built-in PP-OCRv4 | **92.5%** | Kept |
| `en_PP-OCRv3_rec_infer.onnx` | 92.5% | Tie: fixed COPV on scanned p.8, lost TT&C (weak on "&") |
| `ch_PP-OCRv4_rec_server_infer.onnx` | 87.5% | Rejected: bigger did not mean better on these files |

On work machines, treat model files like any third-party download: get IT approval, download only from the
repository above, and keep the fingerprint with the build.

---

## 8. Train your own OCR model (fine-tuning)

This is real training: teaching the recognition model your fonts and layouts. Worth it only when one
recurring style (drawing title blocks, a stamp font, a scanned form) fails across hundreds of images and
sections 5 to 7 did not fix it.

**You need:** a separate PC with Python, PaddlePaddle and PaddleOCR (an NVIDIA GPU makes training
hours instead of days), and 500 to 5,000 labeled text-line images from your own documents.

**Step by step:**
1. **Collect crops.** Cut single text lines out of the failing images, one line per PNG.
   PaddleOCR's labeling tool, PPOCRLabel, speeds this up.
2. **Label them** in a tab-separated text file, one line per image:
   `crops/line_0001.png<TAB>COPV inspected before each fill`
3. **Split** 90% into `train.txt`, 10% into `val.txt`. Never train on the val set.
4. **Install** PaddlePaddle and clone the PaddleOCR repository. Use the README of the exact version you
   install; command names change between releases.
5. **Download the pretrained training weights** for the English PP-OCR recognition model from the PaddleOCR model list.
6. **Copy the matching config** (for example `configs/rec/PP-OCRv4/en_PP-OCRv4_rec.yml`) and set:
   training and validation data paths, `pretrained_model` (the weights from step 5),
   `character_dict_path` (`ppocr/utils/en_dict.txt`), and a small learning rate for fine-tuning.
7. **Train:** `python tools/train.py -c your_config.yml`. Watch validation accuracy; stop when it stops improving.
8. **Export** the best checkpoint as an inference model with `tools/export_model.py`.
9. **Convert to ONNX** with `paddle2onnx`, producing `rec.onnx`.
10. **Install it:** copy `rec.onnx` into `config\models\`. If it does not embed a character list,
    also copy the dictionary used in training as `config\models\rec_keys.txt`.
11. **Score it** (section 11). Adopt it only if it beats the built-in model on both the test samples and
    your real-document set, because a model tuned to one style can get worse on others.

**Data handling:** training data from real documents may be CUI or ITAR-controlled. Keep crops, labels and
the training PC inside approved systems, and treat the trained model file at the same sensitivity as the
data it learned from. Do not commit real crops or models trained on them to GitHub.

---

## 9. Better source files

Some content cannot be read no matter how good the OCR is. The app lists it under
**Status > "Errors / not scanned"**.

| Problem | Fix at the source |
|---|---|
| Linked picture in PowerPoint/Word | Re-insert as an embedded picture (Insert > Pictures, not "Link to File") |
| Visio or vector diagram (EMF/WMF/SVG) | Paste Special as PNG, or export the diagram as PNG at 200-300% |
| Low-quality scans | Rescan at 300 dpi grayscale; avoid heavy JPEG compression |
| Text pasted as screenshots | Paste as text when possible; typed text is read exactly |

---

## 10. Matching rules (code changes in `app_gui.py`)

The remaining misses and noise in the scorer come from rules, not OCR. Planned improvements from the
architecture review, with the scorer lines each one fixes:

| ID | Change | Fixes in the scorer |
|---|---|---|
| F4 | Patterns for mixed-case (DoD, ConOps) and hyphenated designators (MIL-STD-882E) | 2 misses |
| F5 | Skip words that end a sentence (`award.`, `panel.`) | 1 false alarm |
| F6 | Bundled English word list: suppress dictionary words like SCOPE, SAFETY, APPENDIX unless in the DB | 4 false alarms |
| F7 | Read definitions the document states, like "Statement of Work (SOW)" | Fills definitions for new candidates |

After any code change: rescan `test_samples`, run the scorer, and confirm recall did not drop.

---

## 11. Measure: ground truth and the scorer

`test_samples\ground_truth.csv` lists what the app should and should not report:

```
File,Term,Expect,Note
Kestrel_Technical_Volume.docx,CUI,found,header
Kestrel_Technical_Volume.docx,SCOPE,absent,all-caps heading word
```

- `found`: must be reported from that file (counts toward **RECALL**).
- `absent`: must not be reported (counts toward **FALSE ALARMS**).
- `File` can be `*` for any file in the folder.

**Run it:**
```
.\venv\Scripts\python.exe tools\evaluate.py --note "what changed"
```
Every run appends a row to `tools\eval_history.csv`, which is your accuracy record over time.

**Build a real-document set (most valuable step):**
1. Make a folder **outside this repository**, for example `D:\AH_eval`. Real documents may be sensitive;
   never put them in the repo.
2. Copy in 10 to 30 representative real files, including the ones that caused trouble.
3. Create `D:\AH_eval\ground_truth.csv` in the format above. Start with 5 to 10 terms per file you know
   are there, plus the noise words you keep excluding.
4. Run `.\venv\Scripts\python.exe tools\evaluate.py D:\AH_eval --note "real set baseline"`.
5. Add lines every time a project turns up a miss. This file becomes the truest measure of the app.

**Release rule:** do not ship a build whose recall dropped or whose false alarms rose on either set.

---

## 12. Where changes live and how to ship them

| What you changed | Where it is saved | To make it permanent |
|---|---|---|
| Include / Exclude in the app | `acronym_database.csv` in the app folder you ran | Copy it over the project's `acronym_database.csv` |
| Fix OCR in the app | `config\ocr_corrections.csv` in the app folder you ran | Copy it over the project's `config\ocr_corrections.csv` |
| OCR settings or models | `config\` in the project folder | Already in place |

Then rebuild and save to GitHub:
```
powershell -ExecutionPolicy Bypass -File .\build.ps1
git add -A
git commit -m "Describe the accuracy change and the new scores"
git push
```
`build.ps1` copies the whole `config\` folder into the zip, so recipients get your corrections, settings and models.
Large model files add to the zip size and to Git LFS storage.

---

## 13. Quick reference

| Symptom | First thing to try |
|---|---|
| Same OCR misread keeps appearing | **Fix OCR** button (section 5) |
| Real acronym listed as new candidate | **Include in DB** with its definition |
| Heading words or noise listed | **Exclude**; long term, F6 word list (section 10) |
| Scanned PDF pages miss lines | `pdf_scan_dpi` 300 to 400 (section 6) |
| Phone photos read badly | Keep `denoise_strength` 10 or higher; raise `contrast_clip` to 3 |
| Small text in diagrams missed | `upscale_below_px` 1600 or `upscale_factor` 2.5 |
| Junk words from images | `min_confidence` 0.6 |
| Characters consistently wrong in images | Try another `rec.onnx` (section 7) |
| One recurring style always fails | Fine-tune (section 8) |
| "Not scanned" rows | Fix the source file (section 9) |
| DoD, MIL-STD-882E missed | Code change F4 (section 10) |
