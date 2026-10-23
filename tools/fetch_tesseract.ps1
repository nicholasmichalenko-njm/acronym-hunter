# Fetches the Tesseract OCR engine for the US edition into vendor\tesseract (not committed; build.ps1 bundles it).
#   Engine:  Tesseract 5.5.3 Windows build, official tesseract-ocr GitHub release (Apache 2.0)
#   Model:   eng.traineddata from Google's tessdata_best (Apache 2.0), float model: accurate and fine-tunable
#   Tool:    7-Zip 24.09 MSI, unpacked to a temp folder (no install, no admin) only to open the Tesseract installer
# Every download is checked against a pinned SHA-256. Any mismatch stops the script.
#   powershell -ExecutionPolicy Bypass -File .\tools\fetch_tesseract.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot)
$pins = @{
  'tesseract-setup.exe' = @('https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe',
                            'BEE9E3434BD94FD65387D9BE28CD467A41F61B1275383B55B0F59A1331270AE4')
  'eng.traineddata'     = @('https://github.com/tesseract-ocr/tessdata_best/raw/main/eng.traineddata',
                            '8280AED0782FE27257A68EA10FE7EF324CA0F8D85BD2FD145D1C2B560BCB66BA')
  '7z.msi'              = @('https://www.7-zip.org/a/7z2409-x64.msi',
                            'EC6AF1EA0367D16DDE6639A89A080A524CEBC4D4BEDFE00ED0CAC4B865A918D8')
}
$tmp = Join-Path $env:TEMP "ah_tess_$(Get-Random)"
New-Item -ItemType Directory -Force $tmp | Out-Null
foreach ($name in $pins.Keys) {
  $url, $sha = $pins[$name]
  Invoke-WebRequest $url -OutFile "$tmp\$name"
  $got = (Get-FileHash "$tmp\$name" -Algorithm SHA256).Hash
  if ($got -ne $sha) { throw "SHA-256 mismatch for $name`n expected $sha`n got      $got" }
  "verified $name"
}
Start-Process msiexec -ArgumentList "/a `"$tmp\7z.msi`" /qn TARGETDIR=`"$tmp\7zip`"" -Wait
& "$tmp\7zip\Files\7-Zip\7z.exe" x "$tmp\tesseract-setup.exe" "-o$tmp\ex" -y | Out-Null
# Only the engine, the 4 training tools, and the DLLs they load. Leaves out text2image/ICU/Pango/Cairo (font rendering).
$exes = 'tesseract.exe', 'lstmtraining.exe', 'combine_tessdata.exe', 'lstmeval.exe'
$dlls = 'libarchive-13','libb2-1','libbrotlicommon','libbrotlidec','libbz2-1','libcurl-4','libdeflate','libexpat-1',
        'libgcc_s_seh-1','libgif-7','libiconv-2','libidn2-0','libintl-8','libjbig-0','libjpeg-8','libleptonica-6','libLerc',
        'liblz4','liblzma-5','libopenjp2-7','libpng16-16','libpsl-5','libsharpyuv-0','libssh2-1','libstdc++-6','libtesseract-5',
        'libtiff-6','libunistring-5','libwebp-7','libwebpmux-3','libwinpthread-1','libzstd','zlib1'
$dst = 'vendor\tesseract'
Remove-Item -Recurse -Force $dst -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "$dst\tessdata\configs" | Out-Null
foreach ($f in $exes) { Copy-Item "$tmp\ex\$f" $dst }
foreach ($f in $dlls) { Copy-Item "$tmp\ex\$f.dll" $dst }
Copy-Item "$tmp\ex\tessdata\configs\lstm.train" "$dst\tessdata\configs"
Copy-Item "$tmp\eng.traineddata" "$dst\tessdata"
New-Item -ItemType Directory -Force "$dst\doc" | Out-Null; Copy-Item "$tmp\ex\doc\*" "$dst\doc" -Recurse
@"
Tesseract OCR 5.5.3 (Apache License 2.0), https://github.com/tesseract-ocr/tesseract
  Windows build from the official release: tesseract-ocr-w64-setup-5.5.3.20260724.exe
  SHA-256 BEE9E3434BD94FD65387D9BE28CD467A41F61B1275383B55B0F59A1331270AE4
eng.traineddata from https://github.com/tesseract-ocr/tessdata_best (Apache License 2.0)
  SHA-256 8280AED0782FE27257A68EA10FE7EF324CA0F8D85BD2FD145D1C2B560BCB66BA
Included: tesseract.exe, lstmtraining.exe, combine_tessdata.exe, lstmeval.exe and the DLLs they load.
"@ | Out-File -Encoding ascii "$dst\SOURCE.txt"
Remove-Item -Recurse -Force $tmp
& "$dst\tesseract.exe" --version 2>&1 | Select-Object -First 1
"Done: $dst"
