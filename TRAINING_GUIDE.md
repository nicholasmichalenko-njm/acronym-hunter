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

Current score on `test_samples` (v1.0.2): **93.2% of expected terms found (41 of 44), 6 of 8 known noise words still reported.**
The 3 misses and 6 false alarms break down as: 2 matching-rule gaps, 1 OCR miss, 6 matching-rule noise.
Matching rules are the biggest remaining lever.

---

## 2. The levers, cheapest first

| # | Lever | Effort | Fixes | File or place |
|---|---|---|---|---|
| 4 | Database | Seconds | Unknown terms, definitions, noise words | `acronym_database.csv`, Include / Exclude buttons |
| 5 | OCR corrections | Seconds | A specific misread that keeps happening (RFF for RFP) | `config\ocr_corrections.csv`, **Fix OCR** button |
| 5b | Trainer: region rescan + samples | Minutes | Text missed or misread in a picture; builds training data | `AcronymHunterTrainer.exe` / **Region Trainer** button |
| 6 | OCR settings | Minutes | Whole classes of OCR misses (small text, scans, photos) | `config\ocr_settings.json` |
| 7 | Swap OCR models | 30 minutes | Systematic OCR weakness | `config\models\` (drop-in files) |
| 8 | Train your own OCR model | Hours to days | OCR on a recurring style; lines read as text | Trainer samples > training PC > `config\models\` |
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
- **Symbols and other alphabets work.** Terms like `°C`, `µm`, `Ω`, `ΔV`, Cyrillic, or math letters are fine.
  - The files are saved as UTF-8 with a byte-order mark, which holds every Unicode character (the same set
    UTF-16 holds). UTF-16 is not needed.
  - In Excel, save with **File > Save As > CSV UTF-8 (Comma delimited)**. Plain "CSV (Comma delimited)"
    writes an old Windows encoding and turns symbols into `?`.
  - The app still reads UTF-16 ("Unicode Text", tab-separated) and old Windows-encoded files, and converts
    them to UTF-8 the next time it saves. A non-UTF-8 file adds a reminder to `logs\error.log`.
  - Look-alike characters match each other: micro sign `µ` / Greek `μ`, ohm sign `Ω` / Greek `Ω`,
    angstrom sign `Å` / `Å`, and the various hyphens and dashes. Results show the standard form.
  - Units may touch numbers: `25°C`, `10µm`, and `150psi` all match their database terms.
  - OCR can only return characters its model knows. The built-in model reads common symbols (°, μ, Ω)
    but rare ones in pictures may come back wrong; use **Fix OCR** or the Trainer for those.

---

## 5. OCR corrections (`config\ocr_corrections.csv`)

For a misread that repeats. Format:

```
Misread,Correct,Note
RFF,RFP,F/P misread seen in test samples
C0PV,COPV,zero read for letter O
```

**From the results table (fastest; turn on the Advanced switch first):**
1. Select the misread row (for example `RFF`).
2. Type the correct term (`RFP`) in the box.
3. Click **Fix OCR**. The row turns to "OCR fix saved".
4. Rescan. The term is reported under `RFP`, and its location is tagged `[OCR fix: RFF]`.

**View, edit, or undo fixes:** click **OCR Fixes** (top right). The window lists every saved fix.
- **Add / Update:** type a misread and its correct term, click Add / Update. An existing misread is updated in place.
- **Edit:** click a line to load it into the boxes, change it, click Add / Update.
- **Delete Selected:** removes the highlighted line.
- **Undo Last Entry:** removes the most recently added line (use it right after an accidental Fix OCR).
Changes save immediately and apply on the next scan.

**By hand:** open `config\ocr_corrections.csv` in Notepad or Excel, edit, save, rescan. No restart needed.

Rules:
- Matching is exact and case-sensitive, one word per line (`RFF`, not `the RFF`).
- If `Correct` is in the database, the hit resolves with that definition; if it is excluded, it stays hidden; otherwise it appears as a new candidate under the corrected spelling.
- Do not add a pair whose misread is also a real term in your documents.
- 0/O, 1/I, 5/S, 8/B swaps for database terms are already automatic. Add pairs only for other confusions.

---

## 5b. The Trainer: re-read a missed spot and save training samples

Use it when the scanner missed or misread text in a picture. It ships in `AcronymHunter_WithTrainer.zip`
(built by `build.ps1`), not in the standard scanner-only zip.

1. Open `AcronymHunterTrainer.exe`, or click **Region Trainer** in the scanner.
2. **Open File**. Pick the page (PDF) or picture (PowerPoint, Word, Excel) in the left list. SVG, EMF, and WMF
   files, and EMF/WMF diagrams inside Office files, are drawn at about 2400 px so small labels can be boxed.
3. **Drag a box** around the missed text. Zoom with **+ / -**, **Fit**, or Ctrl + mouse wheel.
4. Read the right panel. Each line has a number that matches its box on the picture.
   - **Green** = confidence at or above `min_confidence`. The scanner keeps it, so a wrong green reading can
     become a false result.
   - **Red** = below the cutoff. The scanner already drops it. A red line that is correct means the cutoff is
     too strict for that style (section 6).
   - **Whole box as ONE line**: the box read as a single line without text detection. Use it when no lines were found.
5. Pick a choice for each line:

   | Choice | Use it when | What is saved | What it teaches |
   |---|---|---|---|
   | **Skip** | You are unsure, or it does not matter | Nothing for this line; marked "unsure" in the region sample | Nothing either way |
   | **Save as text** | It is real text. Fix the spelling first (typing selects this) | The line crop + correct text (`images\`, `labels.txt`) | The **reader** (recognition model): how this text is spelled |
   | **Not text** | A diagram line, arrow, border, hatching, or speck read as letters or Asian characters | The whole box with that spot as background (`regions\`, `det_labels.txt`). Green lines also go on `config\ocr_ignore.csv` | The **finder** (detection model): no text here. The ignore list stops it in the scanner **right away** |

6. Click **Save Choices** (or **Save Whole Box as One Sample**).
7. Click **Add OCR Fixes from Corrections** to also teach the scanner the word-level fix right away (for example LI to LL).
8. **Undo Last Save** removes everything the last save added, including ignore-list entries.

**The ignore list (`config\ocr_ignore.csv`)** holds exact readings, one per row (`Reading,Note`). The scanner
drops an OCR line whose whole text equals a listed reading. It applies only to text read from pictures, never
to typed document text, so ignoring `III` from a diagram does not hide a typed `III`. Open it with **Ignore List**
in the Trainer; delete a row to undo it. Changing the list makes projects re-read their files on the next rescan.

What gets saved, inside the app folder:
```
training_data\
  images\...png        one cropped text line per "Save as text" (1-50 KB)
  labels.txt           images/x.png<TAB>LL                          (PaddleOCR recognition format)
  regions\...png       the whole box you drew, per Save Choices
  det_labels.txt       regions/y.png<TAB>[{"transcription": "LL", "points": [...]}]   (PaddleOCR detection format)
  samples.csv          date, image, text ("(not text)" for Not text), what OCR read, confidence, source, box
  save_log.jsonl       what each save added, so Undo Last Save can remove it
  package\             train/check lists from Prepare Training Package
