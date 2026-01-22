"""
Sector Rotation Dashboard Page

Track sector momentum and rotation signals across the Indian market.
Identify which sectors are gaining/losing strength for allocation decisions.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config import DASHBOARD_CACHE_TTL

# Page config
st.set_page_config(
    page_title="Sector Rotation - Stock Analyzer",
    page_icon="",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .sector-gaining {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 0.75rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 0.5rem;
    }
    .sector-losing {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 0.75rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 0.5rem;
    }
    .sector-neutral {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.75rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)  # 10 minute cache
def get_sector_analysis():
    """Get sector analysis with caching."""
    from sector_tracker import analyze_all_sectors, get_sector_rotation_signals
    metrics = analyze_all_sectors()
    signals = get_sector_rotation_signals(metrics)
    return metrics, signals


def create_momentum_chart(metrics):
    """Create sector momentum bar chart."""
    data = [{
        "Sector": m.sector,
        "Momentum": m.momentum_score,
        "Trend": m.momentum_trend,
    } for m in metrics]

    df = pd.DataFrame(data)

    colors = {
        "gaining": "#00c853",
        "losing": "#ff1744",
        "neutral": "#9e9e9e"
    }

    fig = px.bar(
        df,
        x="Sector",
        y="Momentum",
        color="Trend",
        color_discrete_map=colors,
        title="Sector Momentum Scores",
    )

    fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Neutral")
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=True,
    )

    return fig


def create_returns_heatmap(metrics):
    """Create sector returns heatmap."""
    data = [{
        "Sector": m.sector,
        "1D": m.avg_return_1d,
        "5D": m.avg_return_5d,
        "20D": m.avg_return_20d,
    } for m in metrics]

    df = pd.DataFrame(data).set_index("Sector")

    fig = px.imshow(
        df,
        labels=dict(x="Period", y="Sector", color="Return %"),
        color_continuous_scale="RdYlGn",
        aspect="auto",
        title="Sector Returns Heatmap",
    )

    fig.update_layout(height=500)
    return fig


def create_rsi_gauge(avg_rsi: float, sector: str):
    """Create RSI gauge for a sector."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_rsi,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': sector},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "lightgreen"},
                {'range': [30, 70], 'color': "lightyellow"},
                {'range': [70, 100], 'color': "lightcoral"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': avg_rsi
            }
        }
    ))

    fig.update_layout(height=200, margin=dict(t=50, b=0, l=20, r=20))
    return fig


