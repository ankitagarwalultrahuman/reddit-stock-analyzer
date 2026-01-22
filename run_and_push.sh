#!/bin/bash
# Helper script to run the scraper locally and push results to Git

set -e

echo "=========================================="
echo "  Reddit Stock Analyzer - Local Runner"
echo "=========================================="

# Determine session
SESSION=${1:-next}
echo "Session: $SESSION"

# Run the analyzer
echo ""
echo "Running analyzer..."
python main.py --session "$SESSION"

# Check if there are new files to commit
echo ""
echo "Checking for new files..."

# Add report and comparison files
git add output/report_*.txt 2>/dev/null || true
git add output/comparison_*.json 2>/dev/null || true

# Check if anything was staged
if git diff --staged --quiet; then
    echo "No new files to commit."
else
    echo ""
    echo "New files to commit:"
    git diff --staged --name-only

    echo ""
    read -p "Push to Git? (y/n): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        git commit -m "Add $(date +'%Y-%m-%d') report (local run)"
        git push
        echo ""
        echo "Pushed successfully!"
    else
        echo "Skipped. Files are staged but not committed."
    fi
fi

echo ""
echo "Done!"
