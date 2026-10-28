@echo off
cd /d "%~dp0.."
venv\Scripts\python.exe prototypes\assign_qt.py %*
