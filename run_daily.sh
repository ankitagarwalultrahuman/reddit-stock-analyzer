#!/bin/bash
# Daily Reddit Stock Analyzer Runner
# Add to crontab: 0 8 * * * /path/to/reddit-stock-analyzer/run_daily.sh

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Log file
LOG_FILE="$SCRIPT_DIR/logs/daily_run_$(date +%Y%m%d).log"
mkdir -p "$SCRIPT_DIR/logs"

echo "=== Reddit Stock Analyzer Daily Run ===" >> "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the analyzer
echo "Running analyzer..." >> "$LOG_FILE"
python main.py >> "$LOG_FILE" 2>&1

# Git commit the new report (optional - for version tracking)
if [ -d ".git" ]; then
    echo "Committing new report to git..." >> "$LOG_FILE"
    git add output/report_*.txt >> "$LOG_FILE" 2>&1 || true
    git commit -m "Daily report: $(date +%Y-%m-%d)" >> "$LOG_FILE" 2>&1 || true
fi

echo "Completed at: $(date)" >> "$LOG_FILE"
echo "=======================================" >> "$LOG_FILE"

# Clean up old logs (keep last 30 days)
find "$SCRIPT_DIR/logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true