```
`labels.txt` is already in the format PaddleOCR's recognition training expects (section 8, step 2), so the
Trainer replaces the manual crop-and-label work.

Rules:
- Save **one line of text per sample**. Tight boxes work best; the Trainer trims empty margins automatically.
- Type exactly what is printed, including case and punctuation.
- Save examples of what goes **wrong**, plus some that go right, so a trained model does not forget.
- `training_data\` holds crops of real documents. It is excluded from builds and from Git. Keep it on
  approved storage, and delete it when done.

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
| `tile_large_images` | 1 | Keep 1: small text on large images is otherwise erased | Set 0 only to compare or to speed up scans of large, clean images | Large images take 2 to 3 times longer |
| `tile_size_px` | 1800 | Rarely; keep under 2000 | Very small text on huge images (try 1200) | Smaller tiles = more passes |
| `tile_overlap_px` | 300 | Words on tile edges come out split | Rarely | More duplicate work |

**Why tiling matters:** the OCR engine shrinks any image whose longest side exceeds 2000 pixels before reading it.
On a 6000-pixel drawing, 14-pixel labels shrink to about 5 pixels and vanish. Cropping the image by hand "fixed" it
for the same reason. Tiling re-reads large images in overlapping full-resolution sections automatically.
Measured on `Kestrel_Large_Diagram.png`: tiling off found 0 of 12 labels; tiling on found 12 of 12.

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
| Tiled OCR added (v1.0.2), plus the large-drawing test file | **93.2%** (41 of 44) | Adopted. Full test scan 16 s to 37 s |

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

## 8. Turn your samples into a better model (step by step)

Your samples improve the scanner in two ways.

**Right away, no training:**
- **Not text** on a green line puts that reading on `config\ocr_ignore.csv`. Gone from the next scan.
- **Add OCR Fixes from Corrections** puts word fixes in `config\ocr_corrections.csv`. Fixed on the next scan.

**Over time, by training new models.** Two models do the reading, and your two kinds of samples train them:

| Model | Job | File in `config\models\` | Trained by | Start training at |
|---|---|---|---|---|
| Finder (detection) | Draws a box around each piece of text; mistakes lines for text | `det.onnx` | Region samples (Save Choices, especially **Not text**) | 100+ regions (300+ better) |
| Reader (recognition) | Reads the letters inside each box; misspells | `rec.onnx` + `rec_keys.txt` | Text-line samples (**Save as text**) | 300+ lines (1,000+ better) |

### Step 1. Collect (in the Trainer)
Work through real documents. Save every misread line as **Save as text** with the correct spelling, and every
false box as **Not text**. Also save some lines the reader got right, so a trained model does not forget them.
The counter at the bottom shows Text lines, Regions, and Not-text examples.

### Step 2. Prepare the package (one click)
Click **Prepare Training Package**. It writes `training_data\package\`:
`rec_train.txt`, `rec_val.txt`, `det_train.txt`, `det_val.txt` (90% train, 10% check, the same split every time),
and `package_report.txt`. It copies no images, so it adds only a few KB. It warns when there are too few samples
and lists any character the current reader cannot output (fix those labels or they are skipped).

### Step 3. Set up a training PC (once)
Training needs PaddlePaddle and PaddleOCR, about 2 GB of tools that do not belong in the app. Use your build PC or
another approved Windows PC. Internet is needed only to install the tools; your samples never leave the PC.
```powershell
py -3.11 -m venv C:\ocr-train\venv
C:\ocr-train\venv\Scripts\python.exe -m pip install paddlepaddle==2.6.2 paddle2onnx==1.2.3
git clone -b release/2.8 https://github.com/PaddlePaddle/PaddleOCR C:\ocr-train\PaddleOCR
C:\ocr-train\venv\Scripts\python.exe -m pip install -r C:\ocr-train\PaddleOCR\requirements.txt
```
Download the **PP-OCRv4 training weights** (the files ending `_train`, not `_infer`) for the Chinese/English
models from the PaddleOCR model list, and unzip them into `C:\ocr-train\pretrain\`. Use the Chinese/English
(`ch_`) models: the app's built-in models are `ch_PP-OCRv4`, so your fine-tuned models stay drop-in compatible.

### Step 4. Copy the samples
Copy the whole `training_data\` folder to `C:\ocr-train\data\` (it already holds the package lists).

### Step 5. Train the reader (recognition)
```powershell
cd C:\ocr-train\PaddleOCR
..\venv\Scripts\python.exe tools/train.py -c configs/rec/PP-OCRv4/ch_PP-OCRv4_rec.yml -o `
  Global.pretrained_model=C:/ocr-train/pretrain/ch_PP-OCRv4_rec_train/student `
  Global.character_dict_path=ppocr/utils/ppocr_keys_v1.txt Global.epoch_num=50 Optimizer.lr.learning_rate=0.0001 `
  Train.dataset.data_dir=C:/ocr-train/data Train.dataset.label_file_list=[C:/ocr-train/data/package/rec_train.txt] `
  Eval.dataset.data_dir=C:/ocr-train/data Eval.dataset.label_file_list=[C:/ocr-train/data/package/rec_val.txt] `
  Global.save_model_dir=C:/ocr-train/out/rec
```
`Global.pretrained_model` points at the `.pdparams` file inside the unzipped weights folder, written without
the `.pdparams` extension (`student` or `best_accuracy`, whichever the folder holds).
Watch the `acc` printed after each check. Stop (Ctrl+C) when it stops rising; the best checkpoint is kept as
`out\rec\best_accuracy`. Keep the dictionary as `ppocr_keys_v1.txt`: changing it throws away what the model knows.

