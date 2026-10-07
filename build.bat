@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================================
echo  Building Inside Track Standalone Executable
echo ========================================================
echo.

:: Detect Python launcher or executable
set PYTHON_CMD=
where py >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=py -3
) else (
    where python >nul 2>nul
    if %ERRORLEVEL%==0 (
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] Python was not found. Please install Python 3.10+ from https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

echo [1/4] Creating temporary isolated build environment...
if exist ".build_env" rd /s /q ".build_env"
%PYTHON_CMD% -m venv ".build_env"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to create build environment.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing build dependencies in isolated environment...
.\.build_env\Scripts\python.exe -m pip install --upgrade pip
.\.build_env\Scripts\python.exe -m pip install pyinstaller keyboard mss pillow pydirectinput pytesseract
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install build dependencies.
    rd /s /q ".build_env"
    pause
    exit /b 1
)

echo.
echo [3/4] Compiling bot.py into standalone InsideTrack.exe...
.\.build_env\Scripts\pyinstaller.exe --clean --noconfirm --onefile --exclude-module tkinter --exclude-module unittest --exclude-module pydoc --exclude-module sqlite3 --name "InsideTrack" bot.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller compilation failed.
    rd /s /q ".build_env"
    pause
    exit /b 1
)

echo.
echo [4/4] Finalizing build and cleaning up temporary files...
if exist "build" rd /s /q "build"
if exist "InsideTrack.spec" del /f /q "InsideTrack.spec"
if exist ".build_env" rd /s /q ".build_env"

echo.
echo ========================================================
echo  SUCCESS! dist\InsideTrack.exe is ready.
echo  You can now run dist\InsideTrack.exe directly on any Windows PC.
echo ========================================================
echo.
