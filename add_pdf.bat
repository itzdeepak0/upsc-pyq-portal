@echo off
setlocal enabledelayedexpansion

echo ====================================================================
echo        UPSC Prelims PYQ - Future PDF Importer (Upcoming Months)
echo ====================================================================

if "%~1"=="" (
    echo [INFO] No file dropped.
    echo.
    echo How to use this:
    echo   1. Simply DRAG AND DROP your new PDF (e.g., July 2026 GMT) onto this .bat file!
    echo   OR
    echo   2. Drop your PDF into the 'incoming_pdfs' folder and press Enter below.
    echo.
    set /p CHOICE="Scan 'incoming_pdfs' folder now? (y/n): "
    if /i "!CHOICE!"=="y" (
        "C:\Users\Deepa\AppData\Local\Programs\Python\Python314\python.exe" manage.py scan_incoming
    )
    goto end
)

set PDF_PATH=%~1
echo Target PDF: %PDF_PATH%
echo Parsing and importing into SQLite database...
echo.

"C:\Users\Deepa\AppData\Local\Programs\Python\Python314\python.exe" manage.py import_pyq "%PDF_PATH%"

:end
echo.
echo ====================================================================
echo Done! Refresh your browser at http://127.0.0.1:8000/ to practice.
echo ====================================================================
pause
