# Actualizador Oficial CORVI Control de Asistencia v1.5.3
$ErrorActionPreference = "SilentlyContinue"
Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

$dir = Join-Path $env:LOCALAPPDATA "CORVI_Asistencia"
if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

$baseUrl = "https://raw.githubusercontent.com/Tecnologiacorvi/setup/main"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Invoke-WebRequest -Uri "$baseUrl/corvi_asistencia.pyw" -OutFile (Join-Path $dir "corvi_asistencia.pyw") -UseBasicParsing
Copy-Item (Join-Path $dir "corvi_asistencia.pyw") (Join-Path $dir "corvi_asistencia.py") -Force
Invoke-WebRequest -Uri "$baseUrl/iniciar_asistencia.vbs" -OutFile (Join-Path $dir "iniciar_asistencia.vbs") -UseBasicParsing
Invoke-WebRequest -Uri "$baseUrl/version.json" -OutFile (Join-Path $dir "version.json") -UseBasicParsing

$vbs = Join-Path $dir "iniciar_asistencia.vbs"
Start-Process "wscript.exe" -ArgumentList "`"$vbs`""
