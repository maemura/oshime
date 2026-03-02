#!/usr/bin/env python3
"""
summarize_articles.py - 記事本文を取得してClaude APIで要約
=====================================================
market_intelligence.json の Google News / 株探 / note から
記事URLをfetch → 本文抽出 → 要約生成 → 保存

出力: article_summaries/YYYY-MM-DD.json
"""

import json, os, sys, datetime, urllib.request, re, time

JST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(JST)
DATE_STR = NOW.strftime("%Y-%m-%d")

# ─── Anthropic SDK ───
try:
    import anthropic
except ImportError:
    print("⚠ anthropic パッケージがありません")
    sys.exit(1)

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY:
    print("⚠ ANTHROPIC_API_KEY が未設定です")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)
MODEL = "claude-sonnet-4-20250514"


def fetch_article_text(url, max_chars=5000):
    """URLから記事本文テキストを抽出"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # HTMLタグ除去
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # 短すぎる場合はスキップ
        if len(text) < 200:
            return None

        return text[:max_chars]
    except Exception as e:
        print(f"    ⚠ fetch失敗: {e}")
        return None


def summarize_text(title, text):
    """Claude APIで記事を要約"""
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"""以下の記事を日本株投資家向けに3行で要約してください。
重要な数値（株価、%、金額）は必ず含めてください。

タイトル: {title}
本文: {text[:3000]}

要約（3行、各行50文字以内）:"""
            }]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"    ⚠ 要約失敗: {e}")
        return None


def main():
    # market_intelligence.json 読み込み
    try:
        with open("market_intelligence.json", "r", encoding="utf-8") as f:
            intel = json.load(f)
    except:
        print("⚠ market_intelligence.json が見つかりません")
        sys.exit(1)

    summaries = {
        "date": DATE_STR,
        "updated_at": NOW.strftime("%Y-%m-%d %H:%M JST"),
        "articles": []
    }

    # 対象記事を収集（Google News + 株探 + note無料記事）
    targets = []

    # Google News（上位8件）
    for article in intel.get("google_news", [])[:8]:
        targets.append({
            "source": "google_news",
            "title": article["title"],
            "url": article["url"]
        })

    # 株探（上位5件）
    for article in intel.get("kabutan_news", [])[:5]:
        targets.append({
            "source": "kabutan",
            "title": article["title"],
            "url": article["url"]
        })

    # note 無料記事（price=0のもの、上位5件）
    for article in intel.get("note_trends", []):
        if article.get("price", 0) == 0 and len(targets) < 18:
            targets.append({
                "source": "note",
                "title": article["title"],
                "url": article["url"]
            })

    print(f"📰 {len(targets)}件の記事を処理します\n")

    for i, target in enumerate(targets):
        print(f"[{i+1}/{len(targets)}] {target['title'][:40]}...")

        # 1. 本文取得
        text = fetch_article_text(target["url"])
        if not text:
            print("    → スキップ（本文取得不可）")
            continue

        # 2. Claude API で要約
        summary = summarize_text(target["title"], text)
        if not summary:
            print("    → スキップ（要約失敗）")
            continue

        summaries["articles"].append({
            "source": target["source"],
            "title": target["title"][:80],
            "url": target["url"],
            "summary": summary,
            "text_length": len(text)
        })
        print(f"    ✅ 要約完了（{len(text)}文字 → {len(summary)}文字）")

        # レートリミット対策
        time.sleep(1)

    # 保存
    os.makedirs("article_summaries", exist_ok=True)
    output_path = f"article_summaries/{DATE_STR}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    # 最新版も保存（コメント生成用）
    with open("article_summaries_latest.json", "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 {len(summaries['articles'])}件の要約を保存")
    print(f"   📁 {output_path}")
    print(f"   📁 article_summaries_latest.json")

    # コスト概算
    total_input = sum(a.get("text_length", 0) for a in summaries["articles"])
    est_cost = (total_input / 1000) * 0.003 + len(summaries["articles"]) * 0.005
    print(f"   💰 推定コスト: ${est_cost:.3f}")


if __name__ == "__main__":
    main()
