#!/usr/bin/env python3
"""
collect_sentiment.py - マーケットセンチメント収集スクリプト
YouTube株系チャンネルの最新動画からセンチメントを抽出し、
sentiment_data/YYYY-MM-DD.json に蓄積する。

Usage:
  python collect_sentiment.py

環境変数:
  YOUTUBE_API_KEY   - YouTube Data API v3 キー（必須）
  ANTHROPIC_API_KEY - Claude API キー（任意。なければキーワード抽出のみ）
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# ── 定数 ──────────────────────────────────
CHANNELS = {
    # チャンネルID: 表示名
    "UCkKVLw3kFsYmEwjRafdFjkg": "後藤達也",
    "UCFXl12dZUPaiolwPMIbascA": "高橋ダン",
    "UCtEpOqXeDFRy3jhJB2GQGOQ": "エミンユルマズ",
    "UCQPPXy9LCznUQHHG_kh6Bpg": "バフェット太郎",
    "UCLEbHAkkSFGbCiPosa0qTMg": "SBI証券ビジネスドライブ",
}

# 過去N日以内の動画のみ取得
MAX_AGE_DAYS = 2

# センチメントデータの保存先
SENTIMENT_DIR = Path("sentiment_data")

# Claude APIエンドポイント
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# ── YouTube Data API ──────────────────────
def fetch_latest_videos(api_key, channel_id, max_results=3):
    """チャンネルの最新動画を取得"""
    import urllib.request
    import urllib.parse

    # 過去MAX_AGE_DAYS以内
    after = (datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = urllib.parse.urlencode({
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": max_results,
        "order": "date",
        "type": "video",
        "publishedAfter": after,
        "key": api_key,
    })

    url = f"https://www.googleapis.com/youtube/v3/search?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        videos = []
        for item in data.get("items", []):
            vid = item["id"].get("videoId")
            if vid:
                videos.append({
                    "video_id": vid,
                    "title": item["snippet"]["title"],
                    "published": item["snippet"]["publishedAt"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                })
        return videos
    except Exception as e:
        print(f"  ⚠ YouTube API エラー: {e}")
        return []


# ── Transcript取得 ────────────────────────
def fetch_transcript(video_id):
    """YouTubeの自動字幕を取得"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # 日本語 → 英語 → 自動生成の順で試行
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        for lang in ["ja", "en"]:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except:
                continue

        if not transcript:
            # 自動生成を試す
            try:
                transcript = transcript_list.find_generated_transcript(["ja", "en"])
            except:
                return None

        entries = transcript.fetch()
        text = " ".join([e.text if isinstance(e, dict) is False else e.get("text", "") for e in entries])

        # entries がオブジェクトの場合
        if not text.strip():
            text = " ".join([str(e) for e in entries])

        return text[:8000]  # 最大8000文字（コスト制御）

    except Exception as e:
        print(f"    ⚠ Transcript取得失敗: {e}")
        return None


# ── Claude APIで要約・センチメント抽出 ────
def extract_sentiment_claude(text, channel_name, video_title, api_key):
    """Claude APIでテキストからセンチメントを抽出"""
    import urllib.request

    prompt = f"""以下はYouTubeの株式投資チャンネル「{channel_name}」の動画「{video_title}」の文字起こしです。

この動画から以下の情報をJSON形式で抽出してください。

1. topics: 話題になっている項目のリスト。各項目に以下を含む：
   - topic: テーマ名（銘柄名、セクター名、経済イベント名など）
   - category: "stock"（個別銘柄）, "sector"（セクター）, "macro"（マクロ経済）, "event"（イベント）のいずれか
   - sentiment: "bullish"（強気）, "bearish"（弱気）, "neutral"（中立）, "hype"（過熱）, "fear"（恐怖）のいずれか
   - confidence: 0.0〜1.0（確信度）
   - summary: 一言要約（30文字以内）

2. overall_mood: 動画全体のムード（"bullish", "bearish", "neutral", "cautious", "mixed"のいずれか）

3. key_quote: 印象的な一言（50文字以内）

JSONのみを出力してください。マークダウンのバッククォートは不要です。

--- 文字起こし ---
{text[:5000]}
"""

    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())

        text_content = result["content"][0]["text"]
        # JSON部分を抽出
        text_content = text_content.strip()
        if text_content.startswith("```"):
            text_content = re.sub(r"^```\w*\n?", "", text_content)
            text_content = re.sub(r"\n?```$", "", text_content)

        return json.loads(text_content)

    except Exception as e:
        print(f"    ⚠ Claude API エラー: {e}")
        return None


# ── キーワードベースのフォールバック ──────
def extract_sentiment_keywords(text, video_title):
    """Claude APIが使えない場合のキーワード抽出"""
    bullish_words = ["上昇", "買い", "強気", "期待", "好決算", "上がる", "チャンス", "押し目", "反発", "高配当"]
    bearish_words = ["下落", "売り", "弱気", "暴落", "リスク", "下がる", "危険", "損切", "天井", "過熱"]

    # 銘柄名・キーワード検出
    stock_patterns = [
        r"日経平均|日経225|TOPIX",
        r"NVDA|NVIDIA|エヌビディア",
        r"半導体|AI銘柄|SaaS",
        r"トヨタ|ソニー|任天堂|信越化学|イビデン",
        r"S&P500|ダウ|ナスダック",
        r"配当|優待|高配当",
        r"円安|円高|ドル円",
        r"金利|FRB|日銀",
    ]

    topics = []
    for pattern in stock_patterns:
        matches = re.findall(pattern, text)
        if matches:
            word = matches[0]
            # 前後の文脈でセンチメント推定
            bull = sum(1 for bw in bullish_words if bw in text)
            bear = sum(1 for bw in bearish_words if bw in text)
            sentiment = "bullish" if bull > bear else "bearish" if bear > bull else "neutral"

            topics.append({
                "topic": word,
                "category": "macro" if any(w in word for w in ["日経", "S&P", "円", "金利", "FRB", "日銀"]) else "stock",
                "sentiment": sentiment,
                "confidence": 0.4,
                "summary": f"キーワード検出: {word}",
            })

    bull_total = sum(1 for bw in bullish_words if bw in text)
    bear_total = sum(1 for bw in bearish_words if bw in text)
    mood = "bullish" if bull_total > bear_total * 1.3 else "bearish" if bear_total > bull_total * 1.3 else "mixed"

    return {
        "topics": topics[:10],
        "overall_mood": mood,
        "key_quote": video_title[:50],
    }


