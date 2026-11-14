' =============================================================================
' CORVI CONTROL DE ASISTENCIA — LANZADOR SILENCIOSO WINDOWS (MODO DISCRETO)
' Ejecuta el motor mediante pythonw.exe sin abrir ninguna consola CMD ni ventana negra.
' =============================================================================
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = currentDir

' 1. Usar SIEMPRE el motor propio y portatil de CORVI
If fso.FileExists(currentDir & "\python\pythonw.exe") Then
    pyExe = """" & currentDir & "\python\pythonw.exe"""
Else
    localAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
    If fso.FileExists(localAppData & "\Programs\Python\Python311\pythonw.exe") Then
        pyExe = """" & localAppData & "\Programs\Python\Python311\pythonw.exe"""
    ElseIf fso.FileExists(localAppData & "\Programs\Python\Python312\pythonw.exe") Then
        pyExe = """" & localAppData & "\Programs\Python\Python312\pythonw.exe"""
    ElseIf fso.FileExists("C:\Python311\pythonw.exe") Then
        pyExe = """C:\Python311\pythonw.exe"""
    Else
        pyExe = "pythonw.exe"
    End If
End If

On Error Resume Next
WshShell.Run pyExe & " """ & currentDir & "\corvi_asistencia.py""", 0, False
If Err.Number <> 0 Then
    MsgBox "No se encontró el motor de ejecución en su equipo." & vbCrLf & "Por favor ejecute el instalador oficial de CORVI para configurarlo automáticamente.", 48, "CORVI Control de Asistencia"
End If
