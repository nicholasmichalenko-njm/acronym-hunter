# 3.47.0: build NumPy from its source release without OpenBLAS and put it in the build venv.
# The program calls no BLAS or LAPACK routine (matrix products, solvers); NumPy's own fallback covers anything else.
# OpenBLAS began at the Chinese Academy of Sciences (ISCAS); leaving it out removes the question and about 20 MB.
# Needs Visual Studio Build Tools (MSVC) and the network once for NumPy's source and build tools from PyPI.
param([string]$Version = "2.4.6", [string]$Out = "$env:USERPROFILE\ah_wheels")
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
New-Item -ItemType Directory -Force $Out | Out-Null
& .\venv\Scripts\python.exe -m pip wheel "numpy==$Version" --no-binary numpy --no-deps -w $Out `
    "-Csetup-args=--vsenv" "-Csetup-args=-Dallow-noblas=true" "-Csetup-args=-Dblas=none" "-Csetup-args=-Dlapack=none"
if ($LASTEXITCODE -ne 0) { throw "NumPy did not build" }
$whl = Get-ChildItem "$Out\numpy-$Version-*.whl" | Select-Object -First 1
& .\venv\Scripts\python.exe -m pip install --force-reinstall --no-deps $whl.FullName
& .\venv\Scripts\python.exe -c "import numpy; b = numpy.show_config('dicts')['Build Dependencies']; assert not b['blas'].get('found') and not b['lapack'].get('found'), b; print('NumPy', numpy.__version__, 'without BLAS or LAPACK')"
"NumPy wheel SHA-256: $((Get-FileHash $whl.FullName).Hash)"
