# 2.55.0: adds the three character-set tools (unicharset_extractor, merge_unicharsets, combine_lang_model) and the
# radical-stroke table to vendor\tesseract from the no-network Tesseract build already in the toolchain folder
# (tools\build_tesseract.ps1 made it). No download: copies from this PC only. The user app leaves them out (spec).
#   powershell -File .\tools\collect_tess_tools.ps1
param([string]$Toolchain = "$env:USERPROFILE\ah_toolchain")
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot)
$proj = (Get-Location).Path
$src = "$Toolchain\tesseract-5.5.3"
$msys = Join-Path $Toolchain 'msys64'
$bash = "$msys\usr\bin\bash.exe"
$dst = "$proj\vendor\tesseract"
if (-not (Test-Path "$dst\tesseract.exe")) { throw 'vendor\tesseract missing: run tools\build_tesseract.ps1 first' }
$env:MSYSTEM = 'UCRT64'; $env:CHERE_INVOKING = '1'
$dlls = @{}
foreach ($e in 'unicharset_extractor.exe', 'merge_unicharsets.exe', 'combine_lang_model.exe') {
    $exe = "$src\build\bin\$e"
    if (-not (Test-Path $exe)) { throw "$e was not built (rerun tools\build_tesseract.ps1)" }
    Copy-Item $exe $dst -Force
    $deps = & $bash -lc "ldd '$($exe -replace '\\','/')' | grep -i -e ucrt64 -e 'tesseract-5.5.3/build' | awk '{print `$3}'"
    foreach ($d in $deps) { if ($d) { $dlls[$d] = 1 } }
}
foreach ($d in $dlls.Keys) {
    $w = & "$msys\usr\bin\cygpath.exe" -w $d
    if (-not (Test-Path (Join-Path $dst (Split-Path $w -Leaf)))) { Copy-Item $w $dst }
}
New-Item -ItemType Directory -Force "$dst\langdata" | Out-Null
Copy-Item "$proj\tools\tess_langdata\*" "$dst\langdata" -Force
Add-Content "$dst\SOURCE.txt" "2.55.0: added unicharset_extractor.exe, merge_unicharsets.exe, combine_lang_model.exe from the same no-network build, and langdata\radical-stroke.txt (langdata_lstm, Apache 2.0). DLLs: $(($dlls.Keys | ForEach-Object { Split-Path $_ -Leaf } | Sort-Object) -join ', ')"
"Added: $(($dlls.Keys | ForEach-Object { Split-Path $_ -Leaf } | Sort-Object) -join ', ')"
