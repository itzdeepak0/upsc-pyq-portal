@echo off
setlocal

echo ====================================================================
echo             Push UPSC PYQ Portal to GitHub for Hosting
echo ====================================================================
echo.
echo 1. Create a new repository on GitHub: https://github.com/new
echo    (Name it e.g. "upsc-pyq-portal" - Leave it empty, no README)
echo.
set /p REPO_URL="2. Paste your GitHub Repository URL here: "

if "%REPO_URL%"=="" (
    echo [ERROR] No URL entered. Exiting.
    pause
    exit /b
)

cd /d "%~dp0"
echo.
echo Setting branch to main...
git branch -M main

echo Configuring remote origin...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo Pushing code and database to GitHub...
git push -u origin main

echo.
echo ====================================================================
echo Success! Your code and database are now on GitHub.
echo Now go to https://dashboard.render.com and link this repository!
echo ====================================================================
pause
