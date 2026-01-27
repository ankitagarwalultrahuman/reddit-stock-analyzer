"""Summarizer module - uses Perplexity API to generate insights from Reddit data."""

from openai import OpenAI
from config import PERPLEXITY_API_KEY

# Perplexity API configuration
PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
PERPLEXITY_MODEL = "sonar"  # Perplexity's main model for analysis tasks


def format_posts_for_analysis(all_data: dict[str, list[dict]]) -> str:
    """Format scraped data into a structured text for analysis."""
    formatted_parts = []

    for subreddit, posts in all_data.items():
        formatted_parts.append(f"\n{'='*60}")
        formatted_parts.append(f"SUBREDDIT: r/{subreddit}")
        formatted_parts.append('='*60)

        for i, post in enumerate(posts, 1):
            formatted_parts.append(f"\n--- POST {i} [ID: {subreddit}_{i}] ---")
            formatted_parts.append(f"Title: {post['title']}")
            age_str = post.get('age', 'unknown')
            formatted_parts.append(f"Posted: {age_str} | Score: {post['score']} | Comments: {post['num_comments']}")
            if post.get('flair'):
                formatted_parts.append(f"Flair: {post['flair']}")
            if post.get('selftext'):
                # Truncate very long posts
                text = post['selftext'][:2000]
                if len(post['selftext']) > 2000:
                    text += "... [truncated]"
                formatted_parts.append(f"Content: {text}")

            if post.get('comments'):
                formatted_parts.append("\nTop Comments:")
                for j, comment in enumerate(post['comments'], 1):
                    body = comment['body'][:500]
                    if len(comment['body']) > 500:
                        body += "... [truncated]"
                    formatted_parts.append(f"  [{j}] (Score: {comment['score']}) {body}")

    return "\n".join(formatted_parts)


def get_analysis_prompt(formatted_data: str, total_posts: int, total_comments: int) -> str:
    """Generate the analysis prompt for Perplexity."""
    return f"""You are an expert financial analyst specializing in the Indian stock market. Analyze the following Reddit posts and comments from Indian stock market communities collected over the last 48 hours.

DATASET STATISTICS:
- Total Posts: {total_posts}
- Total Comments: {total_comments}

Your task is to extract actionable insights and market sentiment. Focus on:
1. Specific stock tickers mentioned (NSE/BSE symbols)
2. Market sentiment (bullish/bearish/neutral)
3. Reasons given for recommendations
4. Any news or events discussed
5. Common themes across discussions

CRITICAL REQUIREMENTS:
- **CITATIONS ARE MANDATORY**: For EVERY insight, you MUST count and report exactly how many posts and comments mention it
- Only include insights that appear in at least 2+ posts OR have significant discussion (5+ comments)
- Use the post IDs (e.g., "IndianStreetBets_1") to track which posts mention each topic
- Be precise with counts - don't estimate, actually count the occurrences
- Note the sentiment and reasoning for each stock
- Identify any emerging trends or sector-specific discussions
- Flag any potential red flags or pump-and-dump discussions
- Be objective - report what the community is saying, not your own opinion

DATA FROM REDDIT:
{formatted_data}

Please provide your analysis in the following format:

## TOP 10 KEY INSIGHTS

For each insight, provide:
1. **[STOCK_TICKER or TOPIC]** - Brief description of the insight
   - **Citations: X posts, Y comments** (REQUIRED - must be specific numbers)
   - Sentiment: Bullish/Bearish/Neutral
   - Sources: List the subreddit(s) and post IDs where this was discussed
   - Key points: What users are saying

## MOST DISCUSSED STOCKS

List the top 5-10 most mentioned stocks with:
- Ticker symbol
- **Exact count: X posts, Y comments mentioning this stock**
- Overall sentiment
- Brief summary of discussion

## SECTOR TRENDS

Any notable sector-specific trends (IT, Banking, Pharma, etc.) with citation counts

## MARKET SENTIMENT SUMMARY

Overall community sentiment and any notable observations

## NEWS CONTEXT

For the top mentioned stocks, provide relevant recent news:
- [News Context] Stock: Brief news headline/development
- Cite source where possible
- Indicate if news confirms or contradicts Reddit sentiment

## CAUTION FLAGS

Any discussions that seem speculative, pump-and-dump, or require extra caution

---

Remember: This combines aggregated social media sentiment WITH real-time news context. Always recommend users do their own research before making investment decisions."""


