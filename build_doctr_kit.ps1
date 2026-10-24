# Builds the Acronym Hunter docTR Training Kit ONCE, on a PC with internet access. The finished kit runs on any Windows
# PC with NO internet: every Python inside it loads sitecustomize.py first, which refuses all outbound connections.
#
#   powershell -ExecutionPolicy Bypass -File .\build_doctr_kit.ps1        CPU kit
#   powershell -ExecutionPolicy Bypass -File .\build_doctr_kit.ps1 -Gpu   GPU kit (NVIDIA, CUDA 12.8 libraries inside;
#                                                                         Blackwell RTX 50 / RTX PRO). Split into 1.9 GB parts.
# Contents: Python 3.11.9 (embedded) + PyTorch 2.11.0 (CPU or cu128) + docTR (wheel built from the pinned source in
# _local_sandbox\mathbench\doctr_src) + docTR's reference training scripts + Mindee's two starting weights (SHA-256
# checked) + the app's bundled docTR models (base_models) + kit\train_doctr.py. No Hugging Face Hub library (an
# offline stand-in takes its place). Every download, package version and SHA-256 goes into KIT_MANIFEST.txt.
# No document data is included.
param([switch]$Gpu, [string]$DoctrSrc = "_local_sandbox\mathbench\doctr_src")
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$ProgressPreference = 'SilentlyContinue'

$work = 'kit_build'
$kitName = if ($Gpu) { 'AcronymHunter_TrainingKit_docTR_GPU' } else { 'AcronymHunter_TrainingKit_docTR' }
$K = "$work\$kitName"
$dl = "$work\downloads"
Remove-Item -Recurse -Force $K -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $K, $dl, "$work\wheels" | Out-Null
if (-not (Test-Path "$DoctrSrc\pyproject.toml")) { throw "docTR source not found at $DoctrSrc" }

$manifest = @("ACRONYM HUNTER TRAINING KIT (docTR) MANIFEST ($kitName)", "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm') on $env:COMPUTERNAME", "")

