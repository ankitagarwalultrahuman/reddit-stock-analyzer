"""Portfolio Analysis Page - Compare your holdings against Reddit sentiment."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from groww_integration import (
    GrowwClient,
    get_portfolio_summary,
    analyze_holdings_against_sentiment,
    get_mf_underlying_stocks,
    load_mf_portfolio,
    save_mf_portfolio,
    add_mf_holding,
    remove_mf_holding,
    analyze_mf_against_sentiment,
    MF_CATEGORY_HOLDINGS,
)
from dashboard_analytics import get_available_dates, get_report_for_date
from portfolio_analyzer import normalize_ticker

# Page config
st.set_page_config(
    page_title="Portfolio Analysis | Reddit Stock Analyzer",
    page_icon="💼",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .portfolio-header {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .metric-card {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #3b82f6;
    }
    .metric-card-profit {
        border-left-color: #10b981;
        background: #f0fdf4;
    }
    .metric-card-loss {
        border-left-color: #ef4444;
        background: #fef2f2;
    }
    .risk-high { color: #dc2626; font-weight: 700; }
    .risk-medium { color: #f59e0b; font-weight: 700; }
    .risk-low { color: #10b981; font-weight: 700; }
    .sentiment-bullish { color: #10b981; font-weight: 700; }
    .sentiment-bearish { color: #dc2626; font-weight: 700; }
    .sentiment-neutral { color: #6b7280; font-weight: 700; }
    .action-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .action-hold { background: #dbeafe; color: #1d4ed8; }
    .action-review { background: #fef3c7; color: #92400e; }
    .action-exit { background: #fee2e2; color: #991b1b; }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render portfolio page header."""
    st.markdown("""
    <div class="portfolio-header">
        <h1>💼 Portfolio Analysis</h1>
        <p>Compare your Groww holdings against Reddit market sentiment</p>
    </div>
    """, unsafe_allow_html=True)


