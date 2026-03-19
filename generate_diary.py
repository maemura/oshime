#!/usr/bin/env python3
"""
かぶのすけ投資日記 9点セット生成 — generate_diary.py
portfolio.json + commentary.json + stocks_data.json → diary/YYYY-MM-DD.txt
"""

import json, os, sys, datetime, random

HASHTAGS = "#株式投資 #日本株 #投資日記 #AI投資 #高配当 #資産運用 #NISA #投資初心者"

CLOSING_QUOTES = [
    "ルールは、感情が正しいと言い張るときのためにある。",
    "動かないことも、判断です。",
    "相場は、焦った人から退場していく。",
    "嵐の夜に窓を開けない。それだけです。",
    "下がる理由がある間は、安いとは言えない。",
    "市場は短期的には投票機、長期的には体重計。",
    "強欲なときに恐れ、恐れているときに強欲に。でも今夜は、まだその日じゃない。",
]

THEME_LABELS = {
    "dividend": "💰高配当",
    "ai": "🤖AI・半導体",
    "kokusaku": "🏛️国策・エネルギー",
    "trend": "🔥トレンド",
    "守り": "🛡️守り",
    "攻め": "⚔️攻め",
}


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ {path} 読込失敗: {e}")
        return None


def fmt_yen(n):
    """¥10,354,280 形式"""
    return f"¥{int(n):,}"


def fmt_pct(n):
    """+3.54% / -1.00% 形式"""
    return f"+{n:.2f}%" if n >= 0 else f"{n:.2f}%"


def sign_pct(n):
    """+3.5% / -1.0% 形式（1桁）"""
    return f"+{n:.1f}%" if n >= 0 else f"{n:.1f}%"


# ── データ解析 ──────────────────────────────────────────

def analyze(pf, cm, sd):
    day = pf.get("day", "?")
    date = pf.get("date", "????-??-??")
    total = pf.get("total_asset", 0)
    cash = pf.get("cash", 0)
    initial = pf.get("initial_capital", 10_000_000)
    pnl = pf.get("pnl_pct", 0)
    holdings = pf.get("holdings", [])
    positions = pf.get("positions", [])
    all_stocks = holdings + positions
    stock_value = total - cash
    cash_ratio = cash / total * 100 if total else 0

    # 市場データ
    nikkei = sd.get("nikkei_price", 0)
    nikkei_chg = sd.get("nikkei_1d_chg", 0)
    vix = sd.get("vix", 0)
    usdjpy = sd.get("usdjpy", 0)

    # ±5%以上の銘柄
    big_movers = [s for s in all_stocks if abs(s.get("pnl_pct", 0)) >= 5]
    small_movers = [s for s in all_stocks if abs(s.get("pnl_pct", 0)) < 5]

    # テーマ別まとめ
    theme_groups = {}
    for s in small_movers:
        t = s.get("theme") or s.get("type") or "other"
        theme_groups.setdefault(t, []).append(s)

    # 売買履歴（今日分）
    today_trades = [h for h in pf.get("history", []) if h.get("date") == date]
    sold_today = pf.get("sold_today", [])

    # commentary
    market_text = cm.get("market", {}).get("text", cm.get("market", {}).get("comment", ""))
    tags = cm.get("market", {}).get("tags", [])
    interview = cm.get("interview", [])

    return {
        "day": day, "date": date, "total": total, "cash": cash,
        "initial": initial, "pnl": pnl, "stock_value": stock_value,
        "cash_ratio": cash_ratio, "nikkei": nikkei, "nikkei_chg": nikkei_chg,
        "vix": vix, "usdjpy": usdjpy, "all_stocks": all_stocks,
        "big_movers": big_movers, "theme_groups": theme_groups,
        "today_trades": today_trades, "sold_today": sold_today,
        "market_text": market_text, "tags": tags, "interview": interview,
        "holdings": holdings, "positions": positions,
    }


# ── ① note記事（txt） ──────────────────────────────────

