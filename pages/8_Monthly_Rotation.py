"""
Monthly Sector Rotation Dashboard

Helps identify:
- Which sectors are gaining/losing momentum
- Sector rotation patterns
- Best sectors to be in this month
- Money flow between sectors
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Monthly Rotation - Stock Analyzer",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 Monthly Sector Rotation")
st.markdown("*Follow the money - monthly sector trends and rotation signals*")

# Import after page config
from sector_tracker import (
    analyze_all_sectors,
    get_sector_rotation_signals,
    SectorMetrics
)


# Cache sector analysis
@st.cache_data(ttl=1800)  # 30 min cache
def get_sector_data():
    return analyze_all_sectors(max_workers=5)


# Sidebar
st.sidebar.header("Settings")

if st.sidebar.button("🔄 Refresh Data", type="primary"):
    st.cache_data.clear()

timeframe = st.sidebar.selectbox(
    "Analysis Timeframe",
    ["Short-term (5D)", "Medium-term (20D)", "Long-term (60D)"],
    index=1
)


# Load data
with st.spinner("Analyzing sectors..."):
    sectors = get_sector_data()
    rotation_signals = get_sector_rotation_signals(sectors)


# Overview metrics
st.subheader("Market Overview")

col1, col2, col3, col4 = st.columns(4)

# Calculate market stats
bullish_sectors = len([s for s in sectors if s.momentum_trend == "gaining"])
bearish_sectors = len([s for s in sectors if s.momentum_trend == "losing"])
neutral_sectors = len([s for s in sectors if s.momentum_trend == "stable"])

avg_momentum = sum(s.momentum_score for s in sectors) / len(sectors) if sectors else 0

with col1:
    st.metric("Bullish Sectors", bullish_sectors, delta=None)

with col2:
    st.metric("Bearish Sectors", bearish_sectors, delta=None)

with col3:
    st.metric("Avg Momentum", f"{avg_momentum:.0f}", delta=None)

with col4:
    market_bias = "Bullish" if bullish_sectors > bearish_sectors else "Bearish" if bearish_sectors > bullish_sectors else "Neutral"
    st.metric("Market Bias", market_bias)


# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Sector Rankings",
    "🔄 Rotation Signals",
    "📈 Performance Matrix",
    "🎯 Trade Ideas"
])


with tab1:
    st.subheader("Sector Performance Rankings")

    # Select timeframe column
    if "Short" in timeframe:
        sort_col = "avg_return_5d"
        display_col = "5D Return"
    elif "Long" in timeframe:
        sort_col = "avg_return_60d"
        display_col = "60D Return"
    else:
        sort_col = "avg_return_20d"
        display_col = "20D Return"

    # Sort sectors
    sorted_sectors = sorted(sectors, key=lambda x: getattr(x, sort_col), reverse=True)

    # Create ranking table
    ranking_data = []
    for i, s in enumerate(sorted_sectors, 1):
        ranking_data.append({
            "Rank": i,
            "Sector": s.sector,
            "1D": f"{s.avg_return_1d:+.1f}%",
            "5D": f"{s.avg_return_5d:+.1f}%",
            "20D": f"{s.avg_return_20d:+.1f}%",
            "60D": f"{s.avg_return_60d:+.1f}%",
            "Momentum": f"{s.momentum_score:.0f}",
            "Trend": s.momentum_trend,
            "Avg RSI": f"{s.avg_rsi:.0f}"
        })

    df = pd.DataFrame(ranking_data)

    # Color code the trend
    def highlight_trend(val):
        if val == "gaining":
            return "background-color: #90EE90"
        elif val == "losing":
            return "background-color: #FFB6C1"
        return ""

    st.dataframe(df, hide_index=True, use_container_width=True)

    # Bar chart
    fig = px.bar(
        df,
        x="Sector",
        y=[float(x.replace('%', '').replace('+', '')) for x in df[display_col.split()[0] + "D"]],
        color=[float(x.replace('%', '').replace('+', '')) for x in df[display_col.split()[0] + "D"]],
        color_continuous_scale="RdYlGn",
        title=f"Sector Performance ({display_col})"
    )
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


with tab2:
    st.subheader("Rotation Signals")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🚀 Sectors Gaining Momentum")
        gaining = [s for s in sectors if s.momentum_trend == "gaining"]
        gaining = sorted(gaining, key=lambda x: x.momentum_score, reverse=True)

        if gaining:
            for s in gaining:
                with st.container():
                    cols = st.columns([2, 1, 1, 1])
                    cols[0].markdown(f"**{s.sector}**")
                    cols[1].metric("Momentum", f"{s.momentum_score:.0f}")
                    cols[2].metric("5D", f"{s.avg_return_5d:+.1f}%")
                    cols[3].metric("RSI", f"{s.avg_rsi:.0f}")

                    # Show top stocks
                    if s.top_stocks:
                        top_tickers = [t[0] for t in s.top_stocks[:3]]
                        st.caption(f"Leaders: {', '.join(top_tickers)}")
                    st.markdown("---")
        else:
            st.info("No sectors currently gaining momentum")

    with col2:
        st.markdown("### 📉 Sectors Losing Momentum")
        losing = [s for s in sectors if s.momentum_trend == "losing"]
        losing = sorted(losing, key=lambda x: x.momentum_score)

        if losing:
            for s in losing:
                with st.container():
                    cols = st.columns([2, 1, 1, 1])
                    cols[0].markdown(f"**{s.sector}**")
                    cols[1].metric("Momentum", f"{s.momentum_score:.0f}")
                    cols[2].metric("5D", f"{s.avg_return_5d:+.1f}%")
                    cols[3].metric("RSI", f"{s.avg_rsi:.0f}")

                    # Show bottom stocks
                    if s.bottom_stocks:
                        bottom_tickers = [t[0] for t in s.bottom_stocks[:3]]
                        st.caption(f"Laggards: {', '.join(bottom_tickers)}")
                    st.markdown("---")
        else:
            st.info("No sectors currently losing momentum")

    # Rotation signals from sector_tracker
    st.markdown("---")
    st.markdown("### 📊 Rotation Analysis")

    if rotation_signals and isinstance(rotation_signals, dict):
        # Show recommendations
        recommendations = rotation_signals.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                if "ROTATE INTO" in rec:
                    st.success(f"✅ {rec}")
                elif "ROTATE OUT" in rec:
                    st.warning(f"⚠️ {rec}")
                else:
                    st.info(f"💡 {rec}")

        # Show gaining momentum sectors
        gaining = rotation_signals.get("gaining_momentum", [])
        if gaining:
            st.markdown("**Gaining Momentum:**")
            for sector, score, ret in gaining:
                st.markdown(f"- {sector}: Momentum {score:.0f}, 5D Return {ret:+.1f}%")

        # Show losing momentum sectors
        losing = rotation_signals.get("losing_momentum", [])
        if losing:
            st.markdown("**Losing Momentum:**")
            for sector, score, ret in losing:
                st.markdown(f"- {sector}: Momentum {score:.0f}, 5D Return {ret:+.1f}%")

        if not recommendations and not gaining and not losing:
            st.info("No significant rotation signals detected")
    else:
        st.info("No significant rotation signals detected")


with tab3:
    st.subheader("Sector Performance Matrix")

    # Create performance matrix
    matrix_data = []
    for s in sectors:
        matrix_data.append({
            "Sector": s.sector,
            "1D": s.avg_return_1d,
            "5D": s.avg_return_5d,
            "20D": s.avg_return_20d,
            "60D": s.avg_return_60d
        })

    matrix_df = pd.DataFrame(matrix_data)

    # Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=matrix_df[["1D", "5D", "20D", "60D"]].values,
        x=["1D", "5D", "20D", "60D"],
        y=matrix_df["Sector"].tolist(),
        colorscale="RdYlGn",
        text=[[f"{v:.1f}%" for v in row] for row in matrix_df[["1D", "5D", "20D", "60D"]].values],
        texttemplate="%{text}",
        textfont={"size": 12},
        hovertemplate="Sector: %{y}<br>Timeframe: %{x}<br>Return: %{z:.2f}%<extra></extra>"
    ))

    fig.update_layout(
        title="Sector Returns Heatmap",
        height=500,
        yaxis=dict(tickmode='array', tickvals=list(range(len(matrix_df))), ticktext=matrix_df["Sector"].tolist())
    )

    st.plotly_chart(fig, use_container_width=True)

    # Momentum vs RSI scatter
    st.markdown("### Momentum vs RSI")

    scatter_data = {
        "Sector": [s.sector for s in sectors],
        "Momentum": [s.momentum_score for s in sectors],
        "RSI": [s.avg_rsi for s in sectors],
        "5D Return": [s.avg_return_5d for s in sectors]
    }

    fig = px.scatter(
        scatter_data,
        x="RSI",
        y="Momentum",
        text="Sector",
        size=[abs(r) + 1 for r in scatter_data["5D Return"]],
        color="5D Return",
        color_continuous_scale="RdYlGn"
    )

    # Add quadrant lines
    fig.add_hline(y=50, line_dash="dash", line_color="gray")
    fig.add_vline(x=50, line_dash="dash", line_color="gray")

    fig.update_traces(textposition='top center')
    fig.update_layout(height=500)

    # Add annotations for quadrants
    fig.add_annotation(x=75, y=75, text="Overbought & Strong", showarrow=False, font=dict(size=10, color="green"))
    fig.add_annotation(x=25, y=75, text="Oversold & Strong", showarrow=False, font=dict(size=10, color="blue"))
    fig.add_annotation(x=25, y=25, text="Oversold & Weak", showarrow=False, font=dict(size=10, color="orange"))
    fig.add_annotation(x=75, y=25, text="Overbought & Weak", showarrow=False, font=dict(size=10, color="red"))

    st.plotly_chart(fig, use_container_width=True)

    st.caption("""
    **Interpretation:**
    - Top Right: Strong momentum but overbought - potential pullback
    - Top Left: Strong momentum and oversold - best buying opportunity
    - Bottom Left: Weak and oversold - avoid or wait for reversal
    - Bottom Right: Weak but overbought - potential short candidates
    """)


with tab4:
    st.subheader("🎯 Sector-Based Trade Ideas")

    # Best sectors to be long
    st.markdown("### ✅ Best Sectors for Longs (This Month)")

    best_sectors = sorted(sectors, key=lambda x: (x.momentum_score, x.avg_return_5d), reverse=True)[:3]

    for s in best_sectors:
        with st.expander(f"🔥 {s.sector}", expanded=True):
            cols = st.columns(4)
            cols[0].metric("Momentum Score", f"{s.momentum_score:.0f}/100")
            cols[1].metric("5D Return", f"{s.avg_return_5d:+.1f}%")
            cols[2].metric("Trend", s.momentum_trend)
            cols[3].metric("Avg RSI", f"{s.avg_rsi:.0f}")

            st.markdown("**Why this sector?**")
            reasons = []
            if s.momentum_score >= 60:
                reasons.append("Strong momentum score")
            if s.avg_return_5d > 0:
                reasons.append("Positive short-term returns")
            if s.momentum_trend == "gaining":
                reasons.append("Momentum is accelerating")
            if 40 <= s.avg_rsi <= 60:
                reasons.append("RSI in healthy range")

            for r in reasons:
                st.markdown(f"- {r}")

            st.markdown("**Top Stocks to Consider:**")
            if s.top_stocks:
                for ticker, ret in s.top_stocks[:5]:
                    st.markdown(f"- **{ticker}**: {ret:+.1f}% (5D)")

    # Sectors to avoid
    st.markdown("---")
    st.markdown("### ⚠️ Sectors to Avoid")

    worst_sectors = sorted(sectors, key=lambda x: (x.momentum_score, x.avg_return_5d))[:3]

    for s in worst_sectors:
        with st.expander(f"❄️ {s.sector}", expanded=False):
            cols = st.columns(4)
            cols[0].metric("Momentum Score", f"{s.momentum_score:.0f}/100")
            cols[1].metric("5D Return", f"{s.avg_return_5d:+.1f}%")
            cols[2].metric("Trend", s.momentum_trend)
            cols[3].metric("Avg RSI", f"{s.avg_rsi:.0f}")

            st.markdown("**Weakest Stocks:**")
            if s.bottom_stocks:
                for ticker, ret in s.bottom_stocks[:5]:
                    st.markdown(f"- **{ticker}**: {ret:+.1f}% (5D)")

    # Oversold sectors for contrarian plays
    st.markdown("---")
    st.markdown("### 🔄 Oversold Sectors (Contrarian Opportunity)")

    oversold_sectors = [s for s in sectors if s.avg_rsi < 40]
    oversold_sectors = sorted(oversold_sectors, key=lambda x: x.avg_rsi)

    if oversold_sectors:
        for s in oversold_sectors:
            st.info(f"**{s.sector}** - RSI: {s.avg_rsi:.0f} - May be due for a bounce if market stabilizes")
    else:
        st.success("No sectors currently oversold - market is healthy")


# Footer
st.markdown("---")
st.caption(f"Analysis generated: {datetime.now().strftime('%d %b %Y, %H:%M')} | Sectors analyzed: {len(sectors)}")
