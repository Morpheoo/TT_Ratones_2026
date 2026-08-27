Option Explicit

Dim shell, fso, appDir, dataDir, logDir, logPath, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
dataDir = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\TT_Ratones_2026"
logDir = dataDir & "\logs"
If Not fso.FolderExists(dataDir) Then fso.CreateFolder(dataDir)
If Not fso.FolderExists(logDir) Then fso.CreateFolder(logDir)
logPath = logDir & "\launcher.log"

shell.CurrentDirectory = appDir
command = "cmd.exe /d /c set TT_SILENT=1&& call " & Chr(34) & appDir & "\launcher.bat" & Chr(34) & " >> " & Chr(34) & logPath & Chr(34) & " 2>&1"
shell.Run command, 0, False
