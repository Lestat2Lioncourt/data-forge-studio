@echo off
setlocal

:: ============================================================
::   DataForge Studio - Force Update (recovery script)
::
::   Use this when "Update on Quit" fails repeatedly with errors
::   like "Unlink of file '.git/objects/pack/pack-XXXX.idx' failed".
::
::   How to use:
::     1. Close DataForge Studio completely.
::     2. Drop this .bat into your DataForge Studio install folder
::        (the folder containing pyproject.toml and run.py).
::     3. Double-click it.
::
::   What it does:
::     - Waits 5 seconds for any leftover python.exe to fully exit.
::     - Forces termination of any remaining python.exe / uv.exe
::       still holding a handle in the install folder.
::     - Suppresses git's interactive prompts (GIT_TERMINAL_PROMPT=0).
::     - Retries `git pull` up to 5 times with growing backoff,
::       so transient antivirus / Windows indexer locks resolve on
::       their own.
::     - Runs `uv sync` to refresh dependencies.
:: ============================================================

cd /d "%~dp0"

:: If the user dropped this file in scripts\, jump up one level
if exist "..\pyproject.toml" if not exist "pyproject.toml" cd ..

if not exist "pyproject.toml" (
    echo.
    echo ============================================
    echo   ERROR: pyproject.toml not found in:
    echo   %CD%
    echo.
    echo   Place this script in the DataForge Studio install
    echo   folder (the one with pyproject.toml and run.py).
    echo ============================================
    echo.
    pause
    exit /b 1
)

if not exist ".git\" (
    echo.
    echo ============================================
    echo   This install has no .git folder (standalone).
    echo   Auto-update only works on git-based installs.
    echo.
    echo   Download the latest release manually from:
    echo     https://github.com/Lestat2Lioncourt/data-forge-studio
    echo.
    echo   Or contact the person who provided this build for an
    echo   updated standalone version.
    echo ============================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   DataForge Studio - Force Update
echo ============================================
echo.
echo Folder: %CD%
echo.
echo Step 1/4 - Waiting 5 seconds for app to fully release files...
timeout /t 5 /nobreak >nul

echo Step 2/4 - Terminating any leftover python.exe / uv.exe...
:: /F = force, /FI = filter on image name. Errors are ignored (no process).
taskkill /F /FI "IMAGENAME eq python.exe" >nul 2>&1
taskkill /F /FI "IMAGENAME eq pythonw.exe" >nul 2>&1
taskkill /F /FI "IMAGENAME eq uv.exe" >nul 2>&1
:: Give the OS a moment to actually release handles after the kill
timeout /t 2 /nobreak >nul

echo Step 3/4 - Pulling latest from GitHub...
echo.
set GIT_TERMINAL_PROMPT=0
git config --global --add safe.directory "%CD:\=/%" >nul 2>&1
git reset --hard
git checkout main

set _PULL_TRY=0
:retry_pull
git pull origin main
if not errorlevel 1 goto :pull_ok
set /a _PULL_TRY+=1
if %_PULL_TRY% GEQ 5 goto :pull_failed
echo.
echo Pull failed (attempt %_PULL_TRY%/5). Retrying in 8 seconds...
echo If errors persist, exclude this folder from your antivirus.
timeout /t 8 /nobreak >nul
goto :retry_pull

:pull_failed
echo.
echo ============================================
echo   GIT PULL FAILED AFTER 5 ATTEMPTS
echo ============================================
echo.
echo Likely causes:
echo   - Antivirus is locking files in the .git folder.
echo     ^> Try excluding the install folder from your AV.
echo   - Another app (file explorer, code editor) has the
echo     folder open. Close them and try again.
echo   - DataForge Studio is still running. Close it.
echo.
echo Manual fallback (open cmd in the install folder, then run):
echo   git reset --hard
echo   git pull origin main
echo   uv sync
echo.
echo ============================================
pause
exit /b 1

:pull_ok
echo.
echo Step 4/4 - Syncing dependencies (uv sync)...
echo.
uv sync
if errorlevel 1 (
    echo.
    echo ============================================
    echo   uv sync FAILED.
    echo   Try running it manually in this folder.
    echo ============================================
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   UPDATE COMPLETE
echo ============================================
echo.
echo Relaunching DataForge Studio...
:: Launch in a fresh detached console so this script can exit cleanly
start "" /b cmd /c uv run python run.py
:: Self-delete and exit
(del "%~f0") ^& exit /b 0
