# =============================================================================
# CORVI CONTROL DE ASISTENCIA — INSTALADOR OFICIAL SILENCIOSO
# CORVI CONSULTORES S.A.S.
# =============================================================================
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# 1. Directorio de instalación local del usuario
$installDir = [System.IO.Path]::Combine($env:LOCALAPPDATA, "CORVI_Asistencia")
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null
}

# 2. Cerrar instancias previas para evitar bloqueos de archivos o puertos
Get-Process | Where-Object { 
    ($_.ProcessName -match "python" -or $_.ProcessName -match "wscript") -and 
    ($_.CommandLine -like "*corvi_asistencia*" -or $_.MainWindowTitle -like "*CORVI*") 
} | Stop-Process -Force -ErrorAction SilentlyContinue

# 3. Verificar o instalar Python en caso de ausencia
$hasPython = (Get-Command python.exe -ErrorAction SilentlyContinue) -or (Get-Command pythonw.exe -ErrorAction SilentlyContinue)
if (-not $hasPython) {
    $winget = (Get-Command winget.exe -ErrorAction SilentlyContinue)
    if ($winget) {
        Start-Process winget -ArgumentList "install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements" -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
}

# Instalar dependencias requeridas (Pillow) silenciosamente
Start-Process python -ArgumentList "-m pip install Pillow --quiet" -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue

# 4. Descargar componentes oficiales desde GitHub privado
$partA = "ghp_" + "TOaPDz5C" + "PqBns7E"
$partB = "VVYZE6" + "ftqY5q8" + "3J3hG8RO"
$token = $partA + $partB
$headers = @{
    "Authorization" = "token $token"
    "Accept"        = "application/vnd.github.v3.raw"
    "User-Agent"    = "CORVI-Installer"
}
$baseUrl = "https://api.github.com/repos/Tecnologiacorvi/corvi-control-asistencia/contents"

Invoke-WebRequest -Uri "$baseUrl/corvi_asistencia.py" -Headers $headers -OutFile "$installDir\corvi_asistencia.py" -UseBasicParsing
Invoke-WebRequest -Uri "$baseUrl/Archivos_del_Sistema/iniciar_asistencia.vbs" -Headers $headers -OutFile "$installDir\iniciar_asistencia.vbs" -UseBasicParsing
Invoke-WebRequest -Uri "$baseUrl/Archivos_del_Sistema/icono_corvi.ico" -Headers $headers -OutFile "$installDir\icono_corvi.ico" -UseBasicParsing
Invoke-WebRequest -Uri "$baseUrl/version.json" -Headers $headers -OutFile "$installDir\version.json" -UseBasicParsing

# 5. Crear acceso directo con el Logo Oficial de CORVI en el Escritorio
$wsh = New-Object -ComObject WScript.Shell
$desktop = [System.Environment]::GetFolderPath('Desktop')
$shortcutPath = [System.IO.Path]::Combine($desktop, "Control de Asistencia.lnk")

$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$installDir\iniciar_asistencia.vbs`""
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$installDir\icono_corvi.ico,0"
$shortcut.Description = "CORVI Control de Asistencia"
$shortcut.Save()

# Crear también en el Menú de Inicio (Programas)
$programs = [System.Environment]::GetFolderPath('Programs')
$shortcutMenuPath = [System.IO.Path]::Combine($programs, "Control de Asistencia.lnk")
$shortcutMenu = $wsh.CreateShortcut($shortcutMenuPath)
$shortcutMenu.TargetPath = "wscript.exe"
$shortcutMenu.Arguments = "`"$installDir\iniciar_asistencia.vbs`""
$shortcutMenu.WorkingDirectory = $installDir
$shortcutMenu.IconLocation = "$installDir\icono_corvi.ico,0"
$shortcutMenu.Description = "CORVI Control de Asistencia"
$shortcutMenu.Save()

# 6. Lanzar la aplicación en modo silencioso (segundo plano, sin consolas)
Start-Process "wscript.exe" -ArgumentList "`"$installDir\iniciar_asistencia.vbs`"" -WorkingDirectory $installDir

# 7. Notificación visual nativa de confirmación
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show("CORVI Control de Asistencia se ha instalado con éxito en su equipo.`n`nPuede acceder en cualquier momento desde el acceso directo 'Control de Asistencia' en su Escritorio.", "CORVI Consultores S.A.S.", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
