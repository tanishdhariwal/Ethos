@echo off
REM Windows batch script to run Ethos pipeline

echo ============================================================
echo ETHOS - Automated Pipeline
echo ============================================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

echo Step 1: Fetching Slack Messages...
echo ============================================================
python -m scripts.fetch_messages
if errorlevel 1 (
    echo.
    echo ERROR: Failed to fetch messages
    pause
    exit /b 1
)

echo.
echo Step 2: Indexing Messages...
echo ============================================================
python -m scripts.index_messages
if errorlevel 1 (
    echo.
    echo ERROR: Failed to index messages
    pause
    exit /b 1
)

echo.
echo Step 3: Starting Slack Bot...
echo ============================================================
echo Press Ctrl+C to stop the bot
echo.
python -m src.slack_bot

echo.
echo ============================================================
echo Ethos pipeline completed!
echo ============================================================
pause
