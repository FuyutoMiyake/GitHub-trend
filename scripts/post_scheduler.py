#!/usr/bin/env python3
"""
Blog Post Scheduler

Posts pending articles to the blog API with configurable limits.
Supports daily posting (2 articles) and bulk posting (all pending).
"""

import os
import argparse
import time
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
import httpx

from utils import (
    setup_logger, get_pending_articles, update_article_status
)


# Load environment variables
load_dotenv()

# Configuration
BLOG_API_URL = os.getenv("BLOG_API_URL")
BLOG_API_KEY = os.getenv("BLOG_API_KEY")
HEADER_IMAGE_URL = os.getenv("HEADER_IMAGE_URL")
TIMEOUT = 30.0
MAX_RETRIES = 3

# Logger
logger = setup_logger(__name__, "post.log")


def generate_slug(owner: str, repo: str, date: str = None) -> str:
    """
    Generate URL-friendly slug for the article.

    Args:
        owner: Repository owner
        repo: Repository name
        date: Date string (optional, defaults to today)

    Returns:
        Slug string

    Example:
        generate_slug("anthropics", "anthropic-sdk-python", "2025-10-06")
        -> "github-trend-anthropic-sdk-python-2025-10-06"
    """
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Convert repo name to slug-friendly format
    slug_repo = repo.lower().replace("_", "-").replace(".", "-")

    return f"github-trend-{slug_repo}-{date}"


def generate_title(owner: str, repo: str) -> str:
    """
    Generate article title.

    Args:
        owner: Repository owner
        repo: Repository name

    Returns:
        Title string
    """
    return f"GitHubトレンド解説：{owner}/{repo}"


def generate_tags(license: str = None) -> list:
    """
    Generate tags for the article.

    Args:
        license: License type (optional)

    Returns:
        List of tags
    """
    tags = ["GitHub", "Tech", "OpenSource"]

    if license and "MIT" in license:
        tags.append("MIT")

    return tags


def post_article(article: dict) -> bool:
    """
    Post a single article to the blog API.

    Args:
        article: Article dictionary from database

    Returns:
        True if successful, False otherwise
    """
    article_id = article["id"]
    owner = article["owner"]
    repo = article["repo"]

    logger.info(f"Posting article: {owner}/{repo} (ID: {article_id})")

    # Build payload
    payload = {
        "slug": generate_slug(owner, repo),
        "title": generate_title(owner, repo),
        "body": article["markdown"],
        "category": "テクノロジー",
        "tags": generate_tags(article.get("license")),
        "status": "published",
        "publishAt": datetime.now(timezone.utc).isoformat()
    }

    # Add header image if configured
    if HEADER_IMAGE_URL:
        payload["headerImageUrl"] = HEADER_IMAGE_URL

    headers = {
        "x-api-key": BLOG_API_KEY,
        "Content-Type": "application/json"
    }

    # Post to API with retries
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                response = client.post(
                    BLOG_API_URL,
                    json=payload,
                    headers=headers
                )

                if response.status_code in [200, 201]:
                    logger.info(f"✅ Successfully posted {owner}/{repo}")
                    update_article_status(article_id, "success")
                    return True

                elif response.status_code >= 500:
                    # Server error, retry
                    if attempt >= MAX_RETRIES:
                        error_msg = f"Server error {response.status_code}: {response.text}"
                        logger.error(f"❌ Failed to post {owner}/{repo}: {error_msg}")
                        update_article_status(article_id, "failed", error_msg)
                        return False

                    wait_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

                else:
                    # Client error, don't retry
                    error_msg = f"Client error {response.status_code}: {response.text}"
                    logger.error(f"❌ Failed to post {owner}/{repo}: {error_msg}")
                    update_article_status(article_id, "failed", error_msg)
                    return False

        except httpx.RequestError as e:
            if attempt >= MAX_RETRIES:
                error_msg = f"Request error: {str(e)}"
                logger.error(f"❌ Failed to post {owner}/{repo}: {error_msg}")
                update_article_status(article_id, "failed", error_msg)
                return False

            wait_time = 2 ** attempt
            logger.warning(f"Request error: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

    return False


def post_articles(limit: Optional[int] = None, bulk: bool = False):
    """
    Post pending articles to the blog.

    Args:
        limit: Maximum number of articles to post (None = all)
        bulk: If True, post all pending articles
    """
    # Get pending articles
    if bulk:
        articles = get_pending_articles()
        logger.info(f"Bulk posting mode: {len(articles)} pending articles")
    elif limit:
        articles = get_pending_articles(limit=limit)
        logger.info(f"Posting up to {limit} articles ({len(articles)} found)")
    else:
        articles = get_pending_articles(limit=2)
        logger.info(f"Daily posting mode: {len(articles)} pending articles")

    if not articles:
        logger.info("✅ No pending articles to post")
        return

    # Post each article
    success_count = 0
    for i, article in enumerate(articles, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Article {i}/{len(articles)}")
        logger.info(f"{'='*60}")

        success = post_article(article)

        if success:
            success_count += 1

        # Wait between posts (rate limiting)
        if i < len(articles):
            logger.info("Waiting 2s before next post...")
            time.sleep(2)

    logger.info(f"\n✅ Posted {success_count}/{len(articles)} articles successfully")

    # Print summary
    print(f"\n📊 Post Summary:\n")
    print(f"  Total attempted: {len(articles)}")
    print(f"  Success: {success_count}")
    print(f"  Failed: {len(articles) - success_count}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Post pending articles to blog API")

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of articles to post"
    )

    parser.add_argument(
        "--bulk",
        action="store_true",
        help="Post all pending articles (ignores --limit)"
    )

    parser.add_argument(
        "--retry",
        action="store_true",
        help="Retry failed articles"
    )

    args = parser.parse_args()

    try:
        # Check required environment variables
        if not BLOG_API_URL:
            logger.error("❌ BLOG_API_URL not found in environment variables")
            return

        if not BLOG_API_KEY:
            logger.error("❌ BLOG_API_KEY not found in environment variables")
            return

        logger.info("🚀 Starting post scheduler...")

        # Post articles
        if args.retry:
            logger.info("Retry mode: This feature is not yet implemented")
            # TODO: Implement retry for failed articles
            # For now, manually set failed articles to 'pending' in DB
        else:
            post_articles(limit=args.limit, bulk=args.bulk)

        logger.info("✅ Post scheduler completed")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
