"""
Swing Trade Screener Dashboard

Identifies swing trading opportunities:
- Oversold bounce setups
- Pullback to EMA setups
- Breakout setups
- Momentum continuation setups
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Swing Screener - Stock Analyzer",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Swing Trade Screener")
st.markdown("*Find your next swing trade setup*")

# Import after page config
from swing_screener import (
    run_swing_screener,
    get_top_swing_setups,
    get_screener_summary,
    SwingSetupType,
    ScreenerResult
)
from watchlist_manager import (
    NIFTY50_STOCKS, NIFTY100_STOCKS, SECTOR_STOCKS,
    NIFTY_MIDCAP100_STOCKS, NIFTY_SMALLCAP100_STOCKS, NIFTY_MIDSMALL_STOCKS
)


# Sidebar
st.sidebar.header("Screener Settings")

# Stock universe selection
universe_option = st.sidebar.selectbox(
    "Stock Universe",
    [
        "NIFTY 50",
        "NIFTY 100",
        "Midcap 100",
        "Smallcap 100",
        "Midcap + Smallcap",
        "By Sector"
    ]
)

if universe_option == "NIFTY 50":
    stocks = NIFTY50_STOCKS
elif universe_option == "NIFTY 100":
    stocks = NIFTY100_STOCKS
elif universe_option == "Midcap 100":
    stocks = NIFTY_MIDCAP100_STOCKS
elif universe_option == "Smallcap 100":
    stocks = NIFTY_SMALLCAP100_STOCKS
elif universe_option == "Midcap + Smallcap":
    stocks = NIFTY_MIDSMALL_STOCKS
else:
    sector = st.sidebar.selectbox(
        "Select Sector",
        list(SECTOR_STOCKS.keys())
    )
    stocks = SECTOR_STOCKS.get(sector, [])

# Filter settings
st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

min_score = st.sidebar.slider(
    "Minimum Score",
    min_value=40,
    max_value=90,
    value=55,
    step=5,
    help="Higher score = stronger setup"
)

setup_filter = st.sidebar.multiselect(
    "Setup Types",
    [st.value for st in SwingSetupType],
    default=[st.value for st in SwingSetupType],
    help="Filter by specific setup types"
)

# Convert to enum
selected_setups = [st for st in SwingSetupType if st.value in setup_filter]


# Cache screener results
@st.cache_data(ttl=900)  # 15 min cache
def get_screener_results(stock_list: tuple, min_score: int, setup_types: tuple):
    setup_list = [st for st in SwingSetupType if st.value in setup_types] if setup_types else None
    return run_swing_screener(
        stocks=list(stock_list),
        min_score=min_score,
        setup_types=setup_list,
        max_workers=5
    )


# Run screener
if st.sidebar.button("🔍 Run Screener", type="primary"):
    st.cache_data.clear()

with st.spinner(f"Screening {len(stocks)} stocks..."):
    results = get_screener_results(
        tuple(stocks),
        min_score,
        tuple(setup_filter)
    )

# Summary metrics
st.subheader("Screener Summary")

summary = get_screener_summary(results)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Stocks Screened", len(stocks))

with col2:
    st.metric("Setups Found", summary.get("total_setups", 0))

with col3:
    st.metric("Avg Score", f"{summary.get('avg_score', 0):.0f}")

with col4:
    st.metric("Avg RS", f"{summary.get('avg_rs', 0):+.1f}%")


# Setup breakdown
if summary.get("setup_breakdown"):
    st.markdown("**Setup Breakdown:**")
    cols = st.columns(len(summary["setup_breakdown"]))
    for i, (setup_type, count) in enumerate(summary["setup_breakdown"].items()):
        cols[i].metric(setup_type, count)


# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 All Setups",
    "📈 Oversold Bounces",
    "🚀 Breakouts",
    "📊 Pullbacks"
])


with tab1:
    st.subheader("All Swing Setups")

    if results:
        # Get all setups sorted by confidence
        all_setups = get_top_swing_setups(results, top_n=20)

        for setup in all_setups:
            setup_emoji = {
                SwingSetupType.OVERSOLD_BOUNCE: "📉",
                SwingSetupType.BREAKOUT: "🚀",
                SwingSetupType.PULLBACK_TO_EMA: "📊",
                SwingSetupType.MOMENTUM_CONTINUATION: "💨",
                SwingSetupType.MEAN_REVERSION: "🔄",
                SwingSetupType.SECTOR_ROTATION: "🔀"
            }.get(setup.setup_type, "📌")

            with st.expander(
                f"{setup_emoji} {setup.ticker} - {setup.setup_type.value} (Confidence: {setup.confidence_score}/10)",
                expanded=setup.confidence_score >= 7
            ):
                # Key metrics
                cols = st.columns(5)
                cols[0].metric("Price", f"₹{setup.current_price:.2f}")
                cols[1].metric("Entry Zone", f"₹{setup.entry_zone[0]:.0f}-{setup.entry_zone[1]:.0f}")
                cols[2].metric("Stop Loss", f"₹{setup.stop_loss:.2f}")
                cols[3].metric("Target 1", f"₹{setup.target_1:.2f}")
                cols[4].metric("R:R", f"{setup.risk_reward:.1f}")

                # Second row
                cols2 = st.columns(4)
                cols2[0].metric("Target 2", f"₹{setup.target_2:.2f}")
                cols2[1].metric("Sector", setup.sector)
                cols2[2].metric("RS vs NIFTY", f"{setup.relative_strength:+.1f}%")
                cols2[3].metric("Confidence", f"{setup.confidence_score}/10")

                # Signals
                st.markdown("**Bullish Signals:**")
                for signal in setup.signals:
                    st.markdown(f"✅ {signal}")

                # Trade plan
                st.markdown("---")
                st.markdown("**Trade Plan:**")
                risk_pct = ((setup.current_price - setup.stop_loss) / setup.current_price) * 100
                reward_pct = ((setup.target_1 - setup.current_price) / setup.current_price) * 100

                st.markdown(f"""
                - **Entry:** ₹{setup.entry_zone[0]:.2f} - ₹{setup.entry_zone[1]:.2f}
                - **Stop Loss:** ₹{setup.stop_loss:.2f} ({risk_pct:.1f}% risk)
                - **Target 1:** ₹{setup.target_1:.2f} ({reward_pct:.1f}% reward)
                - **Target 2:** ₹{setup.target_2:.2f}
                - **Risk:Reward:** 1:{setup.risk_reward:.1f}
                """)

    else:
        st.info("No setups found matching your criteria. Try lowering the minimum score.")


with tab2:
    st.subheader("📉 Oversold Bounce Setups")
    st.caption("Stocks with RSI < 35 showing potential reversal")

    oversold_setups = [
        s for r in results for s in r.setups
        if s.setup_type == SwingSetupType.OVERSOLD_BOUNCE
    ]

    if oversold_setups:
        oversold_setups.sort(key=lambda x: x.confidence_score, reverse=True)

        # Summary table
        table_data = []
        for s in oversold_setups[:15]:
            table_data.append({
                "Stock": s.ticker,
                "Sector": s.sector,
                "Price": f"₹{s.current_price:.2f}",
                "RSI": s.technical_summary.get("rsi", "N/A"),
                "Stop": f"₹{s.stop_loss:.2f}",
                "Target": f"₹{s.target_1:.2f}",
                "R:R": f"{s.risk_reward:.1f}",
                "Confidence": f"{s.confidence_score}/10"
            })

        st.dataframe(pd.DataFrame(table_data), hide_index=True, use_container_width=True)

        # RSI distribution
        rsi_values = [s.technical_summary.get("rsi", 50) for s in oversold_setups]
        fig = go.Figure(data=[go.Histogram(x=rsi_values, nbinsx=10)])
        fig.update_layout(
            title="RSI Distribution",
            xaxis_title="RSI",
            yaxis_title="Count",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No oversold bounce setups found")


with tab3:
    st.subheader("🚀 Breakout Setups")
    st.caption("Stocks breaking resistance with volume")

    breakout_setups = [
        s for r in results for s in r.setups
        if s.setup_type == SwingSetupType.BREAKOUT
    ]

    if breakout_setups:
        breakout_setups.sort(key=lambda x: (x.confidence_score, x.risk_reward), reverse=True)

        for setup in breakout_setups[:10]:
            with st.expander(f"🚀 {setup.ticker} - Breaking ₹{setup.technical_summary.get('resistance', 0):.2f}"):
                cols = st.columns(4)
                cols[0].metric("Price", f"₹{setup.current_price:.2f}")
                cols[1].metric("Resistance", f"₹{setup.technical_summary.get('resistance', 0):.2f}")
                cols[2].metric("Volume", f"{setup.technical_summary.get('volume', 1):.1f}x")
                cols[3].metric("R:R", f"{setup.risk_reward:.1f}")

                st.markdown("**Signals:**")
                for signal in setup.signals:
                    st.markdown(f"✅ {signal}")

                st.markdown(f"""
                **Trade Plan:**
                - Entry: ₹{setup.entry_zone[0]:.2f} - ₹{setup.entry_zone[1]:.2f}
                - Stop: ₹{setup.stop_loss:.2f} (below breakout level)
                - T1: ₹{setup.target_1:.2f} | T2: ₹{setup.target_2:.2f}
                """)

    else:
        st.info("No breakout setups found")


with tab4:
    st.subheader("📊 Pullback to EMA Setups")
    st.caption("Stocks in uptrend pulling back to moving averages")

    pullback_setups = [
        s for r in results for s in r.setups
        if s.setup_type == SwingSetupType.PULLBACK_TO_EMA
    ]

    if pullback_setups:
        pullback_setups.sort(key=lambda x: x.confidence_score, reverse=True)

        for setup in pullback_setups[:10]:
            ema20 = setup.technical_summary.get("ema20", 0)
            ema50 = setup.technical_summary.get("ema50", 0)

            with st.expander(f"📊 {setup.ticker} - Pullback Setup"):
                cols = st.columns(5)
                cols[0].metric("Price", f"₹{setup.current_price:.2f}")
                cols[1].metric("EMA 20", f"₹{ema20:.2f}" if ema20 else "N/A")
                cols[2].metric("EMA 50", f"₹{ema50:.2f}" if ema50 else "N/A")
                cols[3].metric("RSI", f"{setup.technical_summary.get('rsi', 'N/A')}")
                cols[4].metric("R:R", f"{setup.risk_reward:.1f}")

                st.markdown("**Signals:**")
                for signal in setup.signals:
                    st.markdown(f"✅ {signal}")

                st.markdown(f"""
                **Trade Plan:**
                - Entry: Near ₹{setup.entry_zone[0]:.2f}
                - Stop: ₹{setup.stop_loss:.2f} (below EMA)
                - T1: ₹{setup.target_1:.2f} | T2: ₹{setup.target_2:.2f}
                """)

    else:
        st.info("No pullback setups found")


# Stock details section
st.markdown("---")
st.subheader("📋 All Screened Stocks")

if results:
    # Full results table
    full_data = []
    for r in results:
        # 52W High indicator
        high_indicator = "⭐" if r.near_52w_high else ""
        full_data.append({
            "Stock": r.ticker,
            "Sector": r.sector,
            "Price": f"₹{r.current_price:.2f}",
            "52W High": f"₹{r.week_52_high:.0f}" if r.week_52_high else "N/A",
            "% from 52W": f"{r.pct_from_52w_high:+.1f}%{high_indicator}" if r.pct_from_52w_high else "N/A",
            "Week %": f"{r.week_change:+.1f}%",
            "RSI": r.rsi,
            "MACD": r.macd_signal,
            "MA Trend": r.ma_trend,
            "Bias": r.technical_bias,
            "RS vs NIFTY": f"{r.relative_strength:+.1f}%",
            "Setups": len(r.setups),
            "Score": r.total_score
        })

    df = pd.DataFrame(full_data)
    df = df.sort_values("Score", ascending=False)

    st.dataframe(df, hide_index=True, use_container_width=True, height=400)

    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Download Results",
        csv,
        f"swing_screener_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )


# Footer
st.markdown("---")
col1, col2 = st.columns(2)
with col1:
    st.caption(f"Screened: {datetime.now().strftime('%d %b %Y, %H:%M')}")
with col2:
    st.caption("⚠️ Not financial advice. Always do your own research.")
