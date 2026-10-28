@echo off
setlocal
title Granite 3.1 Grounded Chat Installer

echo ====================================================
echo   Granite 3.1 Grounded Chat Installer
echo ====================================================
echo.

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

call :create_shortcut
if errorlevel 1 goto install_failed

call :ensure_python
if errorlevel 1 goto install_failed

where ollama >nul 2>nul
if errorlevel 1 goto install_ollama
echo [INFO] Ollama is already installed.
goto pull_model

:install_ollama
echo [INFO] Downloading the official Ollama installer...
set "OLLAMA_EXE=%TEMP%\OllamaSetup.exe"
del /f /q "%OLLAMA_EXE%" >nul 2>nul
where curl.exe >nul 2>nul
if errorlevel 1 goto powershell_download_ollama
curl.exe --fail --location --retry 3 --retry-delay 2 --retry-connrefused --connect-timeout 30 --output "%OLLAMA_EXE%" "https://ollama.com/download/OllamaSetup.exe"
if errorlevel 1 (
    echo [WARN] curl could not download Ollama. Trying PowerShell...
    del /f /q "%OLLAMA_EXE%" >nul 2>nul
    goto powershell_download_ollama
)
goto verify_ollama_download

:powershell_download_ollama
powershell -NoProfile -Command "try { $ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile $env:OLLAMA_EXE } catch { Write-Error ('Ollama installer download failed: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 (
    echo [ERROR] Could not download the Ollama installer.
    echo Check your internet connection, proxy or firewall settings, then rerun the installer.
    goto install_failed
)

:verify_ollama_download
if not exist "%OLLAMA_EXE%" (
    echo [ERROR] The Ollama installer was not downloaded.
    goto install_failed
)
for %%I in ("%OLLAMA_EXE%") do if %%~zI equ 0 (
    echo [ERROR] The downloaded Ollama installer is empty.
    del /f /q "%OLLAMA_EXE%" >nul 2>nul
    goto install_failed
)

echo Installing Ollama. Approve any Windows security prompt if requested.
start /wait "" "%OLLAMA_EXE%" /silent
del /f /q "%OLLAMA_EXE%" >nul 2>nul
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Ollama"
where ollama >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Ollama was not found after installation. Restart Windows, then run this installer again.
    goto install_failed
)

:pull_model
echo.
echo Downloading Granite 3.1 model. This may take several minutes.
ollama pull granite3.1-dense:latest
if errorlevel 1 (
    echo [ERROR] The model download failed. Check your internet connection and Ollama installation, then rerun this installer.
    goto install_failed
)

if not exist "%APP_DIR%Grounding Data" mkdir "%APP_DIR%Grounding Data"

echo.
echo ====================================================
echo   Installation completed successfully.
echo   Python 3, Tkinter, Ollama, and the Granite model are ready.
echo   Launch Granite 3.1 Grounded Chat from your desktop.
echo ====================================================
pause
exit /b 0

:create_shortcut
echo Creating desktop shortcut...
powershell -NoProfile -Command "try { $ErrorActionPreference = 'Stop'; $appDir = $env:APP_DIR; $target = Join-Path $appDir 'run_app.bat'; if (-not (Test-Path -LiteralPath $target)) { throw ('Launcher not found: ' + $target) }; $shell = New-Object -ComObject WScript.Shell; $desktop = $shell.SpecialFolders.Item('Desktop'); if ([string]::IsNullOrWhiteSpace($desktop)) { throw 'Windows did not return a desktop folder.' }; if (-not (Test-Path -LiteralPath $desktop)) { New-Item -ItemType Directory -Path $desktop -Force | Out-Null }; $link = Join-Path $desktop 'Granite 3.1 Grounded Chat.lnk'; $shortcut = $shell.CreateShortcut($link); $shortcut.TargetPath = $target; $shortcut.WorkingDirectory = $appDir; $shortcut.Description = 'Launch Granite 3.1 Grounded Chat'; $shortcut.Save(); if (-not (Test-Path -LiteralPath $link)) { throw ('Shortcut was not created: ' + $link) }; Write-Host ('Desktop shortcut created at: ' + $link) } catch { Write-Error $_; exit 1 }"
if errorlevel 1 (
    echo [ERROR] Could not create the desktop shortcut.
    exit /b 1
)
exit /b 0

:ensure_python
call :check_python
if not errorlevel 1 exit /b 0

echo [INFO] Python 3 with Tkinter was not found. Installing Python 3.13...
where winget >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Windows Package Manager (winget) is unavailable.
    echo Install Python 3 from https://www.python.org/downloads/windows/
    echo Ensure Tcl/Tk and IDLE is selected, then rerun this installer.
    exit /b 1
)

winget install --id Python.Python.3.13 --exact --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo [ERROR] Python installation failed. Install Python 3 with Tcl/Tk and IDLE from python.org, then rerun this installer.
    exit /b 1
)

call :check_python
if errorlevel 1 (
    echo [ERROR] Python or Tkinter could not be verified after installation.
    echo Restart Windows, then rerun this installer. If it still fails, reinstall Python with Tcl/Tk and IDLE enabled.
    exit /b 1
)
echo [INFO] Python 3 and Tkinter are ready.
exit /b 0

:check_python
where pyw >nul 2>nul
if errorlevel 1 goto check_pythonw
py -3 -c "import tkinter" >nul 2>nul
if errorlevel 1 exit /b 1
exit /b 0

:check_pythonw
where pythonw >nul 2>nul
if errorlevel 1 exit /b 1
python -c "import tkinter" >nul 2>nul
if errorlevel 1 exit /b 1
exit /b 0

:install_failed
echo.
echo [ERROR] Installation did not complete.
pause
exit /b 1
