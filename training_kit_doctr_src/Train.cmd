@echo off
cd /d "%~dp0"
echo ACRONYM HUNTER TRAINING KIT (docTR)   offline: network access is disabled inside this kit
echo.
echo   1  Check the kit (network lockdown, PyTorch, graphics card, starting weights, samples)
echo   2  Train the reader  (corrected text lines: fixes misreadings)
echo   3  Train the finder  (boxed regions: finds missed text, skips lines and arrows)
echo   4  Train both
echo.
set /p choice=Choose 1-4: 
if "%choice%"=="1" python\python.exe kit\train_doctr.py --check
if "%choice%"=="2" python\python.exe kit\train_doctr.py --reader
if "%choice%"=="3" python\python.exe kit\train_doctr.py --finder
if "%choice%"=="4" python\python.exe kit\train_doctr.py --reader --finder
echo.
echo Results: output\models\REPORT.txt
pause
