# Builds the app ONCE and makes the package:
#   AcronymHunter_US.zip           one program: scanner + Trainer window -> GitHub Release (generic data only)
#   internal_builds\AcronymHunter_Internal_<pack>.zip     -> approved SharePoint ONLY (when -KnowledgePack is given)
# Training features can be switched off for a distribution in base\config\app_settings.json (allow_training).
#
# Data boundary: the GitHub packages are built from base\ ONLY, never from the working database or config\.
# A leak check refuses to finish if anything outside the approved file list, or any model file, would ship.
#
#   powershell -ExecutionPolicy Bypass -File .\build.ps1
#   powershell -ExecutionPolicy Bypass -File .\build.ps1 -KnowledgePack "S:\Approved\AcronymHunter_Knowledge_2026.11.03-1400.zip"
#
# Editions:
#   -Edition us      (default) Tesseract OCR: HP origin, Google-developed, Google-trained English model. CPU training built in.
#                    Plus docTR (Mindee, Apache 2.0) on ONNX Runtime (Microsoft) as a second text finder and reader.
#                    Needs vendor\tesseract once: tools\build_tesseract.ps1 (built from source with no network library).
#   -Edition legacy  RapidOCR + PaddleOCR (Baidu) models on ONNX Runtime, the v1.5.x engine: AcronymHunter_Legacy.zip.
#   -Classic         US edition without docTR: Tesseract is the only reader (for reviewers who want no neural text finder).
param([string]$KnowledgePack = "", [ValidateSet('us', 'legacy')][string]$Edition = 'us', [switch]$Classic)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$env:AH_EDITION = $Edition
$prefix = if ($Edition -eq 'us') { 'AcronymHunter_US' } else { 'AcronymHunter_Legacy' }
$env:AH_CLASSIC = if ($Classic) { '1' } else { '' }
if ($Classic) { $prefix = 'AcronymHunter_US_Classic' }

function Test-PublicPackage([string]$dir) {
    # 1. Only these files may sit outside _internal
    $allowed = @('AcronymHunter.exe', 'acronym_database.csv', 'README.txt', 'OVERVIEW.md', 'SECURITY.md', 'CHECKSUM.txt',
                 'config\app_settings.json', 'config\ocr_settings.json', 'config\ocr_corrections.csv', 'config\models\README.txt')
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
        # US edition: no Chinese-origin OCR code or models; Google's public English model; and only the two docTR
        # models this project exported from Mindee's weights, byte for byte as recorded in vendor\doctr\doctr_models.json
        $foreign = $files | Where-Object { $_ -match 'rapidocr|paddle|pyclipper|shapely' }
        if ($foreign) { throw "ORIGIN CHECK FAILED: legacy OCR files in the US edition: $($foreign -join ', ')" }
        $onnx = @($files | Where-Object { $_ -like '*.onnx' } | Sort-Object)
        $want = if ($Classic) { @() } else { @('_internal\doctr\doctr_det.onnx', '_internal\doctr\doctr_reco.onnx') }
        if (($onnx -join ',') -ne ($want -join ',')) { throw "LEAK CHECK FAILED: unexpected ONNX model file(s): $($onnx -join ', ')" }
        $dinfo = Get-Content "vendor\doctr\doctr_models.json" -Raw | ConvertFrom-Json
        foreach ($m in $(if ($Classic) { @() } else { @('doctr_det', 'doctr_reco') })) {
            $h = (Get-FileHash "$root\_internal\doctr\$m.onnx").Hash
            if ($h -ne $dinfo.models.$m.onnx_sha256) { throw "ORIGIN CHECK FAILED: $m.onnx is not the file this project exported (SHA-256 mismatch)" }
        }
        $tdata = $files | Where-Object { $_ -like '*.traineddata' }
        if (($tdata -join ',') -ne '_internal\tesseract\tessdata\eng.traineddata') { throw "LEAK CHECK FAILED: unexpected model file(s): $($tdata -join ', ')" }
        $engHash = (Get-FileHash "$root\_internal\tesseract\tessdata\eng.traineddata").Hash
        if ($engHash -ne '8280AED0782FE27257A68EA10FE7EF324CA0F8D85BD2FD145D1C2B560BCB66BA') { throw "LEAK CHECK FAILED: eng.traineddata is not Google's tessdata_best file" }
        if (-not (Test-Path "$root\_internal\tesseract\tesseract.exe")) { throw "BUILD CHECK FAILED: Tesseract engine missing" }
        if (-not (Select-String -Path "$root\_internal\tesseract\SOURCE.txt" -Pattern 'DISABLE_CURL=ON' -Quiet)) { throw "BUILD CHECK FAILED: vendor\tesseract is not the no-network source build (run tools\build_tesseract.ps1)" }
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

# Core check: no generative AI runtime or model weights in Core (those ship only as separate add-ons).
& .\venv\Scripts\python.exe tools\check_core.py $out
if ($LASTEXITCODE -ne 0) { throw "CORE CHECK FAILED. See the list above." }

# Logging check: every log message is fixed text from our code, never data (file names, terms, document text).
& .\venv\Scripts\python.exe tools\check_diag.py
if ($LASTEXITCODE -ne 0) { throw "LOGGING CHECK FAILED. See the list above." }

# Network audit: every program file must be on the reviewed list of files allowed to link Windows networking APIs.
# Tesseract files may link none (built without libcurl). Fails the build on anything new.
& .\venv\Scripts\python.exe tools\network_audit.py $out
if ($LASTEXITCODE -ne 0) { throw "NETWORK AUDIT FAILED. See the list above." }

$exeHash = (Get-FileHash "$out\AcronymHunter.exe" -Algorithm SHA256).Hash
"AcronymHunter.exe  SHA256  $exeHash" | Out-File -Encoding ascii "$out\CHECKSUM.txt"
Test-PublicPackage $out
# Software Bill of Materials (CycloneDX): what ships, with versions, licenses and SHA-256 of every program and model file
$edLabel = if ($Classic) { 'US Classic (Tesseract only)' } elseif ($Edition -eq 'legacy') { 'Legacy' } else { 'US' }
& .\venv\Scripts\python.exe tools\make_sbom.py $out "${prefix}_SBOM.cdx.json" $edLabel
if ($LASTEXITCODE -ne 0) { throw "SBOM generation failed. See the output above." }
$zip = "$prefix.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $out -DestinationPath $zip -CompressionLevel Optimal
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
$lines = @("$zip  SHA256  $zipHash",
           "AcronymHunter.exe  SHA256  $exeHash",
           "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
$stage = $out

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
"Done: $zip (GitHub Release file, generic data only)"
"Zip SHA256: $zipHash"
