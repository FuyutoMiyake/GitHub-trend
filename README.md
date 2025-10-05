# GitHub週間トレンド自動記事生成・投稿システム

GitHubの週間トレンドリポジトリを自動収集し、Anthropic Claude APIで要約・解説記事を生成、ブログAPIへ自動投稿するワークフローシステムです。

## 📋 目次

- [概要](#概要)
- [主な機能](#主な機能)
- [システム構成](#システム構成)
- [セットアップ](#セットアップ)
- [使い方](#使い方)
- [スケジュール設定](#スケジュール設定)
- [ディレクトリ構成](#ディレクトリ構成)
- [環境変数](#環境変数)
- [開発ガイド](#開発ガイド)
- [トラブルシューティング](#トラブルシューティング)
- [ライセンス](#ライセンス)

---

## 概要

本システムは、以下のワークフローを自動化します：

1. **収集**: GitHub Trendingから週間上位18件のリポジトリを取得
2. **重複排除**: 過去に投稿済みのリポジトリを除外
3. **解析**: README + メタ情報をClaude APIに送信し、1800〜2500字の解説記事を生成
4. **投稿**: 毎朝7時に2件ずつブログAPIに投稿、日曜は残り一括投稿

医療・教育など非エンジニア層にも技術価値が伝わる記事を、完全自動で週18本生成・投稿できます。

---

## 主な機能

| 機能 | 説明 |
|------|------|
| 🔍 **トレンド収集** | GitHub Trendingから週間トップ18リポジトリを自動取得 |
| 📝 **AI記事生成** | Claude APIでREADMEを解析し、非専門家向け解説記事を自動生成 |
| 🔄 **重複防止** | SQLite/SupabaseでリポジトリSHAを管理、既投稿分を除外 |
| 📅 **スケジュール投稿** | 毎朝7時に2件ずつ、日曜18時に残り一括投稿 |
| 🛡️ **エラーハンドリング** | API障害時の自動リトライ（指数バックオフ） |
| 📊 **ログ管理** | 投稿成功/失敗/ペンディングをDB管理 |

---

## システム構成

### 技術スタック

| 項目 | 技術 |
|------|------|
| 言語 | Python 3.11+ |
| HTTPクライアント | httpx (非同期対応) |
| HTML解析 | selectolax |
| AI API | Anthropic Claude API (Sonnet/Opus) |
| データベース | SQLite3 / Supabase |
| スケジューラー | GitHub Actions / Vercel Cron |
| 並列処理 | asyncio (5並列) |

### データフロー

```plaintext
[GitHub Actions: 月曜 06:00 JST]
         │
         ▼
  fetch_trending.py ──▶ データ収集（top18.json）
         │
         ▼
  fetch_readme_meta.py ──▶ README + メタ情報取得
         │
         ▼
  anthropic_generate.py ──▶ Claude記事生成（articles_ready.json）
         │
         ▼
  post_scheduler.py ──▶ ブログAPI投稿
         │
         ▼
     投稿ログ（DB）
```

---

## セットアップ

### 1. リポジトリクローン

```bash
git clone https://github.com/yourusername/github-trend-auto-blog.git
cd github-trend-auto-blog
```

### 2. Python環境構築

```bash
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 環境変数設定

`.env.example`をコピーして`.env`を作成：

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
# GitHub API
GITHUB_TOKEN_PAT=ghp_your_github_personal_access_token

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key

# Blog API
BLOG_API_URL=https://yourblog.com/api/posts
BLOG_API_KEY=your_blog_api_key

# Database (Optional: Supabase)
# SQLite3 is used by default - no configuration needed
# Supabase is NOT currently implemented
SUPABASE_URL=
SUPABASE_KEY=

# Timezone
TZ=Asia/Tokyo
```

### 4. データベース初期化

```bash
python scripts/init_db.py
```

**注意**: 現在の実装ではSQLite3のみを使用します。Supabaseは実装されていません。

### 5. GitHub Secretsに環境変数を登録

GitHub Actions用に、リポジトリのSettings > Secrets and variablesに以下を登録：

- `GITHUB_TOKEN_PAT` - GitHub Personal Access Token
- `ANTHROPIC_API_KEY` - Anthropic Claude API Key
- `BLOG_API_URL` - ブログAPIエンドポイント
- `BLOG_API_KEY` - ブログAPI認証キー

---

## 使い方

### 手動実行（テスト用）

#### 1. トレンドリポジトリ取得

```bash
python scripts/fetch_trending.py
```

→ `data/trending_weekly.json` に上位18件が保存されます

#### 2. README + メタ情報取得

```bash
python scripts/fetch_readme_meta.py
```

→ `data/articles_raw.json` にREADME本文とメタ情報が保存されます

#### 3. Claude記事生成

```bash
python scripts/anthropic_generate.py
```

→ `data/articles_ready.json` に生成記事が保存され、DBに登録されます

#### 4. ブログ投稿

```bash
python scripts/post_scheduler.py
```

→ 未投稿記事を2件ブログAPIに送信します

### 自動実行（GitHub Actions）

`.github/workflows/trend_cron.yml` で以下のスケジュールが設定されています：

| タイミング | 動作 |
|----------|------|
| 月曜 06:00 JST | トレンド収集 → 記事生成 |
| 月〜日 07:00 JST | 未投稿記事2件を投稿 |
| 日曜 18:00 JST | 残り未投稿記事を一括投稿 |

---

## スケジュール設定

### GitHub Actions Cron設定

`.github/workflows/trend_cron.yml`:

```yaml
name: GitHub Trending Auto Blog

on:
  schedule:
    # 月曜 06:00 JST (日曜 21:00 UTC)
    - cron: '0 21 * * 0'
    # 毎朝 07:00 JST (22:00 UTC前日)
    - cron: '0 22 * * *'
    # 日曜 18:00 JST (09:00 UTC)
    - cron: '0 9 * * 0'
  workflow_dispatch: # 手動実行可能

jobs:
  collect_and_generate:
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 21 * * 0'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/fetch_trending.py
      - run: python scripts/fetch_readme_meta.py
      - run: python scripts/anthropic_generate.py
        env:
          GITHUB_TOKEN_PAT: ${{ secrets.GITHUB_TOKEN_PAT }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  daily_post:
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 22 * * *'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/post_scheduler.py --limit 2
        env:
          BLOG_API_KEY: ${{ secrets.BLOG_API_KEY }}

  sunday_bulk_post:
    runs-on: ubuntu-latest
    if: github.event.schedule == '0 9 * * 0'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scripts/post_scheduler.py --bulk
        env:
          BLOG_API_KEY: ${{ secrets.BLOG_API_KEY }}
```

---

## ディレクトリ構成

```
github-trend-auto-blog/
├── .github/
│   └── workflows/
│       └── trend_cron.yml          # GitHub Actions設定
├── scripts/
│   ├── fetch_trending.py           # GitHub Trending収集
│   ├── fetch_readme_meta.py        # README + メタ情報取得
│   ├── anthropic_generate.py       # Claude記事生成
│   ├── post_scheduler.py           # ブログAPI投稿
│   └── init_db.py                  # DB初期化
├── db/
│   ├── schema.sql                  # DB定義（SQLite/Supabase共通）
│   └── articles.db                 # SQLiteデータベース（自動生成）
├── data/
│   ├── trending_weekly.json        # トレンドリスト（一時ファイル）
│   ├── articles_raw.json           # README収集結果（一時ファイル）
│   └── articles_ready.json         # 生成記事（一時ファイル）
├── docs/
│   ├── TECHNICAL_REQUIREMENTS.md   # 技術要件書
│   └── CLAUDE_PROMPT.md            # Claude APIプロンプト仕様
├── .env.example                    # 環境変数テンプレート
├── .env                            # 環境変数（.gitignore対象）
├── requirements.txt                # Python依存パッケージ
├── README.md                       # このファイル
└── LICENSE                         # ライセンス
```

---

## 環境変数

| 変数名 | 必須 | 説明 | 例 |
|--------|------|------|-----|
| `GITHUB_TOKEN_PAT` | ✅ | GitHub Personal Access Token (read-only) | `ghp_xxxxx` |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic Claude API Key | `sk-ant-xxxxx` |
| `BLOG_API_URL` | ✅ | ブログAPIエンドポイント | `https://blog.com/api/posts` |
| `BLOG_API_KEY` | ✅ | ブログAPI認証キー | `blog_xxxxx` |
| `TZ` | - | タイムゾーン（デフォルト：UTC） | `Asia/Tokyo` |

**注意**: SQLite3がデフォルトで使用されます。Supabase関連の環境変数は不要です。

---

## 開発ガイド

### ローカル開発環境

```bash
# 仮想環境有効化
source venv/bin/activate

# 依存パッケージインストール
pip install -r requirements.txt

# テスト実行
pytest tests/

# コードフォーマット
black scripts/
flake8 scripts/
```

### カスタマイズポイント

#### 1. 記事生成プロンプト変更

`scripts/anthropic_generate.py` 内の `SYSTEM_INSTRUCTION` および `USER_INSTRUCTION_TEMPLATE` を編集

詳細は [`CLAUDE_PROMPT.md`](docs/CLAUDE_PROMPT.md) を参照

#### 2. 投稿スケジュール変更

`.github/workflows/trend_cron.yml` のcron設定を編集

```yaml
# 例: 毎日12時に変更（UTC 03:00）
- cron: '0 3 * * *'
```

#### 3. 投稿件数変更

`scripts/post_scheduler.py --limit N` のN値を変更

```bash
# 例: 毎日5件投稿
python scripts/post_scheduler.py --limit 5
```

#### 4. 対象言語の変更

`scripts/fetch_trending.py` 内の `LANGUAGE` 変数を編集

```python
LANGUAGE = "python"  # "javascript", "go", "rust" など
```

---

## トラブルシューティング

### Q1. GitHub API Rate Limitエラー

**エラー**: `403 API rate limit exceeded`

**解決策**:
- GitHub Personal Access Tokenが正しく設定されているか確認
- Fine-grained tokenの場合、Read-Only権限が付与されているか確認
- 認証済みは5000 req/h、未認証は60 req/hのため、必ずトークン設定が必要

### Q2. Claude API Timeoutエラー

**エラー**: `TimeoutException: Request timed out`

**解決策**:
- `scripts/anthropic_generate.py` の `generate_with_retry()` で自動リトライ（3回、指数バックオフ）
- READMEが長すぎる場合、`MAX_README_LENGTH = 8000` で制限中
- それでもエラーが続く場合、Anthropicのステータスページを確認: https://status.anthropic.com/

### Q3. データベースロックエラー（SQLite）

**エラー**: `database is locked`

**解決策**:
- 並列実行を避ける（GitHub Actionsで同時実行しない）
- または、Supabaseなど外部DBに移行

### Q4. 記事が投稿されない

**チェック項目**:
1. `data/articles_ready.json` にデータが存在するか確認
2. DBで `status = 'pending'` のレコードが存在するか確認
   ```bash
   sqlite3 db/articles.db "SELECT * FROM articles WHERE status = 'pending';"
   ```
3. ブログAPI認証キーが正しいか確認
4. `scripts/post_scheduler.py` を手動実行してエラーログ確認

---

## ライセンス

MIT License

本システムは、GitHubリポジトリの公開情報をAIで要約した記事を生成します。
各記事の末尾には、元リポジトリへのリンクとライセンス情報を自動記載しています。

---

## 貢献

Pull Request歓迎です！以下の点にご協力ください：

- コードフォーマット: `black` + `flake8`
- テスト: `pytest`で既存テストが通ることを確認
- ドキュメント: 新機能追加時はREADME更新

---

## サポート

- **Issue報告**: [GitHub Issues](https://github.com/yourusername/github-trend-auto-blog/issues)
- **質問**: [GitHub Discussions](https://github.com/yourusername/github-trend-auto-blog/discussions)

---

## 関連ドキュメント

- [技術要件書](docs/TECHNICAL_REQUIREMENTS.md)
- [Claude APIプロンプト仕様](docs/CLAUDE_PROMPT.md)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)

---

**Last Updated**: 2025-10-06
