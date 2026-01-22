#!/usr/bin/env python3
"""
Article Generation with Claude API

Generates blog articles from GitHub repository READMEs using Anthropic Claude API.
"""

import os
import time
from typing import Optional
from dotenv import load_dotenv
from anthropic import Anthropic, RateLimitError, APITimeoutError

from utils import (
    setup_logger, load_json, save_json, get_data_path,
    check_duplicate, insert_article, get_week_key,
    truncate_text, sanitize_content
)


# Load environment variables
load_dotenv()

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 4096
MAX_README_LENGTH = 8000
MAX_RETRIES = 3

# Logger
logger = setup_logger(__name__, "article_generate.log")


# ============================
# Prompts
# ============================

SYSTEM_INSTRUCTION = """あなたは専門技術と社会実装の両面を理解した、テックライターです。GitHubのREADMEをもとに、専門家と非専門家の両方に伝わる解説記事を執筆してください。

【トーン】
- 中立的で知的、実用的でありながら親しみやすい
- 専門用語の羅列を避け、わかりやすい比喩や段階的説明を用いる
- 医療・教育など、非エンジニア層にも技術的価値が伝わる表現を心がける
- 宣伝口調や抽象的な表現を避ける

【出力形式】
- Markdown形式
- 文字数：1800〜2500字程度
- 見出しはH2（##）とH3（###）のみを使用（H1は絶対に使用しない）
- 記事は必ずH2（##）から開始すること（冒頭にH1タイトルを追加しない）
- コードブロックや表を適宜活用

【スタイルガイドライン】
- 避けるべき表現：専門用語の羅列、抽象的な表現、宣伝口調
- 推奨する表現：わかりやすい比喩、段階的説明、社会的・医療的応用例の提示
"""

USER_INSTRUCTION_TEMPLATE = """以下のGitHubリポジトリのREADMEの内容を要約・分析して、医療・教育など非エンジニア層にも伝わる構成の記事を作成してください。

【リポジトリ情報】
- リポジトリ名: {owner}/{repo}
- Stars: {stars:,}
- ライセンス: {license}
- 最終更新: {last_push}
- URL: https://github.com/{owner}/{repo}

【README内容】
```markdown
{readme_content}
```

【記事作成要件】
1. 冒頭でどんなツールか／どんな新しさがあるか／それがどんな未来を開くかを専門用語なしで200〜300字で説明する
2. プロジェクト概要（ライセンス情報含む）を簡潔にまとめる
3. これまでになかった新規性を3〜4点、具体的に説明する
4. 技術構成と具体的ユースケース
   - スタックや処理フローを表または箇条書きで示す
   - READMEに使い方・活用例が紹介されていれば、それを分かりやすく解説する
   - READMEに具体例がなければ、プロジェクトの特性から実践的な活用シナリオを提案する
5. 医療・教育・行政など応用分野を3領域以上例示する
6. 今後の発展・社会的インパクトを展望する
7. 必ず最後に公式GitHubリンクをMarkdownで掲載する

【出力構成】
## 1. 導入
## 2. プロジェクト概要
## 3. 新規性と革新ポイント
## 4. 技術構成と具体的ユースケース
## 5. 応用可能性（医療・教育・行政など）
## 6. 今後の展望
## 7. まとめとGitHubリンク

【注意事項】
- README全文をそのまま転載しないこと
- 技術的正確性を保ちつつ、非専門家にも理解できる表現を使用
- 記事末尾に必ず出典とライセンス情報を明記
- H1（#）は使用せず、必ずH2（##）から記事を開始すること
- 記事冒頭にタイトル行（H1）を追加しないこと
"""


def build_user_instruction(repo_data: dict) -> str:
    """
    Build user instruction from repository data.

    Args:
        repo_data: Repository data dictionary

    Returns:
        Formatted user instruction string
    """
    # Sanitize and truncate README
    readme = repo_data.get("readme_content", "")
    readme = sanitize_content(readme)
    readme = truncate_text(readme, MAX_README_LENGTH)

    return USER_INSTRUCTION_TEMPLATE.format(
        owner=repo_data["owner"],
        repo=repo_data["repo"],
        stars=repo_data.get("stars", 0),
        license=repo_data.get("license", "Unknown"),
        last_push=repo_data.get("last_push", "Unknown"),
        readme_content=readme
    )


