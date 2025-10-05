"""
Utility functions for GitHub Trend Auto Blog

This module contains helper functions for:
- Database operations
- Logging
- Retry logic
- File I/O
"""

import os
import re
import json
import logging
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from functools import wraps


# ============================
# Path Utilities
# ============================

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_db_path() -> Path:
    """Get the database file path."""
    return get_project_root() / "db" / "articles.db"


def get_data_path(filename: str) -> Path:
    """Get path to a file in the data directory."""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / filename


def get_log_path(filename: str = None) -> Path:
    """Get path to a log file."""
    log_dir = get_project_root() / "logs"
    log_dir.mkdir(exist_ok=True)

    if filename is None:
        filename = f"{datetime.now().strftime('%Y%m%d')}.log"

    return log_dir / filename


# ============================
# Logging Setup
# ============================

def setup_logger(name: str, log_file: str = None, level=logging.INFO) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.

    Args:
        name: Logger name
        log_file: Log file name (optional)
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        file_handler = logging.FileHandler(get_log_path(log_file), encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ============================
# Retry Decorator
# ============================

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch

    Example:
        @retry(max_attempts=3, delay=1, backoff=2)
        def fetch_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1
            current_delay = delay

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt >= max_attempts:
                        raise

                    logger = logging.getLogger(func.__module__)
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1

        return wrapper
    return decorator


# ============================
# JSON Utilities
# ============================

def save_json(data: Any, filepath: Path) -> None:
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(filepath: Path) -> Any:
    """Load data from JSON file."""
    if not filepath.exists():
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================
# Database Utilities
# ============================

def get_db_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def check_duplicate(owner: str, repo: str, sha: str) -> bool:
    """
    Check if an article with the same owner/repo/SHA already exists.

    Args:
        owner: Repository owner
        repo: Repository name
        sha: README SHA

    Returns:
        True if duplicate exists, False otherwise
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM articles WHERE owner = ? AND repo = ? AND sha = ?",
            (owner, repo, sha)
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def insert_article(
    week_key: str,
    owner: str,
    repo: str,
    sha: str,
    stars: int,
    license: str,
    last_push: str,
    readme_content: str,
    markdown: str
) -> Optional[int]:
    """
    Insert a new article into the database.

    Returns:
        Article ID if successful, None otherwise
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO articles (
                week_key, owner, repo, sha, stars, license, last_push,
                readme_content, markdown, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (week_key, owner, repo, sha, stars, license, last_push, readme_content, markdown))

        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Duplicate entry
        return None
    finally:
        conn.close()


def get_pending_articles(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get pending articles from the database.

    Args:
        limit: Maximum number of articles to retrieve

    Returns:
        List of article dictionaries
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        query = "SELECT * FROM articles WHERE status = 'pending' ORDER BY created_at ASC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def update_article_status(article_id: int, status: str, error_message: Optional[str] = None) -> None:
    """
    Update article status.

    Args:
        article_id: Article ID
        status: New status ('pending', 'success', 'failed')
        error_message: Error message (for 'failed' status)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        if status == 'success':
            cursor.execute(
                "UPDATE articles SET status = ?, posted_at = ?, error_message = NULL WHERE id = ?",
                (status, datetime.now(timezone.utc).isoformat(), article_id)
            )
        else:
            cursor.execute(
                "UPDATE articles SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, article_id)
            )

        conn.commit()
    finally:
        conn.close()


# ============================
# String Utilities
# ============================

SENSITIVE_PATTERNS = [
    r'sk-[a-zA-Z0-9]{32,}',      # API Keys
    r'ghp_[a-zA-Z0-9]{36,}',     # GitHub PAT
    r'password\s*[:=]\s*\S+',    # Passwords
    r'Bearer\s+[a-zA-Z0-9_\-\.]+',  # Bearer tokens
]


def sanitize_content(content: str) -> str:
    """
    Remove sensitive information from content.

    Args:
        content: Text content to sanitize

    Returns:
        Sanitized content
    """
    for pattern in SENSITIVE_PATTERNS:
        content = re.sub(pattern, '[REDACTED]', content, flags=re.IGNORECASE)
    return content


def get_week_key() -> str:
    """
    Get current week key in format YYYY-Wxx.

    Returns:
        Week key (e.g., "2025-W41")
    """
    now = datetime.now()
    week_number = now.isocalendar()[1]
    return f"{now.year}-W{week_number:02d}"


def truncate_text(text: str, max_length: int = 8000, suffix: str = "\n\n... (truncated)") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix
