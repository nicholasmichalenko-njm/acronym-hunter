# Acronym Hunter

Offline Windows desktop app (scanner + Trainer) that scans PDF, Word, PowerPoint, Excel, image, and vector (SVG, EMF, WMF)
files, finds acronyms, abbreviations, and units, matches them against a curated database, and flags ambiguous or new terms.
Projects (v1.3.0) remember a document folder between scans: rescans read only new or changed files and mark every term
New, Changed, Unchanged, or No longer found.
Runs 100% locally: no network connections, no files written outside its own folder except reports and project files the user saves.

## Start here
| File | Purpose |
|---|---|
| `OVERVIEW.md` | **Start here.** Plain-language overview of the whole app, plus the full security assessment for IT and security teams |
| `SECURITY.md` | Security and data-handling statement: architecture, every file written, offline proof, verification steps |
| `PROJECT_GUIDE.txt` | Why every file exists, how to modify, rebuild, test, and share |
| `TRAINING_GUIDE.md` | How to make it more accurate over time: OCR corrections, settings, model swaps, training, scoring |
| `config/` | OCR corrections, OCR settings, optional drop-in OCR models (shipped inside the zip) |
| `tools/evaluate.py` | Scores accuracy against `test_samples/ground_truth.csv`; history in `tools/eval_history.csv` |
| `AcronymHunter_Portable.zip` | Ready-to-run scanner (stored with Git LFS). Unzip, run `AcronymHunter.exe`. The Trainer package (`AcronymHunter_WithTrainer.zip`) is produced by `build.ps1` and not committed |
| `README.txt` | Instructions shipped to recipients inside the zip |
| `test_samples/` | Fictional test files, `EXPECTED_RESULTS.txt`, and `ground_truth.csv` |

## Rebuild from source (Windows, Python 3.11)
```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

## Notes
- The exe is not code-signed. See `PROJECT_GUIDE.txt` > Signing and security approval.
- Test sample content and any CUI/ITAR markings in it are fictional.
- `venv/` is not committed; `requirements.txt` recreates it exactly.
