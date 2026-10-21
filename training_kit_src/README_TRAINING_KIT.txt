ACRONYM HUNTER TRAINING KIT
===========================
Turns Trainer samples into better OCR models. Runs on any Windows 10/11 PC with NO internet.

TWO VERSIONS
  AcronymHunter_TrainingKit_GPU  For PCs with an NVIDIA RTX card (tested: RTX 5070 Ti Laptop; works with RTX 50 and
                                 RTX PRO Blackwell cards such as the Dell Pro Max 16's RTX PRO 1000). About 100x faster:
                                 1,000 text lines x 20 passes in about 6 minutes instead of about 8 hours.
                                 Needs only a current NVIDIA driver; the CUDA libraries are inside the kit.
                                 ASUS laptops: Armoury Crate > GPU Mode > Standard (Eco switches the NVIDIA card off).
                                 Without a visible GPU it still works, on the CPU.
                                 Batch size follows the card's memory (12 GB+: reader 128; 8 GB such as the RTX PRO
                                 1000: reader 32). If a card still runs out of memory, the kit halves it and retries.
                                 Driver check: in a Command Prompt run  nvidia-smi  ; "CUDA Version" at the top right
                                 must be 12.9 or higher. If lower, ask IT for a current NVIDIA driver.
                                 Download: parts .001/.002/... plus Join_AcronymHunter_TrainingKit_GPU.cmd. Put them in
                                 one folder, double-click the Join file (it checks the fingerprint), then unzip.
  AcronymHunter_TrainingKit      CPU only, smaller (about 410 MB). Any Windows PC. Overnight for 1,000 lines.

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
     The kit prints an estimated time before it starts (GPU: minutes; CPU: hours).
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
  python\      portable Python 3.11. CPU kit: PaddlePaddle 2.6.2 + paddle2onnx + ONNX Runtime.
               GPU kit: PaddlePaddle 3.4 with CUDA 12.9 libraries (training only)
  PaddleOCR\   training tools (CPU kit: PaddleOCR 2.8; GPU kit: PaddleOCR 3.7)
  export\      GPU kit only: the CPU kit's proven toolchain, used to export and convert the trained models
  pretrain\    PP-OCRv4 starting weights (reader: student.pdparams, finder: best_accuracy.pdparams)
  kit\         train.py (driver), sitecustomize.py (network lockdown), logs\
  samples\     your samples (you add these)
  work\        merged data, configs, checkpoints (rebuilt each run)
  output\      finished models
  KIT_MANIFEST.txt  every download with its SHA-256, and every package version
