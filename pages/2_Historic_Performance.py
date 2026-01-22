"""Historic Stock Performance Page - 30-day price trends and sentiment analysis."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from stock_history import (
    fetch_stock_history,
    fetch_multiple_stocks,
    calculate_performance_metrics,
    compare_sentiment_vs_performance,
    get_stock_summary,
)
from dashboard_analytics import (
    get_available_dates,
    get_report_for_date,
    parse_stock_mentions,
    generate_todays_actions,
)
from portfolio_analyzer import load_portfolio, normalize_ticker
from groww_integration import GrowwClient, load_mf_portfolio, get_mf_underlying_stocks

# Page configuration
st.set_page_config(
    page_title="Historic Performance | Reddit Stock Analyzer",
    page_icon="📈",
    layout="wide",
)

# Color scheme
COLORS = {
    "positive": "#16a34a",
    "negative": "#dc2626",
    "neutral": "#f59e0b",
    "chart_lines": ["#3b82f6", "#16a34a", "#dc2626", "#f59e0b", "#8b5cf6"],
    "background": "#f8fafc",
}

# Custom CSS
st.markdown("""
<style>
    .history-header {
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 50%, #4f46e5 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
    }
    .history-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        color: white;
    }
    .history-header p {
        margin: 0.5rem 0 0 0;
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
    }

    .metric-card {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #3b82f6;
        margin-bottom: 0.5rem;
    }
    .metric-card-positive {
        border-left-color: #16a34a;
        background: #f0fdf4;
    }
    .metric-card-negative {
        border-left-color: #dc2626;
        background: #fef2f2;
    }

    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-value-positive { color: #16a34a; }
    .metric-value-negative { color: #dc2626; }

    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        margin-top: 0.25rem;
    }

    .sentiment-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .sentiment-bullish { background: #dcfce7; color: #166534; }
    .sentiment-bearish { background: #fee2e2; color: #991b1b; }
    .sentiment-neutral { background: #fef3c7; color: #92400e; }
    .sentiment-mixed { background: #ede9fe; color: #5b21b6; }

    .verdict-aligned { color: #16a34a; font-weight: 700; }
    .verdict-misaligned { color: #dc2626; font-weight: 700; }
    .verdict-partial { color: #f59e0b; font-weight: 700; }

    .stock-card {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.5rem;
    }
    .stock-ticker {
        font-size: 1.1rem;
        font-weight: 700;
        color: #0f172a;
    }

    .section-header {
        background: #f1f5f9;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 1.5rem 0 1rem 0;
        border-left: 4px solid #6366f1;
        font-weight: 600;
        color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render page header with gradient background."""
    st.markdown("""
    <div class="history-header">
        <h1>📈 Historic Stock Performance</h1>
        <p>30-day price trends | Sentiment vs Reality | Performance Metrics</p>
    </div>
    """, unsafe_allow_html=True)


def get_portfolio_stocks() -> list[str]:
    """Get stock tickers from portfolio."""
    stocks = []

    # Try Groww API first
    try:
        client = GrowwClient()
        if client.is_configured():
            holdings = client.get_holdings()
            for h in holdings:
                ticker = normalize_ticker(h.trading_symbol)
                if ticker:
                    stocks.append(ticker)
    except Exception:
        pass

    # Also check local portfolio
    portfolio = load_portfolio()
    for holding in portfolio:
        ticker = normalize_ticker(holding.get("ticker", holding.get("trading_symbol", "")))
        if ticker and ticker not in stocks:
            stocks.append(ticker)

    # Add MF underlying stocks
    mf_portfolio = load_mf_portfolio()
    for mf in mf_portfolio:
        underlying = get_mf_underlying_stocks(mf.get("name", ""))
        for stock in underlying[:5]:  # Top 5 from each MF
            if stock not in stocks:
                stocks.append(stock)

    return stocks


def get_reddit_recommended_stocks() -> dict:
    """Get stocks from latest Reddit report."""
    available_dates = get_available_dates()
    if not available_dates:
        return {"watch_list": [], "consider_list": [], "avoid_list": []}

    latest_date = available_dates[0]
    report = get_report_for_date(latest_date)

    if not report:
        return {"watch_list": [], "consider_list": [], "avoid_list": []}

    content = report.get("content", "")
    actions = generate_todays_actions(content)

    return {
        "watch_list": actions.get("watch_list", []),
        "consider_list": actions.get("consider_list", []),
        "avoid_list": actions.get("avoid_list", []),
    }


def render_stock_selection() -> list[str]:
    """
    Render stock selection panel with three tabs.

    Returns:
        List of selected ticker symbols
    """
    tab1, tab2, tab3 = st.tabs([
        "💼 From Portfolio",
        "📊 Reddit Picks",
        "🔍 Custom Search"
    ])

    selected_stocks = []

    with tab1:
        portfolio_stocks = get_portfolio_stocks()
        if portfolio_stocks:
            selected = st.multiselect(
                "Select stocks from your portfolio",
                options=portfolio_stocks,
                default=portfolio_stocks[:min(3, len(portfolio_stocks))],
                max_selections=5,
                key="portfolio_select"
            )
            selected_stocks.extend(selected)
        else:
            st.info("No portfolio loaded. Go to Portfolio Analysis to add holdings, or use the other tabs.")

    with tab2:
        reddit_stocks = get_reddit_recommended_stocks()

        col1, col2 = st.columns(2)

        with col1:
            watch_tickers = [s['ticker'] for s in reddit_stocks['watch_list']]
            if watch_tickers:
                st.markdown("**Watch List (Bullish)**")
                watch_selected = st.multiselect(
                    "Select from watch list",
                    options=watch_tickers,
                    key="watch_select",
                    label_visibility="collapsed"
                )
                selected_stocks.extend(watch_selected)

        with col2:
            consider_tickers = [s['ticker'] for s in reddit_stocks['consider_list']]
            if consider_tickers:
                st.markdown("**Consider List (Opportunities)**")
                consider_selected = st.multiselect(
                    "Select from consider list",
                    options=consider_tickers,
                    key="consider_select",
                    label_visibility="collapsed"
                )
                selected_stocks.extend(consider_selected)

        if not watch_tickers and not consider_tickers:
            st.info("No Reddit recommendations available. Run the analyzer first to generate reports.")

    with tab3:
        custom_input = st.text_input(
            "Enter NSE symbols (comma-separated)",
            placeholder="e.g., RELIANCE, TCS, INFY, HDFCBANK",
            key="custom_input"
        )
        if custom_input:
            custom_tickers = [normalize_ticker(t.strip()) for t in custom_input.split(",") if t.strip()]
            selected_stocks.extend(custom_tickers)

    # Remove duplicates and limit to 5
    unique_stocks = list(dict.fromkeys(selected_stocks))[:5]

    if unique_stocks:
        st.markdown(f"**Selected stocks:** {', '.join(unique_stocks)}")

    return unique_stocks


def render_price_chart(stocks_data: dict[str, pd.DataFrame]):
    """
    Render multi-line price chart with Plotly.

    Args:
        stocks_data: Dict mapping ticker to price DataFrame
    """
    if not stocks_data:
        st.warning("No price data available")
        return

    fig = go.Figure()

    for i, (ticker, df) in enumerate(stocks_data.items()):
        if df.empty or 'Close' not in df.columns:
            continue

        # Normalize to 100 for comparison
        close_prices = df['Close']
        normalized = (close_prices / close_prices.iloc[0]) * 100

        # Get dates
        dates = df['Date'] if 'Date' in df.columns else df.index

        fig.add_trace(go.Scatter(
            x=dates,
            y=normalized,
            mode='lines',
            name=ticker,
            line=dict(color=COLORS["chart_lines"][i % len(COLORS["chart_lines"])], width=2.5),
            hovertemplate=f"<b>{ticker}</b><br>Date: %{{x|%b %d}}<br>Price: ₹%{{customdata:.2f}}<br>Change: %{{y:.1f}}%<extra></extra>",
            customdata=close_prices
        ))

    fig.update_layout(
        title="30-Day Price Performance (Normalized to 100)",
        xaxis_title="Date",
        yaxis_title="Relative Performance (%)",
        height=450,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    fig.update_xaxes(showgrid=True, gridcolor='#f1f5f9')
    fig.update_yaxes(showgrid=True, gridcolor='#f1f5f9')

    # Add 100 baseline
    fig.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5,
                  annotation_text="Starting Point", annotation_position="right")

    st.plotly_chart(fig, use_container_width=True)


def render_metrics_dashboard(metrics: dict[str, dict]):
    """Render performance metrics cards for each stock."""
    st.markdown('<div class="section-header">📊 Performance Metrics (30-Day)</div>', unsafe_allow_html=True)

    if not metrics:
        st.info("No metrics available")
        return

    # Create columns for each stock
    cols = st.columns(min(len(metrics), 5))

    for i, (ticker, m) in enumerate(metrics.items()):
        with cols[i % len(cols)]:
            total_return = m.get('total_return', 0)
            is_positive = total_return >= 0

            card_class = "metric-card-positive" if is_positive else "metric-card-negative"
            value_class = "metric-value-positive" if is_positive else "metric-value-negative"

            st.markdown(f"""
            <div class="metric-card {card_class}">
                <div class="stock-ticker">{ticker}</div>
                <div class="metric-value {value_class}">
                    {total_return:+.2f}%
                </div>
                <div class="metric-label">
                    Vol: {m.get('volatility', 0):.1f}% |
                    Max DD: {m.get('max_drawdown', 0):.1f}%
                </div>
                <div class="metric-label" style="margin-top: 0.5rem;">
                    ₹{m.get('start_price', 0):,.2f} → ₹{m.get('end_price', 0):,.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)


def get_sentiment_for_stock(ticker: str) -> dict:
    """Get Reddit sentiment for a stock from latest report."""
    available_dates = get_available_dates()
    if not available_dates:
        return {"sentiment": "unknown", "mentions": 0}

    report = get_report_for_date(available_dates[0])
    if not report:
        return {"sentiment": "unknown", "mentions": 0}

    content = report.get("content", "")
    stocks = parse_stock_mentions(content)

    normalized_ticker = normalize_ticker(ticker)

    for stock in stocks:
        if normalize_ticker(stock.get("ticker", "")) == normalized_ticker:
            return {
                "sentiment": stock.get("sentiment", "neutral"),
                "mentions": stock.get("total_mentions", 0),
            }

    return {"sentiment": "not_discussed", "mentions": 0}


def render_sentiment_comparison(stocks_data: dict[str, pd.DataFrame], metrics: dict[str, dict]):
    """Render sentiment vs actual performance comparison."""
    st.markdown('<div class="section-header">🎯 Reddit Sentiment vs Reality</div>', unsafe_allow_html=True)

    if not stocks_data:
        st.info("No data for sentiment comparison")
        return

    comparison_data = []

    for ticker, df in stocks_data.items():
        if df.empty:
            continue

        # Get sentiment
        sentiment_data = get_sentiment_for_stock(ticker)
        sentiment = sentiment_data.get("sentiment", "unknown")
        mentions = sentiment_data.get("mentions", 0)

        # Get price change
        m = metrics.get(ticker, {})
        price_change = m.get("total_return", 0)

        # Compare
        comparison = compare_sentiment_vs_performance(sentiment, price_change, mentions)
        comparison["ticker"] = ticker
        comparison_data.append(comparison)

    if not comparison_data:
        st.info("No comparison data available")
        return

    # Create table
    for item in comparison_data:
        emoji = item['emoji']
        ticker = item['ticker']
        verdict = item['verdict']
        sentiment = item['sentiment']
        price_change = item['price_change']
        mentions = item['mentions']

        # Sentiment badge class
        sentiment_class = f"sentiment-{sentiment}" if sentiment in ["bullish", "bearish", "neutral", "mixed"] else "sentiment-neutral"

        # Verdict class
        verdict_class = "verdict-aligned" if verdict == "ALIGNED" else "verdict-misaligned" if verdict == "MISALIGNED" else "verdict-partial"

        # Price change color
        price_color = "#16a34a" if price_change >= 0 else "#dc2626"

        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 3])

        with col1:
            st.markdown(f"**{ticker}**")
        with col2:
            st.markdown(f'<span class="sentiment-badge {sentiment_class}">{sentiment.upper()}</span>', unsafe_allow_html=True)
        with col3:
            st.markdown(f"<span style='font-weight: 600;'>{mentions} mentions</span>", unsafe_allow_html=True)
        with col4:
            st.markdown(f'<span style="color: {price_color}; font-weight: 700;">{price_change:+.2f}%</span>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'{emoji} <span class="{verdict_class}">{verdict}</span>', unsafe_allow_html=True)

    # Summary
    aligned_count = sum(1 for c in comparison_data if c['verdict'] == "ALIGNED")
    total_count = len(comparison_data)

    if total_count > 0:
        accuracy = (aligned_count / total_count) * 100
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
            <strong>Sentiment Accuracy:</strong> {aligned_count}/{total_count} aligned ({accuracy:.0f}%)
        </div>
        """, unsafe_allow_html=True)


def render_detailed_metrics(metrics: dict[str, dict]):
    """Render detailed metrics in expandable sections."""
    st.markdown('<div class="section-header">📋 Detailed Analysis</div>', unsafe_allow_html=True)

    for ticker, m in metrics.items():
        with st.expander(f"📈 {ticker} - Full Analysis"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Return", f"{m.get('total_return', 0):+.2f}%")
                st.metric("Annualized Return", f"{m.get('annualized_return', 0):+.2f}%")

            with col2:
                st.metric("Volatility (Ann.)", f"{m.get('volatility', 0):.2f}%")
                st.metric("Sharpe Ratio", f"{m.get('sharpe_ratio', 0):.2f}")

            with col3:
                st.metric("Max Drawdown", f"{m.get('max_drawdown', 0):.2f}%")
                st.metric("Best Day", f"{m.get('best_day', 0):+.2f}%")

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Price Range:** ₹{m.get('low', 0):,.2f} - ₹{m.get('high', 0):,.2f}")
            with col2:
                st.write(f"**Worst Day:** {m.get('worst_day', 0):.2f}%")


def main():
    """Main page function."""
    render_header()

    # Stock selection
    st.markdown('<div class="section-header">🔍 Select Stocks to Analyze</div>', unsafe_allow_html=True)
    selected_stocks = render_stock_selection()

    if not selected_stocks:
        st.info("Please select at least one stock to view historic performance.")
        return

    # Fetch data
    with st.spinner(f"Fetching price data for {len(selected_stocks)} stocks..."):
        stocks_data = fetch_multiple_stocks(selected_stocks, days=30)

    if not stocks_data:
        st.error("Could not fetch price data. Please check if the stock symbols are valid NSE tickers.")
        return

    # Calculate metrics
    metrics = {}
    for ticker, df in stocks_data.items():
        if not df.empty:
            metrics[ticker] = calculate_performance_metrics(df)

    # Render sections
    st.markdown("---")

    # Price chart
    render_price_chart(stocks_data)

    st.markdown("---")

    # Metrics dashboard
    render_metrics_dashboard(metrics)

    st.markdown("---")

    # Sentiment comparison
    render_sentiment_comparison(stocks_data, metrics)

    st.markdown("---")

    # Detailed metrics
    render_detailed_metrics(metrics)

    # Footer
    st.markdown("---")
    st.caption(
        "**Note:** Price data is fetched from Yahoo Finance and may be delayed. "
        "Reddit sentiment is based on the latest available report. "
        "This is for informational purposes only - always do your own research."
    )


if __name__ == "__main__":
    main()