def analyze_with_perplexity(all_data: dict[str, list[dict]]) -> str:
    """Send data to Perplexity API and get analysis."""
    if not PERPLEXITY_API_KEY:
        return "ERROR: PERPLEXITY_API_KEY not set. Please add it to your .env file."

    # Format the data
    formatted_data = format_posts_for_analysis(all_data)

    # Check if we have meaningful data
    total_posts = sum(len(posts) for posts in all_data.values())
    total_comments = sum(
        len(post.get('comments', []))
        for posts in all_data.values()
        for post in posts
    )

    if total_posts == 0:
        return "No posts found to analyze. The subreddits may be empty or requests failed."

    print(f"\nSending {total_posts} posts ({total_comments} comments) to Perplexity for analysis...")
    print(f"Data size: {len(formatted_data)} characters")

    # Initialize the Perplexity client (OpenAI-compatible)
    client = OpenAI(
        api_key=PERPLEXITY_API_KEY,
        base_url=PERPLEXITY_BASE_URL
    )

    try:
        response = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert financial analyst specializing in the Indian stock market.

Your task is to analyze Reddit data from Indian stock market communities AND supplement your analysis with relevant real-time news.

APPROACH:
1. PRIMARY: Analyze the Reddit posts and comments provided by the user - cite specific post IDs and comment counts
2. SUPPLEMENTARY: Search for relevant recent news about the stocks/topics mentioned to provide additional context
3. SYNTHESIS: Combine Reddit sentiment with news to provide a comprehensive market view

When citing:
- For Reddit data: Use specific post IDs (e.g., "IndianStreetBets_1") and exact counts
- For news: Clearly mark as "[News Context]" and cite the source

This dual approach gives users both community sentiment AND factual news context."""
                },
                {
                    "role": "user",
                    "content": get_analysis_prompt(formatted_data, total_posts, total_comments)
                }
            ],
            max_tokens=4096,
            temperature=0.2  # Lower temperature for more consistent analysis
        )

        # Extract text from response
        response_text = response.choices[0].message.content

        return response_text

    except Exception as e:
        return f"Perplexity API error: {e}"


# Alias for backward compatibility
def analyze_with_claude(all_data: dict[str, list[dict]]) -> str:
    """Backward compatible alias - now uses Perplexity."""
    return analyze_with_perplexity(all_data)


def generate_report(analysis: str, total_posts: int, total_comments: int, subreddits: list[str], time_window_hours: int) -> str:
    """Format the final report with header and footer."""
    from datetime import datetime

    header = f"""
================================================================================
                    INDIAN STOCK MARKET DAILY DIGEST
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

Data Sources: {', '.join([f'r/{s}' for s in subreddits])}
Time Window: Last {time_window_hours} hours
Total Posts Analyzed: {total_posts}
Total Comments Analyzed: {total_comments}
AI Analysis: Perplexity ({PERPLEXITY_MODEL})

================================================================================
"""

    footer = """
================================================================================
                              DISCLAIMER
================================================================================

This report is generated from aggregated social media discussions and represents
community sentiment only. It is NOT financial advice.

- Always do your own research (DYOR) before making investment decisions
- Social media sentiment can be manipulated or biased
- Past discussions do not predict future stock performance
- Consult a registered financial advisor for professional advice

Generated by Reddit Stock Analyzer - For educational purposes only.
================================================================================
"""

    return header + analysis + footer


if __name__ == "__main__":
    # Quick test with sample data
    sample_data = {
        "IndianStreetBets": [
            {
                "title": "TATA Motors looking bullish after Q3 results",
                "score": 150,
                "num_comments": 45,
                "selftext": "Great quarterly results, EV segment growing...",
                "flair": "Discussion",
                "comments": [
                    {"body": "Bought at 600, holding strong!", "score": 25},
                    {"body": "JLR recovery is real", "score": 18},
                ]
            }
        ]
    }

    formatted = format_posts_for_analysis(sample_data)
    print(formatted)