# 1. Embedded Python
$py = 'python-3.11.9-embed-amd64.zip'
if (-not (Test-Path "$dl\$py")) { Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/$py" -OutFile "$dl\$py" -UseBasicParsing }
$manifest += "DOWNLOADS (SHA-256)", "  $py  $((Get-FileHash "$dl\$py").Hash)  https://www.python.org/ftp/python/3.11.9/$py"
Expand-Archive "$dl\$py" "$K\python"
@('python311.zip', '.', 'Lib\site-packages', 'import site') | Out-File -Encoding ascii "$K\python\python311._pth"
New-Item -ItemType Directory -Force "$K\python\Lib\site-packages" | Out-Null
$site = "$K\python\Lib\site-packages"

# 2. docTR wheel from the pinned source (no dependencies pulled in this step)
Remove-Item "$work\wheels\python_doctr-*.whl" -ErrorAction SilentlyContinue
& py -3.11 -m pip wheel --disable-pip-version-check --no-deps -w "$work\wheels" $DoctrSrc
if ($LASTEXITCODE -ne 0) { throw "docTR wheel build failed" }
$whl = (Get-ChildItem "$work\wheels\python_doctr-*.whl" | Select-Object -First 1).FullName
$commit = (& git -C $DoctrSrc rev-parse HEAD) 2>$null
$manifest += "  $(Split-Path $whl -Leaf)  $((Get-FileHash $whl).Hash)  built from github.com/mindee/doctr @ $commit"

# 3. Packages, pinned (the same versions that trained the phase 1 reader). huggingface_hub is deliberately left out.
$index = if ($Gpu) { 'https://download.pytorch.org/whl/cu128' } else { 'https://download.pytorch.org/whl/cpu' }
$tv = if ($Gpu) { @('torch==2.11.0+cu128', 'torchvision==0.26.0+cu128') } else { @('torch==2.11.0+cpu', 'torchvision==0.26.0+cpu') }
$pkgs = $tv + @('numpy==2.4.6', 'scipy==1.17.1', 'h5py==3.16.0', 'opencv-python==5.0.0.93', 'pypdfium2==5.14.0',
                'pyclipper==1.4.0', 'shapely==2.2.0', 'langdetect==1.0.9', 'RapidFuzz==3.14.6', 'pillow==12.3.0',
                'anyascii==0.3.3', 'validators==0.36.0', 'tqdm==4.70.1', 'onnx==1.23.2', 'onnxscript==0.7.2', 'onnx-ir==1.1.0',
                'onnxruntime==1.31.0', 'matplotlib==3.11.2')
& py -3.11 -m pip install --disable-pip-version-check --no-warn-script-location --retries 10 --timeout 180 --only-binary=:all: `
    --target $site --extra-index-url $index @pkgs
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
& py -3.11 -m pip install --disable-pip-version-check --no-warn-script-location --no-deps --target $site $whl
if ($LASTEXITCODE -ne 0) { throw "docTR install failed" }
if (Test-Path "$site\huggingface_hub") { throw "huggingface_hub was pulled in; the kit must not contain it" }
Copy-Item training_kit_doctr_src\kit\offline_shims\huggingface_hub "$site\huggingface_hub" -Recurse
Copy-Item training_kit_doctr_src\kit\sitecustomize.py "$site\sitecustomize.py" -Force
Get-ChildItem $site -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 4. Starting weights (Mindee), checked against the SHA-256 in their file names' prefixes and train_doctr.py
New-Item -ItemType Directory -Force "$K\weights\models", "$K\base_models", "$K\doctr_ref" | Out-Null
$want = @{ 'db_mobilenet_v3_large-21748dd0.pt' = '21748DD02C0E40475D9EA53E72817C4F08BA90ADEA5231D0DC2C1A65D7D6B4E1'
           'crnn_vgg16_bn-0417f351.pt' = '0417F3511F5C75369BDCBE06539853B9C2D170AA3BACEB2ACC454C775DDAC087' }
$manifest += "", "STARTING WEIGHTS (Mindee, Apache 2.0, from doctr-static.mindee.com)"
foreach ($w in $want.Keys) {
    $src = Join-Path $env:USERPROFILE ".cache\doctr\models\$w"
    if (-not (Test-Path $src)) { throw "Starting weights missing: $src" }
    $h = (Get-FileHash $src).Hash
    if ($h -ne $want[$w]) { throw "Starting weights $w do not match their SHA-256" }
    Copy-Item $src "$K\weights\models\$w"
    $manifest += "  weights\models\$w  $h"
}

# 5. The app's bundled docTR models (the baseline a trained model must beat) and docTR's reference training scripts
foreach ($f in 'doctr_det.onnx', 'doctr_reco.onnx', 'doctr_models.json') { Copy-Item "vendor\doctr\$f" "$K\base_models\$f" }
$manifest += "", "BASE MODELS (the app's bundled docTR models)"
$manifest += (Get-ChildItem "$K\base_models" -File | ForEach-Object { "  base_models\$($_.Name)  $((Get-FileHash $_.FullName).Hash)" })
foreach ($d in 'recognition', 'detection') { Copy-Item "$DoctrSrc\references\$d" "$K\doctr_ref\$d" -Recurse }
Copy-Item "$DoctrSrc\LICENSE" "$K\doctr_ref\LICENSE_docTR.txt"
Get-ChildItem "$K\doctr_ref" -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 6. Kit scripts and folders
New-Item -ItemType Directory -Force "$K\kit", "$K\samples", "$K\output" | Out-Null
Copy-Item training_kit_doctr_src\kit\train_doctr.py "$K\kit\train_doctr.py"
Copy-Item training_kit_doctr_src\Train.cmd, training_kit_doctr_src\README_TRAINING_KIT.txt $K

# 7. Exact versions, then the self-check (lockdown refuses a connection, PyTorch and docTR load, weights match)
$manifest += "", "PYTHON PACKAGES"
$manifest += (& "$K\python\python.exe" "$K\kit\train_doctr.py" --packages)
$manifest | Out-File -Encoding utf8 "$K\KIT_MANIFEST.txt"
& "$K\python\python.exe" "$K\kit\train_doctr.py" --check
if ($LASTEXITCODE -ne 0) { throw "Kit self-check failed" }
Remove-Item -Recurse -Force "$K\output\*", "$K\kit\__pycache__" -ErrorAction SilentlyContinue
Get-ChildItem $K -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# 8. Zip (split for GitHub Releases, which limit each file to 2 GiB)
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
