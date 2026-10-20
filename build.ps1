# Rebuilds the app and makes two zips from ONE build:
#   AcronymHunter_Portable.zip     scanner only (share this)
#   AcronymHunter_WithTrainer.zip  scanner + Trainer (for whoever curates OCR fixes and training samples)
# Run from this folder:  powershell -ExecutionPolicy Bypass -File .\build.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& .\venv\Scripts\pyinstaller.exe --noconfirm --clean AcronymHunter.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. See output above." }

$out = 'dist\AcronymHunter'
Copy-Item acronym_database.csv $out -Force
Copy-Item README.txt $out -Force
Copy-Item OVERVIEW.md, SECURITY.md $out -Force   # plain-language overview + security statement for reviewers
Copy-Item config $out -Recurse -Force   # OCR settings, corrections, optional drop-in models
Remove-Item -Recurse -Force "$out\_local_sandbox", "$out\logs" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue

# Microsoft Defender scan of the finished app (report only, nothing is deleted)
$mp = Join-Path $env:ProgramFiles 'Windows Defender\MpCmdRun.exe'
if (Test-Path $mp) {
    & $mp -Scan -ScanType 3 -File (Resolve-Path $out).Path -DisableRemediation | Out-Null
    if ($LASTEXITCODE -eq 0) { "Defender scan: no threats found" }
    else { throw "Defender flagged the build (exit $LASTEXITCODE). Do not share it. Check Windows Security > Protection history." }
} else { "Defender command-line scanner not found; scan skipped." }

# Checksums of the programs (shipped inside each package so recipients or IT can verify them)
$exeHash = (Get-FileHash "$out\AcronymHunter.exe" -Algorithm SHA256).Hash
$trainerHash = (Get-FileHash "$out\AcronymHunterTrainer.exe" -Algorithm SHA256).Hash
@("AcronymHunter.exe         SHA256  $exeHash",
  "AcronymHunterTrainer.exe  SHA256  $trainerHash") | Out-File -Encoding ascii "$out\CHECKSUM.txt"

# Package 1: scanner + Trainer
$zipFull = 'AcronymHunter_WithTrainer.zip'
Remove-Item $zipFull -ErrorAction SilentlyContinue
Compress-Archive -Path $out -DestinationPath $zipFull -CompressionLevel Optimal

# Package 2: scanner only. Same build, Trainer exe removed. Everything in _internal is shared and
# still needed by the scanner. The scanner hides its Region Trainer button when the Trainer is absent.
$stage = 'dist\scanner_only\AcronymHunter'
New-Item -ItemType Directory -Force (Split-Path $stage) | Out-Null
Copy-Item $out $stage -Recurse -Force
Remove-Item "$stage\AcronymHunterTrainer.exe" -Force
"AcronymHunter.exe  SHA256  $exeHash" | Out-File -Encoding ascii "$stage\CHECKSUM.txt"
$zip = 'AcronymHunter_Portable.zip'
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal

# Checksums of the zips, kept beside them (send the value separately from the zip)
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
$zipFullHash = (Get-FileHash $zipFull -Algorithm SHA256).Hash
@("AcronymHunter_Portable.zip     SHA256  $zipHash      (scanner only: share this)",
  "AcronymHunter_WithTrainer.zip  SHA256  $zipFullHash  (scanner + Trainer)",
  "AcronymHunter.exe              SHA256  $exeHash",
  "AcronymHunterTrainer.exe       SHA256  $trainerHash",
  "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm')") | Out-File -Encoding ascii 'AcronymHunter_SHA256.txt'

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
"Done: $zip (scanner only) and $zipFull (scanner + Trainer)"
"Zip SHA256: $zipHash"
