Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)

pythonwPath = "C:\Users\Usuario\AppData\Local\Programs\Python\Python313\pythonw.exe"
If Not fso.FileExists(pythonwPath) Then
    pythonwPath = "pythonw.exe"
End If

scriptPath = fso.BuildPath(strDir, "pomodoro_app.py")
cmd = """" & pythonwPath & """ """ & scriptPath & """"
WshShell.CurrentDirectory = strDir
WshShell.Run cmd, 0, False
