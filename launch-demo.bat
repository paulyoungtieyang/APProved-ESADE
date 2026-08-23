@echo off
REM APProved Medical Writing Platform — Launch Script (Windows)
REM Starts the Flask development server and opens the landing page in your browser

setlocal enabledelayedexpansion

echo ========================================================
echo   APProved Medical Writing Platform
echo ========================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.9 or later.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VERSION=%%i
echo OK - Python %PY_VERSION%

REM Check dependencies
echo OK - Checking dependencies...
python -c "import flask, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies with pip...
    python -m pip install -q flask sqlalchemy python-pptx markupsafe
)

REM Kill process on port 5001 if it exists
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001') do (
    echo Stopping existing process on port 5001...
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Starting APProved server...
echo.

REM Start the server
set OPEN_BROWSER=1
python app.py

pause
