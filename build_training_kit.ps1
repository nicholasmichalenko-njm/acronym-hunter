# Builds the Acronym Hunter Training Kit ONCE, on a PC with internet access.
# The finished kit (kit_build\AcronymHunter_TrainingKit.zip) runs on any Windows PC with NO internet:
# its own Python has a network lockdown (kit\sitecustomize.py) that refuses every outbound connection.
#
#   powershell -ExecutionPolicy Bypass -File .\build_training_kit.ps1
#
# Downloads (all pinned; fingerprints recorded in KIT_MANIFEST.txt):
#   Python 3.11.9 embeddable (python.org), PaddlePaddle 2.6.2 CPU + paddle2onnx 1.3.1 + PaddleOCR 2.8
#   requirements (PyPI), PaddleOCR release/2.8 source (GitHub), PP-OCRv4 ch training weights (PaddleOCR CDN).
# Contains no document data. Samples are added later by the trainer, on the training PC.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$ProgressPreference = 'SilentlyContinue'

$work = 'kit_build'
$K = "$work\AcronymHunter_TrainingKit"
$dl = "$work\downloads"
Remove-Item -Recurse -Force $K -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $K, $dl | Out-Null

$sources = [ordered]@{
  'python-3.11.9-embed-amd64.zip' = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip'
  'PaddleOCR-release-2.8.zip'     = 'https://github.com/PaddlePaddle/PaddleOCR/archive/refs/heads/release/2.8.zip'
  'ch_PP-OCRv4_rec_train.tar'     = 'https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_train.tar'
  'ch_PP-OCRv4_det_train.tar'     = 'https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_train.tar'
}
$manifest = @("ACRONYM HUNTER TRAINING KIT MANIFEST", "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm') on $env:COMPUTERNAME", "", "DOWNLOADS (SHA-256)")
foreach ($name in $sources.Keys) {
    $file = "$dl\$name"
    if (-not (Test-Path $file)) { "Downloading $name"; Invoke-WebRequest -Uri $sources[$name] -OutFile $file -UseBasicParsing }
    $manifest += "  $name  $((Get-FileHash $file).Hash)  $($sources[$name])"
}

# 1. Portable Python
Expand-Archive "$dl\python-3.11.9-embed-amd64.zip" "$K\python"
$pth = "$K\python\python311._pth"
@('python311.zip', '.', 'Lib\site-packages', 'import site') | Out-File -Encoding ascii $pth
New-Item -ItemType Directory -Force "$K\python\Lib\site-packages" | Out-Null

# 2. Training packages (installed with this PC's Python 3.11 into the kit; same ABI)
$pkgs = @('paddlepaddle==2.6.2', 'paddle2onnx==1.3.1', 'onnx==1.16.2', 'onnxruntime==1.19.2', 'numpy==1.26.4',
          'opencv-python==4.10.0.84', 'opencv-contrib-python==4.10.0.84', 'shapely', 'scikit-image', 'imgaug', 'pyclipper',
          'lmdb', 'tqdm', 'rapidfuzz', 'Pillow', 'pyyaml', 'requests', 'protobuf==3.20.2', 'setuptools==69.5.1')
& py -3.11 -m pip install --disable-pip-version-check --no-warn-script-location --only-binary=:all: --target "$K\python\Lib\site-packages" @pkgs
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

# 3. PaddleOCR 2.8 source, trimmed to what training and export use
Expand-Archive "$dl\PaddleOCR-release-2.8.zip" "$work\src_tmp" -Force
Move-Item "$work\src_tmp\PaddleOCR-release-2.8" "$K\PaddleOCR"
Remove-Item -Recurse -Force "$work\src_tmp"
foreach ($d in 'doc', 'docs', 'deploy', 'applications', 'benchmark', 'test_tipc', 'PPOCRLabel', 'StyleText', 'ppstructure', 'notebook', '.github', 'overrides', 'readme') {
    Remove-Item -Recurse -Force "$K\PaddleOCR\$d" -ErrorAction SilentlyContinue
}

# 4. Starting weights
New-Item -ItemType Directory -Force "$K\pretrain" | Out-Null
foreach ($t in 'ch_PP-OCRv4_rec_train.tar', 'ch_PP-OCRv4_det_train.tar') { tar -xf "$dl\$t" -C "$K\pretrain" }
Get-ChildItem "$K\pretrain" -Recurse -Force -Filter '._*' | Remove-Item -Force   # macOS metadata files inside the archives

# 5. Kit scripts + the network lockdown
Copy-Item training_kit_src\* $K -Recurse -Force
Copy-Item "$K\kit\sitecustomize.py" "$K\python\Lib\site-packages\sitecustomize.py" -Force
New-Item -ItemType Directory -Force "$K\samples", "$K\output" | Out-Null

# 6. Record exact versions
$manifest += "", "PYTHON PACKAGES"
$manifest += (& "$K\python\python.exe" "$K\kit\train.py" --packages)
$manifest += "", "STARTING WEIGHTS"
$manifest += (Get-ChildItem "$K\pretrain" -Recurse -File | ForEach-Object { "  $($_.FullName.Substring((Resolve-Path $K).Path.Length + 1))  $((Get-FileHash $_.FullName).Hash)" })
$manifest | Out-File -Encoding utf8 "$K\KIT_MANIFEST.txt"

# 7. Self-check: lockdown active, PaddlePaddle imports, weights present
& "$K\python\python.exe" "$K\kit\train.py" --check
if ($LASTEXITCODE -ne 0) { throw "Kit self-check failed" }
Remove-Item -Recurse -Force "$K\kit\logs", "$K\kit\__pycache__" -ErrorAction SilentlyContinue

# 8. Zip
$zip = "$work\AcronymHunter_TrainingKit.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $K -DestinationPath $zip -CompressionLevel Optimal
$size = [math]::Round((Get-Item $zip).Length / 1MB)
"Done: $zip ($size MB)  SHA256 $((Get-FileHash $zip).Hash)"
