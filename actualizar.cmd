@echo off
title Actualizacion CORVI Control de Asistencia
echo [*] Actualizando Control de Asistencia a la ultima version...
taskkill /F /IM pythonw.exe >nul 2>&1
taskkill /F /IM python.exe >nul 2>&1
set "INSTALL_DIR=%LOCALAPPDATA%\CORVI_Asistencia"
curl.exe -sL https://raw.githubusercontent.com/Tecnologiacorvi/setup/main/corvi_asistencia.pyw -o "%INSTALL_DIR%\corvi_asistencia.pyw"
copy /Y "%INSTALL_DIR%\corvi_asistencia.pyw" "%INSTALL_DIR%\corvi_asistencia.py" >nul 2>&1
curl.exe -sL https://raw.githubusercontent.com/Tecnologiacorvi/setup/main/iniciar_asistencia.vbs -o "%INSTALL_DIR%\iniciar_asistencia.vbs"
curl.exe -sL https://raw.githubusercontent.com/Tecnologiacorvi/setup/main/version.json -o "%INSTALL_DIR%\version.json"
start "" wscript.exe "%INSTALL_DIR%\iniciar_asistencia.vbs"
echo [OK] Actualizado con exito.
timeout /t 2 >nul