def gen_note_txt(d):
    lines = []
    lines.append(f"📊 かぶのすけ投資日記 Day{d['day']}（{d['date']}）")
    lines.append("")
    lines.append("こんにちは、かぶのすけです📊")
    lines.append(f"AIが1000万円を運用する投資日記、{d['day']}日目です。")
    lines.append("")

    # 昨日の仮説検証
    lines.append("■ 昨日の仮説の検証")
    lines.append("")
    lines.append("（前日の日記の「明日への仮説」を振り返ります）")
    lines.append("")

    # 地合い
    lines.append("■ 今日の地合い")
    lines.append("")
    lines.append(f"日経平均：{d['nikkei']:,.0f}円（{sign_pct(d['nikkei_chg'])}）")
    lines.append(f"VIX：{d['vix']}")
    lines.append(f"ドル円：{d['usdjpy']}")
    lines.append("")
    if d["market_text"]:
        lines.append(d["market_text"])
        lines.append("")

    # 成績
    lines.append("■ 本日の成績")
    lines.append("")
    lines.append(f"総資産：{fmt_yen(d['total'])}")
    lines.append(f"開始来：{fmt_pct(d['pnl'])}")
    lines.append(f"現金：{fmt_yen(d['cash'])}（{d['cash_ratio']:.0f}%）")
    lines.append(f"株式：{fmt_yen(d['stock_value'])}（{100 - d['cash_ratio']:.0f}%）")
    lines.append("")

    # 保有銘柄
    lines.append(f"■ 保有銘柄（{len(d['all_stocks'])}銘柄）")
    lines.append("")

    if d["big_movers"]:
        lines.append("▼ 注目（±5%以上）")
        for s in sorted(d["big_movers"], key=lambda x: x.get("pnl_pct", 0), reverse=True):
            lines.append(f"  {s['name']}（{s['code']}）{sign_pct(s.get('pnl_pct', 0))}")
        lines.append("")

    if d["theme_groups"]:
        lines.append("▼ テーマ別まとめ")
        for theme, stocks in d["theme_groups"].items():
            label = THEME_LABELS.get(theme, theme)
            names = "、".join(s["name"] for s in stocks)
            avg_pnl = sum(s.get("pnl_pct", 0) for s in stocks) / len(stocks)
            lines.append(f"  {label}：{names}（平均{sign_pct(avg_pnl)}）")
        lines.append("")

    # 売買
    lines.append("■ 本日の売買")
    lines.append("")
    if d["today_trades"] or d["sold_today"]:
        for t in d["today_trades"]:
            action = "買い" if t.get("action") == "buy" else "売り"
            lines.append(f"  {action}：{t['name']}（{t['code']}）@{t['price']:,} × {t['shares']}株")
            if t.get("reason"):
                lines.append(f"    理由：{t['reason']}")
        for t in d["sold_today"]:
            lines.append(f"  売り：{t.get('name', '')}（{t.get('code', '')}）")
    else:
        lines.append("  本日の売買はありません。")
    lines.append("")

    # 中の人コーナー
    lines.append("■ 今日の中の人コーナー")
    lines.append("")
    lines.append("中の人（Hideyuki）は集中投資派。かぶのすけとは真逆のスタイルで攻めています。")
    lines.append("（中の人の売買・コメントはここに追記してください）")
    lines.append("")

    # 明日への仮説
    lines.append("■ 明日への仮説")
    lines.append("")
    lines.append("（明日の展望・注目ポイントをここに記入してください）")
    lines.append("")

    # 締め
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(random.choice(CLOSING_QUOTES))
    lines.append("")
    lines.append("⚠️ 本記事はAI（かぶのすけ）による投資シミュレーションです。")
    lines.append("実際の投資判断はご自身の責任で行ってください。")
    lines.append("")
    lines.append("📊 ダッシュボード → https://oshime.vercel.app/app.html")
    lines.append("📱 X → https://x.com/kabunosuke_navi")
    lines.append("")
    lines.append(HASHTAGS)

    return "\n".join(lines)


# ── ② note記事（md） ──────────────────────────────────

