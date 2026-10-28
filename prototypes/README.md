# Prototypes (not part of the app)

`assign_qt.py`: Stationkeeper Assign rebuilt in PySide6, as a test beside the real app (2.58). It opens an effort's
compliance matrix and offers Page view with clickable sentence boxes (Ctrl+click, rubber-band drag, Ctrl+wheel zoom),
the sentence card and the response structure, with the keys R, C, G, X, M, Ctrl+Z and Ctrl+S.

- Needs `PySide6-Essentials` (6.11.3) in the venv: `venv\Scripts\python.exe -m pip install PySide6-Essentials==6.11.3`
  (no Qt WebEngine, no network parts). The app's build excludes PySide6.
- Run: `venv\Scripts\python.exe prototypes\assign_qt.py "path\to\Effort_Compliance_Matrix.xlsx"`
- Close the matrix in Stationkeeper first: Save writes the same file; the first save keeps a copy named
  "(before the Qt test)".
- Word, Excel and PowerPoint files show once Stationkeeper's Page view has made their PDF copy.
