-- Articles table for storing GitHub trending repos and generated articles
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_key TEXT NOT NULL,                    -- e.g., "2025-W41"
    owner TEXT NOT NULL,                       -- Repository owner
    repo TEXT NOT NULL,                        -- Repository name
    sha TEXT NOT NULL,                         -- README SHA for duplicate detection
    stars INTEGER,                             -- Star count
    license TEXT,                              -- License type (e.g., "MIT License")
    last_push TIMESTAMP,                       -- Last push date
    readme_content TEXT,                       -- README content (Base64 decoded)
    markdown TEXT NOT NULL,                    -- Generated article (Markdown)
    status TEXT NOT NULL CHECK(status IN ('pending', 'success', 'failed')),
    error_message TEXT,                        -- Error message if failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    posted_at TIMESTAMP,                       -- When the article was posted
    UNIQUE(owner, repo, sha)                   -- Prevent duplicate articles
);

-- Index for efficient status queries
CREATE INDEX IF NOT EXISTS idx_status ON articles(status);

-- Index for week-based queries
CREATE INDEX IF NOT EXISTS idx_week_key ON articles(week_key);

-- Index for posting date queries
CREATE INDEX IF NOT EXISTS idx_posted_at ON articles(posted_at);
