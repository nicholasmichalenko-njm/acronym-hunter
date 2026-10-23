# Builds the optional math reader add-on: AcronymHunter_MathAddon.zip (folder math_addon\ to unzip next to
# AcronymHunter.exe). Contents: AcronymHunterMath.exe (PyTorch CPU + transformers, frozen) and IBM's
# Granite-Docling-258M model files (Apache 2.0) with their SHA-256 in math_models.json.
# Needs vendor\granite\ (IBM's files from huggingface.co/ibm-granite/granite-docling-258M). Internet only for the
# first venv setup; the add-on itself never connects (and runs only inside the app's no-network sandbox).
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$IBM_SAFETENSORS_SHA256 = '1CDAD234DEB1CDE18EE6A586F849057F19851DAF1FEDCE2E40AFF791DBE46F61'
$files = 'added_tokens.json','chat_template.jinja','config.json','generation_config.json','merges.txt','model.safetensors',
         'preprocessor_config.json','processor_config.json','special_tokens_map.json','tokenizer.json','tokenizer_config.json','vocab.json'
foreach ($f in $files) { if (-not (Test-Path "vendor\granite\$f")) { throw "vendor\granite\$f missing" } }
if ((Get-FileHash vendor\granite\model.safetensors).Hash -ne $IBM_SAFETENSORS_SHA256) { throw "ORIGIN CHECK FAILED: model.safetensors is not IBM's file" }

if (-not (Test-Path venv_math\Scripts\python.exe)) {
    $base = (& .\venv\Scripts\python.exe -c "import sys;print(sys.base_prefix)")
    & "$base\python.exe" -m venv venv_math
    & venv_math\Scripts\python.exe -m pip install -q --upgrade pip
    & venv_math\Scripts\python.exe -m pip install -q torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
    & venv_math\Scripts\python.exe -m pip install -q transformers==5.20.2 tokenizers==0.23.3 safetensors==0.8.0 huggingface_hub==2.3.0 pillow==12.3.0 numpy==2.4.6 pyinstaller==6.22.3
}
& venv_math\Scripts\python.exe -m pip freeze | Set-Content requirements_math.txt
if (Test-Path dist_math) { Remove-Item dist_math -Recurse -Force }
& venv_math\Scripts\pyinstaller.exe --noconfirm --clean --log-level WARN --distpath dist_math --workpath build_math math_helper.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
$out = "dist_math\math_addon"
New-Item -ItemType Directory -Force "$out\models\granite" | Out-Null
$man = [ordered]@{ model = 'ibm-granite/granite-docling-258M (IBM, Apache 2.0)'; files = [ordered]@{} }
foreach ($f in $files) {
    Copy-Item "vendor\granite\$f" "$out\models\granite\$f"
    $man.files[$f] = (Get-FileHash "$out\models\granite\$f").Hash
}
$man | ConvertTo-Json -Depth 4 | Set-Content "$out\math_models.json" -Encoding ascii
Copy-Item vendor\granite\NOTICE.txt "$out\NOTICE.txt"
# Checks: no pickle-format model files, no stray models, Defender
$pk = Get-ChildItem $out -Recurse -File | Where-Object { $_.Extension -in '.bin','.pt','.pth','.pkl','.ckpt','.onnx' }
if ($pk) { throw "LEAK CHECK FAILED: unexpected model file(s): $($pk.FullName -join ', ')" }
$mp = "$env:ProgramFiles\Windows Defender\MpCmdRun.exe"
if (Test-Path $mp) { & $mp -Scan -ScanType 3 -File (Resolve-Path $out) -DisableRemediation | Out-Null; if ($LASTEXITCODE -ne 0) { throw "Defender flagged the add-on" }; "Defender scan: no threats found" }
& .\venv\Scripts\python.exe tools\network_audit.py $out --report 2>$null | Select-Object -Last 3
if (Test-Path AcronymHunter_MathAddon.zip) { Remove-Item AcronymHunter_MathAddon.zip }
Compress-Archive -Path $out -DestinationPath AcronymHunter_MathAddon.zip -CompressionLevel Optimal
$zh = (Get-FileHash AcronymHunter_MathAddon.zip).Hash; $eh = (Get-FileHash "$out\AcronymHunterMath.exe").Hash
"AcronymHunter_MathAddon.zip  SHA256  $zh`r`nAcronymHunterMath.exe  SHA256  $eh`r`nBuilt $(Get-Date -Format 'yyyy-MM-dd HH:mm')" | Set-Content AcronymHunter_MathAddon_SHA256.txt
"Done: AcronymHunter_MathAddon.zip  $([math]::Round((Get-Item AcronymHunter_MathAddon.zip).Length/1MB)) MB  SHA256 $zh"