### Step 6. Train the finder (detection), when you have enough regions
Same pattern with `configs/det/ch_PP-OCRv4/ch_PP-OCRv4_det_student.yml`, the `ch_PP-OCRv4_det_train` weights,
`det_train.txt` / `det_val.txt`, and `Global.save_model_dir=C:/ocr-train/out/det`. Watch `hmean`.

### Step 7. Convert to the app's format
```powershell
..\venv\Scripts\python.exe tools/export_model.py -c configs/rec/PP-OCRv4/ch_PP-OCRv4_rec.yml -o `
  Global.pretrained_model=C:/ocr-train/out/rec/best_accuracy Global.save_inference_dir=C:/ocr-train/export/rec
..\venv\Scripts\paddle2onnx.exe --model_dir C:/ocr-train/export/rec --model_filename inference.pdmodel `
  --params_filename inference.pdiparams --save_file C:/ocr-train/export/rec.onnx --opset_version 14
```
(For the finder: the det config and `out/det`, producing `det.onnx`.)

### Step 8. Install and score
1. Copy `rec.onnx` into the app's `config\models\`, and copy `PaddleOCR\ppocr\utils\ppocr_keys_v1.txt` there
   as `rec_keys.txt` (an exported model does not carry its character list). Copy `det.onnx` if you trained one.
