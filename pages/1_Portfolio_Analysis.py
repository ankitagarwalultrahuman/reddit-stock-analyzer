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
        use_container_width=True,
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
        st.plotly_chart(fig, use_container_width=True)


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
    """Render mutual fund underlying stocks analysis."""
    st.subheader("📊 Mutual Fund Underlying Analysis")

    mf_name = st.text_input(
        "Enter Mutual Fund Name",
        placeholder="e.g., Nifty 50 Index Fund, Large Cap Fund",
        help="Enter the name of your mutual fund to see sentiment of its underlying stocks"
    )

    if mf_name:
        underlying = get_mf_underlying_stocks(mf_name)

        st.write(f"**Analyzing {len(underlying)} underlying stocks for:** {mf_name}")

        # Parse sentiment from report
        from dashboard_analytics import parse_key_insights_structured, parse_stock_mentions

        insights = parse_key_insights_structured(report_content)
        stocks = parse_stock_mentions(report_content)

        discussed = {}
        for i in insights + stocks:
            ticker = normalize_ticker(i.get("ticker", ""))
            if ticker not in discussed:
                discussed[ticker] = {
                    "sentiment": i.get("sentiment", "neutral"),
                    "mentions": i.get("total_mentions", 0),
                }

        # Analyze underlying stocks
        mf_analysis = []
        for stock in underlying:
            normalized = normalize_ticker(stock)
            if normalized in discussed:
                mf_analysis.append({
                    "Stock": stock,
                    "Sentiment": discussed[normalized]["sentiment"].capitalize(),
                    "Mentions": discussed[normalized]["mentions"],
                    "Status": "Discussed"
                })
            else:
                mf_analysis.append({
                    "Stock": stock,
                    "Sentiment": "-",
                    "Mentions": 0,
                    "Status": "Not Discussed"
                })

        df = pd.DataFrame(mf_analysis)

        # Summary
        discussed_count = len([x for x in mf_analysis if x["Status"] == "Discussed"])
        bullish_count = len([x for x in mf_analysis if x["Sentiment"] == "Bullish"])
        bearish_count = len([x for x in mf_analysis if x["Sentiment"] == "Bearish"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Stocks", len(underlying))
        col2.metric("Discussed", discussed_count)
        col3.metric("Bullish", bullish_count)
        col4.metric("Bearish", bearish_count)

        # Show table
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Overall assessment
        if bearish_count > bullish_count:
            st.warning(f"⚠️ More bearish sentiment ({bearish_count}) than bullish ({bullish_count}) among discussed stocks")
        elif bullish_count > bearish_count:
            st.success(f"✅ More bullish sentiment ({bullish_count}) than bearish ({bearish_count}) among discussed stocks")
        else:
            st.info("ℹ️ Mixed sentiment among underlying stocks")


def main():
    """Main portfolio analysis page."""
    render_header()

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

        # Show manual portfolio option
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

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Equity Holdings", "📈 Mutual Funds", "⚙️ Manual Entry"])

    with tab1:
        st.subheader("Equity Holdings vs Reddit Sentiment")

        # Debug: Show configuration status
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
                    # Get summary
                    try:
                        summary = get_portfolio_summary(holdings)
                        render_portfolio_summary(summary)
                    except Exception as e:
                        st.error(f"Error rendering portfolio summary: {e}")
                        import traceback
                        st.code(traceback.format_exc())

                    st.markdown("---")

                    # Analyze against sentiment
                    try:
                        analyzed = analyze_holdings_against_sentiment(holdings, report_content)
                    except Exception as e:
                        st.error(f"Error analyzing holdings: {e}")
                        import traceback
                        st.code(traceback.format_exc())
                        analyzed = []

                    if analyzed:
                        # Layout
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.subheader("Holdings Analysis")
                            try:
                                render_holdings_table(analyzed)
                            except Exception as e:
                                st.error(f"Error rendering holdings table: {e}")
                                import traceback
                                st.code(traceback.format_exc())

                        with col2:
                            st.subheader("Sentiment Split")
                            try:
                                render_sentiment_chart(analyzed)
                            except Exception as e:
                                st.error(f"Error rendering sentiment chart: {e}")
                                import traceback
                                st.code(traceback.format_exc())

                        st.markdown("---")

                        # Risk alerts
                        try:
                            render_risk_alerts(analyzed)
                        except Exception as e:
                            st.error(f"Error rendering risk alerts: {e}")
                            import traceback
                            st.code(traceback.format_exc())

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
                import traceback
                st.code(traceback.format_exc())
                st.write("Try the manual entry option instead.")

    with tab2:
        render_mf_analysis(report_content)

    with tab3:
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
