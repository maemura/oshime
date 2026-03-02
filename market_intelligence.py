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
    "fear_greed": {},
    "kabutan_news": [],
    "tradingview_signals": [],
    "yahoo_board": []
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


# ─── 4. 株探ニュース ───
print("📰 株探ニュース収集中...")
try:
    import re
    req = urllib.request.Request("https://kabutan.jp/news/", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    titles = re.findall(r'<a[^>]*href="(/news/[^"]+)"[^>]*>([^<]{15,80})</a>', html)
    seen = set()
    for url_path, title in titles:
        title = title.strip()
        if title not in seen and len(title) > 15:
            seen.add(title)
            result["kabutan_news"].append({
                "title": title[:80],
                "url": f"https://kabutan.jp{url_path}"
            })
            if len(result["kabutan_news"]) >= 10:
                break
    print(f"  ✅ {len(result['kabutan_news'])}件取得")
except Exception as e:
    print(f"  ⚠ 株探取得失敗: {e}")


# ─── 5. TradingView テクニカルシグナル ───
print("📊 TradingView シグナル収集中...")
try:
    tickers = ["TSE:4676", "TSE:7270", "TSE:4331", "TSE:7172", "TSE:2181", "TSE:3668"]
    try:
        with open("stocks_data.json", "r") as f:
            sd = json.load(f)
        top_codes = sorted(
            [s for s in sd.get("stocks", []) if s.get("market_cap_b", 0) > 0],
            key=lambda s: s.get("market_cap_b", 0),
            reverse=True
        )[:10]
        for s in top_codes:
            t = f"TSE:{s['code']}"
            if t not in tickers:
                tickers.append(t)
    except:
        pass

    payload = json.dumps({
        "symbols": {"tickers": tickers, "query": {"types": []}},
        "columns": ["Recommend.All", "Recommend.MA", "Recommend.Other"]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://scanner.tradingview.com/japan/scan",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        tv_data = json.loads(resp.read())

    for item in tv_data.get("data", []):
        symbol = item.get("s", "").replace("TSE:", "")
        vals = item.get("d", [0, 0, 0])
        score = vals[0] if vals[0] else 0
        if score >= 0.5:
            signal_jp = "強い買い"
        elif score >= 0.1:
            signal_jp = "買い"
        elif score >= -0.1:
            signal_jp = "中立"
        elif score >= -0.5:
            signal_jp = "売り"
        else:
            signal_jp = "強い売り"
        result["tradingview_signals"].append({
            "code": symbol,
            "score": round(score, 3),
            "signal_jp": signal_jp,
            "ma_score": round(vals[1], 3) if vals[1] else 0,
            "osc_score": round(vals[2], 3) if vals[2] else 0
        })
    print(f"  ✅ {len(result['tradingview_signals'])}銘柄取得")
except Exception as e:
    print(f"  ⚠ TradingView取得失敗: {e}")


# ─── 6. みんかぶ 個人投資家予想 ───
print("💬 みんかぶ予想収集中...")
import re as re_mod
MINKABU_CODES = ["4676", "7270", "4331", "7172", "2181", "3668"]
for code in MINKABU_CODES:
    try:
        url = f"https://minkabu.jp/stock/{code}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        target = re_mod.findall(r'(?:目標株価|理論株価)[^0-9]*?([0-9,]{3,8})\s*円', html)
        individual = re_mod.findall(r'個人投資家[^買売中]*?(買い|売り|中立)', html)
        analyst = re_mod.findall(r'アナリスト[^買売中]*?(買い|売り|中立)', html)
        result["yahoo_board"].append({
            "code": code,
            "source": "minkabu",
            "target_price": target[0] if target else None,
            "individual_rating": individual[0] if individual else None,
            "analyst_rating": analyst[0] if analyst else None
        })
    except Exception as e:
        result["yahoo_board"].append({"code": code, "error": str(e)[:50]})
print(f"  ✅ {len(result['yahoo_board'])}銘柄取得")


# ─── 保存 ───
with open("market_intelligence.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n🎉 market_intelligence.json 保存完了！")
print(f"   note: {len(result['note_trends'])}件")
print(f"   日経: {len(result['nikkei_headlines'])}件")
print(f"   恐怖指数: {result['fear_greed'].get('rating_jp', '不明')}")
