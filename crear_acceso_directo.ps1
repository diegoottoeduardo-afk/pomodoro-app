$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Pomodoro Focus.lnk"
$appDir = "C:\Users\Usuario\.gemini\antigravity\scratch\pomodoro-app"
$targetScript = Join-Path $appDir "iniciar_silencioso.vbs"
$iconPath = Join-Path $appDir "pomodoro.ico"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$targetScript`""
$shortcut.WorkingDirectory = $appDir
$shortcut.IconLocation = "$iconPath, 0"
$shortcut.Description = "Temporizador Pomodoro para Windows"
$shortcut.Save()

Write-Host "Acceso directo creado con éxito en el Escritorio: $shortcutPath"
