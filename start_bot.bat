@echo off
REM ============================================================================
REM DAUGHTER VOICE BOT - WINDOWS LAUNCHER
REM ============================================================================

setlocal enabledelayedexpansion

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found!
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo.
    echo ============================================================================
    echo FIRST TIME SETUP - ENTER YOUR LIVEKIT CREDENTIALS
    echo ============================================================================
    echo.
    
    set /p LIVEKIT_URL="Enter LiveKit URL (ws://your-url:7880): "
    set /p LIVEKIT_API_KEY="Enter LiveKit API Key: "
    set /p LIVEKIT_API_SECRET="Enter LiveKit API Secret: "
    
    (
        echo LIVEKIT_URL=%LIVEKIT_URL%
        echo LIVEKIT_API_KEY=%LIVEKIT_API_KEY%
        echo LIVEKIT_API_SECRET=%LIVEKIT_API_SECRET%
    ) > .env
    
    echo.
    echo [✓] Credentials saved to .env
    echo.
)

REM Check if dependencies are installed
pip show pystray >nul 2>&1
if errorlevel 1 (
    echo.
    echo [*] Installing dependencies (first time)...
    echo.
    pip install -r background_requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies
        echo.
        pause
        exit /b 1
    )
    echo [✓] Dependencies installed
    echo.
)

REM Start the bot
echo.
echo ============================================================================
echo STARTING DAUGHTER VOICE BOT
echo ============================================================================
echo.
echo [✓] System tray starting...
echo [✓] Right-click icon to listen
echo [✓] Only LiveKit required (no other API keys)
echo.
echo ============================================================================
echo.

python background_voice_bot.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot encountered an error
    echo.
    pause
)

exit /b 0
