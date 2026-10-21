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
| Releases | `AcronymHunter_Portable.zip` (scanner), `AcronymHunter_WithTrainer.zip` (scanner + Trainer), `AcronymHunter_TrainingKit.zip` (offline, network-locked training). Generic data only |
| `base/` | The only data packaged for GitHub: an empty acronym database and generic settings. `build.ps1` enforces it with a leak check |
| `training_kit_src/`, `build_training_kit.ps1` | Training Kit sources and builder |
| `README.txt` | Instructions shipped to recipients inside the zip |
| `test_samples/` | Fictional test files, `EXPECTED_RESULTS.txt`, and `ground_truth.csv` |

## Rebuild from source (Windows, Python 3.11)
```powershell
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

## Data boundary
Knowledge Packs (trained models, the real acronym database, OCR fixes, ignore list) live **only** in the approved
SharePoint folder. They are never committed or attached to a release. The working `acronym_database.csv` and `config/`
are ignored by Git.

## Notes
- The exe is not code-signed. See `PROJECT_GUIDE.txt` > Signing and security approval.
- Test sample content and any CUI/ITAR markings in it are fictional.
- `venv/` is not committed; `requirements.txt` recreates it exactly.
