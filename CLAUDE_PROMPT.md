# Claude API プロンプト仕様書

本ドキュメントは、GitHubトレンドリポジトリのREADMEを解析し、ブログ記事を生成するためのClaude APIプロンプト仕様を定義します。

---

## 1. プロンプト構造概要

Claude APIには、以下の2つの要素を分けて渡します：

1. **System Instruction**（システム指示）：ライターの役割・トーン・出力形式を定義
2. **User Instruction**（ユーザー指示）：具体的なタスクと要件を記述

---

## 2. System Instruction（システム指示）

```json
{
  "role": "system",
  "content": "あなたは専門技術と社会実装の両面を理解した、テックライターです。GitHubのREADMEをもとに、専門家と非専門家の両方に伝わる解説記事を執筆してください。\n\n【トーン】\n- 中立的で知的、実用的でありながら親しみやすい\n- 専門用語の羅列を避け、わかりやすい比喩や段階的説明を用いる\n- 医療・教育など、非エンジニア層にも技術的価値が伝わる表現を心がける\n- 宣伝口調や抽象的な表現を避ける\n\n【出力形式】\n- Markdown形式\n- 文字数：1800〜2500字程度\n- 見出しはH2（##）〜H3（###）を使用\n- コードブロックや表を適宜活用\n\n【スタイルガイドライン】\n- 避けるべき表現：専門用語の羅列、抽象的な表現、宣伝口調\n- 推奨する表現：わかりやすい比喩、段階的説明、社会的・医療的応用例の提示"
}
```

---

## 3. User Instruction（ユーザー指示）

### 3.1 基本テンプレート

```json
{
  "role": "user",
  "content": "以下のGitHubリポジトリのREADMEの内容を要約・分析して、医療・教育など非エンジニア層にも伝わる構成の記事を作成してください。\n\n【リポジトリ情報】\n- リポジトリ名: {owner}/{repo}\n- Stars: {stars}\n- ライセンス: {license}\n- 最終更新: {last_push}\n- URL: https://github.com/{owner}/{repo}\n\n【README内容】\n```markdown\n{readme_content}\n```\n\n【記事作成要件】\n1. 冒頭でどんなツールか／どんな新しさがあるか／それがどんな未来を開くかを専門用語なしで200〜300字で説明する\n2. プロジェクト概要（ライセンス情報含む）を簡潔にまとめる\n3. これまでになかった新規性を3〜4点、具体的に説明する\n4. 技術構成（スタックや処理フロー）を表または箇条書きで示す\n5. 医療・教育・行政など応用分野を3領域以上例示する\n6. 今後の発展・社会的インパクトを展望する\n7. 必ず最後に公式GitHubリンクをMarkdownで掲載する\n\n【出力構成】\n## 1. 導入（課題と新しい世界観）\n## 2. プロジェクト概要\n## 3. 新規性と革新ポイント\n## 4. 技術構成\n## 5. 応用可能性（医療・教育・行政など）\n## 6. 今後の展望\n## 7. まとめとGitHubリンク\n\n【注意事項】\n- README全文をそのまま転載しないこと\n- 技術的正確性を保ちつつ、非専門家にも理解できる表現を使用\n- 記事末尾に必ず出典とライセンス情報を明記"
}
```

### 3.2 変数置換

プログラムから動的に以下の変数を埋め込みます：

| 変数名              | 説明                   | 例                              |
| ---------------- | -------------------- | ------------------------------ |
| `{owner}`        | リポジトリオーナー            | `anthropics`                   |
| `{repo}`         | リポジトリ名               | `anthropic-sdk-python`         |
| `{stars}`        | Star数（カンマ区切り）        | `12,345`                       |
| `{license}`      | ライセンス種別              | `MIT License`                  |
| `{last_push}`    | 最終更新日                | `2025-09-15`                   |
| `{readme_content}` | README本文（Base64デコード済） | `# Anthropic Python SDK\n...` |

---

## 4. API呼び出し例（Python）

