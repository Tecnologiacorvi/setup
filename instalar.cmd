@echo off
setlocal EnableDelayedExpansion
title Instalador CORVI Control de Asistencia

echo ============================================================
echo    CORVI CONTROL DE ASISTENCIA - ACTIVACION OFICIAL
echo                CORVI CONSULTORES S.A.S.
echo ============================================================
echo.

:: 1. Detener instancias previas
echo [*] Preparando entorno...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *CORVI*" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

:: Limpiar residuos viejos de NSIS en Menu Inicio
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" (
    rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" >nul 2>&1
)

:: 2. Crear directorio de instalacion en AppData local del usuario
set "INSTALL_DIR=%LOCALAPPDATA%\CORVI_Asistencia"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 3. Descargar componentes oficiales de CORVI directamente
echo [*] Descargando aplicacion CORVI...
set "BASE_URL=https://raw.githubusercontent.com/Tecnologiacorvi/setup/main"

curl.exe -sL "%BASE_URL%/corvi_asistencia.py" -o "%INSTALL_DIR%\corvi_asistencia.py"
curl.exe -sL "%BASE_URL%/iniciar_asistencia.vbs" -o "%INSTALL_DIR%\iniciar_asistencia.vbs"
curl.exe -sL "%BASE_URL%/icono_corvi.ico" -o "%INSTALL_DIR%\icono_corvi.ico"
curl.exe -sL "%BASE_URL%/version.json" -o "%INSTALL_DIR%\version.json"

:: 4. Verificar presencia de Python y dependencias
echo [*] Verificando motor de ejecucion...
where python.exe >nul 2>&1
if %errorlevel% equ 0 (
    python.exe -m pip install Pillow --quiet >nul 2>&1
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m pip install Pillow --quiet >nul 2>&1
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install Pillow --quiet >nul 2>&1
)

:: 5. Crear acceso directo con logo oficial en TODOS los escritorios posibles (OneDrive + Local)
echo [*] Creando acceso directo en el Escritorio con logo oficial...
set "VBS_SHORTCUT=%TEMP%\create_corvi_shortcut_%RANDOM%.vbs"
(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo Set fso = CreateObject^("Scripting.FileSystemObject"^)
echo sAppDir = "%INSTALL_DIR%"
echo sIco = "%INSTALL_DIR%\icono_corvi.ico,0"
echo.
echo Sub CrearLnk^(sRutaFolder^)
echo   If fso.FolderExists^(sRutaFolder^) Then
echo     Set oLink = oWS.CreateShortcut^(sRutaFolder ^& "\Control de Asistencia.lnk"^)
echo     oLink.TargetPath = "wscript.exe"
echo     oLink.Arguments = """" ^& sAppDir ^& "\iniciar_asistencia.vbs" ^& """"
echo     oLink.WorkingDirectory = sAppDir
echo     oLink.IconLocation = sIco
echo     oLink.Description = "CORVI Control de Asistencia"
echo     oLink.Save
echo   End If
echo End Sub
echo.
echo CrearLnk oWS.SpecialFolders^("Desktop"^)
echo CrearLnk oWS.SpecialFolders^("Programs"^)
echo CrearLnk oWS.ExpandEnvironmentStrings^("%%USERPROFILE%%\Desktop"^)
echo CrearLnk oWS.ExpandEnvironmentStrings^("%%USERPROFILE%%\Escritorio"^)
echo CrearLnk oWS.ExpandEnvironmentStrings^("%%USERPROFILE%%\OneDrive\Desktop"^)
echo CrearLnk oWS.ExpandEnvironmentStrings^("%%USERPROFILE%%\OneDrive\Escritorio"^)
) > "%VBS_SHORTCUT%"

cscript //nologo "%VBS_SHORTCUT%"
del /f /q "%VBS_SHORTCUT%" >nul 2>&1

:: Forzar refresco visual inmediato de iconos en Windows
ie4uinit.exe -show >nul 2>&1

:: 6. Iniciar panel de control de asistencia
echo [*] Iniciando panel de control de asistencia...
cd /d "%INSTALL_DIR%"
start "" wscript.exe "%INSTALL_DIR%\iniciar_asistencia.vbs"

echo.
echo ============================================================
echo   ACTIVACION COMPLETADA CON EXITO
echo   Icono creado en el Escritorio con Logo Oficial de CORVI.
echo ============================================================
timeout /t 3 >nul
exit
