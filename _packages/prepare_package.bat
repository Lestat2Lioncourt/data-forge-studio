@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: DataForge Studio - Prepare Offline Package
:: ============================================================

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set OUTPUT_DIR=%SCRIPT_DIR%DataForgeStudio

:: Lire la version depuis pyproject.toml
set APP_VERSION=
for /f "tokens=2 delims== " %%v in ('findstr /B "version" "%PROJECT_DIR%\pyproject.toml"') do (
    set APP_VERSION=%%~v
)
if "%APP_VERSION%"=="" set APP_VERSION=unknown

echo.
echo ============================================================
echo  DataForge Studio v%APP_VERSION% - Preparation du package offline
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

:: Nettoyer pyvenv.cfg : remplacer le chemin local par un chemin relatif
echo [INFO] Nettoyage de pyvenv.cfg...
(
echo home = _python
echo implementation = CPython
echo version_info = 3.14.0
echo include-system-site-packages = false
echo prompt = data-forge-studio
) > "%OUTPUT_DIR%\.venv\pyvenv.cfg"

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

:: Suppression des anciens archives 7z
if exist "%SCRIPT_DIR%DataForgeStudio*.7z" (
    echo [INFO] Suppression des anciennes archives...
    del "%SCRIPT_DIR%DataForgeStudio*.7z"
)

:: Compression en 7z
echo [INFO] Compression en 7z (cette etape peut prendre plusieurs minutes)...
set ARCHIVE=%SCRIPT_DIR%DataForgeStudio_v%APP_VERSION%.7z

where 7z >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    7z a -t7z -mx=5 -bsp1 "%ARCHIVE%" "%OUTPUT_DIR%"
    echo [OK] Archive creee : %ARCHIVE%
) else (
    :: Essayer le chemin par defaut de 7-Zip
    if exist "C:\Program Files\7-Zip\7z.exe" (
        "C:\Program Files\7-Zip\7z.exe" a -t7z -mx=5 -bsp1 "%ARCHIVE%" "%OUTPUT_DIR%"
        echo [OK] Archive creee : %ARCHIVE%
    ) else (
        echo [WARN] 7z introuvable, compression ignoree
        echo        Installez 7-Zip ou compressez manuellement le dossier
    )
)

echo.
echo ============================================================
echo  Package pret !
echo ============================================================
echo.
echo  Dossier  : %OUTPUT_DIR%
echo  Archive  : %ARCHIVE%
echo  Python   : %OUTPUT_DIR%\_python
echo.
echo  Pour distribuer :
echo  1. Copier DataForgeStudio_v%APP_VERSION%.7z sur cle USB
echo  2. Sur la machine cible, extraire vers C:\Apps\DataForgeStudio
echo  3. Lancer run.bat
echo.
echo ============================================================

endlocal
