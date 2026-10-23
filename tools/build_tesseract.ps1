# Builds Tesseract 5.5.3 from the official source WITHOUT any network library, into vendor\tesseract.
#   -DDISABLE_CURL=ON     no libcurl: Tesseract cannot fetch a URL (the code is not compiled in)
#   -DDISABLE_ARCHIVE=ON  no libarchive
#   training tools ON     lstmtraining, lstmeval, combine_tessdata for the in-app "Improve Reading"
# Toolchain: MSYS2 UCRT64 (GCC, CMake, Ninja, Leptonica) unpacked into a user folder. No admin rights needed.
# Internet is used only while this script runs (toolchain packages, source tarball, Google's model).
#   powershell -ExecutionPolicy Bypass -File .\tools\build_tesseract.ps1
param([string]$Toolchain = "$env:USERPROFILE\ah_toolchain")
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # the progress bar makes Invoke-WebRequest many times slower
Set-Location (Split-Path $PSScriptRoot)
$proj = (Get-Location).Path
$TESS_VER = '5.5.3'
$ENG_URL = 'https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata'
$ENG_SHA = '8280AED0782FE27257A68EA10FE7EF324CA0F8D85BD2FD145D1C2B560BCB66BA'
New-Item -ItemType Directory -Force $Toolchain | Out-Null
$msys = Join-Path $Toolchain 'msys64'
if (-not (Test-Path "$msys\usr\bin\bash.exe")) {
    Invoke-WebRequest 'https://repo.msys2.org/distrib/msys2-x86_64-latest.sfx.exe' -OutFile "$Toolchain\msys2.sfx.exe"
    "MSYS2 base SHA-256: $((Get-FileHash "$Toolchain\msys2.sfx.exe").Hash)"
    & "$Toolchain\msys2.sfx.exe" -y "-o$Toolchain" | Out-Null
}
$bash = "$msys\usr\bin\bash.exe"
$env:MSYSTEM = 'UCRT64'; $env:CHERE_INVOKING = '1'; $env:MSYS2_PATH_TYPE = 'minimal'
function Msys([string]$cmd) {
    # native tools write progress to stderr; that is not an error, only the exit code is
    $ErrorActionPreference = 'Continue'
    & $bash -lc "$cmd 2>&1"
    if ($LASTEXITCODE -ne 0) { throw "MSYS2 step failed: $cmd" }
}
Msys 'pacman-key --init && pacman-key --populate msys2'   # package signatures stay verified
Msys 'pacman -Syuu --noconfirm || true'                    # first run updates the core and may exit early
Msys 'pacman -Syuu --noconfirm'
# pango is needed only to configure the training tools; only DLLs our 4 programs load are copied out
Msys 'pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja mingw-w64-ucrt-x86_64-pkgconf mingw-w64-ucrt-x86_64-leptonica mingw-w64-ucrt-x86_64-icu mingw-w64-ucrt-x86_64-pango tar'
$src = "$Toolchain\tesseract-$TESS_VER"
if (-not (Test-Path "$src\CMakeLists.txt")) {
    Invoke-WebRequest "https://github.com/tesseract-ocr/tesseract/archive/refs/tags/$TESS_VER.tar.gz" -OutFile "$Toolchain\tesseract-$TESS_VER.tar.gz"
    $srcSha = (Get-FileHash "$Toolchain\tesseract-$TESS_VER.tar.gz").Hash
    if ($srcSha -ne '9218E62793116D42A9F6D14CD9348518B27F382096EEA3D0F2D1A24616BB5884') { throw "Tesseract source SHA-256 mismatch: $srcSha" }
    Msys "cd '$($Toolchain -replace '\\','/')' && tar xzf tesseract-$TESS_VER.tar.gz"
}
$u = ($src -replace '\\', '/')
Msys "cd '$u' && rm -rf build && cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DDISABLE_CURL=ON -DDISABLE_ARCHIVE=ON -DBUILD_TRAINING_TOOLS=ON -DBUILD_TESTS=OFF -DGRAPHICS_DISABLED=ON | grep -iE 'curl|archive|error|done'"
Msys "cd '$u' && cmake --build build -j `$(nproc) | tail -3"
# (no 'cmake --install': the source tree has an INSTALL file that clashes with an install\ folder on Windows)
# Collect: 4 programs + exactly the DLLs they load from the toolchain (ldd), nothing else
$dst = "$proj\vendor\tesseract"
Remove-Item -Recurse -Force $dst -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "$dst\tessdata\configs", "$dst\doc" | Out-Null
$exes = 'tesseract.exe', 'lstmtraining.exe', 'lstmeval.exe', 'combine_tessdata.exe'
$dlls = @{}
foreach ($e in $exes) {
    $exe = "$src\build\bin\$e"
    if (-not (Test-Path $exe)) { throw "$e was not built" }
    Copy-Item $exe $dst
    $deps = & $bash -lc "ldd '$($exe -replace '\\','/')' | grep -i -e ucrt64 -e 'tesseract-$TESS_VER/build' | awk '{print `$3}'"
    foreach ($d in $deps) { if ($d) { $dlls[$d] = 1 } }
}
foreach ($d in $dlls.Keys) { Copy-Item (& "$msys\usr\bin\cygpath.exe" -w $d) $dst }
Copy-Item "$src\tessdata\configs\lstm.train" "$dst\tessdata\configs"
Copy-Item "$src\LICENSE", "$src\AUTHORS" "$dst\doc"
Invoke-WebRequest $ENG_URL -OutFile "$dst\tessdata\eng.traineddata"
if ((Get-FileHash "$dst\tessdata\eng.traineddata").Hash -ne $ENG_SHA) { throw 'eng.traineddata SHA-256 mismatch' }
$ver = & "$dst\tesseract.exe" --version 2>&1 | Out-String
@"
Tesseract OCR $TESS_VER (Apache License 2.0), built from https://github.com/tesseract-ocr/tesseract/archive/refs/tags/$TESS_VER.tar.gz
Built $(Get-Date -Format 'yyyy-MM-dd HH:mm') with MSYS2 UCRT64 GCC: -DDISABLE_CURL=ON -DDISABLE_ARCHIVE=ON -DBUILD_TRAINING_TOOLS=ON
No network library is compiled in. Version report:
$ver
eng.traineddata from https://github.com/tesseract-ocr/tessdata_best (Apache License 2.0), SHA-256 $ENG_SHA
Programs: $($exes -join ', ')
DLLs: $(($dlls.Keys | ForEach-Object { Split-Path $_ -Leaf } | Sort-Object) -join ', ')
"@ | Out-File -Encoding ascii "$dst\SOURCE.txt"
$ver
"Done: $dst ($([math]::Round(((Get-ChildItem $dst -Recurse | Measure-Object Length -Sum).Sum / 1MB), 1)) MB)"