# ── メイン処理 ────────────────────────────
def main():
    yt_key = os.environ.get("YOUTUBE_API_KEY", "")
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not yt_key:
        print("❌ YOUTUBE_API_KEY が未設定です")
        sys.exit(1)

    use_claude = bool(claude_key)
    if use_claude:
        print("🤖 Claude API 有効 — AI要約モード")
    else:
        print("📝 Claude API 未設定 — キーワード抽出モード")

    today = datetime.now().strftime("%Y-%m-%d")
    SENTIMENT_DIR.mkdir(exist_ok=True)

    all_entries = []
    video_count = 0

    print(f"\n{'='*50}")
    print(f"📡 MARKET SENTIMENT COLLECTOR — {today}")
    print(f"{'='*50}")

    for ch_id, ch_name in CHANNELS.items():
        print(f"\n📺 {ch_name}")

        videos = fetch_latest_videos(yt_key, ch_id, max_results=3)
        if not videos:
            print(f"  → 新しい動画なし")
            continue

        for v in videos:
            print(f"  🎬 {v['title'][:50]}...")
            video_count += 1

            # Transcript取得
            transcript = fetch_transcript(v["video_id"])
            if not transcript:
                print(f"    → 字幕取得できず、スキップ")
                continue

            print(f"    → 字幕取得OK（{len(transcript)}文字）")

            # センチメント抽出
            if use_claude:
                result = extract_sentiment_claude(transcript, ch_name, v["title"], claude_key)
            else:
                result = None

            if not result:
                result = extract_sentiment_keywords(transcript, v["title"])

            # エントリ作成
            if result and result.get("topics"):
                for topic in result["topics"]:
                    all_entries.append({
                        "source": "youtube",
                        "channel": ch_name,
                        "video_title": v["title"][:80],
                        "video_url": v["url"],
                        "topic": topic.get("topic", ""),
                        "category": topic.get("category", "macro"),
                        "sentiment": topic.get("sentiment", "neutral"),
                        "confidence": topic.get("confidence", 0.5),
                        "summary": topic.get("summary", ""),
                    })

                print(f"    → {len(result['topics'])}件のトピック抽出")
                print(f"    → 全体ムード: {result.get('overall_mood', '?')}")
                if result.get("key_quote"):
                    print(f"    → 💬 {result['key_quote']}")

    # ── 結果保存 ──
    output = {
        "date": today,
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": "claude" if use_claude else "keywords",
        "channels_checked": len(CHANNELS),
        "videos_processed": video_count,
        "entry_count": len(all_entries),
        "entries": all_entries,
        "summary": {
            "by_source": {},
            "by_topic": {},
            "hot_words": [],
        },
    }

    # サマリー集計
    topic_counts = {}
    for e in all_entries:
        t = e["topic"]
        if t not in topic_counts:
            topic_counts[t] = {"count": 0, "sentiments": []}
        topic_counts[t]["count"] += 1
        topic_counts[t]["sentiments"].append(e["sentiment"])

    # トピックごとの多数決センチメント
    for t, data in topic_counts.items():
        sents = data["sentiments"]
        from collections import Counter
        most_common = Counter(sents).most_common(1)[0][0]
        output["summary"]["by_topic"][t] = {
            "count": data["count"],
            "sentiment": most_common,
        }

    # ホットワード（出現頻度順）
    output["summary"]["hot_words"] = [
        t for t, _ in sorted(topic_counts.items(), key=lambda x: -x[1]["count"])
    ][:15]

    # JSON保存
    out_path = SENTIMENT_DIR / f"{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 完了: {len(all_entries)}件のセンチメントを収集")
    print(f"📁 保存先: {out_path}")
    print(f"🔥 ホットワード: {', '.join(output['summary']['hot_words'][:5])}")
    print(f"{'='*50}")

    # ── Discord通知 ──
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if webhook_url and all_entries:
        try:
            import urllib.request
            hot = ', '.join(output['summary']['hot_words'][:5])

            # センチメント集計
            bull = sum(1 for e in all_entries if e["sentiment"] in ("bullish",))
            bear = sum(1 for e in all_entries if e["sentiment"] in ("bearish", "fear"))
            msg = (
                f"📡 **センチメント収集完了** ({today})\n"
                f"動画: {video_count}本 / トピック: {len(all_entries)}件\n"
                f"強気: {bull} / 弱気: {bear}\n"
                f"🔥 {hot}"
            )

            body = json.dumps({"content": msg}).encode()
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            print("📢 Discord通知送信")
        except Exception as e:
            print(f"⚠ Discord通知失敗: {e}")


if __name__ == "__main__":
    main()
