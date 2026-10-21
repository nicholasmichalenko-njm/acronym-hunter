# Builds an Acronym Hunter Training Kit ONCE, on a PC with internet access. The finished kit runs on any Windows PC
# with NO internet: every Python inside it loads kit\sitecustomize.py first, which refuses all outbound connections.
#
#   powershell -ExecutionPolicy Bypass -File .\build_training_kit.ps1         CPU kit  (~410 MB zip)
#   powershell -ExecutionPolicy Bypass -File .\build_training_kit.ps1 -Gpu    GPU kit  (NVIDIA RTX incl. RTX 50 / RTX PRO
#                                                                              Blackwell; ~4 GB, split into 1.9 GB parts)
# CPU kit: Python 3.11 + PaddlePaddle 2.6.2 + PaddleOCR 2.8 + paddle2onnx 1.3.1 (trains, exports, converts).
# GPU kit: trains with PaddlePaddle 3.4 (CUDA 12.9 libraries bundled) + PaddleOCR 3.7, and exports/converts with a
#          second, proven toolchain in export\ (the CPU kit's stack). Weights cross over as plain arrays (.npz).
#          paddle2onnx 2.x is not used: its Windows wheels fail to load with PaddlePaddle 3.2.2 / 3.3.0 / 3.3.1 / 3.4.0,
#          and PaddlePaddle 3.4's legacy-format export fails on PP-OCRv4 models.
# Downloads are pinned; every SHA-256 and package version goes into KIT_MANIFEST.txt. No document data is included.
param([switch]$Gpu)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$ProgressPreference = 'SilentlyContinue'

$work = 'kit_build'
$kitName = if ($Gpu) { 'AcronymHunter_TrainingKit_GPU' } else { 'AcronymHunter_TrainingKit' }
$K = "$work\$kitName"
$dl = "$work\downloads"
Remove-Item -Recurse -Force $K -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $K, $dl | Out-Null

$sources = [ordered]@{
  'python-3.11.9-embed-amd64.zip' = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip'
  'PaddleOCR-release-2.8.zip'     = 'https://github.com/PaddlePaddle/PaddleOCR/archive/refs/heads/release/2.8.zip'
  'ch_PP-OCRv4_rec_train.tar'     = 'https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_train.tar'
  'ch_PP-OCRv4_det_train.tar'     = 'https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_train.tar'
}
if ($Gpu) { $sources['PaddleOCR-3.7.0.zip'] = 'https://github.com/PaddlePaddle/PaddleOCR/archive/refs/tags/v3.7.0.zip' }
$manifest = @("ACRONYM HUNTER TRAINING KIT MANIFEST ($kitName)", "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm') on $env:COMPUTERNAME", "", "DOWNLOADS (SHA-256)")
foreach ($name in $sources.Keys) {
    $file = "$dl\$name"
    if (-not (Test-Path $file)) { "Downloading $name"; Invoke-WebRequest -Uri $sources[$name] -OutFile $file -UseBasicParsing }
    $manifest += "  $name  $((Get-FileHash $file).Hash)  $($sources[$name])"
}

$cpuPkgs = @('paddlepaddle==2.6.2', 'paddle2onnx==1.3.1', 'onnx==1.16.2', 'onnxruntime==1.19.2', 'numpy==1.26.4',
             'opencv-python==4.10.0.84', 'opencv-contrib-python==4.10.0.84', 'shapely', 'scikit-image', 'imgaug', 'pyclipper',
             'lmdb', 'tqdm', 'rapidfuzz', 'Pillow', 'pyyaml', 'requests', 'protobuf==3.20.2', 'setuptools==69.5.1')
$gpuPkgs = @('paddlepaddle-gpu==3.4.0', 'setuptools==69.5.1', 'numpy==1.26.4', 'shapely', 'scikit-image', 'pyclipper', 'lmdb', 'tqdm',
             'rapidfuzz', 'opencv-python==4.10.0.84', 'opencv-contrib-python==4.10.0.84', 'Pillow', 'pyyaml', 'requests', 'albumentations', 'albucore', 'packaging')

function New-Stack([string]$root, [string[]]$pkgs, [string[]]$extra, [string]$ocrZip) {
    Expand-Archive "$dl\python-3.11.9-embed-amd64.zip" "$root\python"
    @('python311.zip', '.', 'Lib\site-packages', 'import site') | Out-File -Encoding ascii "$root\python\python311._pth"
    New-Item -ItemType Directory -Force "$root\python\Lib\site-packages" | Out-Null
    & py -3.11 -m pip install --disable-pip-version-check --no-warn-script-location --retries 10 --timeout 120 --only-binary=:all: --target "$root\python\Lib\site-packages" @extra @pkgs
    if ($LASTEXITCODE -ne 0) { throw "pip install failed for $root" }
    Remove-Item -Recurse -Force "$work\src_tmp" -ErrorAction SilentlyContinue
    Expand-Archive "$dl\$ocrZip.zip" "$work\src_tmp" -Force
    Move-Item (Get-ChildItem "$work\src_tmp" -Directory)[0].FullName "$root\PaddleOCR"
    Remove-Item -Recurse -Force "$work\src_tmp"
    foreach ($d in 'doc', 'docs', 'deploy', 'applications', 'benchmark', 'test_tipc', 'PPOCRLabel', 'StyleText', 'ppstructure',
                   'notebook', '.github', 'overrides', 'readme', 'tests', 'mcp_server', 'langchain-paddleocr', 'skills') {
        Remove-Item -Recurse -Force "$root\PaddleOCR\$d" -ErrorAction SilentlyContinue
    }
    Copy-Item training_kit_src\kit\sitecustomize.py "$root\python\Lib\site-packages\sitecustomize.py" -Force
}

