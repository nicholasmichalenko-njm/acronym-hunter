DROP-IN OCR MODELS
==================
Leave this folder empty to use the built-in PP-OCRv4 models.

The app loads any of these files it finds here, by exact name:
  det.onnx       text DETECTION model (finds where text is)
  rec.onnx       text RECOGNITION model (reads the characters)
  cls.onnx       orientation classifier (rarely worth changing)
  rec_keys.txt   character list for rec.onnx; needed only if the model does not carry its own

Rules
  - Rename downloaded files to the names above.
  - Only PaddleOCR-family models converted to ONNX work (RapidOCR format).
  - If a model fails to load, the app falls back to the built-in models and writes logs\error.log.
  - Check which models a scan used: run --selftest and read "OCR models:" in logs\selftest.txt.
  - Score every swap with tools\evaluate.py before sharing a build.

Full steps: TRAINING_GUIDE.md, section 5.
