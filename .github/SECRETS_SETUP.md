# GitHub Secrets Setup Guide

This guide explains how to configure GitHub Secrets for the automated workflows.

## Required Secrets

Navigate to your GitHub repository:
```
Settings → Secrets and variables → Actions → New repository secret
```

### 1. ANTHROPIC_API_KEY

**Description**: Anthropic Claude API key for article generation

**Value**:
```
your-anthropic-api-key-here
```

**Used in**: `collect-and-generate.yml`

---

### 2. BLOG_API_URL

**Description**: Your blog's API endpoint for posting articles

**Value**:
```
https://your-blog-domain.com/api/admin/posts
```

**Used in**: `daily-post.yml`, `bulk-post.yml`

---

### 3. BLOG_API_KEY

**Description**: API key for authenticating with your blog

**Value**:
```
your-blog-api-key-here
```

**Used in**: `daily-post.yml`, `bulk-post.yml`

---

### 4. HEADER_IMAGE_URL

**Description**: URL of the header image for blog posts

**Value**:
```
https://your-blog-domain.com/images/header-image.png
```

**Used in**: `daily-post.yml`, `bulk-post.yml`

---

### 5. GITHUB_TOKEN_PAT (Optional)

**Description**: GitHub Personal Access Token for fetching trending repositories

**Value**:
```
ghp_your-github-personal-access-token-here
```

**Used in**: `collect-and-generate.yml`

**Note**: This is optional. If not provided, the workflow will use unauthenticated requests, which have lower rate limits.

---

## Setup Steps

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the name and value listed above
5. Click **Add secret**
6. Repeat for all required secrets

---

## Verify Setup

After adding all secrets, you can verify the setup by:

1. Go to **Actions** tab
2. Select a workflow (e.g., "Daily Post - 2 Articles")
3. Click **Run workflow** → **Run workflow**
4. Check the workflow run logs to ensure no authentication errors

---

## Security Notes

- Never commit these secrets to your repository
- Rotate API keys periodically
- Use GitHub Secrets to keep credentials secure
- Monitor workflow runs for any unauthorized access

---

## Workflow Schedule

- **Collect & Generate**: Every Monday at 06:00 JST (Sunday 21:00 UTC)
- **Daily Post**: Every day at 07:00 JST (22:00 UTC previous day)
- **Bulk Post**: Every Sunday at 18:00 JST (09:00 UTC)

All workflows can also be triggered manually from the Actions tab.
