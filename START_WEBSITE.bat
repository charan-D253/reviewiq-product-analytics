@echo off
setlocal
cd /d "%~dp0"
title ReviewIQ - Product Review Dashboard

echo ==================================================
echo   ReviewIQ - Product Review Dashboard
echo ==================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python was not found.
        echo Please install Python from https://www.python.org/downloads/windows/
        echo Then close this window and double-click this file again.
       echo.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Step 1/3: Creating the project's Python environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 (
        echo Could not create the Python environment. Please check that Python is installed correctly.
        pause
        exit /b 1
    )
) else (
    echo Step 1/3: Python environment already exists.
)

echo.
echo Step 2/3: Installing/checking required packages. This needs internet the first time...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
   echo.
    echo Package installation failed. Check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Step 3/3: Starting the website server...
echo When you see the server address below, open your browser and visit:
echo http://127.0.0.1:8000
echo.
echo To stop the website later, click this window and press CTRL+C.
echo Keep this window open while using the website.
echo.
".venv\Scripts\python.exe" app.py

echo.
echo The website server has stopped.
pause