def gen_note_md(d):
    lines = []
    lines.append(f"# 📊 かぶのすけ投資日記 Day{d['day']}（{d['date']}）")
    lines.append("")
    lines.append("こんにちは、かぶのすけです📊")
    lines.append(f"AIが1000万円を運用する投資日記、**{d['day']}日目**です。")
    lines.append("")

    lines.append("## 昨日の仮説の検証")
    lines.append("")
    lines.append("> （前日の日記の「明日への仮説」を振り返ります）")
    lines.append("")

    lines.append("## 📰 今日の地合い")
    lines.append("")
    lines.append(f"- 日経平均：**{d['nikkei']:,.0f}円**（{sign_pct(d['nikkei_chg'])}）")
    lines.append(f"- VIX：**{d['vix']}**")
    lines.append(f"- ドル円：**{d['usdjpy']}**")
    lines.append("")
    if d["market_text"]:
        lines.append(f"> {d['market_text']}")
        lines.append("")

    lines.append("## 💰 本日の成績")
    lines.append("")
    lines.append("| 項目 | 金額 |")
    lines.append("|------|------|")
    lines.append(f"| 資産総額 | **{fmt_yen(d['total'])}** |")
    lines.append(f"| 開始来 | **{fmt_pct(d['pnl'])}** |")
    lines.append(f"| 現金 | {fmt_yen(d['cash'])}（{d['cash_ratio']:.0f}%） |")
    lines.append(f"| 株式 | {fmt_yen(d['stock_value'])}（{100 - d['cash_ratio']:.0f}%） |")
    lines.append("")

    lines.append(f"## 📦 保有銘柄（{len(d['all_stocks'])}銘柄）")
    lines.append("")

    if d["big_movers"]:
        lines.append("### 注目（±5%以上）")
        lines.append("")
        lines.append("| 銘柄 | コード | 損益 |")
        lines.append("|------|--------|------|")
        for s in sorted(d["big_movers"], key=lambda x: x.get("pnl_pct", 0), reverse=True):
            lines.append(f"| {s['name']} | {s['code']} | **{sign_pct(s.get('pnl_pct', 0))}** |")
        lines.append("")

    if d["theme_groups"]:
        lines.append("### テーマ別まとめ")
        lines.append("")
        for theme, stocks in d["theme_groups"].items():
            label = THEME_LABELS.get(theme, theme)
            names = "、".join(s["name"] for s in stocks)
            avg_pnl = sum(s.get("pnl_pct", 0) for s in stocks) / len(stocks)
            lines.append(f"- **{label}**：{names}（平均{sign_pct(avg_pnl)}）")
        lines.append("")

    lines.append("## 🔄 本日の売買")
    lines.append("")
    if d["today_trades"] or d["sold_today"]:
        for t in d["today_trades"]:
            action = "🟢買い" if t.get("action") == "buy" else "🔴売り"
            lines.append(f"- {action}：**{t['name']}**（{t['code']}）@{t['price']:,} × {t['shares']}株")
            if t.get("reason"):
                lines.append(f"  - 理由：{t['reason']}")
        for t in d["sold_today"]:
            lines.append(f"- 🔴売り：**{t.get('name', '')}**（{t.get('code', '')}）")
    else:
        lines.append("本日の売買はありません。")
    lines.append("")

    lines.append("## 🧑‍💻 今日の中の人コーナー")
    lines.append("")
    lines.append("中の人（Hideyuki）は集中投資派。かぶのすけとは真逆のスタイルで攻めています。")
    lines.append("")
    lines.append("> （中の人の売買・コメントはここに追記してください）")
    lines.append("")

    lines.append("## 🔮 明日への仮説")
    lines.append("")
    lines.append("> （明日の展望・注目ポイントをここに記入してください）")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"**{random.choice(CLOSING_QUOTES)}**")
    lines.append("")
    lines.append("⚠️ 本記事はAI（かぶのすけ）による投資シミュレーションです。実際の投資判断はご自身の責任で行ってください。")
    lines.append("")
    lines.append("📊 [ダッシュボード](https://oshime.vercel.app/app.html) ｜ 📱 [X](https://x.com/kabunosuke_navi)")
    lines.append("")
    lines.append(HASHTAGS)

    return "\n".join(lines)


