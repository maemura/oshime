#!/usr/bin/env python3
"""
generate_diary_draft.py
16:00スキャン後に自動実行。日記ドラフト+かぶこ台本+X投稿を自動生成。
"""
import json, os
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
DATE_STR = NOW.strftime("%Y-%m-%d")
DATE_DISPLAY = NOW.strftime("%Y/%-m/%-d")

PORTFOLIO = [
    {"code": "4676", "name": "フジ・メディアHD", "shares": 300, "cost": 3351, "type": "守り"},
    {"code": "3668", "name": "コロプラ", "shares": 2300, "cost": 425, "type": "守り"},
    {"code": "4331", "name": "テイクアンドギヴ", "shares": 1300, "cost": 721, "type": "守り"},
    {"code": "7172", "name": "JIA", "shares": 500, "cost": 1966, "type": "守り"},
    {"code": "2181", "name": "パーソルHD", "shares": 4100, "cost": 240.5, "type": "守り"},
    {"code": "7270", "name": "SUBARU", "shares": 300, "cost": 2951, "type": "攻め"},
    {"code": "8411", "name": "みずほFG", "shares": 100, "cost": 6382, "type": "守り"},
]
INITIAL_CAPITAL = 10_000_000

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

stocks_data = load_json("stocks_data.json")
article_summaries = load_json("article_summaries_latest.json")

def get_price(code):
    if not stocks_data: return None
    for s in stocks_data.get("stocks", []):
        if s["code"] == code: return s.get("price")
    return None

nikkei = stocks_data.get("nikkei_price", "?") if stocks_data else "?"
nikkei_chg = stocks_data.get("nikkei_change_percent", "?") if stocks_data else "?"
vix = stocks_data.get("vix", "?") if stocks_data else "?"

stock_total = 0
holdings = []
for p in PORTFOLIO:
    price = get_price(p["code"])
    if price is None:
        holdings.append(f"| {p['name']}（{p['code']}） | {p['shares']}株 | @{p['cost']:,} | ? | ? | {p['type']} |")
        continue
    val = price * p["shares"]
    stock_total += val
    chg = (price - p["cost"]) / p["cost"] * 100
    s = "+" if chg >= 0 else ""
    holdings.append(f"| {p['name']}（{p['code']}） | {p['shares']}株 | @{p['cost']:,} | {price:,.1f}円 | **{s}{chg:.1f}%** | {p['type']} |")

cash = INITIAL_CAPITAL
for p in PORTFOLIO:
    cash -= p["cost"] * p["shares"]

total = stock_total + cash
cash_r = cash / total * 100 if total > 0 else 0
total_chg = (total - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

articles = []
if article_summaries:
    for a in article_summaries.get("articles", [])[:5]:
        articles.append(f"- [{a.get('source','')}] {a.get('title','')[:50]}")

day_file = "day_count.txt"
if os.path.exists(day_file):
    with open(day_file) as f:
        day_num = int(f.read().strip())
else:
    day_num = 9

draft = f"""📊 かぶのすけ投資日記 Day {day_num}（{DATE_DISPLAY}）

こんにちは、かぶのすけです📊
AIが1000万円を運用する投資日記、{day_num}日目です。

[TODO: 冒頭の一言]


## 昨日の仮説の検証

[TODO: 前日の仮説を振り返る]


## 📰 今日の地合い

日経平均は**{nikkei:,}円（{nikkei_chg}%）**。
VIXは**{vix}**。

### 今日のニュース
{chr(10).join(articles) if articles else "[記事要約なし]"}


## 💰 本日の成績

| 項目 | 金額 |
|------|------|
| 資産総額 | **¥{total:,.0f}** |
| 開始来 | **{'+' if total_chg >= 0 else ''}{total_chg:.2f}%** |
| 現金 | ¥{cash:,.0f}（{cash_r:.0f}%） |
| 株式 | ¥{stock_total:,.0f}（{100-cash_r:.0f}%） |


## 📦 保有銘柄（{len(PORTFOLIO)}銘柄）

| 銘柄 | 株数 | 購入価格 | 現在値 | 購入比 | タイプ |
|------|------|---------|--------|--------|--------|
{chr(10).join(holdings)}


## 🧑‍💻 中の人コーナー

[TODO: 中の人の動き]


## 明日への仮説

[TODO: 仮説を記入]


━━━━━━━━━━━━━━━━

⚠️ 本記事はAI（かぶのすけ）による投資シミュレーションです。
実際の投資判断はご自身の責任で行ってください。

📊 スキャンデータ → https://oshime.vercel.app/app.html
📱 毎日の投稿はXでも発信中！
https://x.com/kabunosuke_navi
"""

kabuko = f"""やっほー！かぶこだよ！
かぶこのAI株スクリーニング、{NOW.strftime('%-m月%-d日')}！いくよ！

[TODO: ニュース2本]

日経平均{nikkei:,}円、{nikkei_chg}%！
VIXは{vix}！

[TODO: セクター]

[TODO: 注目銘柄]

[TODO: おにいちゃんイジり]

今日のスクリーニングはここまで！詳しくはおにいちゃんのnoteを見てね！またね〜！
"""

x_post = f"""📊 Day {day_num}（{NOW.strftime('%-m/%-d')}）

日経{nikkei:,}円（{nikkei_chg}%）
かぶのすけ {'+' if total_chg >= 0 else ''}{total_chg:.2f}%

[TODO: ポイント2-3行]

▶ https://note.com/kabunosuke_navi
"""

os.makedirs("diary_drafts", exist_ok=True)
for fname, content in [("diary_draft.md", draft), (f"diary_drafts/{DATE_STR}.md", draft), ("kabuko_script_draft.md", kabuko), ("x_draft.md", x_post)]:
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)

print(f"✅ Day {day_num}（{DATE_DISPLAY}）ドラフト生成完了")
print(f"   資産: ¥{total:,.0f}（{'+' if total_chg >= 0 else ''}{total_chg:.2f}%）")
print(f"   現金: ¥{cash:,.0f}（{cash_r:.0f}%）")
print(f"   日経: {nikkei:,}（{nikkei_chg}%） VIX: {vix}")
print(f"   保有: {len(PORTFOLIO)}銘柄")
print(f"📄 diary_draft.md / kabuko_script_draft.md / x_draft.md")
