@echo off
cd /d "%~dp0"
echo ACRONYM HUNTER TRAINING KIT  (offline: network access is disabled inside this kit)
echo.
echo   1  Check the kit (network lockdown, PaddlePaddle, weights)
echo   2  Train the reader  (text-line samples: fixes misspellings)
echo   3  Train the finder  (region samples: stops lines being read as text)
echo   4  Train both
echo.
set /p choice=Choose 1-4: 
if "%choice%"=="1" python\python.exe kit\train.py --check
if "%choice%"=="2" python\python.exe kit\train.py --rec
if "%choice%"=="3" python\python.exe kit\train.py --det
if "%choice%"=="4" python\python.exe kit\train.py --rec --det
echo.
pause
