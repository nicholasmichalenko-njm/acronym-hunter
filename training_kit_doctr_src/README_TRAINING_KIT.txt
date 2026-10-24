ACRONYM HUNTER TRAINING KIT (docTR)
===================================
Teaches Acronym Hunter's second reader (docTR) from your corrections. Runs on any Windows 10/11 PC with NO internet.

TWO VERSIONS
  AcronymHunter_TrainingKit_docTR_GPU   NVIDIA RTX graphics card (Blackwell: RTX 50, RTX PRO; tested on an RTX 5070 Ti,
                                        sized for 8 GB cards such as the Dell Pro's). Minutes instead of hours.
                                        Needs NVIDIA driver 580 or newer (nvidia-smi shows CUDA 13.0 or higher); the CUDA
                                        libraries are inside the kit. Train.cmd > 1 Check says if the driver is too old.
                                        Download: the .001/.002/... parts plus Join_AcronymHunter_TrainingKit_docTR_GPU.cmd
                                        in one folder; double-click the Join file (it checks the fingerprint), then unzip.
  AcronymHunter_TrainingKit_docTR       Processor only, smaller. Any Windows PC.

OFFLINE BY DESIGN
  The kit carries its own Python. python\Lib\site-packages\sitecustomize.py loads before anything else and refuses
  every outbound connection, DNS lookup and UDP packet; attempts are logged to kit\logs\network_blocked.log.
  The Hugging Face Hub library is not included (an offline stand-in with no network code takes its place).
  docTR's starting weights are inside (weights\models, SHA-256 checked). Nothing is downloaded, ever.
  Train.cmd > 1 Check proves the lockdown on the PC you are using.
  No installation, no admin rights, nothing written outside this folder.
  KIT_SBOM.cdx.json lists every package inside (CycloneDX), with the starting weights' SHA-256.

WHAT TRAINING DOES
  Reader: learns from corrected text lines (Correct + Teach in the preview pane, or the Trainer). It learns the look of
          your fonts and drawings, so similar words read better too, not only the ones you corrected.
  Finder: learns from regions you boxed in the Trainer (missed text, and "Not text" lines and arrows).
  The kit holds back 1 sample in 10, scores the reader before and after on those, and keeps the new model ONLY if it
  scores better. REPORT.txt says what improved.

STEP BY STEP
  1. Copy each collector's training_data\ folder into samples\, one subfolder per person:
       samples\nicholas\   samples\jsmith\   (each holds labels.txt, images\, det_labels.txt, regions\)
  2. Double-click Train.cmd. Choose 1 first (Check), then 2, 3 or 4.
     Minimums: 20 corrected words for the reader (more is better), 10 regions for the finder.
  3. The kit writes output\models\: doctr_det.onnx, doctr_reco.onnx, doctr_models.json, REPORT.txt.
  4. In Acronym Hunter: Tools > Knowledge > Load Trained Models > pick output\models.
     The app checks every file's SHA-256 and uses the trained models at once. Undo Last Knowledge Change puts the
     previous models back.
  5. Rescan a folder you know. Keep the models if results improve.
  6. Share: Knowledge > Export Knowledge Pack, saved to the APPROVED SHAREPOINT FOLDER. Colleagues install it.

DATA HANDLING
  samples\ and work\ hold cropped document images: they are your company's data. Keep the kit folder on this PC or
  the approved SharePoint folder. Never GitHub, email or personal storage. Delete work\ when finished.

TESTING ON A BIGGER CARD
  set AH_GPU_MEM_GB=8 before Train.cmd caps PyTorch at 8 GB of graphics memory, to prove a run fits an 8 GB card.
