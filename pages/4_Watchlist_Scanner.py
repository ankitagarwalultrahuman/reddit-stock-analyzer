"""
Watchlist Scanner Dashboard Page

Scan your watchlists for technical setups and trading opportunities.
Independent of Reddit - works on any stocks you want to track.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from config import DASHBOARD_CACHE_TTL

# Page config
st.set_page_config(
    page_title="Watchlist Scanner - Stock Analyzer",
    page_icon="",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .opportunity-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 0.5rem;
    }
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 0.5rem;
    }
    .metric-up { color: #00c853; }
    .metric-down { color: #ff1744; }
    .stars { color: #ffd700; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=DASHBOARD_CACHE_TTL)
def get_watchlists():
    """Get all available watchlists."""
    from watchlist_manager import get_all_watchlists
    return get_all_watchlists()


@st.cache_data(ttl=300)  # 5 minute cache for scan results
def run_scan(watchlist_name: str, strategy_name: str, min_matches: int):
    """Run a scan with caching."""
    from stock_screener import scan_watchlist
    return scan_watchlist(watchlist_name, strategy_name=strategy_name, min_matches=min_matches)


def display_screener_result(result, index: int):
    """Display a single screener result."""
    stars = "" * min(result.score, 5)
    bias_class = "metric-up" if result.technical_bias == "bullish" else "metric-down" if result.technical_bias == "bearish" else ""

    with st.expander(f"{index}. {result.ticker} {stars} - {result.technical_bias.title()}", expanded=index <= 3):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Price", f"{result.current_price}")
            st.metric("RSI", f"{result.rsi}")

        with col2:
            st.metric("MACD", result.macd_trend)
            st.metric("MA Trend", result.ma_trend)

        with col3:
            st.metric("Volume", result.volume_signal)
            st.metric("Matches", f"{result.score} criteria")

        st.markdown("**Matched Criteria:**")
        for criteria in result.matched_criteria:
            st.markdown(f"- {criteria}")


def main():
    st.title("Watchlist Scanner")
    st.markdown("*Scan your watchlists for technical setups - independent of Reddit*")

    # Sidebar - Configuration
    st.sidebar.header("Scan Settings")

    # Get watchlists
    watchlists = get_watchlists()
    watchlist_names = list(watchlists.keys())

    # Organize watchlists by type
    preset_lists = [w for w in watchlist_names if watchlists[w].is_preset and not w.startswith("SECTOR_")]
    sector_lists = [w for w in watchlist_names if w.startswith("SECTOR_")]
    user_lists = [w for w in watchlist_names if not watchlists[w].is_preset]

    # Watchlist selection with categories
    watchlist_options = []
    if preset_lists:
        watchlist_options.extend(preset_lists)
    if sector_lists:
        watchlist_options.extend(sector_lists)
    if user_lists:
        watchlist_options.extend(user_lists)

    selected_watchlist = st.sidebar.selectbox(
        "Select Watchlist",
        watchlist_options,
        index=0 if watchlist_options else None,
        help="Choose a preset (NIFTY50, NIFTY100) or your custom watchlist"
    )

    if selected_watchlist:
        wl = watchlists[selected_watchlist]
        st.sidebar.caption(f"{len(wl.stocks)} stocks | {wl.description}")

    # Strategy selection
    from stock_screener import get_available_strategies
    strategies = get_available_strategies()

    selected_strategy = st.sidebar.selectbox(
        "Screening Strategy",
        list(strategies.keys()),
        format_func=lambda x: strategies[x].name,
        help="Choose a pre-built screening strategy"
    )

    if selected_strategy:
        st.sidebar.caption(strategies[selected_strategy].description)

    # Minimum matches
    min_matches = st.sidebar.slider(
        "Minimum Criteria Matches",
        min_value=1,
        max_value=5,
        value=2,
        help="Stocks must match at least this many criteria"
    )

    st.sidebar.markdown("---")

    # Scan button
    scan_clicked = st.sidebar.button("Run Scan", type="primary", width="stretch")

    # Send to Telegram option
    send_telegram = st.sidebar.checkbox("Send results to Telegram", value=False)

    # Clear cache button - use this if data shows all zeros or errors
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Stock Cache", width="stretch"):
        from stock_history import clear_all_cache
        clear_all_cache()
        st.cache_data.clear()
        st.sidebar.success("Cache cleared! Run scan again.")

    # Main content area
    tab1, tab2, tab3 = st.tabs(["Scan Results", "Quick Scans", "Manage Watchlists"])

    with tab1:
        if scan_clicked and selected_watchlist:
            with st.spinner(f"Scanning {selected_watchlist} with {strategies[selected_strategy].name}..."):
                results = run_scan(selected_watchlist, selected_strategy, min_matches)

            if results:
                st.success(f"Found {len(results)} stocks matching criteria!")

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Stocks Found", len(results))
                with col2:
                    bullish = sum(1 for r in results if r.technical_bias == "bullish")
                    st.metric("Bullish", bullish)
                with col3:
                    avg_rsi = sum(r.rsi for r in results if r.rsi) / len([r for r in results if r.rsi])
                    st.metric("Avg RSI", f"{avg_rsi:.1f}")
                with col4:
                    high_score = sum(1 for r in results if r.score >= 3)
                    st.metric("Strong Signals", high_score)

                st.markdown("---")

                # Results table
                st.subheader("Scan Results")

                # Create DataFrame for display
                df_data = []
                for r in results:
                    df_data.append({
                        "Ticker": r.ticker,
                        "Price": r.current_price,
                        "RSI": r.rsi,
                        "MACD": r.macd_trend,
                        "MA Trend": r.ma_trend,
                        "Volume": r.volume_signal,
                        "Bias": r.technical_bias,
                        "Score": r.score,
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, width="stretch", hide_index=True)

                # Detailed results
                st.subheader("Detailed Analysis")
                for i, result in enumerate(results, 1):
                    display_screener_result(result, i)

                # Send to Telegram if requested
                if send_telegram:
                    from telegram_alerts import send_screener_alert, is_telegram_configured
                    if is_telegram_configured():
                        if send_screener_alert(results, strategies[selected_strategy].name):
                            st.success("Results sent to Telegram!")
                        else:
                            st.error("Failed to send to Telegram")
                    else:
                        st.warning("Telegram not configured. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env")

            else:
                st.info("No stocks match the criteria. Try a different strategy or lower the minimum matches.")

        elif not scan_clicked:
            st.info("Select a watchlist and strategy, then click 'Run Scan' to find opportunities.")

            # Show available strategies
            st.subheader("Available Strategies")

            for key, strategy in strategies.items():
                with st.expander(f"{strategy.name}"):
                    st.write(strategy.description)
                    st.write(f"**Filters:** {len(strategy.filters)} criteria")

    with tab2:
        st.subheader("Quick Scans")
        st.markdown("*One-click scans for common setups*")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Bullish Setups")

            if st.button("Oversold NIFTY50", width="stretch"):
                with st.spinner("Scanning..."):
                    from stock_screener import quick_scan_nifty50
                    results = quick_scan_nifty50("oversold_reversal")

                if results:
                    st.success(f"Found {len(results)} oversold stocks")
                    for r in results[:5]:
                        st.write(f"- {r.ticker}: RSI {r.rsi}, {r.macd_trend}")
                else:
                    st.info("No oversold stocks found")

            if st.button("Strong Buy Signals", width="stretch"):
                with st.spinner("Scanning..."):
                    from stock_screener import quick_scan_nifty50
                    results = quick_scan_nifty50("strong_buy")

                if results:
                    st.success(f"Found {len(results)} strong buy signals")
                    for r in results[:5]:
                        st.write(f"- {r.ticker}: RSI {r.rsi}, {r.macd_trend}")
                else:
                    st.info("No strong buy signals found")

            if st.button("Trend Following", width="stretch"):
                with st.spinner("Scanning..."):
                    from stock_screener import quick_scan_nifty50
                    results = quick_scan_nifty50("trend_following")

                if results:
                    st.success(f"Found {len(results)} trending stocks")
                    for r in results[:5]:
                        st.write(f"- {r.ticker}: MA trend {r.ma_trend}")
                else:
                    st.info("No trending stocks found")

        with col2:
            st.markdown("### Risk Alerts")

            if st.button("Overbought Warnings", width="stretch"):
                with st.spinner("Scanning..."):
                    from stock_screener import quick_scan_nifty50
                    results = quick_scan_nifty50("overbought_warning")

                if results:
                    st.warning(f"Found {len(results)} overbought stocks")
                    for r in results[:5]:
                        st.write(f"- {r.ticker}: RSI {r.rsi}")
                else:
                    st.info("No overbought warnings")

            if st.button("Downtrending Stocks", width="stretch"):
                with st.spinner("Scanning..."):
                    from stock_screener import quick_scan_nifty50
                    results = quick_scan_nifty50("downtrend")

                if results:
                    st.warning(f"Found {len(results)} downtrending stocks")
                    for r in results[:5]:
                        st.write(f"- {r.ticker}: MA trend {r.ma_trend}")
                else:
                    st.info("No downtrending stocks")

    with tab3:
        st.subheader("Manage Watchlists")

        # Create new watchlist
        st.markdown("### Create Custom Watchlist")

        with st.form("create_watchlist"):
            new_name = st.text_input("Watchlist Name", placeholder="My Favorites")
            new_stocks = st.text_area(
                "Stocks (one per line or comma-separated)",
                placeholder="RELIANCE\nTCS\nINFY",
                height=150
            )
            new_desc = st.text_input("Description (optional)", placeholder="My top picks")

            submitted = st.form_submit_button("Create Watchlist")

            if submitted and new_name and new_stocks:
                # Parse stocks
                stocks = []
                for line in new_stocks.split("\n"):
                    for stock in line.split(","):
                        stock = stock.strip().upper()
                        if stock:
                            stocks.append(stock)

                if stocks:
                    from watchlist_manager import create_watchlist
                    create_watchlist(new_name, stocks, new_desc)
                    st.success(f"Created watchlist '{new_name}' with {len(stocks)} stocks!")
                    st.cache_data.clear()
                else:
                    st.error("Please enter at least one stock")

        # View existing watchlists
        st.markdown("### Your Watchlists")

        user_watchlists = {k: v for k, v in watchlists.items() if not v.is_preset}

        if user_watchlists:
            for name, wl in user_watchlists.items():
                with st.expander(f"{name} ({len(wl.stocks)} stocks)"):
                    st.write(f"**Description:** {wl.description or 'N/A'}")
                    st.write(f"**Created:** {wl.created_at[:10] if wl.created_at else 'N/A'}")
                    st.write(f"**Stocks:** {', '.join(wl.stocks[:20])}{'...' if len(wl.stocks) > 20 else ''}")

                    if st.button(f"Delete {name}", key=f"del_{name}"):
                        from watchlist_manager import delete_watchlist
                        delete_watchlist(name)
                        st.success(f"Deleted '{name}'")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.info("No custom watchlists yet. Create one above!")


if __name__ == "__main__":
    main()
