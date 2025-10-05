#!/usr/bin/env python3
"""
GitHub README and Metadata Fetcher

Fetches README content and repository metadata for trending repositories.
Uses async HTTP requests for parallel processing.
"""

import os
import asyncio
import base64
from typing import Dict, List, Optional
from dotenv import load_dotenv
import httpx

from utils import setup_logger, save_json, load_json, get_data_path


# Load environment variables
load_dotenv()

# Configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN_PAT")
MAX_CONCURRENT_REQUESTS = 5
TIMEOUT = 10.0
MAX_RETRIES = 3

# Logger
logger = setup_logger(__name__, "readme_fetch.log")


async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    retries: int = MAX_RETRIES
) -> Optional[Dict]:
    """
    Fetch data from GitHub API with retry logic.

    Args:
        client: httpx AsyncClient
        url: API endpoint URL
        retries: Number of retry attempts

    Returns:
        JSON response or None if all retries failed
    """
    for attempt in range(1, retries + 1):
        try:
            response = await client.get(url)

            if response.status_code == 404:
                logger.warning(f"Resource not found: {url}")
                return None

            if response.status_code == 403:
                # Rate limit or forbidden
                logger.warning(f"Rate limit or forbidden: {url}. Waiting 60s...")
                await asyncio.sleep(60)
                continue

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if attempt >= retries:
                logger.error(f"HTTP error after {retries} attempts: {e}")
                return None

            wait_time = 2 ** attempt
            logger.warning(f"HTTP error on attempt {attempt}/{retries}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

        except httpx.RequestError as e:
            if attempt >= retries:
                logger.error(f"Request error after {retries} attempts: {e}")
                return None

            wait_time = 2 ** attempt
            logger.warning(f"Request error on attempt {attempt}/{retries}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

    return None


async def fetch_readme(client: httpx.AsyncClient, owner: str, repo: str) -> Optional[Dict]:
    """
    Fetch README content for a repository.

    Args:
        client: httpx AsyncClient
        owner: Repository owner
        repo: Repository name

    Returns:
        Dictionary with sha and content, or None
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"
    logger.info(f"Fetching README: {owner}/{repo}")

    data = await fetch_with_retry(client, url)

    if not data:
        return None

    # Decode Base64 content
    try:
        content_base64 = data.get("content", "")
        content = base64.b64decode(content_base64).decode("utf-8", errors="ignore")

        return {
            "sha": data.get("sha"),
            "content": content
        }
    except Exception as e:
        logger.error(f"Failed to decode README for {owner}/{repo}: {e}")
        return None


async def fetch_repo_meta(client: httpx.AsyncClient, owner: str, repo: str) -> Optional[Dict]:
    """
    Fetch repository metadata (stars, license, last push).

    Args:
        client: httpx AsyncClient
        owner: Repository owner
        repo: Repository name

    Returns:
        Dictionary with stars, license, last_push, or None
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    logger.info(f"Fetching metadata: {owner}/{repo}")

    data = await fetch_with_retry(client, url)

    if not data:
        return None

    license_info = data.get("license")
    license_name = license_info.get("name") if license_info else "Unknown"

    return {
        "stars": data.get("stargazers_count", 0),
        "license": license_name,
        "last_push": data.get("pushed_at")
    }


async def fetch_repo_data(client: httpx.AsyncClient, repo_info: Dict) -> Optional[Dict]:
    """
    Fetch both README and metadata for a repository.

    Args:
        client: httpx AsyncClient
        repo_info: Dictionary with owner and repo keys

    Returns:
        Combined dictionary with all data, or None
    """
    owner = repo_info["owner"]
    repo = repo_info["repo"]

    # Fetch README and metadata concurrently
    readme_task = fetch_readme(client, owner, repo)
    meta_task = fetch_repo_meta(client, owner, repo)

    readme, meta = await asyncio.gather(readme_task, meta_task)

    if not readme or not meta:
        logger.warning(f"Incomplete data for {owner}/{repo}")
        return None

    return {
        "owner": owner,
        "repo": repo,
        "full_name": f"{owner}/{repo}",
        "sha": readme["sha"],
        "readme_content": readme["content"],
        "stars": meta["stars"],
        "license": meta["license"],
        "last_push": meta["last_push"]
    }


async def fetch_all_repos(repos: List[Dict]) -> List[Dict]:
    """
    Fetch README and metadata for all repositories (with concurrency limit).

    Args:
        repos: List of repository dictionaries

    Returns:
        List of complete repository data dictionaries
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Trend-Auto-Blog/1.0"
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        logger.info("Using GitHub token for authentication")
    else:
        logger.warning("No GitHub token found. Rate limits will be strict (60 req/h)")

    async with httpx.AsyncClient(headers=headers, timeout=TIMEOUT) as client:
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def bounded_fetch(repo_info):
            async with semaphore:
                return await fetch_repo_data(client, repo_info)

        # Fetch all repos concurrently (with limit)
        tasks = [bounded_fetch(repo) for repo in repos]
        results = await asyncio.gather(*tasks)

    # Filter out None values
    return [r for r in results if r is not None]


def main():
    """Main execution function."""
    try:
        # Load trending repositories
        input_path = get_data_path("trending_weekly.json")
        repos = load_json(input_path)

        if not repos:
            logger.error(f"❌ No trending repositories found in {input_path}")
            logger.info("Please run fetch_trending.py first")
            return

        logger.info(f"📋 Fetching data for {len(repos)} repositories...")

        # Fetch all README and metadata
        complete_repos = asyncio.run(fetch_all_repos(repos))

        logger.info(f"✅ Successfully fetched data for {len(complete_repos)}/{len(repos)} repositories")

        # Save to JSON
        output_path = get_data_path("articles_raw.json")
        save_json(complete_repos, output_path)

        logger.info(f"✅ Saved data to {output_path}")

        # Print summary
        print(f"\n📊 Successfully fetched {len(complete_repos)} repositories:\n")
        for repo in complete_repos:
            print(f"  • {repo['full_name']} - ⭐ {repo['stars']:,} - {repo['license']}")

        print(f"\n✅ Data saved to {output_path}")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
