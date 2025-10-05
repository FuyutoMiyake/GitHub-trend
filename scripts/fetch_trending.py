#!/usr/bin/env python3
"""
GitHub Trending Fetcher

Fetches the top 18 repositories from GitHub Trending (weekly) and saves them to a JSON file.
"""

import httpx
from selectolax.parser import HTMLParser
from utils import setup_logger, save_json, get_data_path, retry


# Configuration
TRENDING_URL = "https://github.com/trending"
LANGUAGE = None  # None = all languages, or specify like "python", "javascript", etc.
PERIOD = "weekly"  # "daily", "weekly", or "monthly"
LIMIT = 18  # Number of repositories to fetch
TIMEOUT = 10.0  # HTTP request timeout in seconds

# Logger
logger = setup_logger(__name__, "trending.log")


@retry(max_attempts=3, delay=2, backoff=2, exceptions=(httpx.RequestError, httpx.HTTPStatusError))
def fetch_trending_html() -> str:
    """
    Fetch GitHub Trending HTML page.

    Returns:
        HTML content as string

    Raises:
        httpx.RequestError: Network error
        httpx.HTTPStatusError: HTTP error
    """
    params = {"since": PERIOD}
    if LANGUAGE:
        params["language"] = LANGUAGE

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    logger.info(f"Fetching GitHub Trending ({PERIOD})...")

    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(TRENDING_URL, params=params, headers=headers)
        response.raise_for_status()

    logger.info(f"✅ Successfully fetched HTML ({len(response.text)} bytes)")
    return response.text


def parse_trending_repos(html: str) -> list:
    """
    Parse trending repositories from HTML.

    Args:
        html: GitHub Trending HTML content

    Returns:
        List of repository dictionaries with keys: owner, repo, full_name

    Example output:
        [
            {"owner": "anthropics", "repo": "anthropic-sdk-python", "full_name": "anthropics/anthropic-sdk-python"},
            ...
        ]
    """
    tree = HTMLParser(html)
    repos = []

    # Find all repository articles
    # GitHub Trending uses <article> tags or similar containers with h2 > a structure
    repo_links = tree.css("article.Box-row h2 a")

    if not repo_links:
        # Try alternative selector (GitHub may change structure)
        repo_links = tree.css("h2.h3 a")

    logger.info(f"Found {len(repo_links)} repositories in HTML")

    for link in repo_links[:LIMIT]:
        href = link.attributes.get("href", "").strip()

        if not href or not href.startswith("/"):
            continue

        # Remove leading slash and split
        # Example: /anthropics/anthropic-sdk-python -> ["anthropics", "anthropic-sdk-python"]
        parts = href.lstrip("/").split("/")

        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1]
            full_name = f"{owner}/{repo}"

            repos.append({
                "owner": owner,
                "repo": repo,
                "full_name": full_name
            })

            logger.debug(f"Parsed repo: {full_name}")

        if len(repos) >= LIMIT:
            break

    logger.info(f"✅ Parsed {len(repos)} repositories")
    return repos


def main():
    """Main execution function."""
    try:
        # Fetch HTML
        html = fetch_trending_html()

        # Parse repositories
        repos = parse_trending_repos(html)

        if not repos:
            logger.warning("⚠️  No repositories found! GitHub may have changed its HTML structure.")
            return

        # Save to JSON
        output_path = get_data_path("trending_weekly.json")
        save_json(repos, output_path)

        logger.info(f"✅ Saved {len(repos)} repositories to {output_path}")

        # Print summary
        print("\n📊 GitHub Trending Repositories (Top 18):\n")
        for i, repo in enumerate(repos, 1):
            print(f"  {i:2d}. {repo['full_name']}")

        print(f"\n✅ Data saved to {output_path}")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
