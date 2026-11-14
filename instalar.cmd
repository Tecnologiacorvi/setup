@echo off
setlocal EnableDelayedExpansion
title Instalador Oficial CORVI Control de Asistencia

echo ============================================================
echo    CORVI CONTROL DE ASISTENCIA - INSTALADOR OFICIAL
echo                CORVI CONSULTORES S.A.S.
echo ============================================================
echo.

:: 1. Detener procesos previos
echo [*] Preparando entorno y liberando puertos...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *CORVI*" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

:: Limpiar residuos viejos de NSIS en el Menu Inicio
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" (
    rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" >nul 2>&1
)

:: 2. Directorio de instalacion en AppData local del usuario
set "INSTALL_DIR=%LOCALAPPDATA%\CORVI_Asistencia"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 3. Descargar componentes oficiales de CORVI directamente (sin tokens)
echo [*] Descargando aplicacion CORVI...
set "BASE_URL=https://raw.githubusercontent.com/Tecnologiacorvi/setup/main"

curl.exe -sL "%BASE_URL%/corvi_asistencia.py" -o "%INSTALL_DIR%\corvi_asistencia.py"
curl.exe -sL "%BASE_URL%/iniciar_asistencia.vbs" -o "%INSTALL_DIR%\iniciar_asistencia.vbs"
curl.exe -sL "%BASE_URL%/icono_corvi.ico" -o "%INSTALL_DIR%\icono_corvi.ico"
curl.exe -sL "%BASE_URL%/version.json" -o "%INSTALL_DIR%\version.json"

:: 4. Validar si el equipo ya tiene Python o instalar la version oficial silenciosa
set "PYTHON_FOUND=0"
set "PY_BIN="

if exist "%INSTALL_DIR%\python\pythonw.exe" (
    set "PYTHON_FOUND=1"
    set "PY_BIN=%INSTALL_DIR%\python\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
    set "PYTHON_FOUND=1"
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe" (
    set "PYTHON_FOUND=1"
    set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "C:\Python311\pythonw.exe" (
    set "PYTHON_FOUND=1"
    set "PY_BIN=C:\Python311\python.exe"
)

if "!PYTHON_FOUND!"=="0" (
    echo.
    echo [*] Configurando motor oficial de Python en su equipo...
    echo [*] Descargando instalador certificado de Python 3.11 (25 MB)...
    
    curl.exe -L --progress-bar "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -o "%TEMP%\python_setup.exe"
    
    echo [*] Instalando motor de Python silenciosamente (espere unos 15 segundos)...
    start /wait "" "%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 SimpleInstall=1
    del /f /q "%TEMP%\python_setup.exe" >nul 2>&1
    
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY_BIN=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        set "PYTHON_FOUND=1"
    )
)

:: 5. Instalar soporte de dependencias graficas
if defined PY_BIN (
    if exist "!PY_BIN!" (
        echo [*] Verificando dependencias del sistema...
        "!PY_BIN!" -m pip install Pillow --quiet >nul 2>&1
    )
)

:: 6. Crear acceso directo en el Escritorio con logo oficial de CORVI
echo [*] Creando acceso directo en el Escritorio con logo oficial...
set "VBS_SHORTCUT=%TEMP%\create_corvi_shortcut_%RANDOM%.vbs"
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sDesktop = oWS.SpecialFolders^("Desktop"^)
echo sAppDir = oWS.ExpandEnvironmentStrings^("%%LOCALAPPDATA%%\CORVI_Asistencia"^)
echo sIco = sAppDir ^& "\icono_corvi.ico,0"
echo Set oLink = oWS.CreateShortcut^(sDesktop ^& "\Control de Asistencia.lnk"^)
echo oLink.TargetPath = "wscript.exe"
echo oLink.Arguments = """" ^& sAppDir ^& "\iniciar_asistencia.vbs" ^& """"
echo oLink.WorkingDirectory = sAppDir
echo oLink.IconLocation = sIco
echo oLink.Description = "CORVI Control de Asistencia"
echo oLink.Save
echo Set oLink2 = oWS.CreateShortcut^(oWS.SpecialFolders^("Programs"^) ^& "\Control de Asistencia.lnk"^)
echo oLink2.TargetPath = "wscript.exe"
echo oLink2.Arguments = """" ^& sAppDir ^& "\iniciar_asistencia.vbs" ^& """"
echo oLink2.WorkingDirectory = sAppDir
echo oLink2.IconLocation = sIco
echo oLink2.Description = "CORVI Control de Asistencia"
echo oLink2.Save
) > "%VBS_SHORTCUT%"
cscript //nologo "%VBS_SHORTCUT%" >nul 2>&1
del /f /q "%VBS_SHORTCUT%" >nul 2>&1

:: Refrescar iconos de Windows
ie4uinit.exe -show >nul 2>&1

:: 7. Iniciar la aplicacion de forma discreta en segundo plano
echo [*] Iniciando panel de control de asistencia...
cd /d "%INSTALL_DIR%"
start "" wscript.exe "%INSTALL_DIR%\iniciar_asistencia.vbs"

echo.
echo ============================================================
echo   INSTALACION COMPLETADA CON EXITO
echo   Acceso directo creado en el Escritorio con Logo Oficial.
echo ============================================================
timeout /t 3 >nul
exit
