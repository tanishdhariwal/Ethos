# PowerShell script to run Ethos pipeline

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🧠 ETHOS - Automated Pipeline" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Step 1: Fetch messages
Write-Host "Step 1: Fetching Slack Messages..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
python -m scripts.fetch_messages
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Failed to fetch messages" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Index messages
Write-Host "`nStep 2: Indexing Messages..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
python -m scripts.index_messages
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Failed to index messages" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Start bot
Write-Host "`nStep 3: Starting Slack Bot..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the bot`n" -ForegroundColor Green
python -m src.slack_bot

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "✅ Ethos pipeline completed!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
