@echo off
cd /d "%~dp0"
if exist "C:\Users\Usuario\AppData\Local\Programs\Python\Python313\pythonw.exe" (
    start "" "C:\Users\Usuario\AppData\Local\Programs\Python\Python313\pythonw.exe" "pomodoro_app.py"
) else (
    start "" pythonw "pomodoro_app.py"
)
exit
