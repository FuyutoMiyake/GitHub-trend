#!/usr/bin/env python3
"""
Database Initialization Script

This script initializes the SQLite database by creating the articles table
and necessary indices based on the schema defined in db/schema.sql.
"""

import sqlite3
import os
from pathlib import Path


def init_database():
    """Initialize the SQLite database with the schema."""
    # Get project root directory
    project_root = Path(__file__).parent.parent
    db_path = project_root / "db" / "articles.db"
    schema_path = project_root / "db" / "schema.sql"

    # Create db directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if schema file exists
    if not schema_path.exists():
        print(f"❌ Error: Schema file not found at {schema_path}")
        return False

    # Read schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Connect to database and execute schema
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute schema
        cursor.executescript(schema_sql)
        conn.commit()

        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='articles'")
        if cursor.fetchone():
            print(f"✅ Database initialized successfully at {db_path}")

            # Show table info
            cursor.execute("PRAGMA table_info(articles)")
            columns = cursor.fetchall()
            print(f"\n📋 Articles table columns:")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")

            # Show indices
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='articles'")
            indices = cursor.fetchall()
            if indices:
                print(f"\n🔍 Indices:")
                for idx in indices:
                    print(f"   - {idx[0]}")

            return True
        else:
            print("❌ Error: Failed to create articles table")
            return False

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("🚀 Initializing GitHub Trend Auto Blog database...\n")
    success = init_database()

    if success:
        print("\n✨ Database is ready to use!")
    else:
        print("\n❌ Database initialization failed")
        exit(1)
