@echo off
echo ============================================
echo   Thermography Compliance AI v2.0
echo   Industrial Monitoring Platform
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

:: Create venv
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate
call venv\Scripts\activate.bat

:: Install
echo Installing dependencies...
pip install -q -r requirements.txt

:: Copy env
if not exist ".env" (
    copy .env.example .env
    echo Created .env - edit it for MongoDB Atlas connection
)

echo.
echo Starting platform...
echo Open: http://localhost:8000
echo.

cd backend
python main.py
pause
