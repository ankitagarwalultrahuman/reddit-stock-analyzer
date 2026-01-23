"""
Technical Analysis Dashboard Page

Displays technical indicators, confluence signals, and signal accuracy tracking.
Combines Reddit sentiment with technical analysis for actionable trading signals.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date

from config import DASHBOARD_CACHE_TTL
from dashboard_analytics import (
    load_reports_by_date,
    get_report_for_date,
    parse_stock_mentions,
    get_top_confluence_signals,
    analyze_confluence_signals,
)

# Page config
st.set_page_config(
    page_title="Technical Analysis - Reddit Stock Analyzer",
    page_icon="",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .signal-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1rem;
    }
    .signal-strong {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .signal-moderate {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .signal-weak {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .metric-positive { color: #00c853; }
    .metric-negative { color: #ff1744; }
    .metric-neutral { color: #9e9e9e; }
    .indicator-box {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    .stars { color: #ffd700; font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def load_cached_reports():
    """Load all reports with caching."""
    return load_reports_by_date()


def get_technical_data(ticker: str) -> dict:
    """Fetch technical analysis data for a ticker."""
    try:
        from stock_history import get_stock_with_technicals
        return get_stock_with_technicals(ticker, days=60)
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_signal_accuracy_stats():
    """Get signal accuracy statistics."""
    try:
        from signal_tracker import get_accuracy_stats
        return get_accuracy_stats(days=30)
    except Exception:
        return None


def create_technical_chart(df: pd.DataFrame, technicals: dict, ticker: str) -> go.Figure:
    """Create a comprehensive technical analysis chart."""
    if df.empty:
        return None

    # Ensure Date column is datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])

    # Create subplots: Price with MAs, RSI, MACD, Volume
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.15, 0.2, 0.15],
        subplot_titles=(f'{ticker} Price', 'RSI (14)', 'MACD', 'Volume')
    )

    # Row 1: Candlestick with MAs and Bollinger Bands
    fig.add_trace(
        go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )

    # Add EMAs if available
    from technical_analysis import calculate_ema
    ema_20 = calculate_ema(df, 20)
    ema_50 = calculate_ema(df, 50)

    if ema_20 is not None:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=ema_20, name='EMA 20',
                      line=dict(color='#2196f3', width=1)),
            row=1, col=1
        )
    if ema_50 is not None:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=ema_50, name='EMA 50',
                      line=dict(color='#ff9800', width=1)),
            row=1, col=1
        )

    # Add Bollinger Bands
    from technical_analysis import calculate_bollinger_bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df)

    if bb_upper is not None:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=bb_upper, name='BB Upper',
                      line=dict(color='rgba(128,128,128,0.3)', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['Date'], y=bb_lower, name='BB Lower',
                      line=dict(color='rgba(128,128,128,0.3)', width=1),
                      fill='tonexty', fillcolor='rgba(128,128,128,0.1)'),
            row=1, col=1
        )

    # Row 2: RSI
    from technical_analysis import calculate_rsi
    rsi = calculate_rsi(df)

    if rsi is not None:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=rsi, name='RSI',
                      line=dict(color='#9c27b0', width=1.5)),
            row=2, col=1
        )
        # Add overbought/oversold lines
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # Row 3: MACD
    from technical_analysis import calculate_macd
    macd_line, signal_line, histogram = calculate_macd(df)

    if macd_line is not None:
        fig.add_trace(
            go.Scatter(x=df['Date'], y=macd_line, name='MACD',
                      line=dict(color='#2196f3', width=1)),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['Date'], y=signal_line, name='Signal',
                      line=dict(color='#ff9800', width=1)),
            row=3, col=1
        )
        colors = ['#26a69a' if val >= 0 else '#ef5350' for val in histogram]
        fig.add_trace(
            go.Bar(x=df['Date'], y=histogram, name='Histogram',
                  marker_color=colors),
            row=3, col=1
        )

    # Row 4: Volume
    if 'Volume' in df.columns:
        colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350'
                 for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['Date'], y=df['Volume'], name='Volume',
                  marker_color=colors),
            row=4, col=1
        )

    fig.update_layout(
        height=800,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        template='plotly_white'
    )

    return fig


def display_technical_indicators(technicals: dict):
    """Display technical indicators in a formatted grid."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### RSI")
        rsi = technicals.get("rsi")
        rsi_signal = technicals.get("rsi_signal", "unknown")

        color_class = "metric-neutral"
        if rsi_signal in ("oversold", "near_oversold"):
            color_class = "metric-positive"
        elif rsi_signal in ("overbought", "near_overbought"):
            color_class = "metric-negative"

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">{rsi if rsi else 'N/A'}</h2>
            <p>{rsi_signal.replace('_', ' ').title()}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### MACD")
        macd_trend = technicals.get("macd_trend", "unknown")

        color_class = "metric-neutral"
        if "bullish" in macd_trend:
            color_class = "metric-positive"
        elif "bearish" in macd_trend:
            color_class = "metric-negative"

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">{macd_trend.replace('_', ' ').title()}</h2>
            <p>Histogram: {technicals.get('macd_histogram', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("### MA Trend")
        ma_trend = technicals.get("ma_trend", "unknown")

        color_class = "metric-neutral"
        if ma_trend == "bullish":
            color_class = "metric-positive"
        elif ma_trend == "bearish":
            color_class = "metric-negative"

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">{ma_trend.title()}</h2>
            <p>Price vs 50 EMA: {technicals.get('price_vs_ema50', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

    # Second row
    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown("### Volume")
        vol_signal = technicals.get("volume_signal", "unknown")
        vol_ratio = technicals.get("volume_ratio")

        color_class = "metric-neutral"
        if vol_signal == "high":
            color_class = "metric-positive"
        elif vol_signal == "low":
            color_class = "metric-negative"

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">{vol_signal.title()}</h2>
            <p>{vol_ratio}x average</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("### Volatility (ATR)")
        vol_level = technicals.get("volatility_level", "unknown")
        atr_pct = technicals.get("atr_percent")

        color_class = "metric-neutral"
        if vol_level == "high":
            color_class = "metric-negative"
        elif vol_level == "low":
            color_class = "metric-positive"

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">{vol_level.title()}</h2>
            <p>ATR: {atr_pct}%</p>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown("### Technical Score")
        score = technicals.get("technical_score", 50)
        bias = technicals.get("technical_bias", "neutral")

        color_class = "metric-neutral"
        if bias == "bullish":
            color_class = "metric-positive"
        elif bias == "bearish":
            color_class = "metric-negative"

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">{score}/100</h2>
            <p>{bias.title()} Bias</p>
        </div>
        """, unsafe_allow_html=True)

    # Third row - 52-week high/low
    col7, col8, col9 = st.columns(3)

    with col7:
        st.markdown("### 52-Week High")
        week_52_high = technicals.get("week_52_high")
        pct_from_high = technicals.get("pct_from_52w_high")
        near_high = technicals.get("near_52w_high", False)

        color_class = "metric-positive" if near_high else "metric-neutral"
        high_indicator = "⭐ Near High!" if near_high else ""

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">₹{week_52_high:.0f if week_52_high else 'N/A'}</h2>
            <p>{pct_from_high:+.1f}% from high {high_indicator}</p>
        </div>
        """, unsafe_allow_html=True)

    with col8:
        st.markdown("### 52-Week Low")
        week_52_low = technicals.get("week_52_low")
        pct_from_low = technicals.get("pct_from_52w_low")
        near_low = technicals.get("near_52w_low", False)

        color_class = "metric-negative" if near_low else "metric-neutral"
        low_indicator = "⚠️ Near Low!" if near_low else ""

        st.markdown(f"""
        <div class="indicator-box">
            <h2 class="{color_class}">₹{week_52_low:.0f if week_52_low else 'N/A'}</h2>
            <p>{pct_from_low:+.1f}% from low {low_indicator}</p>
        </div>
        """, unsafe_allow_html=True)

    with col9:
        st.markdown("### 52-Week Range")
        if week_52_high and week_52_low:
            current_price = technicals.get("current_price", 0)
            range_pct = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100 if (week_52_high - week_52_low) > 0 else 0
            range_position = "Upper" if range_pct > 75 else "Lower" if range_pct < 25 else "Middle"
            color_class = "metric-positive" if range_pct > 60 else "metric-negative" if range_pct < 40 else "metric-neutral"

            st.markdown(f"""
            <div class="indicator-box">
                <h2 class="{color_class}">{range_pct:.0f}%</h2>
                <p>{range_position} of range</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="indicator-box">
                <h2>N/A</h2>
                <p>Insufficient data</p>
            </div>
            """, unsafe_allow_html=True)


def display_confluence_signals(report_content: str):
    """Display confluence signals section."""
    st.header("Confluence Signals")
    st.markdown("*Stocks where Reddit sentiment aligns with technical indicators*")

    try:
        confluence_signals = get_top_confluence_signals(report_content, limit=10)
    except Exception as e:
        st.warning(f"Could not analyze confluence signals: {e}")
        return

    if not confluence_signals:
        st.info("No strong confluence signals detected. Signals require at least 2 aligned indicators.")
        return

    # Strong signals
    strong = [s for s in confluence_signals if s["signal_strength"] == "Strong"]
    if strong:
        st.subheader("Strong Signals (4-5 aligned indicators)")
        for signal in strong:
            stars = "" * signal["confluence_score"]
            sentiment_emoji = "" if signal["sentiment"] == "bullish" else "" if signal["sentiment"] == "bearish" else ""

            with st.expander(f"{stars} {signal['ticker']} - {signal['sentiment'].title()} {sentiment_emoji}", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Price", f"{signal['current_price']}")
                    st.metric("Mentions", signal['mentions'])
                with col2:
                    st.metric("RSI", f"{signal['rsi']} ({signal['rsi_signal']})")
                    st.metric("MACD", signal['macd_trend'])
                with col3:
                    st.metric("Tech Score", f"{signal['technical_score']}/100")
                    st.metric("Volume", signal['volume_signal'])

                st.markdown("**Aligned Signals:**")
                for aligned in signal["aligned_signals"]:
                    st.markdown(f"- {aligned}")

    # Moderate signals
    moderate = [s for s in confluence_signals if s["signal_strength"] == "Moderate"]
    if moderate:
        st.subheader("Moderate Signals (3 aligned indicators)")
        for signal in moderate:
            stars = "" * signal["confluence_score"]
            sentiment_emoji = "" if signal["sentiment"] == "bullish" else "" if signal["sentiment"] == "bearish" else ""

            with st.expander(f"{stars} {signal['ticker']} - {signal['sentiment'].title()} {sentiment_emoji}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Price:** {signal['current_price']}")
                    st.write(f"**RSI:** {signal['rsi']} ({signal['rsi_signal']})")
                with col2:
                    st.write(f"**MACD:** {signal['macd_trend']}")
                    st.write(f"**Tech Score:** {signal['technical_score']}/100")

    # Weak signals
    weak = [s for s in confluence_signals if s["signal_strength"] == "Weak"]
    if weak:
        with st.expander(f"Weak Signals ({len(weak)} stocks)"):
            for signal in weak:
                st.write(f"- {signal['ticker']}: {signal['sentiment']} sentiment, RSI {signal['rsi']}")


def display_accuracy_stats():
    """Display signal accuracy statistics."""
    st.header("Signal Accuracy Tracking")

    stats = get_signal_accuracy_stats()

    if not stats:
        st.info("Signal accuracy tracking requires at least 7 days of data. Keep running daily reports to build history.")
        return

    # Display by sentiment
    st.subheader("Accuracy by Sentiment (Last 30 Days)")

    by_sentiment = stats.get("by_sentiment", {})
    if by_sentiment:
        data = []
        for sentiment, metrics in by_sentiment.items():
            data.append({
                "Sentiment": sentiment.title(),
                "Signals": metrics["total"],
                "1-Day Acc": f"{metrics['accuracy_1d']}%",
                "3-Day Acc": f"{metrics['accuracy_3d']}%",
                "5-Day Acc": f"{metrics['accuracy_5d']}%",
                "Avg Return (3d)": f"{metrics['avg_return_3d']}%",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No accuracy data available yet.")

    # Display by confluence score
    st.subheader("Accuracy by Confluence Strength")

    by_confluence = stats.get("by_confluence", {})
    if by_confluence:
        data = []
        for strength, metrics in by_confluence.items():
            data.append({
                "Signal Strength": strength,
                "Signals": metrics["total"],
                "3-Day Accuracy": f"{metrics['accuracy_3d']}%",
                "Avg Return (3d)": f"{metrics['avg_return_3d']}%",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, width="stretch", hide_index=True)

    # Top performers
    st.subheader("Top Performing Stocks (Based on Signals)")

    top_performers = stats.get("top_performers", [])
    if top_performers:
        data = []
        for perf in top_performers:
            data.append({
                "Ticker": perf["ticker"],
                "Signals": perf["signals"],
                "Avg Return (3d)": f"{perf['avg_return_3d']}%",
                "Accuracy": f"{perf['accuracy']}%",
            })
        df = pd.DataFrame(data)
        st.dataframe(df, width="stretch", hide_index=True)


def main():
    st.title("Technical Analysis Dashboard")
    st.markdown("*Combining Reddit sentiment with technical indicators for confluence signals*")

    # Load reports
    reports = load_cached_reports()

    if not reports:
        st.warning("No reports available. Please run the analyzer first.")
        return

    # Sidebar - Date selection
    available_dates = sorted(reports.keys(), reverse=True)

    st.sidebar.header("Settings")
    selected_date = st.sidebar.selectbox(
        "Select Report Date",
        available_dates,
        format_func=lambda d: d.strftime("%B %d, %Y")
    )

    # Get report for selected date
    report_data = get_report_for_date(selected_date)
    if not report_data:
        st.error("Could not load report for selected date.")
        return

    report_content = report_data.get("content", "")

    # Display date info
    st.markdown(f"**Report Date:** {selected_date.strftime('%A, %B %d, %Y')}")

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["Confluence Signals", "Stock Analysis", "Accuracy Tracking"])

    with tab1:
        display_confluence_signals(report_content)

    with tab2:
        st.header("Individual Stock Analysis")

        # Get stocks from report
        stocks = parse_stock_mentions(report_content)
        if not stocks:
            st.info("No stocks found in the report.")
        else:
            stock_tickers = [s["ticker"] for s in stocks]

            selected_ticker = st.selectbox(
                "Select a stock to analyze",
                stock_tickers,
                help="Choose a stock mentioned in today's report"
            )

            if selected_ticker:
                with st.spinner(f"Loading technical data for {selected_ticker}..."):
                    stock_data = get_technical_data(selected_ticker)

                if stock_data.get("success"):
                    technicals = stock_data.get("technicals", {})

                    # Display current price and basic info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Current Price", f"{technicals.get('current_price', 'N/A')}")
                    with col2:
                        metrics = stock_data.get("metrics", {})
                        st.metric("30D Return", f"{metrics.get('total_return', 0)}%")
                    with col3:
                        st.metric("Volatility", f"{metrics.get('volatility', 0)}%")
                    with col4:
                        st.metric("Tech Bias", technicals.get("technical_bias", "N/A").title())

                    # Display technical indicators
                    st.subheader("Technical Indicators")
                    display_technical_indicators(technicals)

                    # Display chart
                    st.subheader("Price Chart with Indicators")
                    df = stock_data.get("history")
                    if df is not None and not df.empty:
                        fig = create_technical_chart(df, technicals, selected_ticker)
                        if fig:
                            st.plotly_chart(fig, width="stretch")
                else:
                    st.error(f"Could not fetch data for {selected_ticker}: {stock_data.get('error', 'Unknown error')}")

    with tab3:
        display_accuracy_stats()

        st.markdown("---")
        st.markdown("""
        **How Signal Accuracy is Tracked:**
        - Every stock mentioned in daily reports is stored with its sentiment and technical indicators
        - After 1, 3, and 5 trading days, the actual price change is recorded
        - A signal is considered "accurate" if:
          - Bullish signals lead to positive returns
          - Bearish signals lead to negative returns
        - Confluence strength matters: signals with 4-5 aligned indicators should have higher accuracy
        """)


if __name__ == "__main__":
    main()
