# Rebuilds the portable app and the shareable zip.
# Run from this folder:  powershell -ExecutionPolicy Bypass -File .\build.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

& .\venv\Scripts\pyinstaller.exe --noconfirm --clean AcronymHunter.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed. See output above." }

$out = 'dist\AcronymHunter'
Copy-Item acronym_database.csv $out -Force
Copy-Item README.txt $out -Force
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

# Checksum of the exe, shipped inside the folder so recipients or IT can verify it
$exeHash = (Get-FileHash "$out\AcronymHunter.exe" -Algorithm SHA256).Hash
"AcronymHunter.exe  SHA256  $exeHash" | Out-File -Encoding ascii "$out\CHECKSUM.txt"

$zip = 'AcronymHunter_Portable.zip'
Remove-Item $zip -ErrorAction SilentlyContinue
Compress-Archive -Path $out -DestinationPath $zip -CompressionLevel Optimal

# Checksum of the zip, kept beside it (send this value separately from the zip)
$zipHash = (Get-FileHash $zip -Algorithm SHA256).Hash
@("AcronymHunter_Portable.zip  SHA256  $zipHash", "AcronymHunter.exe           SHA256  $exeHash",
  "Built $(Get-Date -Format 'yyyy-MM-dd HH:mm')") | Out-File -Encoding ascii 'AcronymHunter_SHA256.txt'

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
"Done: $zip"
"Zip SHA256: $zipHash"
