#!/usr/bin/env python3
"""
collect_sentiment.py - マーケットセンチメント収集スクリプト
YouTube株系チャンネルの最新動画からセンチメントを抽出し、
sentiment_data/YYYY-MM-DD.json に蓄積する。
"""

import os, sys, json, re
import urllib.request, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# ── 定数 ──────────────────────────────────
CHANNELS = {
    "@SHO1112":       "Sho's投資情報局",
    "@kabureallive":  "株リアルライブ",
    "@higedura24":    "ひげづら株ちゃんねる",
    "@tradelabo2222": "トレードラボ",
    "@bacchama":      "ばっちゃまの投資チャンネル",
    "@yutai_rider":   "優待ライダー",
    "@tabbata":       "たばたの投資ch",
}

MAX_AGE_DAYS = 7
SENTIMENT_DIR = Path("sentiment_data")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


def resolve_handle(api_key, handle):
    """@handle → channelId"""
    params = urllib.parse.urlencode({
        "part": "id,snippet",
        "forHandle": handle.lstrip("@"),
        "key": api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/channels?{params}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as resp:
            items = json.loads(resp.read().decode()).get("items", [])
            if items:
                return items[0]["id"]
    except Exception as e:
        print(f"    ⚠ forHandle失敗: {e}")

    # フォールバック: search
    params = urllib.parse.urlencode({
        "part": "snippet", "q": handle, "type": "channel", "maxResults": 1, "key": api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as resp:
            items = json.loads(resp.read().decode()).get("items", [])
            if items:
                return items[0]["snippet"]["channelId"]
    except Exception as e:
        print(f"    ⚠ search失敗: {e}")
    return None


def fetch_latest_videos(api_key, channel_id, max_results=3):
    after = (datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = urllib.parse.urlencode({
        "part": "snippet", "channelId": channel_id, "maxResults": max_results,
        "order": "date", "type": "video", "publishedAfter": after, "key": api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return [{"video_id": i["id"]["videoId"], "title": i["snippet"]["title"],
                 "published": i["snippet"]["publishedAt"],
                 "url": f"https://www.youtube.com/watch?v={i['id']['videoId']}"}
                for i in data.get("items", []) if i["id"].get("videoId")]
    except Exception as e:
        print(f"  ⚠ YouTube API エラー: {e}")
        return []


def fetch_transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        for langs in [["ja"], ["en"], None]:
            try:
                if langs:
                    entries = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
                else:
                    entries = YouTubeTranscriptApi.get_transcript(video_id)
                text = " ".join([e.get("text", "") if isinstance(e, dict) else str(e) for e in entries])
                if text.strip():
                    return text[:8000]
            except Exception:
                continue
        return None
    except Exception as e:
        print(f"    ⚠ Transcript取得失敗: {e}")
        return None


def extract_sentiment_claude(text, channel_name, video_title, api_key):
    prompt = f"""以下はYouTubeの株式投資チャンネル「{channel_name}」の動画「{video_title}」の文字起こしです。

この動画から以下の情報をJSON形式で抽出してください。

1. topics: 話題になっている項目のリスト。各項目に以下を含む：
   - topic: テーマ名（銘柄名、セクター名、経済イベント名など）
   - category: "stock"/"sector"/"macro"/"event" のいずれか
   - sentiment: "bullish"/"bearish"/"neutral"/"hype"/"fear" のいずれか
   - confidence: 0.0〜1.0
   - summary: 一言要約（30文字以内）

2. overall_mood: 動画全体のムード（"bullish"/"bearish"/"neutral"/"cautious"/"mixed"）

3. key_quote: 印象的な一言（50文字以内）

JSONのみを出力。バッククォート不要。

--- 文字起こし ---
{text[:5000]}
"""
    body = json.dumps({
        "model": "claude-sonnet-4-20250514", "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(ANTHROPIC_API_URL, data=body, headers={
        "Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
        tc = result["content"][0]["text"].strip()
        if tc.startswith("```"):
            tc = re.sub(r"^```\w*\n?", "", tc)
            tc = re.sub(r"\n?```$", "", tc)
        return json.loads(tc)
    except Exception as e:
        print(f"    ⚠ Claude API エラー: {e}")
        return None


def extract_sentiment_keywords(text, video_title):
    bullish = ["上昇","買い","強気","期待","好決算","上がる","チャンス","押し目","反発","高配当","上方修正","最高値","買い増し"]
    bearish = ["下落","売り","弱気","暴落","リスク","下がる","危険","損切","天井","過熱","下方修正","急落","暴落"]
    patterns = [
        (r"日経平均|日経225|TOPIX|日経", "macro"), (r"NVDA|NVIDIA|エヌビディア", "stock"),
        (r"半導体", "sector"), (r"AI銘柄|AI関連", "sector"), (r"SaaS", "sector"),
        (r"トヨタ", "stock"), (r"ソニー", "stock"), (r"任天堂", "stock"),
        (r"信越化学", "stock"), (r"イビデン", "stock"), (r"コーエーテクモ", "stock"),
        (r"S&P500|ナスダック|ダウ", "macro"), (r"配当|高配当", "sector"),
        (r"円安|円高|ドル円", "macro"), (r"金利|FRB|日銀", "macro"),
        (r"決算", "event"), (r"トランプ|関税", "macro"),
        (r"銀行|メガバンク", "sector"), (r"防衛", "sector"), (r"不動産|REIT", "sector"),
    ]
    topics, seen = [], set()
    for pat, cat in patterns:
        ms = re.findall(pat, text)
        if ms:
            w = ms[0]
            if w in seen: continue
            seen.add(w)
            idx = text.find(w)
            ctx = text[max(0,idx-200):idx+200]
            bu = sum(1 for b in bullish if b in ctx)
            be = sum(1 for b in bearish if b in ctx)
            s = "bullish" if bu > be else "bearish" if be > bu else "neutral"
            topics.append({"topic":w,"category":cat,"sentiment":s,"confidence":0.4,"summary":f"キーワード: {w}"})
    bt = sum(1 for b in bullish if b in text)
    bt2 = sum(1 for b in bearish if b in text)
    mood = "bullish" if bt > bt2*1.3 else "bearish" if bt2 > bt*1.3 else "mixed"
    return {"topics": topics[:15], "overall_mood": mood, "key_quote": video_title[:50]}


def main():
    yt_key = os.environ.get("YOUTUBE_API_KEY", "")
    claude_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not yt_key:
        print("❌ YOUTUBE_API_KEY が未設定"); sys.exit(1)

    use_claude = bool(claude_key)
    print(f"{'🤖 AI要約モード' if use_claude else '📝 キーワード抽出モード'}")

    today = datetime.now().strftime("%Y-%m-%d")
    SENTIMENT_DIR.mkdir(exist_ok=True)

    all_entries, video_count, channel_results = [], 0, {}

    print(f"\n{'='*50}")
    print(f"📡 MARKET SENTIMENT COLLECTOR — {today}")
    print(f"{'='*50}")

    for handle, ch_name in CHANNELS.items():
        print(f"\n📺 {ch_name} ({handle})")
        ch_id = resolve_handle(yt_key, handle)
        if not ch_id:
            print("  → チャンネルID取得失敗"); continue
        print(f"  → ID: {ch_id}")

        videos = fetch_latest_videos(yt_key, ch_id, max_results=3)
        if not videos:
            print(f"  → 過去{MAX_AGE_DAYS}日の動画なし"); continue
        print(f"  → {len(videos)}本発見")

        ch_bull, ch_bear = 0, 0
        for v in videos:
            print(f"  🎬 {v['title'][:55]}...")
            video_count += 1
            transcript = fetch_transcript(v["video_id"])
            if not transcript:
                print("    → 字幕なし、スキップ"); continue
            print(f"    → 字幕OK（{len(transcript)}文字）")

            result = None
            if use_claude:
                result = extract_sentiment_claude(transcript, ch_name, v["title"], claude_key)
            if not result:
                result = extract_sentiment_keywords(transcript, v["title"])

            if result and result.get("topics"):
                for topic in result["topics"]:
                    e = {"source":"youtube","channel":ch_name,"video_title":v["title"][:80],
                         "video_url":v["url"],"topic":topic.get("topic",""),
                         "category":topic.get("category","macro"),
                         "sentiment":topic.get("sentiment","neutral"),
                         "confidence":topic.get("confidence",0.5),
                         "summary":topic.get("summary","")}
                    all_entries.append(e)
                    if e["sentiment"] in ("bullish","hype"): ch_bull += 1
                    elif e["sentiment"] in ("bearish","fear"): ch_bear += 1
                print(f"    → {len(result['topics'])}トピック / ムード: {result.get('overall_mood','?')}")
                if result.get("key_quote"):
                    print(f"    💬 {result['key_quote']}")

        channel_results[ch_name] = {"bull": ch_bull, "bear": ch_bear}

    # 集計
    tc = {}
    for e in all_entries:
        t = e["topic"]
        if t not in tc: tc[t] = {"count":0,"sentiments":[],"sources":set()}
        tc[t]["count"] += 1; tc[t]["sentiments"].append(e["sentiment"]); tc[t]["sources"].add(e["channel"])

    by_topic = {t: {"count":d["count"],"sentiment":Counter(d["sentiments"]).most_common(1)[0][0],
                     "sources":list(d["sources"])} for t, d in tc.items()}
    hot_words = [t for t,_ in sorted(tc.items(), key=lambda x:-x[1]["count"])][:15]

    output = {"date":today,"collected_at":datetime.now().strftime("%Y-%m-%d %H:%M"),
              "mode":"claude" if use_claude else "keywords",
              "channels_checked":len(CHANNELS),"videos_processed":video_count,
              "entry_count":len(all_entries),"entries":all_entries,
              "summary":{"by_channel":channel_results,"by_topic":by_topic,"hot_words":hot_words}}

    out_path = SENTIMENT_DIR / f"{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ 完了: {len(all_entries)}件収集 / {video_count}本処理")
    if hot_words: print(f"🔥 ホットワード: {', '.join(hot_words[:5])}")
    for ch, d in channel_results.items():
        print(f"  {ch}: {'🟢'*d['bull']}{'🔴'*d['bear']} ({d['bull']}/{d['bear']})")
    print(f"{'='*50}")

    # Discord
    wh = os.environ.get("DISCORD_WEBHOOK_URL","")
    if wh and all_entries:
        try:
            bull = sum(1 for e in all_entries if e["sentiment"] in ("bullish","hype"))
            bear = sum(1 for e in all_entries if e["sentiment"] in ("bearish","fear"))
            msg = f"📡 **センチメント収集** ({today})\n動画{video_count}本/{len(all_entries)}件\n強気{bull}/弱気{bear}\n🔥 {', '.join(hot_words[:5])}"
            for ch, d in channel_results.items():
                msg += f"\n  {ch}: 🟢{d['bull']} 🔴{d['bear']}"
            body = json.dumps({"content": msg}).encode()
            urllib.request.urlopen(urllib.request.Request(wh, data=body,
                headers={"Content-Type":"application/json"}), timeout=10)
            print("📢 Discord通知送信")
        except Exception as e:
            print(f"⚠ Discord: {e}")


if __name__ == "__main__":
    main()