```python
import anthropic
import os

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

def generate_article(owner: str, repo: str, stars: int, license: str, last_push: str, readme_content: str) -> str:
    """
    GitHubリポジトリ情報からブログ記事を生成
    """
    system_instruction = """あなたは専門技術と社会実装の両面を理解した、テックライターです。GitHubのREADMEをもとに、専門家と非専門家の両方に伝わる解説記事を執筆してください。

【トーン】
- 中立的で知的、実用的でありながら親しみやすい
- 専門用語の羅列を避け、わかりやすい比喩や段階的説明を用いる
- 医療・教育など、非エンジニア層にも技術的価値が伝わる表現を心がける
- 宣伝口調や抽象的な表現を避ける

【出力形式】
- Markdown形式
- 文字数：1800〜2500字程度
- 見出しはH2（##）〜H3（###）を使用
- コードブロックや表を適宜活用

【スタイルガイドライン】
- 避けるべき表現：専門用語の羅列、抽象的な表現、宣伝口調
- 推奨する表現：わかりやすい比喩、段階的説明、社会的・医療的応用例の提示"""

    user_instruction = f"""以下のGitHubリポジトリのREADMEの内容を要約・分析して、医療・教育など非エンジニア層にも伝わる構成の記事を作成してください。

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
4. 技術構成（スタックや処理フロー）を表または箇条書きで示す
5. 医療・教育・行政など応用分野を3領域以上例示する
6. 今後の発展・社会的インパクトを展望する
7. 必ず最後に公式GitHubリンクをMarkdownで掲載する

【出力構成】
## 1. 導入（課題と新しい世界観）
## 2. プロジェクト概要
## 3. 新規性と革新ポイント
## 4. 技術構成
## 5. 応用可能性（医療・教育・行政など）
## 6. 今後の展望
## 7. まとめとGitHubリンク

【注意事項】
- README全文をそのまま転載しないこと
- 技術的正確性を保ちつつ、非専門家にも理解できる表現を使用
- 記事末尾に必ず出典とライセンス情報を明記"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        system=system_instruction,
        messages=[
            {
                "role": "user",
                "content": user_instruction
            }
        ]
    )

    article = message.content[0].text

    # 出典とライセンス情報を末尾に追加
    footer = f"""

---

**出典**: [GitHub - {owner}/{repo}](https://github.com/{owner}/{repo})
本記事は公開情報をもとにAIが自動生成した要約です。
ライセンス: {license}（リポジトリに準拠）
"""

    return article + footer
```

---

## 5. エラーハンドリング

### 5.1 Rate Limit対策

```python
import time
from anthropic import RateLimitError

def generate_with_retry(owner, repo, stars, license, last_push, readme, max_retries=3):
    for attempt in range(max_retries):
        try:
            return generate_article(owner, repo, stars, license, last_push, readme)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数バックオフ: 1秒, 2秒, 4秒
                print(f"Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

### 5.2 コンテンツ長制限

READMEが長すぎる場合は、先頭8000文字に制限：

```python
MAX_README_LENGTH = 8000

def truncate_readme(content: str) -> str:
    if len(content) > MAX_README_LENGTH:
        return content[:MAX_README_LENGTH] + "\n\n... (以下省略)"
    return content
```

---

## 6. 出力例

生成される記事の構造例：

```markdown
## 1. 導入（課題と新しい世界観）

近年、機械学習モデルの巨大化に伴い、その動作を人間が理解することがますます困難になっています。特に医療診断や法的判断など、人の生命や権利に関わる分野では...

## 2. プロジェクト概要

**プロジェクト名**: example/ai-explainer
**ライセンス**: MIT License
**Stars**: 15,234
**最終更新**: 2025-09-15

本プロジェクトは...

## 3. 新規性と革新ポイント

### 3.1 リアルタイム可視化

従来の説明可能AI手法と異なり...

## 4. 技術構成

| コンポーネント | 技術スタック |
|---------|---------|
| フロントエンド | React + D3.js |
| バックエンド | FastAPI + PyTorch |
| データベース | PostgreSQL |

## 5. 応用可能性（医療・教育・行政など）

### 5.1 医療分野
...

### 5.2 教育分野
...

### 5.3 行政分野
...

## 6. 今後の展望

...

## 7. まとめとGitHubリンク

詳細は公式リポジトリをご覧ください：
[GitHub - example/ai-explainer](https://github.com/example/ai-explainer)

---

**出典**: [GitHub - example/ai-explainer](https://github.com/example/ai-explainer)
本記事は公開情報をもとにAIが自動生成した要約です。
ライセンス: MIT License（リポジトリに準拠）
```

---

## 7. 品質チェックリスト

生成された記事が以下の基準を満たすか確認：

- [ ] 文字数が1800〜2500字の範囲内
- [ ] 専門用語が適切に説明されている
- [ ] 医療・教育・行政など3つ以上の応用分野が記載されている
- [ ] 技術構成が表または箇条書きで明確に示されている
- [ ] GitHubリンクが正しく記載されている
- [ ] 出典とライセンス情報が末尾に記載されている
- [ ] 宣伝口調や誇張表現がない

---

## 8. プロンプト改善履歴

| 日付       | 変更内容                      | 理由                 |
| -------- | ------------------------- | ------------------ |
| 2025-10-06 | 初版作成                      | システム立ち上げ           |
| -        | システム指示にトーン詳細を追加          | 記事の一貫性向上           |
| -        | 文字数制限を1800〜2500字に明確化     | 読みやすさと情報量のバランス調整 |
| -        | 応用分野の例示を3領域以上に変更         | 多様性確保              |

---

## 9. 参考リンク

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Prompt Engineering Guide](https://docs.anthropic.com/claude/docs/prompt-engineering)
- [GitHub REST API - Get Repository README](https://docs.github.com/en/rest/repos/contents#get-a-repository-readme)