# ── ③ X投稿（note誘導） ──────────────────────────────

def gen_x_note(d):
    # 140文字以内
    top_mover = ""
    if d["big_movers"]:
        best = max(d["big_movers"], key=lambda s: abs(s.get("pnl_pct", 0)))
        top_mover = f" {best['name']}{sign_pct(best.get('pnl_pct', 0))}"

    body = (
        f"📊Day{d['day']} かぶのすけ投資日記\n"
        f"総資産{fmt_yen(d['total'])}（{fmt_pct(d['pnl'])}）\n"
        f"日経{d['nikkei']:,.0f}円{sign_pct(d['nikkei_chg'])}\n"
        f"{top_mover}\n"
        f"{random.choice(CLOSING_QUOTES)}\n"
        f"▼note\n"
        f"#AI投資 #日本株"
    )
    return body.strip()


# ── ④ X投稿（YouTube誘導） ─────────────────────────────

def gen_x_youtube(d):
    tag_str = " ".join(d["tags"][:3]) if d["tags"] else ""
    body = (
        f"📺Day{d['day']} かぶのすけの相場解説\n"
        f"日経{d['nikkei']:,.0f}円（{sign_pct(d['nikkei_chg'])}）\n"
        f"{tag_str}\n"
        f"今日もかぶ子と一緒に振り返ります🎙️\n"
        f"▼YouTube\n"
        f"#AI投資 #株式投資"
    )
    return body.strip()


# ── ⑤ YouTubeタイトル ──────────────────────────────────

def gen_yt_title(d):
    highlight = ""
    if d["big_movers"]:
        best = max(d["big_movers"], key=lambda s: abs(s.get("pnl_pct", 0)))
        highlight = f" {best['name']}{sign_pct(best.get('pnl_pct', 0))}"
    return (
        f"【Day{d['day']}】日経{d['nikkei']:,.0f}円{sign_pct(d['nikkei_chg'])}"
        f"{highlight}｜かぶのすけ投資日記【AI×1000万円】"
    )


# ── ⑥ YouTube概要欄 ────────────────────────────────────

def gen_yt_desc(d):
    lines = []
    lines.append(f"かぶのすけ投資日記 Day{d['day']}（{d['date']}）")
    lines.append(f"AIキャラ「かぶのすけ」が1000万円を運用するシミュレーション投資日記です。")
    lines.append("")
    lines.append("▼ 今日のハイライト")
    lines.append(f"・日経平均：{d['nikkei']:,.0f}円（{sign_pct(d['nikkei_chg'])}）")
    lines.append(f"・総資産：{fmt_yen(d['total'])}（開始来{fmt_pct(d['pnl'])}）")
    lines.append(f"・現金比率：{d['cash_ratio']:.0f}%")
    if d["big_movers"]:
        for s in d["big_movers"]:
            lines.append(f"・{s['name']}（{s['code']}）{sign_pct(s.get('pnl_pct', 0))}")
    lines.append("")
    if d["today_trades"]:
        lines.append("▼ 本日の売買")
        for t in d["today_trades"]:
            action = "買い" if t.get("action") == "buy" else "売り"
            lines.append(f"・{action} {t['name']}（{t['code']}）@{t['price']:,} × {t['shares']}株")
        lines.append("")
    lines.append("▼ リンク")
    lines.append("📊 ダッシュボード：https://oshime.vercel.app/app.html")
    lines.append("📱 X（旧Twitter）：https://x.com/kabunosuke_navi")
    lines.append("📝 note：（URLを貼ってください）")
    lines.append("")
    lines.append("▼ チャプター")
    lines.append("0:00 オープニング")
    lines.append("0:15 今日の地合い")
    lines.append("0:45 本日の成績")
    lines.append("1:15 注目銘柄")
    lines.append("2:00 本日の売買")
    lines.append("2:30 中の人コーナー")
    lines.append("3:00 明日への仮説")
    lines.append("3:30 エンディング")
    lines.append("")
    lines.append("⚠️ 本動画はAIによる投資シミュレーションです。投資助言ではありません。")
    lines.append("")
    lines.append(HASHTAGS)
    return "\n".join(lines)


