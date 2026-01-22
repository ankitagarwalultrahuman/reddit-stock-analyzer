"""Reddit Stock Analyzer Dashboard - Streamlit UI for viewing daily reports and weekly summaries."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config import DASHBOARD_CACHE_TTL, WEEKLY_SUMMARY_DAYS, NEWS_ENABLED, SESSION_AM, SESSION_PM
from dashboard_analytics import (
    get_available_dates,
    get_report_for_date,
    get_recent_reports,
    get_weekly_summary,
    get_am_pm_reports_for_date,
    load_comparison_for_date,
    parse_report_sections,
    parse_stock_mentions,
    parse_key_insights_structured,
    parse_caution_flags,
    generate_todays_actions,
    calculate_sentiment_distribution,
)

# Import news fetcher (optional - may not be configured)
try:
    from news_fetcher import get_news_highlights, FinnhubClient
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False

# Color scheme
COLORS = {
    "bullish": "#22c55e",
    "bearish": "#ef4444",
    "neutral": "#f59e0b",
    "mixed": "#8b5cf6",
    "consider": "#3b82f6",
    "header_dark": "#1a1a2e",
    "header_light": "#16213e",
}

# Page configuration
st.set_page_config(
    page_title="Reddit Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for light theme styling
st.markdown("""
<style>
    /* Force light background on main container */
    .stApp {
        background-color: #ffffff;
    }

    /* Main content area */
    .main .block-container {
        background-color: #ffffff;
        color: #1e293b;
    }

    /* Modern header with blue gradient */
    .main-header {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 50%, #1d4ed8 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
    }
    .main-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        color: white;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
    }
    .date-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-left: 1rem;
        font-weight: 500;
        color: white;
    }

    /* Action card styling - light backgrounds */
    .action-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        height: 100%;
        border: 1px solid #e2e8f0;
    }
    .action-card-watch {
        border-left: 4px solid #16a34a;
        background: #f0fdf4;
    }
    .action-card-consider {
        border-left: 4px solid #2563eb;
        background: #eff6ff;
    }
    .action-card-avoid {
        border-left: 4px solid #dc2626;
        background: #fef2f2;
    }
    .action-card-mood {
        border-left: 4px solid #7c3aed;
        background: #faf5ff;
    }

    /* Signal badges */
    .signal-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .signal-watch {
        background: #16a34a;
        color: white;
    }
    .signal-consider {
        background: #2563eb;
        color: white;
    }
    .signal-avoid {
        background: #dc2626;
        color: white;
    }

    /* Sentiment pills - solid backgrounds */
    .sentiment-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .pill-bullish {
        background: #16a34a;
        color: white;
    }
    .pill-bearish {
        background: #dc2626;
        color: white;
    }
    .pill-neutral {
        background: #d97706;
        color: white;
    }
    .pill-mixed {
        background: #7c3aed;
        color: white;
    }

    /* Metric card styling */
    .metric-card {
        background: #f1f5f9;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #2563eb;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #475569;
        margin-top: 0.25rem;
        font-weight: 500;
    }

    /* Focus summary box */
    .focus-summary {
        background: #fef9c3;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #ca8a04;
    }
    .focus-summary h4 {
        margin: 0 0 0.5rem 0;
        color: #854d0e;
        font-size: 0.9rem;
        font-weight: 700;
    }
    .focus-summary p {
        margin: 0;
        color: #713f12;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Stock ticker */
    .stock-ticker {
        font-weight: 700;
        font-size: 1rem;
        color: #0f172a;
    }
    .stock-mentions {
        font-size: 0.8rem;
        color: #64748b;
    }
    .stock-reason {
        font-size: 0.85rem;
        color: #475569;
        margin-top: 0.3rem;
        line-height: 1.4;
    }

    /* Mood indicator */
    .mood-bullish {
        color: #16a34a;
    }
    .mood-bearish {
        color: #dc2626;
    }
    .mood-neutral {
        color: #d97706;
    }
    .mood-emoji {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .mood-label {
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: capitalize;
    }

    /* Alert badge */
    .alert-badge {
        background: #dc2626;
        color: white;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Risk alert item */
    .risk-alert-item {
        background: #fee2e2;
        border-radius: 6px;
        padding: 0.5rem 0.75rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid #dc2626;
    }
    .risk-alert-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #991b1b;
    }

    /* Section headers */
    .section-header {
        background: #f1f5f9;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 1.5rem 0 1rem 0;
        border-left: 4px solid #2563eb;
        font-weight: 600;
        color: #1e293b;
    }

    /* Sentiment colors for text */
    .sentiment-bullish { color: #16a34a; font-weight: 700; }
    .sentiment-bearish { color: #dc2626; font-weight: 700; }
    .sentiment-neutral { color: #d97706; font-weight: 700; }
    .sentiment-mixed { color: #7c3aed; font-weight: 700; }

    /* Report content */
    .report-content {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Card title */
    .card-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #374151;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Ensure all text is dark on light background */
    p, span, div, li {
        color: #1e293b;
    }

    /* News Highlights Section */
    .news-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .news-card-bullish {
        border-left-color: #16a34a;
    }
    .news-card-bearish {
        border-left-color: #dc2626;
    }
    .news-card-neutral {
        border-left-color: #f59e0b;
    }
    .news-headline {
        font-weight: 600;
        color: #1e293b;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }
    .news-meta {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.5rem;
    }
    .news-tickers {
        display: inline-flex;
        gap: 0.25rem;
        flex-wrap: wrap;
    }
    .ticker-badge {
        background: #e0e7ff;
        color: #3730a3;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    .news-summary {
        color: #475569;
        font-size: 0.85rem;
        line-height: 1.4;
    }
    .divergence-alert {
        background: #fef3c7;
        border-left: 3px solid #f59e0b;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
    .news-alignment {
        font-size: 0.8rem;
        margin-top: 0.5rem;
        color: #64748b;
    }

    /* Comparison View Styles */
    .comparison-header {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 50%, #6d28d9 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
    }

    .comparison-summary-card {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        border: 1px solid #e2e8f0;
    }
    .comparison-summary-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
    }
    .comparison-summary-card .label {
        font-size: 0.85rem;
        color: #64748b;
        margin-top: 0.25rem;
    }

    .mood-shift-container {
        background: #faf5ff;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #e9d5ff;
        margin: 1rem 0;
    }
    .mood-shift-visual {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 2rem;
        margin: 1rem 0;
    }
    .mood-box {
        text-align: center;
        padding: 1rem 2rem;
        border-radius: 10px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .mood-box .emoji {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .mood-box .label {
        font-size: 0.85rem;
        color: #64748b;
    }
    .mood-box .mood-text {
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .mood-arrow {
        font-size: 2rem;
        color: #7c3aed;
    }
    .mood-description {
        text-align: center;
        color: #6b21a8;
        font-style: italic;
        margin-top: 1rem;
    }

    .sentiment-change-row {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        background: #f8fafc;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #e2e8f0;
    }
    .sentiment-change-row.improving {
        border-left-color: #16a34a;
        background: #f0fdf4;
    }
    .sentiment-change-row.declining {
        border-left-color: #dc2626;
        background: #fef2f2;
    }
    .sentiment-change-row .ticker {
        font-weight: 700;
        min-width: 120px;
    }
    .sentiment-change-row .change {
        flex-grow: 1;
        color: #475569;
    }
    .sentiment-change-row .direction {
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
    }
    .sentiment-change-row .direction.improving {
        background: #dcfce7;
        color: #166534;
    }
    .sentiment-change-row .direction.declining {
        background: #fee2e2;
        color: #991b1b;
    }

    .new-stock-badge {
        display: inline-flex;
        align-items: center;
        background: #ecfdf5;
        border: 1px solid #a7f3d0;
        border-radius: 20px;
        padding: 0.4rem 0.8rem;
        margin: 0.25rem;
    }
    .new-stock-badge .ticker {
        font-weight: 700;
        color: #166534;
    }
    .new-stock-badge .mentions {
        font-size: 0.8rem;
        color: #15803d;
        margin-left: 0.5rem;
    }

    .removed-stock-badge {
        display: inline-flex;
        align-items: center;
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 20px;
        padding: 0.4rem 0.8rem;
        margin: 0.25rem;
    }
    .removed-stock-badge .ticker {
        font-weight: 700;
        color: #991b1b;
    }
    .removed-stock-badge .mentions {
        font-size: 0.8rem;
        color: #b91c1c;
        margin-left: 0.5rem;
    }

    .session-tab {
        padding: 0.75rem 1.5rem;
        border-radius: 8px 8px 0 0;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.2s;
    }
    .session-tab.active {
        background: #3b82f6;
        color: white;
    }
    .session-tab:not(.active) {
        background: #e2e8f0;
        color: #475569;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def cached_weekly_summary(report_dates_key: str) -> str:
    """Cache the weekly summary to avoid repeated API calls."""
    reports = get_recent_reports(WEEKLY_SUMMARY_DAYS)
    return get_weekly_summary(reports)


def format_date_for_display(d) -> str:
    """Format date as human-readable string."""
    return d.strftime("%A, %B %d, %Y")


def format_date_short(d) -> str:
    """Format date as short string for dropdown."""
    return d.strftime("%b %d, %Y")


def colorize_sentiment(text: str) -> str:
    """Add color styling to sentiment words in text."""
    replacements = [
        ("Bullish", '<span class="sentiment-bullish">Bullish</span>'),
        ("Bearish", '<span class="sentiment-bearish">Bearish</span>'),
        ("Neutral", '<span class="sentiment-neutral">Neutral</span>'),
        ("Mixed", '<span class="sentiment-mixed">Mixed</span>'),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def get_mood_emoji(mood: str) -> str:
    """Get emoji for market mood."""
    emojis = {
        "bullish": "📈",
        "bearish": "📉",
        "neutral": "➡️",
    }
    return emojis.get(mood, "➡️")


def get_sentiment_pill(sentiment: str) -> str:
    """Generate HTML for sentiment pill."""
    pill_class = f"pill-{sentiment}"
    return f'<span class="sentiment-pill {pill_class}">{sentiment.capitalize()}</span>'


def render_header():
    """Render the main dashboard header with date badge."""
    today = datetime.now().strftime("%B %d, %Y")
    st.markdown(f"""
    <div class="main-header">
        <h1>📈 Reddit Stock Analyzer Dashboard <span class="date-badge">{today}</span></h1>
        <p>Daily analysis reports from Indian stock market communities</p>
    </div>
    """, unsafe_allow_html=True)


def render_todays_actions(report: dict):
    """Render the Today's Actions section with 4-column layout."""
    content = report.get("content", "")
    actions = generate_todays_actions(content)

    st.markdown('<div class="section-header">📋 TODAY\'S ACTIONS</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    # Column 1: Market Mood
    with col1:
        mood = actions["market_mood"]
        emoji = get_mood_emoji(mood)
        mood_class = f"mood-{mood}"

        st.markdown(f"""
        <div class="action-card action-card-mood">
            <div class="card-title">Market Mood</div>
            <div class="{mood_class}">
                <div class="mood-emoji">{emoji}</div>
                <div class="mood-label">{mood.capitalize()}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Column 2: Watch List
    with col2:
        st.markdown("""
        <div class="action-card action-card-watch">
            <div class="card-title">Watch List</div>
        """, unsafe_allow_html=True)

        watch_list = actions.get("watch_list", [])
        if watch_list:
            for stock in watch_list[:3]:
                pill = get_sentiment_pill(stock["sentiment"])
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem;">
                    <span class="signal-badge signal-watch">WATCH</span>
                    <span class="stock-ticker">{stock['ticker'][:20]}</span>
                    <span class="stock-mentions">({stock['mentions']} mentions)</span><br>
                    {pill}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #64748b; font-size: 0.85rem;">No stocks to watch today</p>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Column 3: Consider List
    with col3:
        st.markdown("""
        <div class="action-card action-card-consider">
            <div class="card-title">Consider Buying</div>
        """, unsafe_allow_html=True)

        consider_list = actions.get("consider_list", [])
        if consider_list:
            for stock in consider_list[:3]:
                pill = get_sentiment_pill(stock["sentiment"])
                st.markdown(f"""
                <div style="margin-bottom: 0.5rem;">
                    <span class="signal-badge signal-consider">CONSIDER</span>
                    <span class="stock-ticker">{stock['ticker'][:20]}</span>
                    <span class="stock-mentions">({stock['mentions']} mentions)</span><br>
                    {pill}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #64748b; font-size: 0.85rem;">No opportunities identified</p>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Column 4: Risk Alerts
    with col4:
        risk_alerts = actions.get("risk_alerts", [])
        alert_count = len(risk_alerts)

        st.markdown(f"""
        <div class="action-card action-card-avoid">
            <div class="card-title">Risk Alerts <span class="alert-badge">{alert_count}</span></div>
        """, unsafe_allow_html=True)

        if risk_alerts:
            for alert in risk_alerts[:2]:
                st.markdown(f"""
                <div class="risk-alert-item">
                    <div class="risk-alert-title">{alert['title'][:30]}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #64748b; font-size: 0.85rem;">No major risks flagged</p>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # Focus Summary
    focus_summary = actions.get("focus_summary", "")
    if focus_summary:
        st.markdown(f"""
        <div class="focus-summary">
            <h4>📌 FOCUS TODAY</h4>
            <p>{focus_summary}</p>
        </div>
        """, unsafe_allow_html=True)


def render_charts_section(report: dict):
    """Render the charts section with bar and donut charts."""
    content = report.get("content", "")

    stocks = parse_stock_mentions(content)
    insights = parse_key_insights_structured(content)

    st.markdown('<div class="section-header">📊 MARKET ANALYSIS</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    # Left: Horizontal bar chart - Top stocks by mentions
    with col1:
        st.markdown("**Top Stock Mentions**")

        if stocks:
            df = pd.DataFrame(stocks[:8])  # Top 8
            df = df.sort_values("total_mentions", ascending=True)

            # Truncate long ticker names
            df["ticker_display"] = df["ticker"].apply(lambda x: x[:25] + "..." if len(x) > 25 else x)

            fig = px.bar(
                df,
                x="total_mentions",
                y="ticker_display",
                orientation="h",
                color="sentiment",
                color_discrete_map={
                    "bullish": COLORS["bullish"],
                    "bearish": COLORS["bearish"],
                    "neutral": COLORS["neutral"],
                    "mixed": COLORS["mixed"],
                },
                labels={"total_mentions": "Total Mentions", "ticker_display": "Stock"},
            )

            fig.update_layout(
                height=350,
                margin=dict(l=0, r=20, t=20, b=20),
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                yaxis=dict(showgrid=False),
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No stock data available for chart")

    # Right: Donut chart - Sentiment distribution
    with col2:
        st.markdown("**Sentiment Distribution**")

        if insights:
            distribution = calculate_sentiment_distribution(insights)
            df_sentiment = pd.DataFrame([
                {"sentiment": k.capitalize(), "count": v, "color": COLORS.get(k, COLORS["neutral"])}
                for k, v in distribution.items() if v > 0
            ])

            if not df_sentiment.empty:
                fig = px.pie(
                    df_sentiment,
                    values="count",
                    names="sentiment",
                    hole=0.5,
                    color="sentiment",
                    color_discrete_map={
                        "Bullish": COLORS["bullish"],
                        "Bearish": COLORS["bearish"],
                        "Neutral": COLORS["neutral"],
                        "Mixed": COLORS["mixed"],
                    },
                )

                fig.update_traces(
                    textposition="outside",
                    textinfo="label+percent",
                    marker=dict(line=dict(color="white", width=2)),
                )

                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=False,
                    paper_bgcolor="white",
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sentiment data available")
        else:
            st.info("No insights data available for chart")


def render_metric_cards(report: dict):
    """Render metric cards row."""
    metadata = report.get("metadata", {})
    timestamp = report.get("timestamp")

    st.markdown('<div class="section-header">📈 REPORT METRICS</div>', unsafe_allow_html=True)

    cols = st.columns(4)

    metrics = [
        ("Posts Analyzed", metadata.get("total_posts", "N/A"), "📝"),
        ("Comments Analyzed", metadata.get("total_comments", "N/A"), "💬"),
        ("Time Window", metadata.get("time_window", "N/A"), "⏰"),
        ("Generated", timestamp.strftime("%H:%M:%S") if timestamp else "N/A", "🕐"),
    ]

    for col, (label, value, icon) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{icon} {value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def render_news_highlights(report: dict, portfolio_stocks: list = None):
    """Render the Financial News Highlights section."""
    if not NEWS_AVAILABLE or not NEWS_ENABLED:
        return

    st.markdown('<div class="section-header">📰 FINANCIAL NEWS HIGHLIGHTS</div>', unsafe_allow_html=True)

    # Check if Finnhub is configured
    try:
        finnhub = FinnhubClient()
        if not finnhub.is_configured():
            st.info("News API not configured. Add FINNHUB_API_KEY to your .env file to enable news highlights.")
            return
    except Exception:
        st.info("News feature not available.")
        return

    content = report.get("content", "")

    with st.spinner("Fetching and analyzing financial news..."):
        try:
            analysis = get_news_highlights(content, portfolio_stocks)
        except Exception as e:
            st.warning(f"Could not fetch news: {e}")
            return

    if analysis.get("error"):
        st.warning(f"News analysis error: {analysis.get('error')}")

    highlights = analysis.get("highlights", [])
    divergences = analysis.get("sentiment_divergences", [])
    market_summary = analysis.get("market_summary", "")
    alerts = analysis.get("key_alerts", [])

    if not highlights and not market_summary:
        st.info("No relevant news found for the discussed stocks.")
        return

    # Render news cards
    if highlights:
        for item in highlights[:5]:
            sentiment = item.get("news_sentiment", "neutral")
            card_class = f"news-card news-card-{sentiment}"

            tickers = item.get("tickers", [])
            tickers_html = " ".join([f'<span class="ticker-badge">{t}</span>' for t in tickers[:3]])

            alignment = item.get("reddit_alignment", "not_discussed")
            alignment_icon = {"aligned": "✅", "divergent": "⚠️", "not_discussed": "➖"}.get(alignment, "➖")

            reddit_sent = item.get("reddit_sentiment", "unknown")

            st.markdown(f"""
            <div class="{card_class}">
                <div class="news-headline">{item.get('headline', 'News')[:100]}</div>
                <div class="news-meta">
                    <span class="news-tickers">{tickers_html}</span>
                    <span style="margin-left: 0.5rem;">| {item.get('source', 'Unknown')}</span>
                    <span style="margin-left: 0.5rem;">| Impact: {item.get('news_impact', 'medium').upper()}</span>
                </div>
                <div class="news-summary">{item.get('summary', '')[:200]}</div>
                <div class="news-alignment">
                    {alignment_icon} News: <strong>{sentiment.upper()}</strong> | Reddit: <strong>{reddit_sent.upper()}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Render divergence alerts
    if divergences:
        st.markdown("#### ⚠️ Sentiment Divergences")
        for div in divergences[:3]:
            st.markdown(f"""
            <div class="divergence-alert">
                <strong>{div.get('ticker', 'Unknown')}</strong>:
                News is <strong>{div.get('news_sentiment', 'unknown').upper()}</strong>
                but Reddit is <strong>{div.get('reddit_sentiment', 'unknown').upper()}</strong>.
                {div.get('note', '')}
            </div>
            """, unsafe_allow_html=True)

    # Market summary
    if market_summary:
        st.markdown(f"""
        <div class="focus-summary" style="margin-top: 1rem;">
            <h4>📊 News Summary</h4>
            <p>{market_summary}</p>
        </div>
        """, unsafe_allow_html=True)

    # Key alerts
    if alerts:
        with st.expander("🔔 Key Alerts", expanded=False):
            for alert in alerts[:4]:
                st.markdown(f"- {alert}")


def render_detailed_sections(report: dict):
    """Render detailed report sections in card-based layout."""
    content = report.get("content", "")
    sections = parse_report_sections(content)

    st.markdown('<div class="section-header">📄 DETAILED ANALYSIS</div>', unsafe_allow_html=True)

    # Key Insights section
    if sections["key_insights"]:
        with st.expander("🎯 Key Insights", expanded=True):
            st.markdown(colorize_sentiment(sections["key_insights"]), unsafe_allow_html=True)

    # Most Discussed Stocks section
    if sections["most_discussed"]:
        with st.expander("📈 Most Discussed Stocks", expanded=True):
            st.markdown(colorize_sentiment(sections["most_discussed"]), unsafe_allow_html=True)

    # Sector Trends section
    if sections["sector_trends"]:
        with st.expander("🏭 Sector Trends", expanded=False):
            st.markdown(colorize_sentiment(sections["sector_trends"]), unsafe_allow_html=True)

    # Market Sentiment section
    if sections["sentiment_summary"]:
        with st.expander("📊 Market Sentiment Summary", expanded=False):
            st.markdown(colorize_sentiment(sections["sentiment_summary"]), unsafe_allow_html=True)

    # Caution Flags section
    if sections["caution_flags"]:
        with st.expander("⚠️ Caution Flags", expanded=True):
            st.markdown(colorize_sentiment(sections["caution_flags"]), unsafe_allow_html=True)


def render_weekly_summary():
    """Render the 7-day AI summary section (collapsed at bottom)."""
    available_dates = get_available_dates()
    if len(available_dates) == 0:
        st.info("No reports available for weekly summary. Run the analyzer to generate reports.")
        return

    dates_key = "_".join(d.isoformat() for d in available_dates[:WEEKLY_SUMMARY_DAYS])

    st.markdown('<div class="section-header">📊 7-DAY AI SUMMARY</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄 Regenerate", key="regenerate_summary", help="Force refresh the weekly summary"):
            st.cache_data.clear()
            st.rerun()

    with st.expander("View Weekly Analysis", expanded=False):
        with st.spinner("Generating weekly summary with AI..."):
            summary = cached_weekly_summary(dates_key)

        if summary.startswith("API key not configured") or summary.startswith("Error"):
            st.warning(summary)
        else:
            st.markdown(summary)

        report_count = min(len(available_dates), WEEKLY_SUMMARY_DAYS)
        st.caption(f"Based on {report_count} day(s) of reports")


def render_date_selector() -> tuple:
    """Render date selector and return selected date and report."""
    available_dates = get_available_dates()

    if not available_dates:
        st.warning("No reports found in the output folder. Run the analyzer first to generate reports.")
        return None, None

    # Create date options for dropdown
    date_options = {format_date_for_display(d): d for d in available_dates}
    date_labels = list(date_options.keys())

    selected_label = st.selectbox(
        "📅 Select Report Date",
        date_labels,
        index=0,
        help="Select a date to view the daily report",
    )

    selected_date = date_options[selected_label]
    report = get_report_for_date(selected_date)

    return selected_date, report


def render_raw_report(report: dict):
    """Render raw report option."""
    with st.expander("📝 View Raw Report"):
        st.text(report.get("content", ""))


def render_session_selector(sessions_data: dict) -> str | None:
    """
    Render AM/PM/Comparison tabs when both sessions exist.

    Args:
        sessions_data: Result from get_am_pm_reports_for_date()

    Returns:
        Selected view: 'AM', 'PM', 'comparison', or None
    """
    available = sessions_data.get("available_sessions", [])
    has_both = sessions_data.get("has_both", False)

    if not available or available == ["legacy"]:
        return None

    if len(available) == 1:
        # Only one session available, no need for tabs
        return available[0]

    # Show tabs when multiple sessions available
    tab_labels = []
    tab_keys = []

    if SESSION_AM in available:
        tab_labels.append("🌅 Morning (8 AM)")
        tab_keys.append(SESSION_AM)

    if SESSION_PM in available:
        tab_labels.append("🌆 Evening (6 PM)")
        tab_keys.append(SESSION_PM)

    if has_both:
        tab_labels.append("🔄 AM vs PM Comparison")
        tab_keys.append("comparison")

    # Use Streamlit tabs
    tabs = st.tabs(tab_labels)

    # Return the selected tab key based on session state
    if "selected_session_tab" not in st.session_state:
        st.session_state.selected_session_tab = tab_keys[-1] if has_both else tab_keys[0]

    return st.session_state.selected_session_tab, tabs, tab_keys


def render_mood_shift_visual(mood: dict):
    """Render visual AM to PM mood comparison."""
    am_mood = mood.get("am_mood", "neutral")
    pm_mood = mood.get("pm_mood", "neutral")
    description = mood.get("shift_description", "")

    mood_emojis = {
        "bullish": "📈",
        "bearish": "📉",
        "neutral": "➡️",
    }
    mood_colors = {
        "bullish": "#16a34a",
        "bearish": "#dc2626",
        "neutral": "#d97706",
    }

    am_emoji = mood_emojis.get(am_mood, "➡️")
    pm_emoji = mood_emojis.get(pm_mood, "➡️")
    am_color = mood_colors.get(am_mood, "#d97706")
    pm_color = mood_colors.get(pm_mood, "#d97706")

    st.markdown(f"""
    <div class="mood-shift-container">
        <h4 style="text-align: center; color: #6b21a8; margin-bottom: 1rem;">MARKET MOOD SHIFT</h4>
        <div class="mood-shift-visual">
            <div class="mood-box">
                <div class="emoji">{am_emoji}</div>
                <div class="label">Morning</div>
                <div class="mood-text" style="color: {am_color};">{am_mood.upper()}</div>
            </div>
            <div class="mood-arrow">→</div>
            <div class="mood-box">
                <div class="emoji">{pm_emoji}</div>
                <div class="label">Evening</div>
                <div class="mood-text" style="color: {pm_color};">{pm_mood.upper()}</div>
            </div>
        </div>
        <div class="mood-description">"{description}"</div>
    </div>
    """, unsafe_allow_html=True)


def render_sentiment_changes_table(changes: list):
    """Render table showing sentiment shifts."""
    if not changes:
        st.info("No sentiment changes detected between AM and PM reports.")
        return

    st.markdown("#### Sentiment Changes")

    for change in changes:
        ticker = change.get("ticker", "Unknown")
        am_sent = change.get("am_sentiment", "neutral")
        pm_sent = change.get("pm_sentiment", "neutral")
        direction = change.get("change_direction", "stable")

        direction_icon = "🔼" if direction == "improving" else "🔽" if direction == "declining" else "➡️"
        direction_label = direction.capitalize()
        row_class = direction

        st.markdown(f"""
        <div class="sentiment-change-row {row_class}">
            <span class="ticker">{ticker}</span>
            <span class="change">{am_sent} → {pm_sent}</span>
            <span class="direction {direction}">{direction_icon} {direction_label}</span>
        </div>
        """, unsafe_allow_html=True)


def render_volume_changes_chart(changes: list):
    """Render bar chart of mention volume changes."""
    if not changes:
        st.info("No significant volume changes detected (threshold: 20%).")
        return

    st.markdown("#### Volume Changes (AM → PM)")

    # Prepare data for chart
    df = pd.DataFrame(changes[:10])  # Top 10

    if df.empty:
        return

    # Create horizontal bar chart
    df["ticker_short"] = df["ticker"].apply(lambda x: x[:20] + "..." if len(x) > 20 else x)
    df["color"] = df["change_percent"].apply(lambda x: "#16a34a" if x > 0 else "#dc2626")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df["ticker_short"],
        x=df["change_percent"],
        orientation="h",
        marker_color=df["color"],
        text=[f"{v:+.1f}%" for v in df["change_percent"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>AM: %{customdata[0]} mentions<br>PM: %{customdata[1]} mentions<br>Change: %{x:.1f}%<extra></extra>",
        customdata=df[["am_mentions", "pm_mentions"]].values,
    ))

    fig.update_layout(
        height=max(200, len(df) * 40),
        margin=dict(l=0, r=60, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            zeroline=True,
            zerolinecolor="#94a3b8",
            zerolinewidth=2,
            title="Change %",
        ),
        yaxis=dict(showgrid=False),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_new_removed_stocks(new_stocks: list, removed_stocks: list):
    """Render lists of new and removed stocks."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✨ New in Evening")
        if new_stocks:
            badges_html = ""
            for stock in new_stocks[:8]:
                ticker = stock.get("ticker", "Unknown")
                mentions = stock.get("mentions", 0)
                sentiment = stock.get("sentiment", "neutral")
                badges_html += f"""
                <span class="new-stock-badge">
                    <span class="ticker">{ticker}</span>
                    <span class="mentions">{mentions} mentions</span>
                </span>
                """
            st.markdown(badges_html, unsafe_allow_html=True)
        else:
            st.info("No new stocks appeared in PM report")

    with col2:
        st.markdown("#### 📉 Dropped from Morning")
        if removed_stocks:
            badges_html = ""
            for stock in removed_stocks[:8]:
                ticker = stock.get("ticker", "Unknown")
                mentions = stock.get("mentions", 0)
                badges_html += f"""
                <span class="removed-stock-badge">
                    <span class="ticker">{ticker}</span>
                    <span class="mentions">{mentions} mentions (AM)</span>
                </span>
                """
            st.markdown(badges_html, unsafe_allow_html=True)
        else:
            st.info("No stocks dropped from PM report")


def render_comparison_summary(comparison: dict):
    """Render comparison summary cards."""
    summary = comparison.get("summary", {})

    cols = st.columns(4)

    metrics = [
        ("✨ New", summary.get("total_new_stocks", 0), "New stocks in PM"),
        ("📉 Removed", summary.get("total_removed_stocks", 0), "Dropped from PM"),
        ("🔄 Shifts", summary.get("total_sentiment_changes", 0), "Sentiment changes"),
        ("📊 Volume", summary.get("total_volume_changes", 0), "Volume changes >20%"),
    ]

    for col, (icon, value, label) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="comparison-summary-card">
                <div class="value">{icon} {value}</div>
                <div class="label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def render_comparison_view(comparison: dict):
    """Render the complete AM vs PM comparison dashboard."""
    if not comparison:
        st.warning("Comparison data not available. Run comparison_generator.py to generate it.")
        return

    # Header
    date_str = comparison.get("date", "Unknown")
    st.markdown(f"""
    <div class="comparison-header">
        <h2 style="margin: 0; color: white;">🔄 AM vs PM Comparison</h2>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Analyzing market sentiment changes throughout {date_str}</p>
    </div>
    """, unsafe_allow_html=True)

    # Summary cards
    render_comparison_summary(comparison)

    st.markdown("---")

    # Mood shift visual
    mood = comparison.get("market_mood_shift", {})
    render_mood_shift_visual(mood)

    st.markdown("---")

    # Two column layout for new/removed stocks
    render_new_removed_stocks(
        comparison.get("new_stocks_pm", []),
        comparison.get("removed_stocks_pm", [])
    )

    st.markdown("---")

    # Sentiment changes and volume changes side by side
    col1, col2 = st.columns(2)

    with col1:
        render_sentiment_changes_table(comparison.get("sentiment_changes", []))

    with col2:
        render_volume_changes_chart(comparison.get("volume_changes", []))


def main():
    """Main dashboard application."""
    render_header()

    # Date selector at top
    available_dates = get_available_dates()

    if not available_dates:
        st.warning("No reports found in the output folder. Run the analyzer first to generate reports.")
        return

    # Create date options for dropdown
    date_options = {format_date_for_display(d): d for d in available_dates}
    date_labels = list(date_options.keys())

    selected_label = st.selectbox(
        "📅 Select Report Date",
        date_labels,
        index=0,
        help="Select a date to view the daily report",
    )

    selected_date = date_options[selected_label]

    # Check for AM/PM reports
    sessions_data = get_am_pm_reports_for_date(selected_date)
    available_sessions = sessions_data.get("available_sessions", [])
    has_both = sessions_data.get("has_both", False)

    # Determine which view to show
    if has_both or (len(available_sessions) > 1 and "legacy" not in available_sessions):
        # Show tabs for AM/PM/Comparison
        tab_labels = []
        tab_keys = []

        if SESSION_AM in available_sessions:
            tab_labels.append("🌅 Morning (8 AM)")
            tab_keys.append(SESSION_AM)

        if SESSION_PM in available_sessions:
            tab_labels.append("🌆 Evening (6 PM)")
            tab_keys.append(SESSION_PM)

        if has_both:
            tab_labels.append("🔄 AM vs PM Comparison")
            tab_keys.append("comparison")

        tabs = st.tabs(tab_labels)

        for i, (tab, key) in enumerate(zip(tabs, tab_keys)):
            with tab:
                if key == "comparison":
                    # Render comparison view
                    comparison = load_comparison_for_date(selected_date)
                    render_comparison_view(comparison)
                else:
                    # Render regular report view
                    report = sessions_data.get("am" if key == SESSION_AM else "pm")
                    if report:
                        render_report_view(report)
                    else:
                        st.error(f"Could not load {key} report")
    else:
        # Single report or legacy - show regular view
        report = get_report_for_date(selected_date)
        if report:
            render_report_view(report)
        else:
            st.error(f"Could not load report for {format_date_for_display(selected_date)}")

    # Footer
    st.markdown("---")
    st.caption(
        "**Disclaimer**: This dashboard displays aggregated social media sentiment "
        "and is for educational purposes only. Always do your own research before "
        "making investment decisions."
    )


def render_report_view(report: dict):
    """Render the standard report view with all sections."""
    # Today's Actions section (prominent at top)
    render_todays_actions(report)

    st.markdown("---")

    # Charts row
    render_charts_section(report)

    st.markdown("---")

    # Metrics row
    render_metric_cards(report)

    st.markdown("---")

    # Financial News Highlights (if enabled)
    try:
        from portfolio_analyzer import load_portfolio
        portfolio = load_portfolio()
        portfolio_tickers = [h.get("ticker", h.get("trading_symbol", "")) for h in portfolio] if portfolio else None
    except Exception:
        portfolio_tickers = None

    render_news_highlights(report, portfolio_tickers)

    st.markdown("---")

    # Detailed sections
    render_detailed_sections(report)

    st.markdown("---")

    # 7-Day Summary (collapsed at bottom)
    render_weekly_summary()

    st.markdown("---")

    # Raw report
    render_raw_report(report)


if __name__ == "__main__":
    main()
