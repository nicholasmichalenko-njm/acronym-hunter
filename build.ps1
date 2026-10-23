# Builds the app ONCE and makes the packages:
#   AcronymHunter_Portable.zip     scanner only           -> GitHub Release (generic data only)
#   AcronymHunter_WithTrainer.zip  scanner + Trainer      -> GitHub Release (generic data only)
#   internal_builds\AcronymHunter_Internal_<pack>.zip     -> approved SharePoint ONLY (when -KnowledgePack is given)
#
# Data boundary: the GitHub packages are built from base\ ONLY, never from the working database or config\.
# A leak check refuses to finish if anything outside the approved file list, or any model file, would ship.
#
#   powershell -ExecutionPolicy Bypass -File .\build.ps1
#   powershell -ExecutionPolicy Bypass -File .\build.ps1 -KnowledgePack "S:\Approved\AcronymHunter_Knowledge_2026.11.03-1400.zip"
#
# Editions:
#   -Edition us      (default) Tesseract OCR: HP origin, Google-developed, Google-trained English model. CPU training built in.
#                    Packages: AcronymHunter_US_Portable.zip, AcronymHunter_US_WithTrainer.zip. Needs tools\fetch_tesseract.ps1 once.
#   -Edition legacy  RapidOCR + PaddleOCR (Baidu) models on ONNX Runtime, the v1.5.x engine. Packages keep the old names.
param([string]$KnowledgePack = "", [ValidateSet('us', 'legacy')][string]$Edition = 'us')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$env:AH_EDITION = $Edition
$prefix = if ($Edition -eq 'us') { 'AcronymHunter_US' } else { 'AcronymHunter' }

function Test-PublicPackage([string]$dir, [bool]$withTrainer) {
    # 1. Only these files may sit outside _internal
    $allowed = @('AcronymHunter.exe', 'acronym_database.csv', 'README.txt', 'OVERVIEW.md', 'SECURITY.md', 'CHECKSUM.txt',
                 'config\app_settings.json', 'config\ocr_settings.json', 'config\ocr_corrections.csv', 'config\models\README.txt')
    if ($withTrainer) { $allowed += 'AcronymHunterTrainer.exe' }
    $root = (Resolve-Path $dir).Path
    $files = Get-ChildItem $root -Recurse -File | ForEach-Object { $_.FullName.Substring($root.Length + 1) }
    $outside = $files | Where-Object { $_ -notlike '_internal\*' }
    $extra = $outside | Where-Object { $allowed -notcontains $_ }
    if ($extra) { throw "LEAK CHECK FAILED: unexpected file(s) in public package: $($extra -join ', ')" }
    # 2. Data files must be byte-identical to base\
    foreach ($f in 'acronym_database.csv', 'config\app_settings.json', 'config\ocr_settings.json', 'config\ocr_corrections.csv', 'config\models\README.txt') {
        if ((Get-FileHash "$root\$f").Hash -ne (Get-FileHash "base\$f").Hash) { throw "LEAK CHECK FAILED: $f differs from base\$f" }
    }
    # 3. No model files except the public ones bundled with RapidOCR; no working data anywhere
    if ($Edition -eq 'us') {
        # US edition: no Chinese-origin OCR code or models, no ONNX Runtime, and only Google's public English model
        $foreign = $files | Where-Object { $_ -match 'rapidocr|onnxruntime|paddle|pyclipper|shapely|\.onnx$' }
        if ($foreign) { throw "ORIGIN CHECK FAILED: legacy OCR files in the US edition: $($foreign -join ', ')" }
        $tdata = $files | Where-Object { $_ -like '*.traineddata' }
        if (($tdata -join ',') -ne '_internal\tesseract\tessdata\eng.traineddata') { throw "LEAK CHECK FAILED: unexpected model file(s): $($tdata -join ', ')" }
        $engHash = (Get-FileHash "$root\_internal\tesseract\tessdata\eng.traineddata").Hash
        if ($engHash -ne '8280AED0782FE27257A68EA10FE7EF324CA0F8D85BD2FD145D1C2B560BCB66BA') { throw "LEAK CHECK FAILED: eng.traineddata is not Google's tessdata_best file" }
        if (-not (Test-Path "$root\_internal\tesseract\tesseract.exe")) { throw "BUILD CHECK FAILED: Tesseract engine missing" }
    } else {
        $models = $files | Where-Object { $_ -like '*.onnx' -and $_ -notlike '_internal\rapidocr_onnxruntime\models\*' }
        if ($models) { throw "LEAK CHECK FAILED: model file(s) outside the public RapidOCR models: $($models -join ', ')" }
    }
    $bad = $files | Where-Object { $_ -match 'ocr_ignore|knowledge|training_data|\.ahproj|_local_sandbox|\\logs\\|samples\.csv|labels\.txt' }
    if ($bad) { throw "LEAK CHECK FAILED: working data in public package: $($bad -join ', ')" }
    "Leak check passed: $dir ($($files.Count) files, data identical to base\)"
}

