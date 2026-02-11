@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: DataForge Studio - Prepare Offline Package
:: ============================================================

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set OUTPUT_DIR=%SCRIPT_DIR%DataForgeStudio_Offline
set UV_URL=https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip

echo.
echo ============================================================
echo  DataForge Studio - Preparation du package offline
echo ============================================================
echo.

:: Verifier que .venv existe
if not exist "%PROJECT_DIR%\.venv" (
    echo [ERREUR] Le dossier .venv n'existe pas.
    echo          Executez d'abord : uv sync
    exit /b 1
)

:: Lire le chemin Python depuis pyvenv.cfg
set PYTHON_HOME=
for /f "tokens=1,* delims==" %%a in ('type "%PROJECT_DIR%\.venv\pyvenv.cfg" ^| findstr /B "home"') do (
    set PYTHON_HOME=%%b
)
:: Supprimer les espaces en debut
set PYTHON_HOME=%PYTHON_HOME: =%

if "%PYTHON_HOME%"=="" (
    echo [ERREUR] Impossible de lire le chemin Python depuis .venv\pyvenv.cfg
    exit /b 1
)

echo [INFO] Python trouve : %PYTHON_HOME%

if not exist "%PYTHON_HOME%\python.exe" (
    echo [ERREUR] python.exe introuvable dans %PYTHON_HOME%
    exit /b 1
)

:: Supprimer l'ancien package si existant
if exist "%OUTPUT_DIR%" (
    echo [INFO] Suppression de l'ancien package...
    rmdir /s /q "%OUTPUT_DIR%"
)

:: Creer le dossier de sortie
echo [INFO] Creation du dossier de sortie...
mkdir "%OUTPUT_DIR%"

:: Copier les fichiers essentiels
echo [INFO] Copie des fichiers du projet...

xcopy /E /I /Q "%PROJECT_DIR%\src" "%OUTPUT_DIR%\src"
xcopy /E /I /Q "%PROJECT_DIR%\.venv" "%OUTPUT_DIR%\.venv"
xcopy /E /I /Q "%PROJECT_DIR%\assets" "%OUTPUT_DIR%\assets"
xcopy /E /I /Q "%PROJECT_DIR%\docs" "%OUTPUT_DIR%\docs"

:: Copier _AppConfig : uniquement les sous-dossiers (themes, langues, etc.)
:: Exclure les fichiers personnels (.db, .json) a la racine
echo [INFO] Copie de _AppConfig (sous-dossiers uniquement)...
mkdir "%OUTPUT_DIR%\_AppConfig"
for /d %%d in ("%PROJECT_DIR%\_AppConfig\*") do (
    xcopy /E /I /Q "%%d" "%OUTPUT_DIR%\_AppConfig\%%~nxd"
)

copy "%PROJECT_DIR%\pyproject.toml" "%OUTPUT_DIR%\" >nul
copy "%PROJECT_DIR%\uv.lock" "%OUTPUT_DIR%\" >nul
copy "%PROJECT_DIR%\run.py" "%OUTPUT_DIR%\" >nul

:: Copier la distribution Python
echo [INFO] Copie de la distribution Python...
xcopy /E /I /Q "%PYTHON_HOME%" "%OUTPUT_DIR%\_python"

:: Creer le run.bat qui corrige pyvenv.cfg au lancement
echo [INFO] Creation du lanceur run.bat...
(
echo @echo off
echo cd /d "%%~dp0"
echo.
echo :: Fix pyvenv.cfg to point to local Python
echo set "LOCAL_PYTHON=%%~dp0_python"
echo ^(
echo echo home = %%LOCAL_PYTHON%%
echo echo implementation = CPython
echo echo version_info = 3.14.0
echo echo include-system-site-packages = false
echo echo prompt = data-forge-studio
echo ^) ^> ".venv\pyvenv.cfg"
echo.
echo .venv\Scripts\python.exe run.py
echo pause
) > "%OUTPUT_DIR%\run.bat"

:: Telecharger UV si curl disponible
echo [INFO] Telechargement de UV...
where curl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    curl -L -o "%SCRIPT_DIR%\uv.zip" %UV_URL% 2>nul
    if exist "%SCRIPT_DIR%\uv.zip" (
        echo [INFO] Extraction de UV...
        powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%\uv.zip' -DestinationPath '%SCRIPT_DIR%\uv_temp' -Force"
        copy "%SCRIPT_DIR%\uv_temp\uv.exe" "%OUTPUT_DIR%\" >nul
        rmdir /s /q "%SCRIPT_DIR%\uv_temp"
        del "%SCRIPT_DIR%\uv.zip"
        echo [OK] UV inclus dans le package
    ) else (
        echo [WARN] Impossible de telecharger UV, package sans UV
    )
) else (
    echo [WARN] curl non disponible, package sans UV
)

echo.
echo ============================================================
echo  Package pret !
echo ============================================================
echo.
echo  Emplacement : %OUTPUT_DIR%
echo  Python embarque dans : %OUTPUT_DIR%\_python
echo.
echo  Pour distribuer :
echo  1. Copier le dossier DataForgeStudio_Offline sur cle USB
echo  2. Sur la machine cible, copier vers C:\Apps\DataForgeStudio
echo  3. Lancer run.bat
echo.
echo ============================================================

endlocal