def main():
    st.title("Sector Rotation Tracker")
    st.markdown("*Track which sectors are gaining/losing momentum for allocation decisions*")

    # Refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()

    # Load data
    with st.spinner("Analyzing all sectors... This may take a minute."):
        try:
            metrics, signals = get_sector_analysis()
        except Exception as e:
            st.error(f"Error loading sector data: {e}")
            return

    if not metrics:
        st.warning("No sector data available. Please try again.")
        return

    # Last updated
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M IST')}")

    # Summary metrics
    st.subheader("Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    gaining = [m for m in metrics if m.momentum_trend == "gaining"]
    losing = [m for m in metrics if m.momentum_trend == "losing"]
    neutral = [m for m in metrics if m.momentum_trend == "neutral"]

    with col1:
        st.metric("Sectors Gaining", len(gaining), delta=f"{len(gaining)} bullish")
    with col2:
        st.metric("Sectors Losing", len(losing), delta=f"-{len(losing)}" if losing else "0")
    with col3:
        st.metric("Sectors Neutral", len(neutral))
    with col4:
        top_sector = metrics[0] if metrics else None
        st.metric("Top Sector", top_sector.sector if top_sector else "N/A",
                 delta=f"+{top_sector.avg_return_5d}%" if top_sector else None)

    st.markdown("---")

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Rotation Signals", "Sector Rankings", "Heatmap", "Sector Details"])

    with tab1:
        st.subheader("Rotation Signals")

        # Recommendations
        recommendations = signals.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                if "ROTATE INTO" in rec:
                    st.markdown(f'<div class="sector-gaining">{rec}</div>', unsafe_allow_html=True)
                elif "ROTATE OUT" in rec:
                    st.markdown(f'<div class="sector-losing">{rec}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="sector-neutral">{rec}</div>', unsafe_allow_html=True)
        else:
            st.info("No strong rotation signals at this time.")

        st.markdown("---")

        # Sectors by momentum
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Gaining Momentum")
            gaining_data = signals.get("gaining_momentum", [])
            if gaining_data:
                for sector, score, ret in gaining_data:
                    st.markdown(f"**{sector}**")
                    st.write(f"  Momentum: {score:.0f} | 5D Return: {ret:+.1f}%")
            else:
                st.info("No sectors gaining momentum")

        with col2:
            st.markdown("### Losing Momentum")
            losing_data = signals.get("losing_momentum", [])
            if losing_data:
                for sector, score, ret in losing_data:
                    st.markdown(f"**{sector}**")
                    st.write(f"  Momentum: {score:.0f} | 5D Return: {ret:+.1f}%")
            else:
                st.info("No sectors losing momentum")

        # Oversold/Overbought
        st.markdown("---")
        col3, col4 = st.columns(2)

        with col3:
            st.markdown("### Oversold Sectors (Potential Bounce)")
            oversold = signals.get("oversold_sectors", [])
            if oversold:
                for sector, rsi in oversold:
                    st.write(f"- {sector}: RSI {rsi:.1f}")
            else:
                st.info("No oversold sectors")

        with col4:
            st.markdown("### Overbought Sectors (Caution)")
            overbought = signals.get("overbought_sectors", [])
            if overbought:
                for sector, rsi in overbought:
                    st.write(f"- {sector}: RSI {rsi:.1f}")
            else:
                st.info("No overbought sectors")

    with tab2:
        st.subheader("Sector Rankings")

        # Momentum chart
        fig = create_momentum_chart(metrics)
        st.plotly_chart(fig, use_container_width=True)

        # Rankings table
        st.markdown("### Full Rankings")

        data = []
        for i, m in enumerate(metrics, 1):
            trend_emoji = "" if m.momentum_trend == "gaining" else "" if m.momentum_trend == "losing" else ""
            data.append({
                "Rank": i,
                "Sector": m.sector,
                "Momentum": f"{m.momentum_score:.0f}",
                "Trend": f"{m.momentum_trend} {trend_emoji}",
                "1D %": f"{m.avg_return_1d:+.2f}%",
                "5D %": f"{m.avg_return_5d:+.2f}%",
                "20D %": f"{m.avg_return_20d:+.2f}%",
                "Avg RSI": f"{m.avg_rsi:.1f}",
                "Bullish": m.bullish_count,
                "Bearish": m.bearish_count,
            })

        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Returns Heatmap")

        fig = create_returns_heatmap(metrics)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **How to read:**
        - Green = Positive returns
        - Red = Negative returns
        - Look for sectors that are green across all timeframes (consistent performers)
        - Red in short-term but green in long-term = potential mean reversion opportunity
        """)

    with tab4:
        st.subheader("Sector Details")

        selected_sector = st.selectbox(
            "Select a sector for detailed view",
            [m.sector for m in metrics]
        )

        if selected_sector:
            sector_data = next((m for m in metrics if m.sector == selected_sector), None)

            if sector_data:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"### {selected_sector}")

                    # Key metrics
                    st.metric("Momentum Score", f"{sector_data.momentum_score:.0f}/100")
                    st.metric("5-Day Return", f"{sector_data.avg_return_5d:+.2f}%")
                    st.metric("Average RSI", f"{sector_data.avg_rsi:.1f}")

                    # Technical bias
                    st.markdown("**Stock Biases:**")
                    st.write(f"- Bullish: {sector_data.bullish_count}")
                    st.write(f"- Bearish: {sector_data.bearish_count}")
                    st.write(f"- Neutral: {sector_data.neutral_count}")

                with col2:
                    # RSI gauge
                    fig = create_rsi_gauge(sector_data.avg_rsi, selected_sector)
                    st.plotly_chart(fig, use_container_width=True)

                # Top performers in sector
                st.markdown("### Top Performers")
                if sector_data.top_stocks:
                    for ticker, ret in sector_data.top_stocks:
                        st.write(f"- {ticker}: {ret:+.1f}%")

                st.markdown("### Worst Performers")
                if sector_data.bottom_stocks:
                    for ticker, ret in sector_data.bottom_stocks:
                        st.write(f"- {ticker}: {ret:+.1f}%")

    # Sidebar - Quick Actions
    st.sidebar.header("Quick Actions")

    if st.sidebar.button("Send to Telegram", use_container_width=True):
        from telegram_alerts import send_sector_alert, is_telegram_configured
        if is_telegram_configured():
            if send_sector_alert(signals):
                st.sidebar.success("Sent to Telegram!")
            else:
                st.sidebar.error("Failed to send")
        else:
            st.sidebar.warning("Telegram not configured")

    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **Sector Rotation Strategy:**
    1. Rotate into gaining momentum sectors
    2. Reduce exposure to losing momentum sectors
    3. Consider oversold sectors for contrarian plays
    4. Watch overbought sectors for potential corrections
    """)


if __name__ == "__main__":
    main()
