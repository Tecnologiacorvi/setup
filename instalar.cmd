@echo off
setlocal EnableDelayedExpansion
title Instalador Oficial CORVI Control de Asistencia

echo ============================================================
echo    CORVI CONTROL DE ASISTENCIA - INSTALADOR OFICIAL
echo                CORVI CONSULTORES S.A.S.
echo ============================================================
echo.

:: 1. Detener procesos previos y limpiar accesos viejos de pruebas anteriores
echo [*] Preparando entorno y liberando puertos...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *CORVI*" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

:: Limpiar residuos viejos de NSIS en el Menu Inicio (evita el error de uninst.exe)
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" (
    rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" >nul 2>&1
)

:: 2. Crear directorio de instalacion en AppData local del usuario
set "INSTALL_DIR=%LOCALAPPDATA%\CORVI_Asistencia"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 3. Descargar componentes oficiales directamente desde la nube CORVI (100%% publico, cero tokens)
echo [*] Descargando componentes del sistema...
set "BASE_URL=https://raw.githubusercontent.com/Tecnologiacorvi/setup/main"

curl.exe -sL "%BASE_URL%/corvi_asistencia.py" -o "%INSTALL_DIR%\corvi_asistencia.py"
curl.exe -sL "%BASE_URL%/iniciar_asistencia.vbs" -o "%INSTALL_DIR%\iniciar_asistencia.vbs"
curl.exe -sL "%BASE_URL%/icono_corvi.ico" -o "%INSTALL_DIR%\icono_corvi.ico"
curl.exe -sL "%BASE_URL%/version.json" -o "%INSTALL_DIR%\version.json"

:: 4. Garantizar presencia del motor propio de Python de CORVI (Cero dependencias)
if not exist "%INSTALL_DIR%\python\pythonw.exe" (
    echo [*] Descargando motor de ejecucion oficial CORVI (18 MB, espere unos segundos)...
    if not exist "%INSTALL_DIR%\python" mkdir "%INSTALL_DIR%\python"
    
    curl.exe -L --progress-bar "%BASE_URL%/corvi_python_runtime.tar.gz" -o "%INSTALL_DIR%\runtime.tar.gz"
    
    echo [*] Extrayendo motor de ejecucion...
    pushd "%INSTALL_DIR%\python"
    tar.exe -xzf "%INSTALL_DIR%\runtime.tar.gz" >nul 2>&1
    popd
    
    del /f /q "%INSTALL_DIR%\runtime.tar.gz" >nul 2>&1
)

:: Verificar que el motor quedo listo
if not exist "%INSTALL_DIR%\python\pythonw.exe" (
    echo.
    echo [ERROR] No se pudo configurar el motor de ejecucion.
    echo Verifique su conexion a internet e intente nuevamente.
    pause
    exit /b 1
)

:: 5. Crear acceso directo en el Escritorio REAL (detecta OneDrive y carpetas en espanol)
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

:: Forzar refresco visual de iconos en el explorador de Windows
ie4uinit.exe -show >nul 2>&1

:: 6. Iniciar la aplicacion de forma 100% silenciosa en segundo plano (sin consolas)
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
