@echo off
title Connectify Chat Website
echo ================================
echo       CONNECTIFY STARTUP
echo ================================
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env (
    copy .env.example .env
    echo.
    echo Created .env. Open it and enter your MySQL password.
    echo Then run run_windows.bat again.
    pause
    exit /b
)
python app.py
pause
