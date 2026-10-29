# Builds the app ONCE and makes the package:
#   Stationkeeper_US.zip           Stationkeeper: scans, saves corrections -> GitHub Release (generic data only)
#   Stationkeeper_US_Training.zip  Stationkeeper Training (-App training): imports corrections, trains the reader,
#                                  exports Knowledge Packs -> GitHub Release (generic data only) (2.15.0)
#   internal_builds\Stationkeeper_Internal_<pack>.zip     -> approved SharePoint ONLY (when -KnowledgePack is given)
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
#   -Edition legacy  RapidOCR + PaddleOCR (Baidu) models on ONNX Runtime, the v1.5.x engine: Stationkeeper_Legacy.zip.
#   -Classic         US edition without docTR: Tesseract is the only reader (for reviewers who want no neural text finder).
#                    On request only: routine releases ship Stationkeeper_US.zip and Stationkeeper_US_Training.zip (AcronymHunter_* before 2.44.0) (from 2.15.0).
#   -App training    Stationkeeper Training instead of Stationkeeper (same code, its own program and package).
param([string]$KnowledgePack = "", [ValidateSet('us', 'legacy')][string]$Edition = 'us', [switch]$Classic,
      [ValidateSet('user', 'training')][string]$App = 'user')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$env:AH_EDITION = $Edition
$prefix = if ($Edition -eq 'us') { 'Stationkeeper_US' } else { 'Stationkeeper_Legacy' }
$env:AH_CLASSIC = if ($Classic) { '1' } else { '' }
if ($Classic) { $prefix = 'Stationkeeper_US_Classic' }
$env:AH_APP = $App
$exeName = if ($App -eq 'training') { 'StationkeeperTraining' } else { 'Stationkeeper' }
# 2.74.0: Stationkeeper.exe (StationkeeperTraining.exe) is the Qt window. 2.75.0: the classic window no longer ships.
$qtExe = $exeName
$qtTest = if ($App -eq 'training') { 'qt_training_selftest.txt' } else { 'qt_selftest.txt' }
if ($App -eq 'training') { $prefix = "${prefix}_Training" }

function Test-PublicPackage([string]$dir) {
    # 1. Only these files may sit outside _internal
    # 2.90.0: the program, its read-me folder and nothing else (no data, no config: the app makes those in Stationkeeper Data)
    $allowed = @("$exeName.exe", 'About Stationkeeper\README.txt', 'About Stationkeeper\OVERVIEW.md', 'About Stationkeeper\SECURITY.md',
                 'About Stationkeeper\CHECKSUM.txt')
    $root = (Resolve-Path $dir).Path
    $files = Get-ChildItem $root -Recurse -File | ForEach-Object { $_.FullName.Substring($root.Length + 1) }
    $outside = $files | Where-Object { $_ -notlike '_internal\*' }
    $extra = $outside | Where-Object { $allowed -notcontains $_ }
    if ($extra) { throw "LEAK CHECK FAILED: unexpected file(s) in public package: $($extra -join ', ')" }
    # 2. The read-me files are this project's own, byte for byte (in the program and in About Stationkeeper)
    foreach ($f in 'README.txt', 'OVERVIEW.md', 'SECURITY.md') {
        foreach ($c in "_internal\docs\$f", "About Stationkeeper\$f") {
            if ((Get-FileHash "$root\$c").Hash -ne (Get-FileHash $f).Hash) { throw "LEAK CHECK FAILED: $c differs from $f" }
        }
    }
    if (Test-Path "$root\config") { throw "LEAK CHECK FAILED: a config folder in the public package" }
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
        # 2.15.0: training belongs to Stationkeeper Training. The user app ships no training tools and no training code.
        $tools = @($files | Where-Object { $_ -match '\\(lstmtraining|lstmeval|combine_tessdata)\.exe$' })
        if ($App -eq 'user' -and $tools) { throw "SPLIT CHECK FAILED: training tools in Stationkeeper: $($tools -join ', ')" }
        if ($App -eq 'training' -and $tools.Count -ne 3) { throw "BUILD CHECK FAILED: Stationkeeper Training needs lstmtraining, lstmeval and combine_tessdata" }
        if (-not (Select-String -Path "$root\_internal\tesseract\SOURCE.txt" -Pattern 'DISABLE_CURL=ON' -Quiet)) { throw "BUILD CHECK FAILED: vendor\tesseract is not the no-network source build (run tools\build_tesseract.ps1)" }
    } else {
        $models = $files | Where-Object { $_ -like '*.onnx' -and $_ -notlike '_internal\rapidocr_onnxruntime\models\*' }
        if ($models) { throw "LEAK CHECK FAILED: model file(s) outside the public RapidOCR models: $($models -join ', ')" }
    }
    $bad = $files | Where-Object { $_ -match 'ocr_ignore|knowledge|training_data|\.ahproj|_local_sandbox|\\logs\\|samples\.csv|labels\.txt' }
    if ($bad) { throw "LEAK CHECK FAILED: working data in public package: $($bad -join ', ')" }
    "Leak check passed: $dir ($($files.Count) files, data identical to base\)"
}

