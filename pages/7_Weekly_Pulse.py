"""
Weekly Market Pulse Dashboard

Provides weekly market analysis for swing traders including:
- Market overview and breadth
- Top/Bottom sectors
- Breakout candidates
- Relative strength leaders
- Actionable insights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Weekly Pulse - Stock Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Weekly Market Pulse")
st.markdown("*Your weekly swing trading compass*")

# Import after page config
from weekly_analysis import (
    generate_weekly_pulse,
    get_weekly_pulse_summary,
    WeeklyPulseReport
)
from watchlist_manager import (
    NIFTY50_STOCKS, NIFTY100_STOCKS,
    NIFTY_MIDCAP100_STOCKS, NIFTY_SMALLCAP100_STOCKS, NIFTY_MIDSMALL_STOCKS
)


# Sidebar
st.sidebar.header("Settings")

stock_universe = st.sidebar.selectbox(
    "Stock Universe",
    ["NIFTY 50", "NIFTY 100", "Midcap 100", "Smallcap 100", "Midcap + Smallcap"],
    index=0
)

if stock_universe == "NIFTY 50":
    stocks = NIFTY50_STOCKS
elif stock_universe == "NIFTY 100":
    stocks = NIFTY100_STOCKS
elif stock_universe == "Midcap 100":
    stocks = NIFTY_MIDCAP100_STOCKS
elif stock_universe == "Smallcap 100":
    stocks = NIFTY_SMALLCAP100_STOCKS
else:  # Midcap + Smallcap
    stocks = NIFTY_MIDSMALL_STOCKS


# Cache the report generation
@st.cache_data(ttl=1800)  # 30 minutes cache
def get_weekly_report(stock_list: tuple):
    return generate_weekly_pulse(list(stock_list), max_workers=5)


# Generate report
if st.sidebar.button("🔄 Refresh Analysis", type="primary"):
    st.cache_data.clear()
    st.rerun()

with st.spinner(f"Analyzing {len(stocks)} stocks..."):
    report = get_weekly_report(tuple(stocks))

# Debug info in sidebar
st.sidebar.markdown("---")
st.sidebar.caption(f"📊 Data Status:")
st.sidebar.caption(f"• Stocks analyzed: {report.market_breadth['advances'] + report.market_breadth['declines'] + report.market_breadth['unchanged']}")
st.sidebar.caption(f"• Gainers: {len(report.top_gainers)}")
st.sidebar.caption(f"• Losers: {len(report.top_losers)}")
st.sidebar.caption(f"• Breakouts: {len(report.breakout_candidates)}")
_all_stocks_for_sidebar = (report.top_gainers + report.top_losers + report.rs_leaders
                           + report.oversold_stocks + report.overbought_stocks
                           + report.breakout_candidates)
_breakdown_count = len(set(s.ticker for s in _all_stocks_for_sidebar if getattr(s, 'breakdown_candidate', False)))
st.sidebar.caption(f"• Breakdowns: {_breakdown_count}")
st.sidebar.caption(f"• Oversold: {len(report.oversold_stocks)}")

# Main content - NIFTY multi-week performance
st.subheader("NIFTY 50 Performance (7-Week View)")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "1 Week",
        f"{report.nifty_week_change:+.1f}%",
        delta=None,
        delta_color="normal" if report.nifty_week_change >= 0 else "inverse"
    )

with col2:
    st.metric(
        "2 Weeks",
        f"{report.nifty_two_week_change:+.1f}%",
        delta=None,
        delta_color="normal" if report.nifty_two_week_change >= 0 else "inverse"
    )

with col3:
    st.metric(
        "4 Weeks",
        f"{report.nifty_four_week_change:+.1f}%",
        delta=None,
        delta_color="normal" if report.nifty_four_week_change >= 0 else "inverse"
    )

with col4:
    st.metric(
        "6 Weeks",
        f"{report.nifty_month_change:+.1f}%",
        delta=None,
        delta_color="normal" if report.nifty_month_change >= 0 else "inverse"
    )

with col5:
    advances = report.market_breadth['advances']
    declines = report.market_breadth['declines']
    st.metric(
        "Breadth",
        f"{advances}↑ / {declines}↓",
        delta="Bullish" if advances > declines else "Bearish",
        delta_color="normal" if advances > declines else "inverse"
    )


# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Key Insights",
    "📊 Multi-Week View",
    "🏭 Sectors",
    "🚀 Breakouts",
    "📉 Oversold",
    "💪 RS Leaders"
])


with tab1:
    st.subheader("Key Insights for This Week")

    for i, insight in enumerate(report.insights):
        if "flowing into" in insight.lower() or "leader" in insight.lower():
            st.success(f"✅ {insight}")
        elif "avoid" in insight.lower() or "weak" in insight.lower():
            st.warning(f"⚠️ {insight}")
        else:
            st.info(f"💡 {insight}")

    st.markdown("---")

    # Top Gainers and Losers side by side
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 Top Gainers (Multi-Week View)")
        gainers_data = []
        for stock in report.top_gainers[:7]:
            high_ind = "⭐" if stock.near_52w_high else ""
            gainers_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "52W High": f"₹{stock.week_52_high:.0f}" if stock.week_52_high else "N/A",
                "% from 52W": f"{stock.pct_from_52w_high:+.1f}%{high_ind}" if stock.pct_from_52w_high else "N/A",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "RSI": f"{stock.rsi:.0f}",
                "RS": f"{stock.relative_strength:+.1f}%"
            })
        if gainers_data:
            st.dataframe(pd.DataFrame(gainers_data), hide_index=True, use_container_width=True)

    with col2:
        st.markdown("### 📉 Top Losers (Multi-Week View)")
        losers_data = []
        for stock in report.top_losers[:7]:
            high_ind = "⭐" if stock.near_52w_high else ""
            losers_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "52W High": f"₹{stock.week_52_high:.0f}" if stock.week_52_high else "N/A",
                "% from 52W": f"{stock.pct_from_52w_high:+.1f}%{high_ind}" if stock.pct_from_52w_high else "N/A",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "RSI": f"{stock.rsi:.0f}",
                "RS": f"{stock.relative_strength:+.1f}%"
            })
        if losers_data:
            st.dataframe(pd.DataFrame(losers_data), hide_index=True, use_container_width=True)


with tab2:
    st.subheader("Multi-Week Stock Performance")
    st.caption("Track stocks over 1-6 weeks to identify sustained trends")

    # Create multi-week performance table
    all_stocks_data = []
    all_stock_metrics = report.top_gainers + report.top_losers + report.rs_leaders
    seen_tickers = set()

    for stock in all_stock_metrics:
        if stock.ticker not in seen_tickers:
            seen_tickers.add(stock.ticker)
            high_ind = "⭐" if stock.near_52w_high else ""
            all_stocks_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "Price": f"₹{stock.current_price:.0f}",
                "52W High": f"₹{stock.week_52_high:.0f}" if stock.week_52_high else "N/A",
                "% from 52W": f"{stock.pct_from_52w_high:+.1f}%{high_ind}" if stock.pct_from_52w_high else "N/A",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "6W": f"{stock.month_change_pct:+.1f}%",
                "Trend": f"{stock.weekly_trend.capitalize()} ({getattr(stock, 'trend_strength', 'moderate').capitalize()})",
                "RSI": stock.rsi,
                "RS": f"{stock.relative_strength:+.1f}%"
            })

    if all_stocks_data:
        df = pd.DataFrame(all_stocks_data)
        st.dataframe(df, hide_index=True, use_container_width=True, height=400)

    # Weekly trend summary
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    uptrend_stocks = [s for s in all_stock_metrics if s.weekly_trend == "up"]
    downtrend_stocks = [s for s in all_stock_metrics if s.weekly_trend == "down"]
    sideways_stocks = [s for s in all_stock_metrics if s.weekly_trend == "sideways"]

    with col1:
        st.metric("Uptrend Stocks", len(set(s.ticker for s in uptrend_stocks)))
        if uptrend_stocks:
            st.caption(f"Top: {', '.join([s.ticker for s in uptrend_stocks[:5]])}")

    with col2:
        st.metric("Downtrend Stocks", len(set(s.ticker for s in downtrend_stocks)))
        if downtrend_stocks:
            st.caption(f"Worst: {', '.join([s.ticker for s in downtrend_stocks[:5]])}")

    with col3:
        st.metric("Sideways Stocks", len(set(s.ticker for s in sideways_stocks)))


with tab3:
    st.subheader("Sector Performance")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔥 Hot Sectors")
        for sector in report.top_sectors:
            with st.container():
                st.markdown(f"**{sector.sector}**")
                cols = st.columns(4)
                cols[0].metric("5D Return", f"{sector.avg_return_5d:+.1f}%")
                cols[1].metric("Momentum", f"{sector.momentum_score:.0f}")
                cols[2].metric("Avg RSI", f"{sector.avg_rsi:.0f}")
                cols[3].metric("Trend", sector.momentum_trend)
                st.markdown("---")

    with col2:
        st.markdown("### ❄️ Cold Sectors")
        for sector in report.bottom_sectors:
            with st.container():
                st.markdown(f"**{sector.sector}**")
                cols = st.columns(4)
                cols[0].metric("5D Return", f"{sector.avg_return_5d:+.1f}%")
                cols[1].metric("Momentum", f"{sector.momentum_score:.0f}")
                cols[2].metric("Avg RSI", f"{sector.avg_rsi:.0f}")
                cols[3].metric("Trend", sector.momentum_trend)
                st.markdown("---")

    # Sector heatmap
    st.markdown("### Sector Heatmap")
    sector_data = []
    for s in report.sector_metrics:
        sector_data.append({
            "Sector": s.sector,
            "1D": s.avg_return_1d,
            "5D": s.avg_return_5d,
            "20D": s.avg_return_20d,
            "Momentum": s.momentum_score
        })

    if sector_data:
        df = pd.DataFrame(sector_data)

        fig = px.imshow(
            df[["1D", "5D", "20D"]].values,
            labels=dict(x="Timeframe", y="Sector", color="Return %"),
            x=["1D", "5D", "20D"],
            y=df["Sector"].tolist(),
            color_continuous_scale="RdYlGn",
            aspect="auto"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


with tab4:
    st.subheader("🚀 Breakout Candidates")
    st.caption("Stocks consolidating near resistance with momentum")

    if report.breakout_candidates:
        # Multi-week table view
        breakout_data = []
        for stock in report.breakout_candidates[:10]:
            breakout_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "Price": f"₹{stock.current_price:.0f}",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "2W": f"{stock.two_week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "6W": f"{stock.month_change_pct:+.1f}%",
                "Trend": f"{stock.weekly_trend.capitalize()} ({getattr(stock, 'trend_strength', 'moderate').capitalize()})",
                "RSI": f"{stock.rsi:.0f}",
                "RS": f"{stock.relative_strength:+.1f}%",
                "Volume": f"{stock.volume_ratio:.1f}x",
                "Support": f"₹{stock.support_level:.0f}" if stock.support_level else "N/A",
                "Resistance": f"₹{stock.resistance_level:.0f}" if stock.resistance_level else "N/A"
            })

        st.dataframe(pd.DataFrame(breakout_data), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### Detailed View")

        for stock in report.breakout_candidates[:10]:
            with st.expander(f"{stock.ticker} - {stock.sector}", expanded=False):
                cols = st.columns(5)
                cols[0].metric("Price", f"₹{stock.current_price:.2f}")
                cols[1].metric("1W", f"{stock.week_change_pct:+.1f}%")
                cols[2].metric("4W", f"{stock.four_week_change_pct:+.1f}%")
                cols[3].metric("RS vs NIFTY", f"{stock.relative_strength:+.1f}%")
                cols[4].metric("Volume", f"{stock.volume_ratio:.1f}x")

                st.markdown(f"**Resistance:** ₹{stock.resistance_level} | **Support:** ₹{stock.support_level}")

                signals = []
                if stock.consolidating:
                    signals.append("📦 Consolidating")
                if stock.near_resistance:
                    signals.append("🎯 Near Resistance")
                if stock.macd_signal == "bullish_crossover" or stock.macd_signal == "bullish":
                    signals.append("✅ MACD Bullish")
                if stock.volume_ratio > 1.5:
                    signals.append("📊 Volume Spike")

                if signals:
                    st.markdown(" | ".join(signals))
    else:
        st.info("No breakout candidates found this week")

    # Breakdown Candidates section
    st.markdown("---")
    st.subheader("📉 Breakdown Candidates")
    st.caption("Stocks near or breaking support with downward momentum")

    # Gather breakdown candidates from all analyzed stocks
    all_analyzed_stocks = (report.top_gainers + report.top_losers + report.rs_leaders
                           + report.oversold_stocks + report.overbought_stocks
                           + report.breakout_candidates)
    seen_breakdown = set()
    breakdown_candidates = []
    for s in all_analyzed_stocks:
        if getattr(s, 'breakdown_candidate', False) and s.ticker not in seen_breakdown:
            seen_breakdown.add(s.ticker)
            breakdown_candidates.append(s)
    breakdown_candidates = sorted(breakdown_candidates, key=lambda x: x.week_change_pct)[:10]

    if breakdown_candidates:
        breakdown_data = []
        for stock in breakdown_candidates:
            breakdown_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "Price": f"₹{stock.current_price:.0f}",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "2W": f"{stock.two_week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "6W": f"{stock.month_change_pct:+.1f}%",
                "Trend": f"{stock.weekly_trend.capitalize()} ({getattr(stock, 'trend_strength', 'moderate').capitalize()})",
                "RSI": f"{stock.rsi:.0f}",
                "RS": f"{stock.relative_strength:+.1f}%",
                "Volume": f"{stock.volume_ratio:.1f}x",
                "Support": f"₹{stock.support_level:.0f}" if stock.support_level else "N/A",
                "Resistance": f"₹{stock.resistance_level:.0f}" if stock.resistance_level else "N/A"
            })

        st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.markdown("### Detailed View")

        for stock in breakdown_candidates:
            with st.expander(f"{stock.ticker} - {stock.sector}", expanded=False):
                cols = st.columns(5)
                cols[0].metric("Price", f"₹{stock.current_price:.2f}")
                cols[1].metric("1W", f"{stock.week_change_pct:+.1f}%")
                cols[2].metric("4W", f"{stock.four_week_change_pct:+.1f}%")
                cols[3].metric("RS vs NIFTY", f"{stock.relative_strength:+.1f}%")
                cols[4].metric("Volume", f"{stock.volume_ratio:.1f}x")

                st.markdown(f"**Support:** ₹{stock.support_level} | **Resistance:** ₹{stock.resistance_level}")

                signals = []
                if stock.near_support:
                    signals.append("⚠️ Near Support")
                if stock.macd_signal == "bearish_crossover" or stock.macd_signal == "bearish":
                    signals.append("🔴 MACD Bearish")
                if stock.volume_ratio > 1.5:
                    signals.append("📊 Volume Spike")
                if stock.rsi < 35:
                    signals.append("📉 Oversold")

                if signals:
                    st.markdown(" | ".join(signals))
    else:
        st.info("No breakdown candidates found this week")


with tab5:
    st.subheader("📉 Oversold Stocks (RSI < 35)")
    st.caption("Potential bounce candidates - confirm with price action before entry")

    if report.oversold_stocks:
        oversold_data = []
        for stock in report.oversold_stocks:
            oversold_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "Price": f"₹{stock.current_price:.0f}",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "2W": f"{stock.two_week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "6W": f"{stock.month_change_pct:+.1f}%",
                "Trend": f"{stock.weekly_trend.capitalize()} ({getattr(stock, 'trend_strength', 'moderate').capitalize()})",
                "RSI": f"{stock.rsi:.0f}",
                "RS": f"{stock.relative_strength:+.1f}%",
                "Support": f"₹{stock.support_level:.0f}" if stock.support_level else "N/A",
                "MACD": stock.macd_signal,
                "Near Support": "✅" if stock.near_support else "❌"
            })

        st.dataframe(pd.DataFrame(oversold_data), hide_index=True, use_container_width=True)

        # RSI Distribution
        rsi_values = [s.rsi for s in report.oversold_stocks]
        fig = go.Figure(data=[go.Histogram(x=rsi_values, nbinsx=10)])
        fig.update_layout(
            title="RSI Distribution of Oversold Stocks",
            xaxis_title="RSI",
            yaxis_title="Count",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No oversold stocks found - market may be overbought")

    # Overbought section
    st.markdown("---")
    st.subheader("📈 Overbought Stocks (RSI > 70)")
    st.caption("Caution - may be due for pullback")

    if report.overbought_stocks:
        overbought_data = []
        for stock in report.overbought_stocks:
            overbought_data.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "Price": f"₹{stock.current_price:.0f}",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "2W": f"{stock.two_week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "6W": f"{stock.month_change_pct:+.1f}%",
                "Trend": f"{stock.weekly_trend.capitalize()} ({getattr(stock, 'trend_strength', 'moderate').capitalize()})",
                "RSI": f"{stock.rsi:.0f}",
                "RS": f"{stock.relative_strength:+.1f}%"
            })

        st.dataframe(pd.DataFrame(overbought_data), hide_index=True, use_container_width=True)
    else:
        st.info("No overbought stocks found")


with tab6:
    st.subheader("💪 Relative Strength Leaders")
    st.caption("Stocks outperforming NIFTY - strong momentum")

    if report.rs_leaders:
        # Chart
        rs_data = {
            "Stock": [s.ticker for s in report.rs_leaders[:15]],
            "RS vs NIFTY": [s.relative_strength for s in report.rs_leaders[:15]]
        }
        fig = px.bar(
            rs_data,
            x="Stock",
            y="RS vs NIFTY",
            color="RS vs NIFTY",
            color_continuous_scale="RdYlGn"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Table with multi-week view
        rs_table = []
        for stock in report.rs_leaders[:15]:
            rs_table.append({
                "Stock": stock.ticker,
                "Sector": stock.sector,
                "Price": f"₹{stock.current_price:.0f}",
                "1W": f"{stock.week_change_pct:+.1f}%",
                "2W": f"{stock.two_week_change_pct:+.1f}%",
                "4W": f"{stock.four_week_change_pct:+.1f}%",
                "6W": f"{stock.month_change_pct:+.1f}%",
                "Trend": f"{stock.weekly_trend.capitalize()} ({getattr(stock, 'trend_strength', 'moderate').capitalize()})",
                "RS vs NIFTY": f"{stock.relative_strength:+.1f}%",
                "RSI": f"{stock.rsi:.0f}",
                "Bias": stock.technical_bias
            })

        st.dataframe(pd.DataFrame(rs_table), hide_index=True, use_container_width=True)
    else:
        st.info("No relative strength data available")


# Footer
st.markdown("---")
st.caption(f"Report generated: {report.report_date.strftime('%d %b %Y, %H:%M')} | Data from yfinance")
