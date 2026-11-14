@echo off
setlocal EnableDelayedExpansion
title Activacion CORVI Control de Asistencia

echo ============================================================
echo    CORVI CONTROL DE ASISTENCIA - ACTIVACION OFICIAL
echo                CORVI CONSULTORES S.A.S.
echo ============================================================
echo.

:: 1. Detener procesos anteriores si estuvieran corriendo
echo [*] Preparando entorno...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *CORVI*" >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

:: Limpiar accesos viejos de NSIS en Menu Inicio
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" (
    rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\CORVI" >nul 2>&1
)

:: 2. Directorio local de instalacion
set "INSTALL_DIR=%LOCALAPPDATA%\CORVI_Asistencia"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 3. Descargar archivos oficiales de la aplicacion
echo [*] Descargando componentes del aplicativo...
set "BASE_URL=https://raw.githubusercontent.com/Tecnologiacorvi/setup/main"

curl.exe -sL "%BASE_URL%/corvi_asistencia.py" -o "%INSTALL_DIR%\corvi_asistencia.py"
curl.exe -sL "%BASE_URL%/iniciar_asistencia.vbs" -o "%INSTALL_DIR%\iniciar_asistencia.vbs"
curl.exe -sL "%BASE_URL%/icono_corvi.ico" -o "%INSTALL_DIR%\icono_corvi.ico"
curl.exe -sL "%BASE_URL%/version.json" -o "%INSTALL_DIR%\version.json"

:: 4. Validar libreria de capturas silenciosamente
echo [*] Verificando dependencias...
python -m pip install Pillow --quiet >nul 2>&1
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m pip install Pillow --quiet >nul 2>&1
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m pip install Pillow --quiet >nul 2>&1
)

:: 5. Crear acceso directo con logo oficial (linea por linea, sin bloques de parentesis)
echo [*] Creando acceso directo en el Escritorio...
set "VBS_LNK=%TEMP%\mk_corvi_lnk.vbs"

echo Set W = CreateObject("WScript.Shell") > "%VBS_LNK%"
echo Set F = CreateObject("Scripting.FileSystemObject") >> "%VBS_LNK%"
echo P = "%INSTALL_DIR%" >> "%VBS_LNK%"
echo I = P ^& "\icono_corvi.ico,0" >> "%VBS_LNK%"
echo. >> "%VBS_LNK%"
echo D1 = W.SpecialFolders("Desktop") >> "%VBS_LNK%"
echo If F.FolderExists(D1) Then >> "%VBS_LNK%"
echo   Set L = W.CreateShortcut(D1 ^& "\Control de Asistencia.lnk") >> "%VBS_LNK%"
echo   L.TargetPath = "wscript.exe" >> "%VBS_LNK%"
echo   L.Arguments = Chr(34) ^& P ^& "\iniciar_asistencia.vbs" ^& Chr(34) >> "%VBS_LNK%"
echo   L.WorkingDirectory = P >> "%VBS_LNK%"
echo   L.IconLocation = I >> "%VBS_LNK%"
echo   L.Description = "CORVI Control de Asistencia" >> "%VBS_LNK%"
echo   L.Save >> "%VBS_LNK%"
echo End If >> "%VBS_LNK%"
echo. >> "%VBS_LNK%"
echo D2 = W.ExpandEnvironmentStrings("%%USERPROFILE%%\OneDrive\Escritorio") >> "%VBS_LNK%"
echo If F.FolderExists(D2) Then >> "%VBS_LNK%"
echo   Set L2 = W.CreateShortcut(D2 ^& "\Control de Asistencia.lnk") >> "%VBS_LNK%"
echo   L2.TargetPath = "wscript.exe" >> "%VBS_LNK%"
echo   L2.Arguments = Chr(34) ^& P ^& "\iniciar_asistencia.vbs" ^& Chr(34) >> "%VBS_LNK%"
echo   L2.WorkingDirectory = P >> "%VBS_LNK%"
echo   L2.IconLocation = I >> "%VBS_LNK%"
echo   L2.Description = "CORVI Control de Asistencia" >> "%VBS_LNK%"
echo   L2.Save >> "%VBS_LNK%"
echo End If >> "%VBS_LNK%"
echo. >> "%VBS_LNK%"
echo D3 = W.ExpandEnvironmentStrings("%%USERPROFILE%%\OneDrive\Desktop") >> "%VBS_LNK%"
echo If F.FolderExists(D3) Then >> "%VBS_LNK%"
echo   Set L3 = W.CreateShortcut(D3 ^& "\Control de Asistencia.lnk") >> "%VBS_LNK%"
echo   L3.TargetPath = "wscript.exe" >> "%VBS_LNK%"
echo   L3.Arguments = Chr(34) ^& P ^& "\iniciar_asistencia.vbs" ^& Chr(34) >> "%VBS_LNK%"
echo   L3.WorkingDirectory = P >> "%VBS_LNK%"
echo   L3.IconLocation = I >> "%VBS_LNK%"
echo   L3.Description = "CORVI Control de Asistencia" >> "%VBS_LNK%"
echo   L3.Save >> "%VBS_LNK%"
echo End If >> "%VBS_LNK%"

cscript //nologo "%VBS_LNK%"
del /f /q "%VBS_LNK%" >nul 2>&1

:: Refrescar cache de iconos en Windows
ie4uinit.exe -show >nul 2>&1

:: 6. Abrir la aplicacion
echo [*] Iniciando CORVI Control de Asistencia...
cd /d "%INSTALL_DIR%"
start "" wscript.exe "%INSTALL_DIR%\iniciar_asistencia.vbs"

echo.
echo ============================================================
echo   ACTIVACION COMPLETADA
echo   El acceso directo quedo en tu Escritorio.
echo ============================================================
timeout /t 3 >nul
exit