# ── ⑦ YouTubeタグ ──────────────────────────────────────

def gen_yt_tags(d):
    base = [
        "かぶのすけ", "AI投資", "日本株", "投資日記", "株式投資",
        "高配当株", "資産運用", "NISA", "投資初心者", "日経平均",
        "AI", "1000万円運用", "投資シミュレーション",
    ]
    # 銘柄名を追加
    for s in d["big_movers"][:3]:
        base.append(s["name"])
    # タグを追加
    for t in d["tags"][:3]:
        base.append(t)
    return ", ".join(base)


# ── ⑧ かぶ子台本（60秒ショート） ─────────────────────────

def gen_kabuko_script(d):
    top_up = ""
    top_down = ""
    for s in d["big_movers"]:
        if s.get("pnl_pct", 0) >= 5 and not top_up:
            top_up = f"{s['name']}が{sign_pct(s.get('pnl_pct', 0))}"
        if s.get("pnl_pct", 0) <= -5 and not top_down:
            top_down = f"{s['name']}が{sign_pct(s.get('pnl_pct', 0))}"

    trade_line = "今日は売買なし！おにいちゃん慎重派だからね〜"
    if d["today_trades"]:
        t = d["today_trades"][0]
        action = "買った" if t.get("action") == "buy" else "売った"
        trade_line = f"今日おにいちゃん{t['name']}{action}んだって！"

    lines = []
    lines.append("【かぶ子のショート動画台本（60秒）】")
    lines.append("")
    lines.append(f"🎬 [0:00〜0:05] オープニング")
    lines.append(f"かぶ子「はーい！かぶ子だよ〜！Day{d['day']}の結果発表〜！」")
    lines.append("")
    lines.append(f"📊 [0:05〜0:15] 地合い")
    lines.append(f"かぶ子「今日の日経平均は{d['nikkei']:,.0f}円！{sign_pct(d['nikkei_chg'])}だよ！」")
    if d["nikkei_chg"] > 1:
        lines.append(f"かぶ子「けっこう上がったね〜！」")
    elif d["nikkei_chg"] < -1:
        lines.append(f"かぶ子「うう…ちょっと下がっちゃった…」")
    else:
        lines.append(f"かぶ子「まあまあって感じかな〜」")
    lines.append("")
    lines.append(f"💰 [0:15〜0:25] 成績")
    lines.append(f"かぶ子「おにいちゃんの総資産は{fmt_yen(d['total'])}！開始来{fmt_pct(d['pnl'])}！」")
    if d["pnl"] > 0:
        lines.append(f"かぶ子「プラスキープしてるよ！さすがおにいちゃん！」")
    else:
        lines.append(f"かぶ子「マイナス…でも大丈夫！きっと！」")
    lines.append("")
    lines.append(f"🔥 [0:25〜0:40] 注目銘柄")
    if top_up:
        lines.append(f"かぶ子「{top_up}！すごくない？」")
    if top_down:
        lines.append(f"かぶ子「あと{top_down}…おにいちゃん大丈夫？」")
    if not top_up and not top_down:
        lines.append(f"かぶ子「今日は大きく動いた銘柄はなかったよ〜」")
    lines.append("")
    lines.append(f"🔄 [0:40〜0:50] 売買")
    lines.append(f"かぶ子「{trade_line}」")
    lines.append("")
    lines.append(f"👋 [0:50〜0:60] エンディング")
    lines.append(f"かぶ子「詳しくはnoteとYouTube見てね〜！」")
    lines.append(f"かぶ子「おにいちゃんが言ってたよ、『{random.choice(CLOSING_QUOTES)}』って笑」")
    lines.append(f"かぶ子「ばいば〜い！」")

    return "\n".join(lines)


# ── ⑨ サムネプロンプト（英語） ──────────────────────────