if ($Gpu) {
    New-Stack $K $gpuPkgs @('--extra-index-url', 'https://www.paddlepaddle.org.cn/packages/stable/cu129/') 'PaddleOCR-3.7.0'   # training
    New-Stack "$K\export" $cpuPkgs @() 'PaddleOCR-release-2.8'                                                                  # export + convert
} else {
    New-Stack $K $cpuPkgs @() 'PaddleOCR-release-2.8'
}

# Starting weights
New-Item -ItemType Directory -Force "$K\pretrain" | Out-Null
foreach ($t in 'ch_PP-OCRv4_rec_train.tar', 'ch_PP-OCRv4_det_train.tar') { tar -xf "$dl\$t" -C "$K\pretrain" }
Get-ChildItem "$K\pretrain" -Recurse -Force -Filter '._*' | Remove-Item -Force   # macOS metadata files inside the archives

# Kit scripts
Copy-Item training_kit_src\* $K -Recurse -Force
New-Item -ItemType Directory -Force "$K\samples", "$K\output" | Out-Null

# Exact versions
$manifest += "", "PYTHON PACKAGES (training)"
$manifest += (& "$K\python\python.exe" "$K\kit\train.py" --packages)
if ($Gpu) { $manifest += "", "PYTHON PACKAGES (export\)"; $manifest += (& "$K\export\python\python.exe" "$K\kit\train.py" --packages) }
$manifest += "", "STARTING WEIGHTS"
$manifest += (Get-ChildItem "$K\pretrain" -Recurse -File | ForEach-Object { "  $($_.FullName.Substring((Resolve-Path $K).Path.Length + 1))  $((Get-FileHash $_.FullName).Hash)" })
$manifest | Out-File -Encoding utf8 "$K\KIT_MANIFEST.txt"

# Self-check: lockdown active, toolchain(s) load, weights present
& "$K\python\python.exe" "$K\kit\train.py" --check
if ($LASTEXITCODE -ne 0) { throw "Kit self-check failed" }
Remove-Item -Recurse -Force "$K\kit\logs", "$K\kit\__pycache__" -ErrorAction SilentlyContinue

# Zip (and split for GitHub Releases, which limit each file to 2 GB)
$zip = "$work\$kitName.zip"
Remove-Item "$zip*", "$work\Join_$kitName.cmd" -ErrorAction SilentlyContinue
Compress-Archive -Path $K -DestinationPath $zip -CompressionLevel Optimal
$size = [math]::Round((Get-Item $zip).Length / 1MB)
$zipHash = (Get-FileHash $zip).Hash
"Done: $zip ($size MB)  SHA256 $zipHash"
$limit = 1900MB
if ((Get-Item $zip).Length -gt $limit) {
    $in = [IO.File]::OpenRead((Resolve-Path $zip).Path); $buf = New-Object byte[] (64MB); $n = 0
    try {
        while ($in.Position -lt $in.Length) {
            $n++; $part = Join-Path (Resolve-Path $work).Path ("$kitName.zip.{0:D3}" -f $n); $out = [IO.File]::Create($part)
            try { $written = 0; while ($written -lt $limit -and ($r = $in.Read($buf, 0, [Math]::Min($buf.Length, $limit - $written))) -gt 0) { $out.Write($buf, 0, $r); $written += $r } }
            finally { $out.Close() }
        }
    } finally { $in.Close() }
    $parts = (1..$n | ForEach-Object { "$kitName.zip.{0:D3}" -f $_ }) -join '+'
    @("@echo off", "rem Joins the downloaded parts into $kitName.zip and checks its SHA-256. Keep all parts in this folder.",
      "cd /d `"%~dp0`"", "copy /b $parts $kitName.zip",
      "powershell -NoProfile -Command `"if ((Get-FileHash '$kitName.zip').Hash -eq '$zipHash') { 'OK: fingerprint matches. Unzip $kitName.zip.' } else { 'FINGERPRINT MISMATCH: download the parts again.' }`"",
      "pause") | Out-File -Encoding ascii "$work\Join_$kitName.cmd"
    "Split into $n parts + Join_$kitName.cmd for GitHub Releases"
}
