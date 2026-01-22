"""Reddit scraper module - fetches posts and comments without API auth."""

import time
from datetime import datetime
import requests
from typing import Optional
from config import (
    REDDIT_BASE_URL,
    USER_AGENT,
    REQUEST_DELAY,
    POSTS_PER_SUBREDDIT,
    COMMENTS_PER_POST,
    MAX_POST_AGE_HOURS,
)


def make_request(url: str, retries: int = 3) -> Optional[dict]:
    """Make a request to Reddit with retry logic and rate limiting."""
    # Use comprehensive browser-like headers to avoid blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

    for attempt in range(retries):
        try:
            # Add a small random delay to appear more human-like
            if attempt > 0:
                time.sleep(REQUEST_DELAY * (attempt + 1))

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limited - wait longer
                wait_time = REQUEST_DELAY * (attempt + 2)
                print(f"  Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif response.status_code == 403:
                print(f"  Access forbidden for {url} (attempt {attempt + 1}/{retries})")
                # Try with old.reddit.com on retry
                if attempt < retries - 1 and "www.reddit.com" in url:
                    url = url.replace("www.reddit.com", "old.reddit.com")
                    print(f"  Retrying with old.reddit.com...")
                    time.sleep(REQUEST_DELAY)
            else:
                print(f"  HTTP {response.status_code} for {url}")

        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            if attempt < retries - 1:
                time.sleep(REQUEST_DELAY)

    return None


def get_post_age_hours(created_utc: float) -> float:
    """Calculate the age of a post in hours."""
    now = datetime.utcnow().timestamp()
    return (now - created_utc) / 3600


def format_post_age(created_utc: float) -> str:
    """Format post age as human-readable string."""
    hours = get_post_age_hours(created_utc)
    if hours < 1:
        return f"{int(hours * 60)}m ago"
    elif hours < 24:
        return f"{int(hours)}h ago"
    else:
        days = int(hours / 24)
        return f"{days}d ago"


def fetch_posts_from_endpoint(subreddit: str, endpoint: str, params: str, limit: int) -> list[dict]:
    """Fetch posts from a specific Reddit endpoint."""
    url = f"{REDDIT_BASE_URL}/r/{subreddit}/{endpoint}.json?{params}&limit={limit}"

    data = make_request(url)
    if not data:
        return []

    posts = []
    children = data.get("data", {}).get("children", [])
    cutoff_hours = MAX_POST_AGE_HOURS

    for child in children:
        post_data = child.get("data", {})
        created_utc = post_data.get("created_utc", 0)

        # Filter by age
        age_hours = get_post_age_hours(created_utc)
        if age_hours > cutoff_hours:
            continue

        post = {
            "id": post_data.get("id"),
            "title": post_data.get("title"),
            "author": post_data.get("author"),
            "score": post_data.get("score", 0),
            "upvote_ratio": post_data.get("upvote_ratio", 0),
            "num_comments": post_data.get("num_comments", 0),
            "selftext": post_data.get("selftext", ""),
            "url": post_data.get("url"),
            "permalink": post_data.get("permalink"),
            "created_utc": created_utc,
            "age": format_post_age(created_utc),
            "subreddit": subreddit,
            "flair": post_data.get("link_flair_text"),
        }
        posts.append(post)

    time.sleep(REQUEST_DELAY)  # Rate limiting
    return posts


def fetch_top_posts(subreddit: str, limit: int = POSTS_PER_SUBREDDIT) -> list[dict]:
    """Fetch recent top posts from a subreddit (last MAX_POST_AGE_HOURS hours)."""
    print(f"Fetching posts from r/{subreddit} (last {MAX_POST_AGE_HOURS}h)...")

    all_posts = {}

    # Fetch from "top" (day) - gets highly upvoted posts
    print(f"  Checking top posts...")
    top_posts = fetch_posts_from_endpoint(subreddit, "top", "t=day", limit * 2)
    for post in top_posts:
        all_posts[post["id"]] = post

    # Fetch from "hot" - gets trending posts
    print(f"  Checking hot posts...")
    hot_posts = fetch_posts_from_endpoint(subreddit, "hot", "", limit * 2)
    for post in hot_posts:
        if post["id"] not in all_posts:
            all_posts[post["id"]] = post

    # Fetch from "new" - gets latest posts (might have fewer upvotes but recent)
    print(f"  Checking new posts...")
    new_posts = fetch_posts_from_endpoint(subreddit, "new", "", limit)
    for post in new_posts:
        if post["id"] not in all_posts:
            all_posts[post["id"]] = post

    # Convert to list and sort by score
    posts = list(all_posts.values())
    posts.sort(key=lambda x: x["score"], reverse=True)

    # Take top N posts
    posts = posts[:limit]

    print(f"  Found {len(posts)} recent posts (filtered from {len(all_posts)} total)")
    for post in posts[:3]:  # Show top 3 for verification
        print(f"    - [{post['age']}] (score:{post['score']}) {post['title'][:50]}...")

    return posts


def fetch_post_comments(
    subreddit: str, post_id: str, limit: int = COMMENTS_PER_POST
) -> list[dict]:
    """Fetch top comments for a specific post."""
    url = f"{REDDIT_BASE_URL}/r/{subreddit}/comments/{post_id}.json?sort=top&limit={limit}"

    data = make_request(url)
    if not data or len(data) < 2:
        return []

    comments = []
    # Reddit returns [post_data, comments_data]
    comment_listing = data[1].get("data", {}).get("children", [])

    for child in comment_listing[:limit]:
        if child.get("kind") != "t1":  # t1 = comment
            continue

        comment_data = child.get("data", {})
        comment = {
            "id": comment_data.get("id"),
            "author": comment_data.get("author"),
            "body": comment_data.get("body", ""),
            "score": comment_data.get("score", 0),
            "created_utc": comment_data.get("created_utc"),
        }

        # Skip deleted/removed comments
        if comment["body"] in ["[deleted]", "[removed]", ""]:
            continue

        comments.append(comment)

    time.sleep(REQUEST_DELAY)  # Rate limiting
    return comments


def scrape_subreddit(subreddit: str) -> list[dict]:
    """Scrape a subreddit: get top posts and their top comments."""
    posts = fetch_top_posts(subreddit)

    for i, post in enumerate(posts):
        print(f"  Fetching comments for post {i+1}/{len(posts)}: {post['title'][:50]}...")
        comments = fetch_post_comments(subreddit, post["id"])
        post["comments"] = comments
        print(f"    Got {len(comments)} comments")

    return posts


def scrape_all_subreddits(subreddits: list[str]) -> dict[str, list[dict]]:
    """Scrape multiple subreddits and return all data."""
    all_data = {}

    for subreddit in subreddits:
        print(f"\n{'='*50}")
        print(f"Scraping r/{subreddit}")
        print('='*50)
        all_data[subreddit] = scrape_subreddit(subreddit)

    return all_data


if __name__ == "__main__":
    # Quick test
    from config import SUBREDDITS
    import json

    # Test with just one subreddit
    data = scrape_subreddit(SUBREDDITS[0])
    print(f"\nScraped {len(data)} posts")
    print(json.dumps(data[0] if data else {}, indent=2)[:500])
