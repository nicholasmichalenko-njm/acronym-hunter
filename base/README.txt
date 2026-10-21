BASE: THE ONLY DATA THAT SHIPS IN THE GITHUB PACKAGES
======================================================
build.ps1 builds AcronymHunter_Portable.zip and AcronymHunter_WithTrainer.zip from THIS folder only:

  acronym_database.csv          EMPTY: header row only (Term,Definition,Category,Action)
  config\app_settings.json      Advanced switch defaults
  config\ocr_settings.json      OCR tuning numbers
  config\ocr_corrections.csv    two examples from the fictional test samples
  config\models\README.txt      explains drop-in models (no model files)

The working copies in the project root (acronym_database.csv, config\) are what the app uses when run
from source. They fill with real terms, OCR fixes, ignore-list entries, and trained models, so Git
ignores them and the build never packages them.

Real knowledge travels only as a Knowledge Pack (Knowledge > Export Knowledge Pack) saved to the
approved SharePoint folder. Never GitHub.

Change a file here only with generic, non-sensitive content. The build's leak check refuses any
package whose data files differ from this folder, and any model file in a GitHub package.
