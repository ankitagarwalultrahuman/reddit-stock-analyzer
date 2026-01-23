"""
Stock Movement Alerts Dashboard Page

Analyze why your stocks moved and get SMS alerts for significant changes.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Movement Alerts - Stock Analyzer",
    page_icon="📲",
    layout="wide"
)

st.title("📲 Stock Movement Alerts")
st.markdown("*Analyze why your stocks moved and get SMS alerts*")

# Check Twilio configuration
from stock_movement_analyzer import (
    is_twilio_configured,
    detect_significant_movements,
    analyze_movement_with_ai,
    get_stock_context,
    send_sms,
    test_sms,
    MOVEMENT_THRESHOLD
)


# Sidebar configuration
st.sidebar.header("Settings")

threshold = st.sidebar.slider(
    "Movement Threshold (%)",
    min_value=0.5,
    max_value=10.0,
    value=1.0,
    step=0.5,
    help="Alert when stocks move more than this percentage"
)

# Twilio status
st.sidebar.markdown("---")
st.sidebar.subheader("SMS Status")
if is_twilio_configured():
    st.sidebar.success("✅ Twilio configured")
    if st.sidebar.button("Send Test SMS"):
        if test_sms():
            st.sidebar.success("Test SMS sent!")
        else:
            st.sidebar.error("Failed to send test SMS")
else:
    st.sidebar.warning("⚠️ Twilio not configured")
    st.sidebar.caption("Add to .env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, USER_PHONE_NUMBER")


# Main content
tab1, tab2, tab3 = st.tabs(["Check Movements", "Manual Analysis", "Alert History"])

with tab1:
    st.subheader("Check Portfolio for Significant Movements")

    # Handle Quick Load buttons first
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("📂 Load My Portfolio (Groww)", use_container_width=True):
            try:
                from groww_integration import GrowwClient
                client = GrowwClient()
                if client.is_configured():
                    with st.spinner("Fetching portfolio from Groww..."):
                        holdings = client.get_holdings()
                    if holdings:
                        tickers = [h.trading_symbol for h in holdings]
                        st.session_state['stock_input_value'] = ", ".join(tickers)
                        st.success(f"Loaded {len(tickers)} stocks from Groww!")
                        st.rerun()
                    else:
                        st.warning("No holdings found in Groww")
                else:
                    st.warning("Groww not configured. Add GROWW_API_TOKEN and GROWW_API_SECRET to secrets.")
            except Exception as e:
                st.error(f"Error loading Groww portfolio: {e}")

    with col_btn2:
        if st.button("📊 Load NIFTY 50", use_container_width=True):
            from watchlist_manager import NIFTY50_STOCKS
            st.session_state['stock_input_value'] = ", ".join(NIFTY50_STOCKS)
            st.rerun()

    with col_btn3:
        if st.button("🏦 Load Banking Stocks", use_container_width=True):
            from watchlist_manager import SECTOR_STOCKS
            st.session_state['stock_input_value'] = ", ".join(SECTOR_STOCKS.get("Banking", []))
            st.rerun()

    # Get default value from session state or use default
    default_stocks = st.session_state.get('stock_input_value', "RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, SBIN")

    # Stock input
    stock_input = st.text_area(
        "Enter stock symbols (comma or newline separated)",
        value=default_stocks,
        height=100,
        help="Enter your portfolio stocks to check for movements"
    )

    # Parse tickers
    tickers = [t.strip().upper() for t in stock_input.replace("\n", ",").split(",") if t.strip()]
    st.caption(f"Checking {len(tickers)} stocks")

    if st.button("🔍 Check for Movements", type="primary"):
        if not tickers:
            st.warning("Please enter at least one stock symbol")
        else:
            with st.spinner(f"Checking {len(tickers)} stocks for movements > {threshold}%..."):
                movements = detect_significant_movements(tickers, threshold)

            if not movements:
                st.info(f"No stocks moved more than {threshold}% today")
            else:
                st.success(f"Found {len(movements)} significant movements!")

                # Display movements
                for movement in movements:
                    emoji = "📈" if movement.direction == "up" else "📉"
                    color = "green" if movement.direction == "up" else "red"

                    with st.expander(
                        f"{emoji} {movement.ticker}: {movement.change_percent:+.2f}%",
                        expanded=True
                    ):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Current Price", f"₹{movement.current_price:.2f}")
                        with col2:
                            st.metric("Previous Close", f"₹{movement.previous_price:.2f}")
                        with col3:
                            st.metric("Volume", f"{movement.volume_ratio:.1f}x avg")

                        # Analyze with AI
                        if st.button(f"🤖 Analyze Why", key=f"analyze_{movement.ticker}"):
                            with st.spinner("Analyzing with AI..."):
                                context = get_stock_context(movement.ticker)
                                analysis = analyze_movement_with_ai(movement, context)

                            st.markdown("**AI Analysis:**")
                            st.info(analysis.summary)
                            st.markdown(f"**Detailed:** {analysis.detailed_reason}")
                            st.caption(f"Confidence: {analysis.confidence} | Sources: {', '.join(analysis.sources) or 'price data only'}")

                            # Option to send as SMS
                            if is_twilio_configured():
                                if st.button(f"📱 Send SMS Alert", key=f"sms_{movement.ticker}"):
                                    msg = f"{emoji} {movement.ticker} {movement.change_percent:+.1f}%\n{analysis.summary}"
                                    if send_sms(msg):
                                        st.success("SMS sent!")
                                    else:
                                        st.error("Failed to send SMS")

                # Bulk SMS option
                if is_twilio_configured() and len(movements) > 0:
                    st.markdown("---")
                    if st.button("📲 Send All Movements as SMS"):
                        lines = [f"📊 Stock Movements ({datetime.now().strftime('%H:%M')})"]
                        for m in movements[:5]:
                            emoji = "📈" if m.direction == "up" else "📉"
                            lines.append(f"{emoji} {m.ticker}: {m.change_percent:+.1f}%")
                        if len(movements) > 5:
                            lines.append(f"+{len(movements)-5} more")

                        if send_sms("\n".join(lines)):
                            st.success("SMS sent with all movements!")
                        else:
                            st.error("Failed to send SMS")


with tab2:
    st.subheader("Analyze Single Stock")

    col1, col2 = st.columns([2, 1])

    with col1:
        single_ticker = st.text_input("Stock Symbol", value="RELIANCE").upper()

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_single = st.button("🔍 Analyze", type="primary")

    if analyze_single and single_ticker:
        with st.spinner(f"Analyzing {single_ticker}..."):
            # Get price data
            from stock_history import fetch_stock_history, calculate_performance_metrics

            df = fetch_stock_history(single_ticker, days=10)

            if df.empty:
                st.error(f"Could not fetch data for {single_ticker}")
            else:
                # Calculate movement
                current = float(df['Close'].iloc[-1])
                previous = float(df['Close'].iloc[-2])
                change_pct = ((current - previous) / previous) * 100

                # Display price info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Price", f"₹{current:.2f}", f"{change_pct:+.2f}%")
                with col2:
                    st.metric("Previous Close", f"₹{previous:.2f}")
                with col3:
                    metrics = calculate_performance_metrics(df)
                    st.metric("5-Day Return", f"{metrics.get('total_return', 0):.2f}%")

                # Get context and analyze
                st.markdown("---")
                st.markdown("### AI Analysis")

                context = get_stock_context(single_ticker)

                # Show context
                with st.expander("📊 Data Context"):
                    if context.get("technicals"):
                        st.markdown("**Technical Indicators:**")
                        tech = context["technicals"]
                        cols = st.columns(4)
                        cols[0].metric("RSI", f"{tech.get('rsi', 'N/A')}")
                        cols[1].metric("MACD", tech.get('macd_crossover', 'N/A'))
                        cols[2].metric("Bias", tech.get('technical_bias', 'N/A'))
                        cols[3].metric("vs EMA50", tech.get('price_vs_ema50', 'N/A'))

                    if context.get("reddit_sentiment"):
                        st.markdown("**Reddit Sentiment:**")
                        sent = context["reddit_sentiment"]
                        st.write(f"- Sentiment: {sent.get('sentiment', 'N/A')}")
                        st.write(f"- Mentions: {sent.get('mentions', 0)}")

                    if context.get("sector_performance"):
                        st.markdown(f"**Sector ({context.get('sector', 'Unknown')}):**")
                        sec = context["sector_performance"]
                        st.write(f"- Momentum: {sec.get('momentum', 'N/A')}")
                        st.write(f"- Trend: {sec.get('trend', 'N/A')}")

                # Create movement object for analysis
                from stock_movement_analyzer import StockMovement
                movement = StockMovement(
                    ticker=single_ticker,
                    current_price=current,
                    previous_price=previous,
                    change_percent=round(change_pct, 2),
                    direction="up" if change_pct > 0 else "down",
                    volume_ratio=1.0,
                    timestamp=datetime.now()
                )

                with st.spinner("Generating AI analysis..."):
                    analysis = analyze_movement_with_ai(movement, context)

                st.markdown("**Summary (SMS-friendly):**")
                st.info(analysis.summary)

                st.markdown("**Detailed Analysis:**")
                st.write(analysis.detailed_reason)

                st.caption(f"Confidence: {analysis.confidence} | Sources: {', '.join(analysis.sources) or 'price data only'}")

                # Send SMS option
                if is_twilio_configured():
                    st.markdown("---")
                    if st.button("📱 Send Analysis as SMS"):
                        emoji = "📈" if movement.direction == "up" else "📉"
                        msg = f"{emoji} {single_ticker} {change_pct:+.1f}%\n{analysis.summary}"
                        if send_sms(msg):
                            st.success("SMS sent!")
                        else:
                            st.error("Failed to send")


with tab3:
    st.subheader("Alert History")
    st.info("Alert history tracking coming soon. Alerts will be logged here once you start using the movement analyzer.")

    # Placeholder for future feature
    st.markdown("""
    **Planned features:**
    - Log of all sent alerts
    - Accuracy tracking (was the analysis correct?)
    - Most frequently alerted stocks
    - Best/worst AI predictions
    """)


# Footer
st.markdown("---")
st.caption("Stock Movement Alerts uses Claude AI to analyze why stocks moved. Alerts are sent via Twilio SMS.")
