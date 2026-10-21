ACRONYM HUNTER TRAINING KIT
===========================
Turns Trainer samples into better OCR models. Runs on any Windows 10/11 PC with NO internet.

OFFLINE BY DESIGN
  The kit carries its own Python. kit\sitecustomize.py loads before anything else and refuses every
  outbound connection, DNS lookup, and UDP packet. Any attempt is logged to kit\logs\network_blocked.log.
  "Train.cmd > 1 Check" proves it on the PC you are using.
  No installation, no admin rights, nothing written outside this folder.

STEP BY STEP
  1. Copy each collector's training_data\ folder into samples\, one subfolder per person:
       samples\nicholas\   samples\jsmith\   (each holds labels.txt, images\, det_labels.txt, regions\)
     Duplicates across people are removed automatically.
  2. Double-click Train.cmd. Choose 2 (reader), 3 (finder), or 4 (both).
     Minimums: 300 text lines for the reader, 100 regions for the finder.
     A laptop CPU trains 1,000 text lines in roughly 30 to 90 minutes.
  3. The kit writes output\models\: rec.onnx + rec_keys.txt (reader), det.onnx (finder), model_info.json.
  4. In the scanner (Advanced on): Knowledge > Load Trained Models > pick output\models.
  5. Score: tools\evaluate.py (from source) or rescan a known folder. Keep the models only if results improve.
     Knowledge > Undo Last Knowledge Change restores the previous models instantly.
  6. Knowledge > Export Knowledge Pack > save it to the APPROVED SHAREPOINT FOLDER. Colleagues install it
     with Knowledge > Install Knowledge Pack.

DATA HANDLING
  samples\, work\, and output\ hold crops of internal documents and models learned from them.
  Keep this folder on approved storage. Never upload samples, work files, or output models to GitHub.
  The kit as distributed contains no document data.

FOLDERS
  python\      portable Python 3.11 + PaddlePaddle 2.6.2 (CPU) + paddle2onnx + ONNX Runtime
  PaddleOCR\   PaddleOCR 2.8 training and export tools
  pretrain\    PP-OCRv4 starting weights (reader: student.pdparams, finder: best_accuracy.pdparams)
  kit\         train.py (driver), sitecustomize.py (network lockdown), logs\
  samples\     your samples (you add these)
  work\        merged data, configs, checkpoints (rebuilt each run)
  output\      finished models
  KIT_MANIFEST.txt  every download with its SHA-256, and every package version
