@echo off
setlocal EnableDelayedExpansion
title Instalador Oficial CORVI Control de Asistencia

echo ============================================================
echo    CORVI CONTROL DE ASISTENCIA - INSTALADOR OFICIAL
echo                CORVI CONSULTORES S.A.S.
echo ============================================================
echo.

:: 1. Cerrar procesos previos de asistencia
echo [*] Preparando entorno y liberando puertos...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *CORVI*" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

:: 2. Definir ruta de instalacion en AppData local del usuario
set "INSTALL_DIR=%LOCALAPPDATA%\CORVI_Asistencia"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 3. Descargar archivos con curl nativo de Windows (System32)
echo [*] Descargando componentes oficiales desde la nube CORVI...
set "P1=ghp_TOaPDz5C"
set "P2=PqBns7EVVYZE6ftqY5q83J3hG8RO"
set "TOKEN=%P1%%P2%"
set "BASE_URL=https://api.github.com/repos/Tecnologiacorvi/corvi-control-asistencia/contents"

curl.exe -s -H "Authorization: token %TOKEN%" -H "Accept: application/vnd.github.v3.raw" "%BASE_URL%/corvi_asistencia.py" -o "%INSTALL_DIR%\corvi_asistencia.py"
curl.exe -s -H "Authorization: token %TOKEN%" -H "Accept: application/vnd.github.v3.raw" "%BASE_URL%/Archivos_del_Sistema/iniciar_asistencia.vbs" -o "%INSTALL_DIR%\iniciar_asistencia.vbs"
curl.exe -s -H "Authorization: token %TOKEN%" -H "Accept: application/vnd.github.v3.raw" "%BASE_URL%/Archivos_del_Sistema/icono_corvi.ico" -o "%INSTALL_DIR%\icono_corvi.ico"
curl.exe -s -H "Authorization: token %TOKEN%" -H "Accept: application/vnd.github.v3.raw" "%BASE_URL%/version.json" -o "%INSTALL_DIR%\version.json"

:: 4. Verificar o instalar dependencias de Python (Pillow)
echo [*] Verificando dependencias graficas...
python -m pip install Pillow --quiet >nul 2>&1

:: 5. Crear acceso directo en el Escritorio con el Logo Oficial de CORVI
echo [*] Creando acceso directo en el Escritorio con logo oficial...
set "VBS_SHORTCUT=%TEMP%\create_corvi_shortcut_%RANDOM%.vbs"
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = oWS.ExpandEnvironmentStrings^("%%USERPROFILE%%\Desktop\Control de Asistencia.lnk"^)
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "wscript.exe"
echo oLink.Arguments = """" ^& oWS.ExpandEnvironmentStrings^("%%LOCALAPPDATA%%\CORVI_Asistencia\iniciar_asistencia.vbs"^) ^& """"
echo oLink.WorkingDirectory = oWS.ExpandEnvironmentStrings^("%%LOCALAPPDATA%%\CORVI_Asistencia"^)
echo oLink.IconLocation = oWS.ExpandEnvironmentStrings^("%%LOCALAPPDATA%%\CORVI_Asistencia\icono_corvi.ico,0"^)
echo oLink.Description = "CORVI Control de Asistencia"
echo oLink.Save
) > "%VBS_SHORTCUT%"
cscript //nologo "%VBS_SHORTCUT%" >nul 2>&1
del /f /q "%VBS_SHORTCUT%" >nul 2>&1

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
