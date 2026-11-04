# Decisions

Settled decisions, one line each: date or version, the decision, why, and where the full record is (project docs unless
a path says otherwise). Add a line when a decision is made; change a line only with a new reason, and say so.

| When | Decision | Why | Record |
|---|---|---|---|
| 1.6 to 2.1 | US editions read with Tesseract (built from source, no libcurl) and docTR on ONNX Runtime; no PaddleOCR | No Chinese-derived components in US builds | supply-chain-origin-and-memory-safety.md, release notes 1.6.0, 2.1.0 |
| 1.x | GitHub holds code and generic base data only; team data and trained models stay on the approved SharePoint folder | Data boundary | distribution-data-boundary.md |
| 2.15 | Training is its own app (Stationkeeper Training); the main app only saves corrections | Keeps training tools and their data out of the everyday program | release notes 2.15.0 |
| 2.55 | No generative AI in the app | Trust, SCIF use, predictable results | plan-2.54-rfp-sections-2.55-no-generative-ai.md |
| 2.74 to 3.14 | Qt (PySide6) is the app; CustomTkinter Classic retired (2.75) and its window removed (3.14) | One interface to build and test | release notes 2.74.0, 2.75.0, 3.14.0 |
| 2026-10-29 | No live co-editing; team sync by item-level merge through the team folder, one writer per file | Live editing needs a server or network code; teams split work by section | coediting-decision-record.html, team-sync-model-2.83.html |
| 2026-10-29 | Security modes and the SCIF edition as decided | SCIF use | security-modes-decision-2026-10-29.md |
| 3.36.0 | The formatting for every effort is the "global standards"; Effort Formatting holds one effort's own; Make it global sends a value back | Library work and effort work were mixed up | stationkeeper-effort-formatting-plan.html |
| 2026-11-03 | Releases alternate: production, then authors or proposal managers | Both audiences keep moving | stationkeeper-decisions-2026-11-03.md |
| 2026-11-03 | Usability pass deferred | One builder; the team has no time now; revisit when needed | stationkeeper-decisions-2026-11-03.md |
| 2026-11-03 | Production rules are numbered Rule 1 to 13 and live on one Rules page; an effort departs from one only on Effort Formatting | One list, no second copies of values | stationkeeper-production-rules.md |
| 2026-11-03 | Rules check Word files only for now; Excel and PowerPoint later | Bulk up Word first | stationkeeper-decisions-2026-11-03.md |
| 2026-11-03 | A style's family comes from the user's "Used on" column, never from its name; our style names start with AA (kept by people) | The naming convention is ours; the tool must not guess from names | stationkeeper-production-rules.md (R5, R13) |
| 2026-11-03 | Rule 7: the footer's left cell holds the A number (STYLEREF), middle two standard lines, right the page number | The team's footer | stationkeeper-production-rules.md |
| 3.37.0 | Every test runs before every build, found by folder; any failure stops the build | A release must not depend on someone reading the log | stationkeeper-scale-hygiene-review.html |
| 3.37.0 | House rules live in CLAUDE.md; decisions here; what's in flight in the project's stationkeeper-now.md (kept out of git so parallel release branches don't conflict) | Consistency across summary breaks and new sessions | stationkeeper-scale-hygiene-review.html |
| 3.38.1 | Guardrails: house rules test, golden sets per minor version, a format registry, a file size ratchet, a reading floor | Consistency as the code grows; no lost work across versions | stationkeeper-scale-hygiene-review.html |
| 3.38.1 | No upgrade code until a format really changes; the registry and golden sets make the first change safe | Upgrade steps for changes that never happen are dead weight | formats.py |
