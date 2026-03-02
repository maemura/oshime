#!/usr/bin/env python3
"""
market_intelligence.py - 市場インテリジェンス収集
Phase 1: note トレンド / 日経見出し / VIX恐怖指数

出力: market_intelligence.json
"""

import json, urllib.request, datetime, xml.etree.ElementTree as ET

JST = datetime.timezone(datetime.timedelta(hours=9))
NOW = datetime.datetime.now(JST)
DATE_STR = NOW.strftime("%Y-%m-%d")

result = {
    "date": DATE_STR,
    "updated_at": NOW.strftime("%Y-%m-%d %H:%M JST"),
    "note_trends": [],
    "nikkei_headlines": [],
    "fear_greed": {}
}

# ─── 1. note トレンド（#日本株 + #株式投資） ───
print("📝 note トレンド収集中...")
NOTE_TAGS = ["日本株", "株式投資", "日経平均", "高配当"]
seen_keys = set()

for tag in NOTE_TAGS:
    try:
        url = f"https://note.com/api/v3/hashtags/{urllib.parse.quote(tag)}/notes?page=1&sort=like"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        for n in data.get("data", {}).get("notes", [])[:10]:
            key = n.get("key", "")
            if key in seen_keys:
                continue
            seen_keys.add(key)
            price = n.get("price", 0) or 0
            likes = n.get("like_count", 0) or 0
            result["note_trends"].append({
                "title": n.get("name", "")[:80],
                "author": n.get("user", {}).get("nickname", "")[:30],
                "likes": likes,
                "price": price,
                "tag": tag,
                "url": f"https://note.com/{n.get('user',{}).get('urlname','')}/n/{key}"
            })
    except Exception as e:
        print(f"  ⚠ #{tag} 取得失敗: {e}")

# いいね数でソートして上位20件に絞る
result["note_trends"].sort(key=lambda x: x["likes"], reverse=True)
result["note_trends"] = result["note_trends"][:20]
print(f"  ✅ {len(result['note_trends'])}件取得")


# ─── 2. 日経ニュース見出し（RSS） ───
print("📰 日経見出し収集中...")
NIKKEI_FEEDS = [
    ("総合", "https://assets.wor.jp/rss/rdf/nikkei/news.rdf"),
    ("国際", "https://assets.wor.jp/rss/rdf/nikkei/international.rdf"),
    ("テクノロジー", "https://assets.wor.jp/rss/rdf/nikkei/technology.rdf"),
]
NS = {"rss": "http://purl.org/rss/1.0/", "dc": "http://purl.org/dc/elements/1.1/"}

for cat, feed_url in NIKKEI_FEEDS:
    try:
        req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
        for item in list(tree.findall(".//rss:item", NS))[:5]:
            title = item.find("rss:title", NS)
            link = item.find("rss:link", NS)
            date = item.find("dc:date", NS)
            if title is not None:
                result["nikkei_headlines"].append({
                    "category": cat,
                    "title": title.text[:80] if title.text else "",
                    "url": link.text if link is not None and link.text else "",
                    "date": date.text if date is not None and date.text else ""
                })
    except Exception as e:
        print(f"  ⚠ {cat} 取得失敗: {e}")

print(f"  ✅ {len(result['nikkei_headlines'])}件取得")


# ─── 3. VIXベース恐怖指数 ───
print("😱 VIX恐怖指数計算中...")
try:
    # stocks_data.json からVIXを読む（既にfetch_stocks.pyで取得済み）
    with open("stocks_data.json", "r") as f:
        stocks = json.load(f)
    vix = stocks.get("vix", 20)

    # VIXから恐怖/強欲を判定
    # VIX < 12: Extreme Greed
    # VIX 12-17: Greed
    # VIX 17-22: Neutral
    # VIX 22-30: Fear
    # VIX > 30: Extreme Fear
    if vix < 12:
        rating, score = "Extreme Greed", 85
    elif vix < 17:
        rating, score = "Greed", 70
    elif vix < 22:
        rating, score = "Neutral", 50
    elif vix < 30:
        rating, score = "Fear", 30
    else:
        rating, score = "Extreme Fear", 10

    result["fear_greed"] = {
        "vix": vix,
        "score": score,
        "rating": rating,
        "rating_jp": {
            "Extreme Greed": "極度の強欲",
            "Greed": "強欲",
            "Neutral": "中立",
            "Fear": "恐怖",
            "Extreme Fear": "極度の恐怖"
        }.get(rating, "不明")
    }
    print(f"  ✅ VIX={vix} → {rating}（{score}pt）")
except Exception as e:
    print(f"  ⚠ VIX取得失敗: {e}")
    result["fear_greed"] = {"vix": None, "score": 50, "rating": "Unknown", "rating_jp": "不明"}


# ─── 保存 ───
with open("market_intelligence.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n🎉 market_intelligence.json 保存完了！")
print(f"   note: {len(result['note_trends'])}件")
print(f"   日経: {len(result['nikkei_headlines'])}件")
print(f"   恐怖指数: {result['fear_greed'].get('rating_jp', '不明')}")