& .\venv\Scripts\pyinstaller.exe --noconfirm --clean AcronymHunter.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. See output above." }

$out = 'dist\AcronymHunter'
Copy-Item base\acronym_database.csv $out -Force                 # generic data from base\ only
New-Item -ItemType Directory -Force "$out\config\models" | Out-Null
Copy-Item base\config\* "$out\config" -Recurse -Force
Copy-Item README.txt, OVERVIEW.md, SECURITY.md $out -Force
Remove-Item -Recurse -Force "$out\_local_sandbox", "$out\logs" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue

# Microsoft Defender scan of the finished app (report only, nothing is deleted)
$mp = Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
if (Test-Path $mp) {
    & $mp -Scan -ScanType 3 -File (Resolve-Path $out).Path -DisableRemediation | Out-Null
    if ($LASTEXITCODE -eq 0) { "Defender scan: no threats found" }
    else { throw "Defender flagged the build (exit $LASTEXITCODE). Do not share it. Check Windows Security > Protection history." }
} else { "Defender command-line scanner not found; scan skipped." }

$exeHash = (Get-FileHash "$out\AcronymHunter.exe" -Algorithm SHA256).Hash
$trainerHash = (Get-FileHash "$out\AcronymHunterTrainer.exe" -Algorithm SHA256).Hash
@("AcronymHunter.exe         SHA256  $exeHash",
  "AcronymHunterTrainer.exe  SHA256  $trainerHash") | Out-File -Encoding ascii "$out\CHECKSUM.txt"

# Package 1: scanner + Trainer (GitHub)
Test-PublicPackage $out $true
$zipFull = "${prefix}_WithTrainer.zip"
Remove-Item $zipFull -ErrorAction SilentlyContinue
Compress-Archive -Path $out -DestinationPath $zipFull -CompressionLevel Optimal

# Package 2: scanner only (GitHub)
$stage = 'dist\scanner_only\AcronymHunter'
New-Item -ItemType Directory -Force (Split-Path $stage) | Out-Null
Copy-Item $out $stage -Recurse -Force
Remove-Item "$stage\AcronymHunterTrainer.exe" -Force
"AcronymHunter.exe  SHA256  $exeHash" | Out-File -Encoding ascii "$stage\CHECKSUM.txt"
Test-PublicPackage $stage $false
$zip = "${prefix}_Portable.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal

$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
$zipFullHash = (Get-FileHash $zipFull -Algorithm SHA256).Hash
$lines = @("$zip     SHA256  $zipHash      (scanner only: share this)",
           "$zipFull  SHA256  $zipFullHash  (scanner + Trainer)",
           "AcronymHunter.exe              SHA256  $exeHash",
           "AcronymHunterTrainer.exe       SHA256  $trainerHash",
           "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm')")

# Package 3 (optional): internal build with a Knowledge Pack pre-installed. SharePoint ONLY.
if ($KnowledgePack) {
    if (-not (Test-Path $KnowledgePack)) { throw "Knowledge Pack not found: $KnowledgePack" }
    $istage = 'dist\internal\AcronymHunter'
    New-Item -ItemType Directory -Force (Split-Path $istage) | Out-Null
    Copy-Item $stage $istage -Recurse -Force
    $p = Start-Process -FilePath "$istage\AcronymHunter.exe" -ArgumentList '--install-knowledge', "`"$((Resolve-Path $KnowledgePack).Path)`"" -Wait -PassThru
    $log = Get-Content "$istage\logs\knowledge_install.txt" -Raw
    if ($log -notmatch 'INSTALL OK') { throw "Knowledge Pack install failed:`n$log" }
    Remove-Item -Recurse -Force "$istage\logs", "$istage\_local_sandbox", "$istage\config\knowledge_backups" -ErrorAction SilentlyContinue
    $packName = [IO.Path]::GetFileNameWithoutExtension($KnowledgePack) -replace '^AcronymHunter_Knowledge_', ''
    New-Item -ItemType Directory -Force internal_builds | Out-Null
    $izip = "internal_builds\AcronymHunter_Internal_$packName.zip"
    Remove-Item $izip -ErrorAction SilentlyContinue
    Compress-Archive -Path $istage -DestinationPath $izip -CompressionLevel Optimal
    "Internal build (SharePoint ONLY, never GitHub): $izip"
    "  " + ($log -split "`n" | Select-Object -First 5 | Out-String).Trim()
    "  SHA256 $((Get-FileHash $izip).Hash)" | Out-File -Encoding ascii "$izip.sha256.txt"
}

$lines | Out-File -Encoding ascii "${prefix}_SHA256.txt"
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
"Done: $zip and $zipFull (GitHub Release files, generic data only)"
"Zip SHA256: $zipHash"
