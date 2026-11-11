@echo off
echo ========================================================
echo   Starting UPSC Prelims PYQ Interactive Web Portal
echo   Stack: Python, Django, SQLite
echo ========================================================
cd /d "%~dp0"
start http://127.0.0.1:8000/
"C:\Users\Deepa\AppData\Local\Programs\Python\Python314\python.exe" manage.py runserver 127.0.0.1:8000
pause