& .\venv\Scripts\pyinstaller.exe --noconfirm --clean Stationkeeper.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. See output above." }

$out = "dist\$exeName"
# 2.90.0: no data or config ships (the app makes the master database and its settings in Stationkeeper Data on first
# start). The read-me files are in _internal\docs (update packs carry them) and in About Stationkeeper for people to read.
New-Item -ItemType Directory -Force "$out\About Stationkeeper" | Out-Null
Copy-Item README.txt, OVERVIEW.md, SECURITY.md "$out\About Stationkeeper" -Force
# 2.59.0: the Qt edition starts (window shown and closed at once; no effort opened)
if (Test-Path "$out\$qtExe.exe") {
    $q = Start-Process -FilePath "$out\$qtExe.exe" -ArgumentList '--selftest' -Wait -PassThru
    $qt = Get-Content "$out\_local_sandbox\$qtTest" -ErrorAction SilentlyContinue
    if ($q.ExitCode -ne 0 -or -not ($qt -match 'PASS')) { throw "QT SELFTEST FAILED: $qtExe.exe did not start (exit $($q.ExitCode)): $qt" }
    "Qt selftest: $qtExe.exe starts ($qt)"
}
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

$exeHash = (Get-FileHash "$out\$exeName.exe" -Algorithm SHA256).Hash
"$exeName.exe  SHA256  $exeHash" | Out-File -Encoding ascii "$out\_internal\docs\CHECKSUM.txt"
Copy-Item "$out\_internal\docs\CHECKSUM.txt" "$out\About Stationkeeper\CHECKSUM.txt" -Force
$qtLine = $null
# 2.76.0: the list of this build's program files (update packs and Check program files compare against it)
$ver = (Select-String -Path app_gui.py -Pattern '^APP_VERSION = "([0-9.]+)"').Matches[0].Groups[1].Value
& .\venv\Scripts\python.exe tools\make_update.py --manifest $out --program $exeName --edition $Edition --version $ver
if ($LASTEXITCODE -ne 0) { throw "PROGRAM MANIFEST FAILED. See the output above." }
Test-PublicPackage $out
$updKey = '_local_sandbox\keys\update_signing_key.txt'
if ($Edition -eq 'us' -and -not $Classic) {
    if (-not (Test-Path $updKey)) { throw "UPDATE CHECK FAILED: the publisher's signing key is missing ($updKey)" }
    # 2.76.0: update packs end to end on the built program. A copy installs a signed pack (one changed document, and its
    # own exe replaced while it runs), starts, checks its files, undoes the update and starts again.
    $ut = "_local_sandbox\upd_$exeName"; $ub = "_local_sandbox\upd_${exeName}_next"; $um = "_local_sandbox\upd_${exeName}_manifests"
    Remove-Item -Recurse -Force $ut, $ub, $um, "$ut.skupdate" -ErrorAction SilentlyContinue
    Copy-Item $out $ut -Recurse; Copy-Item $out $ub -Recurse
    New-Item -ItemType Directory -Force $um | Out-Null
    Copy-Item "$out\_internal\program_manifest.json" "$um\$exeName-$ver.json"
    Add-Content "$ub\_internal\docs\README.txt" "UPDATE TEST LINE"
    & .\venv\Scripts\python.exe tools\make_update.py --manifest $ub --program $exeName --edition $Edition --version "$ver.1" | Out-Null
    & .\venv\Scripts\python.exe tools\make_update.py --pack $ub --key $updKey --out "$ut.skupdate" --always "$exeName.exe" --manifests $um --no-save
    if ($LASTEXITCODE -ne 0) { throw "UPDATE CHECK FAILED: the test pack was not made" }
    $pk = (Resolve-Path "$ut.skupdate").Path
    $steps = @(@('--apply-update', $pk), @('--selftest'), @('--check-program'), @('--undo-update'), @('--selftest'))
    foreach ($a in $steps) {
        $q = Start-Process -FilePath "$ut\$exeName.exe" -ArgumentList $a -Wait -PassThru
        if ($q.ExitCode -ne 0) { throw "UPDATE CHECK FAILED: $exeName.exe $($a[0]) exited $($q.ExitCode): $(Get-Content "$ut\logs\update.txt" -Raw -ErrorAction SilentlyContinue)" }
        if ($a[0] -eq '--apply-update' -and -not (Select-String -Path "$ut\_internal\docs\README.txt" -Pattern 'UPDATE TEST LINE' -Quiet)) { throw "UPDATE CHECK FAILED: the update did not change README.txt" }
        if ($a[0] -eq '--undo-update' -and (Select-String -Path "$ut\_internal\docs\README.txt" -Pattern 'UPDATE TEST LINE' -Quiet)) { throw "UPDATE CHECK FAILED: undo did not bring README.txt back" }
    }
    $ul = (Get-Content "$ut\logs\update.txt") -join ' | '
    if ($ul -notmatch 'UPDATE OK' -or $ul -notmatch 'CHECK OK' -or $ul -notmatch 'UNDO OK') { throw "UPDATE CHECK FAILED: $ul" }
    "Update check: $exeName.exe installed a signed pack while running, started, matched its files, undid it and started again ($ul)"
    Remove-Item -Recurse -Force $ut, $ub, $um, "$ut.skupdate" -ErrorAction SilentlyContinue
}
# Software Bill of Materials (CycloneDX): what ships, with versions, licenses and SHA-256 of every program and model file
$edLabel = if ($Classic) { 'US Classic (Tesseract only)' } elseif ($Edition -eq 'legacy') { 'Legacy' } else { 'US' }
if ($App -eq 'training') { $edLabel = "$edLabel Training" }
& .\venv\Scripts\python.exe tools\make_sbom.py $out "${prefix}_SBOM.cdx.json" $edLabel
if ($LASTEXITCODE -ne 0) { throw "SBOM generation failed. See the output above." }
$zip = "$prefix.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $out -DestinationPath $zip -CompressionLevel Optimal
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
$lines = @("$zip  SHA256  $zipHash",
           "$exeName.exe  SHA256  $exeHash") + $(if ($qtLine) { @($qtLine) } else { @() }) + @("Built $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
$stage = $out
# 2.76.0: the signed update pack for every copy from 2.76.0 on (none for the first release), and this release's manifest
# kept in tools\manifests for the next pack
if ($Edition -eq 'us' -and -not $Classic) {
    $upd = "${prefix}_Update_$ver.skupdate"
    Remove-Item $upd -ErrorAction SilentlyContinue
    & .\venv\Scripts\python.exe tools\make_update.py --pack $out --key $updKey --out $upd
    if ($LASTEXITCODE -ne 0) { throw "UPDATE PACK FAILED. See the output above." }
    if (Test-Path $upd) { $lines = @($lines[0], "$upd  SHA256  $((Get-FileHash $upd -Algorithm SHA256).Hash)") + $lines[1..($lines.Count - 1)] }
}

# Package 3 (optional): internal build with a Knowledge Pack pre-installed. SharePoint ONLY.
if ($KnowledgePack -and $App -eq 'user') {
    if (-not (Test-Path $KnowledgePack)) { throw "Knowledge Pack not found: $KnowledgePack" }
    $istage = 'dist\internal\Stationkeeper'
    New-Item -ItemType Directory -Force (Split-Path $istage) | Out-Null
    Copy-Item $stage $istage -Recurse -Force
    $env:SK_DATA_DIR = (Resolve-Path $istage).Path     # 2.80.0: install into the package's own config, not a data folder beside it
    $p = Start-Process -FilePath "$istage\Stationkeeper.exe" -ArgumentList '--install-knowledge', "`"$((Resolve-Path $KnowledgePack).Path)`"" -Wait -PassThru
    Remove-Item Env:SK_DATA_DIR
    $log = Get-Content "$istage\logs\knowledge_install.txt" -Raw
    if ($log -notmatch 'INSTALL OK') { throw "Knowledge Pack install failed:`n$log" }
    Remove-Item -Recurse -Force "$istage\logs", "$istage\_local_sandbox", "$istage\config\knowledge_backups" -ErrorAction SilentlyContinue
    $packName = [IO.Path]::GetFileNameWithoutExtension($KnowledgePack) -replace '^(AcronymHunter|Stationkeeper)_Knowledge_', ''
    New-Item -ItemType Directory -Force internal_builds | Out-Null
    $izip = "internal_builds\Stationkeeper_Internal_$packName.zip"
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
