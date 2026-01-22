# Reddit Indian Stock Market Analyzer

A Python tool that scrapes top posts from Indian stock market subreddits and uses Claude AI to generate daily insights, sentiment analysis, and actionable recommendations.

## Features

- **Reddit Scraping**: Fetches top posts and comments from Indian stock market communities (no API auth required)
- **AI-Powered Analysis**: Uses Claude API to extract insights, sentiment, and recommendations
- **Citation Tracking**: Every insight includes exact post/comment counts for credibility
- **Streamlit Dashboard**: Beautiful UI with daily reports, charts, and 7-day summaries
- **Portfolio Integration**: Match your holdings against Reddit sentiment
- **Automated Daily Runs**: Cron-ready script for scheduled analysis

## Subreddits Tracked

| Subreddit | Description |
|-----------|-------------|
| r/IndianStreetBets | Most active, mix of memes and serious discussion |
| r/IndianStockMarket | General stock market discussions |
| r/DalalStreetTalks | Trading focused |
| r/IndiaInvestments | Long-term investing, more serious analysis |

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ankitagarwalultrahuman/reddit-stock-analyzer.git
cd reddit-stock-analyzer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Get your API key from: https://console.anthropic.com/

### 4. Run the Analyzer

```bash
python main.py
```

### 5. View Dashboard

```bash
streamlit run dashboard.py
```

## Configuration

Edit `config.py` to customize:

```python
SUBREDDITS = ["IndianStreetBets", "IndianStockMarket", ...]
POSTS_PER_SUBREDDIT = 15      # Posts to fetch per subreddit
COMMENTS_PER_POST = 10         # Comments per post
MAX_POST_AGE_HOURS = 48        # Only include recent posts
```

## Output

The analyzer generates:

- **Daily Reports**: `output/report_YYYYMMDD_HHMMSS.txt`
- **Raw Data**: `output/raw_data_YYYYMMDD_HHMMSS.json`

### Sample Output

```
TOP 10 KEY INSIGHTS

1. **SILVER/GOLD ETFs** - Major volatility with Trump trade uncertainty
   - **Citations: 15 posts, 89 comments**
   - Sentiment: Mixed
   - Sources: IndianStreetBets, IndianStockMarket

2. **NIFTY 50 ETF** - Systematic buying strategy gaining attention
   - **Citations: 3 posts, 105 comments**
   - Sentiment: Bullish
   ...
```

## Dashboard Features

The Streamlit dashboard provides:

- **Today's Actions**: Watch list, Consider buying, Risk alerts
- **Market Mood**: Overall sentiment indicator
- **Charts**: Stock mentions bar chart, sentiment distribution donut
- **Detailed Sections**: Expandable insights, stocks, sector trends
- **7-Day AI Summary**: Weekly trends and patterns
- **Date Selector**: Browse historical reports

## Automated Daily Runs

### Using GitHub Actions (Recommended)

The repo includes a GitHub Actions workflow that runs daily at 8:00 AM IST automatically.

**Setup:**
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add secret: `ANTHROPIC_API_KEY` with your API key
3. The workflow will run automatically and commit reports to the repo

**Manual trigger:** Go to Actions tab → "Daily Stock Analysis" → "Run workflow"

### Using Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 8 AM
0 8 * * * /path/to/reddit-stock-analyzer/run_daily.sh
```

### Using Task Scheduler (Windows)

Create a scheduled task that runs:
```
python /path/to/reddit-stock-analyzer/main.py
```

## Portfolio Integration

Match your holdings against Reddit sentiment:

### Option 1: CSV Import (Groww/Zerodha)

1. Export portfolio from your broker as CSV
2. Use the portfolio analyzer:

```python
from portfolio_analyzer import import_from_csv, analyze_portfolio_against_sentiment

holdings = import_from_csv("my_portfolio.csv")
analysis = analyze_portfolio_against_sentiment(report_content)
```

### Option 2: Manual Entry

```python
from portfolio_analyzer import add_holding

add_holding("RELIANCE", quantity=10, avg_price=1450.00)
add_holding("TCS", quantity=5, avg_price=3800.00)
```

### Option 3: Zerodha Kite API

For automated sync, configure Kite Connect credentials in `.env`:
```
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
```

Note: Requires Kite Connect subscription (₹2000/month)

## Deployment

### Streamlit Cloud (Free)

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Set main file: `dashboard.py`
5. Add secret: `ANTHROPIC_API_KEY`

### Self-Hosted

```bash
# Run with nohup
nohup streamlit run dashboard.py --server.port 8501 &
```

## Project Structure

```
reddit-stock-analyzer/
├── main.py                 # Entry point - orchestrates scraping & analysis
├── reddit_scraper.py       # Reddit data fetching (no auth required)
├── summarizer.py           # Claude API integration
├── config.py               # Configuration settings
├── dashboard.py            # Streamlit UI
├── dashboard_analytics.py  # Report parsing & weekly summaries
├── portfolio_analyzer.py   # Portfolio integration
├── run_daily.sh           # Automation script for cron
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
└── output/                # Generated reports
```

## API Usage & Costs

- **Reddit**: No API key required (uses public .json endpoints)
- **Claude API**: ~$0.01-0.05 per analysis (depends on data volume)
  - Model: Claude Sonnet 4
  - Tokens: ~40-70k input, ~4k output per run

## Disclaimer

This tool aggregates social media sentiment and is for **educational purposes only**. It is NOT financial advice.

- Always do your own research (DYOR) before making investment decisions
- Social media sentiment can be manipulated or biased
- Past discussions do not predict future stock performance
- Consult a registered financial advisor for professional advice

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT License - feel free to use and modify.

---

Built with Claude AI | Data from Reddit
