@echo off
setlocal EnableExtensions
title DataForge Studio - Force Update

REM ============================================================
REM   DataForge Studio - Force Update (recovery script)
REM
REM   Use this when the in-app update fails. Just double-click it.
REM   Place it in the DataForge Studio install folder (the one
REM   containing pyproject.toml and run.py), or in scripts\.
REM
REM   This window ALWAYS stays open at the end so you can read the
REM   result. It does NOT relaunch the app: once it says
REM   "UPDATE COMPLETE", close it and start DataForge Studio from
REM   your usual shortcut.
REM ============================================================

REM Operate from the install root (folder with pyproject.toml).
cd /d "%~dp0"
if exist "..\pyproject.toml" if not exist "pyproject.toml" cd ..

echo ============================================
echo   DataForge Studio - Force Update
echo ============================================
echo Folder: %CD%
echo.

if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml not found in this folder.
    echo Put this file in the DataForge Studio install folder
    echo ^(the one containing pyproject.toml and run.py^).
    goto :end
)

if not exist ".git" (
    echo This install has no .git folder ^(standalone build^).
    echo Auto-update only works on git-based installs.
    echo Ask for an updated standalone build instead.
    goto :end
)

echo Step 1/4 - Closing any running instance...
taskkill /F /IM pythonw.exe >nul 2>&1
taskkill /F /IM python.exe  >nul 2>&1
timeout /t 2 /nobreak >nul

echo Step 2/4 - Preparing git...
set GIT_TERMINAL_PROMPT=0
git config --global --add safe.directory "%CD:\=/%" >nul 2>&1
git checkout -f main

echo Step 3/4 - Downloading latest version...
REM Fetch + reset --hard (not pull): a merge aborts as soon as an untracked
REM file would be overwritten, whereas reset --hard overwrites it. gc.auto=0
REM silences noisy background repack failures.
set _TRY=0
:retry
git -c gc.auto=0 fetch origin main
if not errorlevel 1 goto :pulled
set /a _TRY+=1
if %_TRY% GEQ 5 (
    echo.
    echo Download failed after 5 attempts. Check network/VPN and retry.
    goto :end
)
echo Attempt %_TRY%/5 failed - retrying in 8 seconds...
timeout /t 8 /nobreak >nul
goto :retry
:pulled
git reset --hard origin/main

echo Step 4/4 - Updating dependencies ^(uv sync^)...
uv sync
if errorlevel 1 (
    echo.
    echo Dependency update failed ^(uv sync^).
    echo Make sure 'uv' is installed and available, then run this file again.
    goto :end
)

echo.
echo ============================================
echo   UPDATE COMPLETE
echo ============================================
echo You can close this window and start DataForge Studio
echo from your usual shortcut.

:end
echo.
pause
endlocal