def gen_thumbnail_prompt(d):
    mood = "confident" if d["pnl"] > 0 else "worried"
    market_dir = "up" if d["nikkei_chg"] > 0 else "down"
    color = "green and gold" if d["pnl"] > 0 else "red and dark blue"

    return (
        f"Anime-style thumbnail for a Japanese stock investment YouTube video. "
        f"A cute male anime character (short brown hair, suit, {mood} expression) "
        f"standing in front of a large stock chart going {market_dir}. "
        f"Bold Japanese text 'Day{d['day']}' in the top left corner. "
        f"'{fmt_pct(d['pnl'])}' displayed prominently in large font. "
        f"Nikkei average '{d['nikkei']:,.0f}' shown on the chart. "
        f"Color scheme: {color}. "
        f"Clean, modern, eye-catching design suitable for YouTube thumbnail. "
        f"16:9 aspect ratio, high contrast text for mobile readability."
    )


# ── メイン ──────────────────────────────────────────────

def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    print(f"📝 投資日記9点セット生成開始: {now.strftime('%Y/%m/%d %H:%M JST')}")

    pf = load_json("portfolio.json")
    cm = load_json("commentary.json")
    sd = load_json("stocks_data.json")

    if not pf:
        print("❌ portfolio.json が読み込めません"); sys.exit(1)
    if not cm:
        print("⚠ commentary.json なし。市場コメントなしで生成します。")
        cm = {}
    if not sd:
        print("⚠ stocks_data.json なし。市場指標なしで生成します。")
        sd = {}

    d = analyze(pf, cm, sd)
    date = d["date"]

    diary_dir = "/Users/maemurahideyuki/Library/CloudStorage/GoogleDrive-hide.maemura@gmail.com/マイドライブ/oshime/diary"
    os.makedirs(diary_dir, exist_ok=True)
    out_path = os.path.join(diary_dir, f"{date}.txt")

    sections = []

    sections.append("=" * 60)
    sections.append(f"  かぶのすけ投資日記 Day{d['day']}（{date}）── 9点セット")
    sections.append("=" * 60)

    # ①
    sections.append("")
    sections.append("━" * 40)
    sections.append("① note記事（txt形式）")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_note_txt(d))

    # ②
    sections.append("")
    sections.append("━" * 40)
    sections.append("② note記事（md形式）")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_note_md(d))

    # ③
    sections.append("")
    sections.append("━" * 40)
    sections.append("③ X投稿（note誘導用）")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_x_note(d))

    # ④
    sections.append("")
    sections.append("━" * 40)
    sections.append("④ X投稿（YouTube誘導用）")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_x_youtube(d))

    # ⑤
    sections.append("")
    sections.append("━" * 40)
    sections.append("⑤ YouTubeタイトル")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_yt_title(d))

    # ⑥
    sections.append("")
    sections.append("━" * 40)
    sections.append("⑥ YouTube概要欄")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_yt_desc(d))

    # ⑦
    sections.append("")
    sections.append("━" * 40)
    sections.append("⑦ YouTubeタグ")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_yt_tags(d))

    # ⑧
    sections.append("")
    sections.append("━" * 40)
    sections.append("⑧ かぶ子台本（ショート動画用・60秒）")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_kabuko_script(d))

    # ⑨
    sections.append("")
    sections.append("━" * 40)
    sections.append("⑨ サムネプロンプト（英語）")
    sections.append("━" * 40)
    sections.append("")
    sections.append(gen_thumbnail_prompt(d))
    sections.append("")

    output = "\n".join(sections)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    file_size = os.path.getsize(out_path) / 1024
    print(f"\n✅ 9点セット生成完了")
    print(f"   📄 出力ファイル: {os.path.abspath(out_path)}")
    print(f"   📏 ファイルサイズ: {file_size:.1f} KB")
    print(f"   📊 保有銘柄数: {len(d['all_stocks'])}")
    print(f"   🔥 注目銘柄（±5%）: {len(d['big_movers'])}銘柄")
    print(f"   🔄 本日の売買: {len(d['today_trades'])}件")


if __name__ == "__main__":
    main()