def render_portfolio_summary(summary: dict):
    """Render portfolio summary metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Invested",
            f"₹{summary['total_invested']:,.0f}",
        )

    with col2:
        st.metric(
            "Current Value",
            f"₹{summary['total_current']:,.0f}",
        )

    with col3:
        pnl_color = "green" if summary['total_pnl'] >= 0 else "red"
        st.metric(
            "Total P&L",
            f"₹{summary['total_pnl']:,.0f}",
            f"{summary['pnl_percent']:.2f}%",
            delta_color="normal" if summary['total_pnl'] >= 0 else "inverse"
        )

    with col4:
        st.metric(
            "Holdings",
            f"{summary['holdings_count']}",
            f"📈 {summary['profitable_count']} | 📉 {summary['loss_count']}"
        )


def render_holdings_table(analyzed_holdings: list):
    """Render holdings table with sentiment analysis."""
    if not analyzed_holdings:
        st.warning("No holdings to display")
        return

    # Convert to DataFrame for display
    df = pd.DataFrame(analyzed_holdings)

    # Format columns
    df["P&L"] = df["pnl"].apply(lambda x: f"₹{x:,.0f}" if x != 0 else "-")
    df["P&L %"] = df["pnl_percent"].apply(lambda x: f"{x:.2f}%" if x != 0 else "-")
    df["Avg Price"] = df["average_price"].apply(lambda x: f"₹{x:,.2f}")
    df["Current"] = df["current_price"].apply(lambda x: f"₹{x:,.2f}" if x > 0 else "N/A")
    df["Invested"] = df["invested_value"].apply(lambda x: f"₹{x:,.0f}")

    # Add sentiment badge
    def sentiment_badge(row):
        sentiment = row.get("sentiment", "unknown")
        if sentiment == "bullish":
            return "🟢 Bullish"
        elif sentiment == "bearish":
            return "🔴 Bearish"
        elif sentiment == "not_discussed":
            return "⚪ Not Discussed"
        else:
            return "🟡 Neutral"

    df["Sentiment"] = df.apply(sentiment_badge, axis=1)

    # Add risk level
    def risk_badge(row):
        risk = row.get("risk_level", "UNKNOWN")
        if risk == "HIGH":
            return "🔴 HIGH"
        elif risk == "MEDIUM":
            return "🟡 MEDIUM"
        elif risk == "LOW":
            return "🟢 LOW"
        else:
            return "⚪ UNKNOWN"

    df["Risk"] = df.apply(risk_badge, axis=1)

    # Select and order columns for display
    display_cols = [
        "trading_symbol", "quantity", "Avg Price", "Current",
        "Invested", "P&L", "P&L %", "Sentiment", "mentions", "Risk", "action"
    ]

    display_df = df[display_cols].copy()
    display_df.columns = [
        "Stock", "Qty", "Avg Price", "Current Price",
        "Invested", "P&L", "P&L %", "Sentiment", "Mentions", "Risk", "Action"
    ]

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Stock": st.column_config.TextColumn("Stock", width="medium"),
            "Mentions": st.column_config.NumberColumn("Reddit Mentions", width="small"),
            "Action": st.column_config.TextColumn("Recommendation", width="large"),
        }
    )


def render_sentiment_chart(analyzed_holdings: list):
    """Render sentiment distribution pie chart."""
    if not analyzed_holdings:
        return

    sentiment_counts = {
        "Bullish": 0,
        "Bearish": 0,
        "Neutral": 0,
        "Not Discussed": 0
    }

    for h in analyzed_holdings:
        sentiment = h.get("sentiment", "neutral")
        if sentiment == "bullish":
            sentiment_counts["Bullish"] += 1
        elif sentiment == "bearish":
            sentiment_counts["Bearish"] += 1
        elif sentiment == "not_discussed":
            sentiment_counts["Not Discussed"] += 1
        else:
            sentiment_counts["Neutral"] += 1

    df = pd.DataFrame([
        {"Sentiment": k, "Count": v}
        for k, v in sentiment_counts.items() if v > 0
    ])

    if not df.empty:
        fig = px.pie(
            df,
            values="Count",
            names="Sentiment",
            color="Sentiment",
            color_discrete_map={
                "Bullish": "#10b981",
                "Bearish": "#ef4444",
                "Neutral": "#f59e0b",
                "Not Discussed": "#6b7280"
            },
            hole=0.4
        )
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=True
        )
        st.plotly_chart(fig, width="stretch")


def render_risk_alerts(analyzed_holdings: list):
    """Render risk alerts for holdings with issues."""
    alerts = [h for h in analyzed_holdings if h.get("alert") or h.get("sentiment") == "bearish"]

    if not alerts:
        st.success("✅ No major risk alerts for your portfolio")
        return

    st.subheader("⚠️ Risk Alerts")

    for alert in alerts:
        with st.expander(f"🚨 {alert['trading_symbol']}", expanded=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(f"**Sentiment:** {alert.get('sentiment', 'unknown').capitalize()}")
                st.write(f"**Reddit Mentions:** {alert.get('mentions', 0)}")

                if alert.get("key_points"):
                    st.write(f"**Community Says:** {alert['key_points']}")

                if alert.get("alert_reason"):
                    st.error(f"⚠️ {alert['alert_reason']}")

            with col2:
                pnl = alert.get("pnl", 0)
                pnl_pct = alert.get("pnl_percent", 0)

                if pnl < 0:
                    st.metric("Your P&L", f"₹{pnl:,.0f}", f"{pnl_pct:.2f}%", delta_color="inverse")
                else:
                    st.metric("Your P&L", f"₹{pnl:,.0f}", f"{pnl_pct:.2f}%")

            st.write(f"**Recommendation:** {alert.get('action', 'Monitor')}")


def render_mf_analysis(report_content: str):
    """Render mutual fund holdings and analysis."""
    st.subheader("📈 Your Mutual Fund Holdings")

    # Load existing MF holdings
    mf_holdings = load_mf_portfolio()

    # Add new MF form
    with st.expander("➕ Add Mutual Fund Holding", expanded=not mf_holdings):
        with st.form("add_mf_holding"):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                mf_name = st.text_input(
                    "Mutual Fund Name",
                    placeholder="e.g., Axis Bluechip Fund, SBI Small Cap",
                    help="Enter the name of your mutual fund"
                )
            with col2:
                invested_amount = st.number_input(
                    "Invested Amount (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0
                )
            with col3:
                current_value = st.number_input(
                    "Current Value (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Leave 0 to use invested amount"
                )

            submitted = st.form_submit_button("Add Mutual Fund")

            if submitted and mf_name and invested_amount > 0:
                add_mf_holding(mf_name, invested_amount, current_value)
                st.success(f"Added {mf_name} to your MF portfolio!")
                st.rerun()

    if not mf_holdings:
        st.info("No mutual fund holdings added yet. Add your MF investments above to analyze them against Reddit sentiment.")

        # Show available fund categories for reference
        with st.expander("📚 Supported Fund Categories"):
            st.write("The system recognizes and maps these fund types to their typical underlying stocks:")
            categories = [
                "**Nifty 50 Index Funds** - UTI, HDFC, SBI, ICICI Nifty 50",
                "**Large Cap / Bluechip** - Mirae, Axis, SBI Bluechip",
                "**Mid Cap Funds** - Axis, Kotak, PGIM Midcap",
                "**Small Cap Funds** - Axis, SBI, Nippon Small Cap",
                "**Flexi Cap / Multi Cap** - Parag Parikh, UTI Flexi Cap",
                "**IT / Technology Funds** - ICICI, Tata Digital India",
                "**Banking & Financial** - ICICI, SBI Banking",
                "**Pharma / Healthcare** - SBI Healthcare, Nippon Pharma",
                "**Infrastructure** - ICICI, SBI Infra",
            ]
            for cat in categories:
                st.write(f"• {cat}")
        return

    # Analyze MF holdings against sentiment
    analyzed_mf = analyze_mf_against_sentiment(mf_holdings, report_content)

    # Portfolio Summary
    total_invested = sum(mf["invested_amount"] for mf in analyzed_mf)
    total_current = sum(mf["current_value"] for mf in analyzed_mf)
    total_pnl = total_current - total_invested
    pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Invested", f"₹{total_invested:,.0f}")
    with col2:
        st.metric("Current Value", f"₹{total_current:,.0f}")
    with col3:
        st.metric("Total P&L", f"₹{total_pnl:,.0f}", f"{pnl_percent:.2f}%",
                  delta_color="normal" if total_pnl >= 0 else "inverse")
    with col4:
        st.metric("Funds", len(analyzed_mf))

    st.markdown("---")

    # MF Holdings Table
    st.subheader("Holdings Analysis")

    # Create summary dataframe
    mf_summary = []
    for mf in analyzed_mf:
        sentiment_emoji = {
            "bullish": "🟢",
            "slightly_bullish": "🟢",
            "bearish": "🔴",
            "slightly_bearish": "🔴",
            "neutral": "🟡"
        }.get(mf["overall_sentiment"], "⚪")

        risk_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(mf["risk_level"], "⚪")

        mf_summary.append({
            "Fund Name": mf["name"],
            "Category": mf["category"].replace("_", " ").title(),
            "Invested": f"₹{mf['invested_amount']:,.0f}",
            "Current": f"₹{mf['current_value']:,.0f}",
            "P&L": f"₹{mf['pnl']:,.0f}",
            "P&L %": f"{mf['pnl_percent']:.2f}%",
            "Sentiment": f"{sentiment_emoji} {mf['overall_sentiment'].replace('_', ' ').title()}",
            "Risk": f"{risk_emoji} {mf['risk_level']}",
            "Bullish": mf["bullish_count"],
            "Bearish": mf["bearish_count"],
        })

    df = pd.DataFrame(mf_summary)
    st.dataframe(df, width="stretch", hide_index=True)

    st.markdown("---")

    # Detailed analysis for each fund
    st.subheader("📊 Underlying Stocks Sentiment")

    for mf in analyzed_mf:
        with st.expander(f"📁 {mf['name']} ({mf['underlying_count']} stocks)", expanded=False):
            # Fund metrics
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Stocks Tracked", mf["underlying_count"])
            col2.metric("Bullish", mf["bullish_count"], delta_color="off")
            col3.metric("Bearish", mf["bearish_count"], delta_color="off")
            col4.metric("Neutral", mf["neutral_count"], delta_color="off")
            col5.metric("Not Discussed", mf["not_discussed_count"], delta_color="off")

            # Underlying stocks table
            underlying_df = pd.DataFrame(mf["underlying_analysis"])

            # Add emoji to sentiment
            def format_sentiment(s):
                if s == "bullish":
                    return "🟢 Bullish"
                elif s == "bearish":
                    return "🔴 Bearish"
                elif s == "not_discussed":
                    return "⚪ Not Discussed"
                else:
                    return "🟡 Neutral"

            underlying_df["Sentiment"] = underlying_df["sentiment"].apply(format_sentiment)
            underlying_df = underlying_df.rename(columns={
                "stock": "Stock",
                "mentions": "Reddit Mentions"
            })

            st.dataframe(
                underlying_df[["Stock", "Sentiment", "Reddit Mentions"]],
                width="stretch",
                hide_index=True
            )

            # Assessment
            if mf["bearish_count"] > mf["bullish_count"]:
                st.warning(f"⚠️ More bearish stocks ({mf['bearish_count']}) than bullish ({mf['bullish_count']})")
            elif mf["bullish_count"] > mf["bearish_count"]:
                st.success(f"✅ More bullish stocks ({mf['bullish_count']}) than bearish ({mf['bearish_count']})")

            # Delete button
            if st.button(f"🗑️ Remove {mf['name']}", key=f"del_{mf['name']}"):
                remove_mf_holding(mf["name"])
                st.success(f"Removed {mf['name']}")
                st.rerun()

    # Clear all button
    st.markdown("---")
    if st.button("🗑️ Clear All MF Holdings"):
        save_mf_portfolio([])
        st.success("All MF holdings cleared!")
        st.rerun()


def main():
    """Main portfolio analysis page."""
    # Force initial render with placeholder
    _ = st.empty()

    render_header()

    # Another render checkpoint
    _ = st.empty()

    # Check Groww API configuration
    client = GrowwClient()

    if not client.is_configured():
        st.warning("""
        ⚠️ **Groww API not configured**

        To use portfolio sync, add your Groww API credentials to `.env`:
        ```
        GROWW_API_TOKEN=your_jwt_token
        GROWW_API_SECRET=your_secret
        ```

        Get credentials from: https://groww.in/trade-api
        """)
        st.info("You can still use manual portfolio entry below.")

    # Get latest report
    available_dates = get_available_dates()
    if not available_dates:
        st.error("No analysis reports found. Run the analyzer first: `python main.py`")
        return

    latest_date = available_dates[0]
    report = get_report_for_date(latest_date)
    report_content = report.get("content", "") if report else ""

    st.caption(f"📅 Using report from: {latest_date.strftime('%B %d, %Y')}")

    # Render checkpoint before tabs
    _ = st.empty()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Equity Holdings", "📈 Mutual Funds", "⚙️ Manual Entry"])

    with tab1:
        # Render checkpoint
        _ = st.empty()
        st.subheader("Equity Holdings vs Reddit Sentiment")

        if not client.is_configured():
            st.error("""
            **Groww API credentials not found.**

            For Streamlit Cloud, add secrets in your app settings:
            ```
            GROWW_API_TOKEN = "your_jwt_token"
            GROWW_API_SECRET = "your_api_secret"
            ```

            For local development, add to `.env` file.
            """)

        # Fetch holdings
        with st.spinner("Fetching portfolio from Groww..."):
            try:
                holdings = client.get_holdings_with_prices()

                if holdings:
                    # Render checkpoint
                    _ = st.empty()

                    # Get summary
                    summary = get_portfolio_summary(holdings)
                    render_portfolio_summary(summary)

                    st.markdown("---")

                    # Analyze against sentiment
                    analyzed = analyze_holdings_against_sentiment(holdings, report_content)

                    if analyzed:
                        # Render checkpoint
                        _ = st.empty()

                        # Layout
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.subheader("Holdings Analysis")
                            render_holdings_table(analyzed)

                        with col2:
                            st.subheader("Sentiment Split")
                            render_sentiment_chart(analyzed)

                        st.markdown("---")

                        # Risk alerts
                        render_risk_alerts(analyzed)

                else:
                    st.info("No holdings found in your Groww account, or API connection failed.")
                    st.write("Try the manual entry option in the '⚙️ Manual Entry' tab.")

            except ImportError as e:
                st.error(f"Missing dependency: {e}")
                st.write("The `growwapi` package may not be installed. Try: `pip install growwapi`")
            except ValueError as e:
                st.error(f"Configuration error: {e}")
                st.write("Please check your Groww API credentials.")
            except Exception as e:
                st.error(f"Error fetching portfolio: {e}")
                st.write("Try the manual entry option instead.")

    with tab2:
        # Render checkpoint
        _ = st.empty()
        render_mf_analysis(report_content)

    with tab3:
        # Render checkpoint
        _ = st.empty()
        st.subheader("Manual Portfolio Entry")

        st.write("Add your holdings manually to analyze against Reddit sentiment.")

        with st.form("add_holding"):
            col1, col2, col3 = st.columns(3)

            with col1:
                ticker = st.text_input("Stock Symbol", placeholder="e.g., RELIANCE")
            with col2:
                quantity = st.number_input("Quantity", min_value=1, value=1)
            with col3:
                avg_price = st.number_input("Average Price (₹)", min_value=0.0, value=0.0)

            submitted = st.form_submit_button("Add Holding")

            if submitted and ticker:
                from portfolio_analyzer import add_holding, load_portfolio

                add_holding(ticker, quantity, avg_price)
                st.success(f"Added {ticker} to portfolio!")
                st.rerun()

        # Show manual portfolio
        from portfolio_analyzer import load_portfolio

        manual_holdings = load_portfolio()
        if manual_holdings:
            st.write("**Your Manual Portfolio:**")

            # Convert to Holding objects for analysis
            from groww_integration import Holding

            holdings = [
                Holding(
                    isin="",
                    trading_symbol=h["ticker"],
                    quantity=h["quantity"],
                    average_price=h["avg_price"],
                    invested_value=h["quantity"] * h["avg_price"]
                )
                for h in manual_holdings
            ]

            summary = get_portfolio_summary(holdings)
            render_portfolio_summary(summary)

            analyzed = analyze_holdings_against_sentiment(holdings, report_content)
            render_holdings_table(analyzed)

            # Clear button
            if st.button("Clear Manual Portfolio"):
                from portfolio_analyzer import save_portfolio
                save_portfolio([])
                st.success("Portfolio cleared!")
                st.rerun()


if __name__ == "__main__":
    main()