2. Run `.\venv\Scripts\python.exe tools\evaluate.py --note "fine-tuned rec, 1200 samples"`. The line
   `OCR models: custom rec.onnx, rec_keys.txt` confirms the model loaded.
3. Re-run the Trainer on a few boxes it got wrong before.
4. **Better on the test samples and your own documents:** keep it and rebuild (`build.ps1` ships `config\`).
   **Worse:** delete the files from `config\models\`; the built-in models return instantly.

### Step 9. Repeat
Keep collecting, re-run Steps 2 and 4 to 8 every few hundred new samples. Each round starts from the previous
best model (`Global.pretrained_model=C:/ocr-train/out/rec/best_accuracy`).

**Status of these commands:** Steps 1, 2 and 8 run in the app and are tested. Steps 3 to 7 use PaddleOCR's
standard tools at the pinned versions; they have not yet been run end to end on this project's data. Do a dry run
with a small package first.

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
| Visio or vector diagram (EMF/WMF/SVG) whose labels were converted to outlines | Read automatically by OCR since v1.3.0. If small labels are missed, export the diagram as PNG at 200-300%, or keep the labels as live text (exact, no OCR) |
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
| Small text on a large image missed, but found when you crop it | Confirm `tile_large_images` is 1; try `tile_size_px` 1200 |
| Small text in small diagrams missed | `upscale_below_px` 1600 or `upscale_factor` 2.5 |
| Fix OCR clicked by mistake | **OCR Fixes** button > **Undo Last Entry** |
| Want to see why a word in a picture was missed | Trainer: box it and read the confidence (red = dropped by the cutoff) |
| Want to build training data | Trainer: save corrected lines as samples (section 5b) |
| Junk words from images | `min_confidence` 0.6 |
| Characters consistently wrong in images | Try another `rec.onnx` (section 7) |
| One recurring style always fails | Fine-tune (section 8) |
| "Not scanned" rows | Fix the source file (section 9) |
| DoD, MIL-STD-882E missed | Code change F4 (section 10) |
