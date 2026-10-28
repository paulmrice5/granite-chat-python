@echo off
title IBM Granite 3.1 Grounded Chat

set "APP_DIR=%~dp0"
if not exist "%APP_DIR%Grounding Data" mkdir "%APP_DIR%Grounding Data"

where pyw >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%APP_DIR%granite_chat_gui.py"
    exit /b
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%APP_DIR%granite_chat_gui.py"
    exit /b
)

echo [ERROR] Python 3 was not found. Install Python 3 with tkinter enabled, then try again.
pause