def generate_article_with_retry(client: Anthropic, user_instruction: str) -> Optional[str]:
    """
    Generate article using Claude API with retry logic.

    Args:
        client: Anthropic client
        user_instruction: User instruction prompt

    Returns:
        Generated article text, or None if failed
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Calling Claude API (attempt {attempt}/{MAX_RETRIES})...")

            message = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_INSTRUCTION,
                messages=[
                    {
                        "role": "user",
                        "content": user_instruction
                    }
                ]
            )

            article = message.content[0].text

            logger.info(f"✅ Article generated ({len(article)} chars, {message.usage.input_tokens} input tokens, {message.usage.output_tokens} output tokens)")

            return article

        except (RateLimitError, APITimeoutError) as e:
            if attempt >= MAX_RETRIES:
                logger.error(f"❌ Failed after {MAX_RETRIES} attempts: {e}")
                return None

            wait_time = 2 ** attempt
            logger.warning(f"API error: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)

        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}", exc_info=True)
            return None

    return None


def append_footer(article: str, owner: str, repo: str, license: str) -> str:
    """
    Append source attribution and license info to article.

    Args:
        article: Generated article
        owner: Repository owner
        repo: Repository name
        license: License type

    Returns:
        Article with footer
    """
    footer = f"""

---

**出典**: [GitHub - {owner}/{repo}](https://github.com/{owner}/{repo})
本記事は公開情報をもとにAIが自動生成した要約です。
ライセンス: {license}（リポジトリに準拠）
"""
    return article + footer


def process_repository(client: Anthropic, repo_data: dict, week_key: str) -> bool:
    """
    Process a single repository: check duplicate, generate article, save to DB.

    Args:
        client: Anthropic client
        repo_data: Repository data dictionary
        week_key: Week key (e.g., "2025-W41")

    Returns:
        True if successful, False otherwise
    """
    owner = repo_data["owner"]
    repo = repo_data["repo"]
    sha = repo_data["sha"]

    logger.info(f"Processing {owner}/{repo}...")

    # Check for duplicates
    if check_duplicate(owner, repo, sha):
        logger.info(f"⏭️  Skipping {owner}/{repo} (already exists)")
        return False

    # Build user instruction
    user_instruction = build_user_instruction(repo_data)

    # Generate article
    article = generate_article_with_retry(client, user_instruction)

    if not article:
        logger.error(f"❌ Failed to generate article for {owner}/{repo}")
        return False

    # Append footer
    article_with_footer = append_footer(
        article,
        owner,
        repo,
        repo_data.get("license", "Unknown")
    )

    # Save to database
    article_id = insert_article(
        week_key=week_key,
        owner=owner,
        repo=repo,
        sha=sha,
        stars=repo_data.get("stars", 0),
        license=repo_data.get("license"),
        last_push=repo_data.get("last_push"),
        readme_content=repo_data.get("readme_content"),
        markdown=article_with_footer
    )

    if article_id:
        logger.info(f"✅ Saved article for {owner}/{repo} (ID: {article_id})")
        return True
    else:
        logger.error(f"❌ Failed to save article for {owner}/{repo}")
        return False


def main():
    """Main execution function."""
    try:
        # Check API key
        if not ANTHROPIC_API_KEY:
            logger.error("❌ ANTHROPIC_API_KEY not found in environment variables")
            logger.info("Please set your API key in .env file")
            return

        # Load repository data
        input_path = get_data_path("articles_raw.json")
        repos = load_json(input_path)

        if not repos:
            logger.error(f"❌ No repository data found in {input_path}")
            logger.info("Please run fetch_readme_meta.py first")
            return

        logger.info(f"📋 Processing {len(repos)} repositories...")

        # Initialize Claude client
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Get current week key
        week_key = get_week_key()
        logger.info(f"Week key: {week_key}")

        # Process each repository
        results = []
        success_count = 0

        for i, repo_data in enumerate(repos, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Repository {i}/{len(repos)}")
            logger.info(f"{'='*60}")

            success = process_repository(client, repo_data, week_key)

            if success:
                success_count += 1
                results.append({
                    "owner": repo_data["owner"],
                    "repo": repo_data["repo"],
                    "status": "success"
                })
            else:
                results.append({
                    "owner": repo_data["owner"],
                    "repo": repo_data["repo"],
                    "status": "skipped or failed"
                })

            # Rate limiting: wait between requests
            if i < len(repos):
                logger.info("Waiting 2s before next request...")
                time.sleep(2)

        # Save results
        output_path = get_data_path("articles_ready.json")
        save_json(results, output_path)

        logger.info(f"\n✅ Processed {success_count}/{len(repos)} repositories successfully")
        logger.info(f"✅ Results saved to {output_path}")

        # Print summary
        print(f"\n📊 Article Generation Summary:\n")
        print(f"  Total: {len(repos)}")
        print(f"  Success: {success_count}")
        print(f"  Skipped/Failed: {len(repos) - success_count}")
        print(f"\n✅ Results saved to {output_path}")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
