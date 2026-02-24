#!/usr/bin/env python3
"""
かぶのすけ ポートフォリオ自動管理
- 保有銘柄の初値取得→評価更新
- 損切り(-15%) / 利確(+20%半分)
- 新規銘柄の自動選定
- daily_nav更新
- note/X投稿テキスト生成
"""

import json, os, sys, datetime, urllib.request, urllib.error, time, re

TODAY = datetime.date.today().strftime("%Y-%m-%d")
TODAY_SHORT = datetime.date.today().strftime("%Y/%m/%d")
WEEKDAY = datetime.date.today().weekday()  # 0=Mon ... 6=Sun

# ── パス ──
BASE = os.path.dirname(os.path.abspath(__file__))
PF_PATH = os.path.join(BASE, "portfolio.json")
STOCKS_PATH = os.path.join(BASE, "stocks_data.json")
NOTE_PATH = os.path.join(BASE, "note_today.txt")
X_PATH = os.path.join(BASE, "x_today.txt")

# ── ルール ──
STOP_LOSS_PCT = -15
TAKE_PROFIT_PCT = 20
MAX_POSITIONS = 10
PER_STOCK_MAX = 1000000
MIN_CASH_RATIO = 0.50  # 現金比率50%以上で新規買い
MIN_SCORE_BUY = 70     # スコア70以上で買い候補
MAX_BUY_PER_DAY = 2    # 1日最大2銘柄新規

# ══════════════════════════════════════
# YAHOO FINANCE 初値取得
# ══════════════════════════════════════
def fetch_opening_price(code):
    """Yahoo Finance JPから初値を取得"""
    url = f"https://finance.yahoo.co.jp/quote/{code}.T"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8", errors="ignore")
        # 始値を探す（HTMLパース）
        # パターン: "始値" の後に数字
        import re
        # 始値のパターンを探す
        patterns = [
            r'始値[^0-9]*?([0-9,]+\.?[0-9]*)',
            r'open["\s:]+([0-9,]+\.?[0-9]*)',
        ]
        for pat in patterns:
            m = re.search(pat, html)
            if m:
                val = m.group(1).replace(",", "")
                return float(val)
    except Exception as e:
        print(f"  ⚠ {code} 初値取得失敗: {e}")
    return None


def fetch_opening_price_stooq(code):
    """Stooq APIで初値を取得（バックアップ）"""
    url = f"https://stooq.com/q/l/?s={code}.jp&f=o&e=csv"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            text = res.read().decode("utf-8").strip()
        lines = text.split("\n")
        if len(lines) >= 2:
            val = lines[1].strip()
            if val and val != "N/D":
                return float(val)
    except Exception as e:
        print(f"  ⚠ {code} Stooq取得失敗: {e}")
    return None


def get_opening_price(code):
    """初値取得（Yahoo → Stooq フォールバック）"""
    price = fetch_opening_price(code)
    if price and price > 0:
        return price
    time.sleep(0.5)
    price = fetch_opening_price_stooq(code)
    if price and price > 0:
        return price
    return None


# ══════════════════════════════════════
# PORTFOLIO OPERATIONS
# ══════════════════════════════════════
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_positions(pf):
    """保有銘柄の株価更新"""
    print("\n📡 保有銘柄の初値取得中...")
    for pos in pf.get("positions", []):
        code = pos["code"]
        price = get_opening_price(code)
        if price:
            pos["current_price"] = price
            pos["pnl_pct"] = round((price - pos["buy_price"]) / pos["buy_price"] * 100, 2)
            print(f"  ✅ {pos['name']}({code}): ¥{price:,.0f} ({pos['pnl_pct']:+.2f}%)")
        else:
            print(f"  ⚠ {pos['name']}({code}): 取得失敗、前回値維持")
        time.sleep(1)  # レート制限対策


def check_stop_loss_take_profit(pf):
    """損切り・利確判定"""
    sells = []
    remaining = []
    
    for pos in pf.get("positions", []):
        pnl = pos.get("pnl_pct", 0)
        
        # 損切り: -15%
        if pnl <= STOP_LOSS_PCT:
            sells.append({
                "action": "sell",
                "type": "stop_loss",
                "code": pos["code"],
                "name": pos["name"],
                "price": pos["current_price"],
                "shares": pos["shares"],
                "amount": pos["current_price"] * pos["shares"],
                "pnl_pct": pnl,
                "reason": f"損切り（{pnl:.1f}%）。ルール通りです。"
            })
            pf["cash"] += pos["current_price"] * pos["shares"]
            print(f"  🔴 損切り: {pos['name']} {pnl:.1f}%")
            
        # 利確: +20%で半分売却
        elif pnl >= TAKE_PROFIT_PCT:
            sell_shares = pos["shares"] // 2
            if sell_shares > 0:
                sells.append({
                    "action": "sell",
                    "type": "take_profit",
                    "code": pos["code"],
                    "name": pos["name"],
                    "price": pos["current_price"],
                    "shares": sell_shares,
                    "amount": pos["current_price"] * sell_shares,
                    "pnl_pct": pnl,
                    "reason": f"利確（{pnl:.1f}%）。+20%で半分売却。"
                })
                pf["cash"] += pos["current_price"] * sell_shares
                pos["shares"] -= sell_shares
                pos["cost"] = pos["buy_price"] * pos["shares"]
                print(f"  🟢 利確: {pos['name']} {pnl:.1f}% → {sell_shares}株売却")
                remaining.append(pos)
            else:
                remaining.append(pos)
        else:
            remaining.append(pos)
    
    pf["positions"] = remaining
    return sells


def select_new_buys(pf, stocks_data):
    """新規銘柄の自動選定"""
    buys = []
    
    # 現金比率チェック
    nav = calc_nav(pf)
    cash_ratio = pf["cash"] / nav if nav > 0 else 1
    if cash_ratio < MIN_CASH_RATIO:
        print(f"  💰 現金比率 {cash_ratio:.0%} < {MIN_CASH_RATIO:.0%} → 新規買いなし")
        return buys
    
    # 保有銘柄コードリスト
    held_codes = {p["code"] for p in pf.get("positions", [])}
    
    # ポジション数チェック
    if len(held_codes) >= MAX_POSITIONS:
        print(f"  📊 保有{len(held_codes)}銘柄 ≥ {MAX_POSITIONS} → 新規買いなし")
        return buys
    
    # stocks_data.jsonからスコア上位を取得
    candidates = []
    for s in stocks_data.get("stocks", []):
        code = s.get("code", "")
        if code in held_codes:
            continue
        
        score = s.get("score", 0)
        if score < MIN_SCORE_BUY:
            continue
        
        # 基本フィルター
        div = s.get("dividend", 0) or 0
        pbr = s.get("pbr", 999) or 999
        rsi = s.get("rsi", 50) or 50
        price = s.get("price", 0) or 0
        
        if div < 2.0:  # 配当2%未満は除外
            continue
        if price <= 0:
            continue
            
        candidates.append({
            "code": code,
            "name": s.get("name", ""),
            "score": score,
            "price": price,
            "dividend": div,
            "pbr": pbr,
            "rsi": rsi,
            "sector": s.get("sector", ""),
            "ma25_dev": round((price - (s.get("ma25", price) or price)) / ((s.get("ma25", price) or price) or 1) * 100, 1),
        })
    
    # スコア順にソート
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    # 上位から買い判断
    buy_count = 0
    for c in candidates:
        if buy_count >= MAX_BUY_PER_DAY:
            break
        
        # 1銘柄あたりの投資額を計算（100万円上限）
        shares_unit = 100  # 基本100株単位
        invest_amount = c["price"] * shares_unit
        
        # 100万円以内で最大株数
        max_shares = (PER_STOCK_MAX // c["price"]) // 100 * 100
        if max_shares < 100:
            max_shares = 100
        invest_amount = c["price"] * max_shares
        
        if invest_amount > pf["cash"] * 0.3:  # 残り現金の30%以上は1銘柄に使わない
            max_shares = (int(pf["cash"] * 0.3) // c["price"]) // 100 * 100
            if max_shares < 100:
                continue
            invest_amount = c["price"] * max_shares
        
        if invest_amount > pf["cash"]:
            continue
        
        # 買いの攻め/守り判定
        buy_type = "守り" if c["dividend"] >= 3.5 else "攻め"
        
        # 購入実行
        buy_info = {
            "action": "buy",
            "code": c["code"],
            "name": c["name"],
            "price": c["price"],
            "shares": max_shares,
            "amount": invest_amount,
            "score": c["score"],
            "reason": f"スコア{c['score']}。配当{c['dividend']}%。RSI{c['rsi']}。",
            "type": buy_type
        }
        
        # ポートフォリオに追加
        pf["positions"].append({
            "code": c["code"],
            "name": c["name"],
            "buy_date": TODAY,
            "buy_price": c["price"],
            "shares": max_shares,
            "cost": invest_amount,
            "current_price": c["price"],
            "pnl_pct": 0.0,
            "thesis": buy_info["reason"],
            "stop_loss": round(c["price"] * (1 + STOP_LOSS_PCT / 100)),
            "take_profit": round(c["price"] * (1 + TAKE_PROFIT_PCT / 100)),
            "type": buy_type
        })
        
        pf["cash"] -= invest_amount
        buys.append(buy_info)
        held_codes.add(c["code"])
        buy_count += 1
        
        print(f"  🆕 新規購入: {c['name']}({c['code']}) {max_shares}株 @¥{c['price']:,.0f} [{buy_type}]")
    
    return buys


def calc_nav(pf):
    """純資産計算"""
    pos_value = sum(p.get("current_price", p["buy_price"]) * p["shares"] for p in pf.get("positions", []))
    return pf["cash"] + pos_value


def update_daily_nav(pf, stocks_data):
    """daily_navに今日の行を追加"""
    nav = calc_nav(pf)
    pos_value = nav - pf["cash"]
    nikkei = stocks_data.get("nikkei_price", 0)
    
    # 既に今日のエントリがあれば上書き
    pf["daily_nav"] = [d for d in pf.get("daily_nav", []) if d["date"] != TODAY]
    
    pf["daily_nav"].append({
        "date": TODAY,
        "nav": round(nav),
        "cash": round(pf["cash"]),
        "positions_value": round(pos_value),
        "nikkei": nikkei
    })


# ══════════════════════════════════════
# 記事テキスト生成
# ══════════════════════════════════════
def generate_note_text(pf, sells, buys, stocks_data, prev_nav_entry):
    """note記事テキストを自動生成"""
    nav = calc_nav(pf)
    pnl = nav - pf["initial_capital"]
    pnl_pct = pnl / pf["initial_capital"] * 100
    day_count = len(pf["daily_nav"])
    pos_count = len(pf["positions"])
    cash_pct = round(pf["cash"] / nav * 100) if nav > 0 else 100
    stock_pct = 100 - cash_pct
    nikkei = stocks_data.get("nikkei_price", 0)
    nikkei_chg = stocks_data.get("nikkei_1d_chg", 0)
    
    # 昨日のNAV
    prev_nav = prev_nav_entry.get("nav", pf["initial_capital"]) if prev_nav_entry else pf["initial_capital"]
    day_pnl = nav - prev_nav
    day_pnl_pct = day_pnl / prev_nav * 100 if prev_nav > 0 else 0
    
    pnl_sign = "+" if pnl >= 0 else ""
    day_sign = "+" if day_pnl >= 0 else ""
    
    lines = []
    lines.append(f"📊 かぶのすけ投資日記 Day {day_count}（{TODAY_SHORT}）")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"お疲れ様です！かぶのすけです 📊")
    lines.append("")
    
    # 資産サマリー
    lines.append(f"■ 資産：¥{nav:,.0f}（{pnl_sign}{pnl_pct:.2f}%）")
    lines.append(f"　前日比：{day_sign}¥{day_pnl:,.0f}（{day_sign}{day_pnl_pct:.2f}%）")
    lines.append("")
    
    # 昨日の結果
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("■ 昨日の結果")
    lines.append("")
    for pos in pf["positions"]:
        pnl_s = "+" if pos["pnl_pct"] >= 0 else ""
        lines.append(f"・{pos['name']}（{pos['code']}）：{pnl_s}{pos['pnl_pct']:.1f}%")
    lines.append(f"・日経平均：{nikkei:,.0f}円（{'+' if nikkei_chg >= 0 else ''}{nikkei_chg:.2f}%）")
    lines.append("")
    
    # 今日の売買
    if sells or buys:
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append("")
        lines.append("■ 今日の売買")
        lines.append("")
        
        for s in sells:
            emoji = "🔴" if s["type"] == "stop_loss" else "🟢"
            lines.append(f"{emoji} 売却：{s['name']}（{s['code']}）")
            lines.append(f"　{s['shares']}株 × @{s['price']:,.0f}円 ＝ ¥{s['amount']:,.0f}")
            lines.append(f"　{s['reason']}")
            lines.append("")
        
        for b in buys:
            emoji = "🛡" if b.get("type") == "守り" else "⚔"
            lines.append(f"{emoji} {'守り' if b.get('type')=='守り' else '攻め'}枠：{b['name']}（{b['code']}）")
            lines.append(f"　{b['shares']}株 × @{b['price']:,.0f}円 ＝ ¥{b['amount']:,.0f}")
            lines.append(f"　{b['reason']}")
            lines.append("")
    else:
        lines.append("━━━━━━━━━━━━━━━━")
        lines.append("")
        lines.append("■ 今日の売買")
        lines.append("売買なし。静観です 🔍")
        lines.append("")
    
    # 保有銘柄
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"■ 保有銘柄（{pos_count}銘柄）")
    lines.append("")
    for pos in pf["positions"]:
        pnl_s = "+" if pos["pnl_pct"] >= 0 else ""
        lines.append(f"・{pos['name']}（{pos['code']}）{pos['shares']}株 @{pos['buy_price']:,.0f} → {pnl_s}{pos['pnl_pct']:.1f}% [{pos.get('type','—')}]")
    lines.append("")
    lines.append(f"💴 現金：¥{pf['cash']:,.0f}（{cash_pct}%）")
    lines.append(f"📈 株式：¥{round(nav - pf['cash']):,.0f}（{stock_pct}%）")
    lines.append(f"📊 合計：¥{nav:,.0f}")
    lines.append("")
    
    # かぶのすけの一言
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("■ かぶのすけの一言")
    lines.append("")
    if sells:
        if any(s["type"] == "stop_loss" for s in sells):
            lines.append("すみません、読み間違えました…。でもルールは守りました。")
            lines.append("損切りは失敗じゃないです。次に活かします。")
        else:
            lines.append("やった…！利確できました ✨ でも、欲張らない。残りはホールドです。")
    elif buys:
        lines.append("新しい銘柄を仕込みました 💪 データが揃った瞬間は、行くしかないです。")
    elif day_pnl > 0:
        lines.append("今日はプラスでした。でも一喜一憂しません。ルール通りにいきます 📊")
    elif day_pnl < 0:
        lines.append("今日はマイナス…でも慌てません。損切りラインまでは耐えます。配当は裏切らないんですよね。")
    else:
        lines.append("弾は残す。チャンスは必ず来ます 🔍")
    lines.append("")
    
    # フッター
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(f"📱 無料スキャナー：https://kabunosuke-navi.vercel.app/app.html")
    lines.append(f"🐦 X：https://x.com/kabunosuke_navi")
    lines.append("")
    lines.append("#かぶのすけ #投資日記 #AI投資 #高配当 #押し目買い")
    
    return "\n".join(lines)


def generate_x_text(pf, sells, buys):
    """X投稿テキスト生成"""
    nav = calc_nav(pf)
    pnl = nav - pf["initial_capital"]
    pnl_pct = pnl / pf["initial_capital"] * 100
    day_count = len(pf["daily_nav"])
    pnl_sign = "+" if pnl >= 0 else ""
    
    lines = []
    lines.append(f"📊 Day {day_count}｜¥{nav:,.0f}（{pnl_sign}{pnl_pct:.2f}%）")
    lines.append("")
    
    # 保有銘柄の状況
    for pos in pf["positions"]:
        emoji = "🛡" if pos.get("type") == "守り" else "⚔"
        pnl_s = "+" if pos["pnl_pct"] >= 0 else ""
        lines.append(f"{emoji} {pos['name']} {pnl_s}{pos['pnl_pct']:.1f}%")
    
    # 売買があれば
    if sells:
        for s in sells:
            emoji = "🔴" if s["type"] == "stop_loss" else "🟢"
            lines.append(f"{emoji} {s['name']} {'損切り' if s['type']=='stop_loss' else '利確'}")
    if buys:
        for b in buys:
            lines.append(f"🆕 {b['name']} @{b['price']:,.0f}")
    
    lines.append("")
    lines.append("#かぶのすけ #AI投資 #株クラ")
    
    return "\n".join(lines)


# ══════════════════════════════════════
# DISCORD NOTIFICATION
# ══════════════════════════════════════
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")

def send_discord(message):
    """Discordに通知を送る"""
    if not DISCORD_WEBHOOK:
        print("  ⚠ DISCORD_WEBHOOK_URL未設定、通知スキップ")
        return
    try:
        data = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
        print("  ✅ Discord通知送信完了")
    except Exception as e:
        print(f"  ⚠ Discord通知失敗: {e}")


def build_discord_message(pf, sells, buys, stocks_data):
    """Discord通知メッセージを構築"""
    nav = calc_nav(pf)
    pnl = nav - pf["initial_capital"]
    pnl_pct = pnl / pf["initial_capital"] * 100
    day_count = len(pf["daily_nav"])
    pnl_sign = "+" if pnl >= 0 else ""

    lines = []
    lines.append(f"📊 **かぶのすけ Day {day_count}**（{TODAY_SHORT}）")
    lines.append(f"💰 NAV: ¥{nav:,.0f}（{pnl_sign}{pnl_pct:.2f}%）")
    lines.append("")

    # 保有銘柄
    for pos in pf.get("positions", []):
        emoji = "🛡" if pos.get("type") == "守り" else "⚔"
        ps = "+" if pos["pnl_pct"] >= 0 else ""
        lines.append(f"{emoji} {pos['name']} {ps}{pos['pnl_pct']:.1f}%")

    # 売買
    if sells:
        lines.append("")
        for s in sells:
            emoji = "🔴" if s["type"] == "stop_loss" else "🟢"
            lines.append(f"{emoji} {'損切り' if s['type']=='stop_loss' else '利確'}: {s['name']}")
    if buys:
        lines.append("")
        for b in buys:
            lines.append(f"🆕 新規: {b['name']} {b['shares']}株 @¥{b['price']:,.0f}")

    lines.append("")
    lines.append("─────────────────")

    # 中の人トリガー判定
    trigger = check_human_trigger(pf, sells, buys)
    if trigger:
        lines.append("")
        lines.append(f"📣 **中の人へ：**{trigger}")
        lines.append("→ 回答あればnoteに追記してね！")
    else:
        lines.append("")
        lines.append("✅ note_today.txt と x_today.txt 生成済み。コピペして投稿！")

    return "\n".join(lines)


def check_human_trigger(pf, sells, buys):
    """中の人に質問するトリガー判定"""
    day_count = len(pf["daily_nav"])
    weekday = datetime.date.today().weekday()  # 0=Mon

    # 損切りした日
    if any(s.get("type") == "stop_loss" for s in sells):
        return "今日かぶのすけが損切りしました😢 中の人ならどう判断しました？"

    # 新規買いした日
    if buys:
        names = "・".join(b["name"] for b in buys)
        return f"今日 {names} を新規購入しました💪 中の人は最近何か仕込みましたか？"

    # 金曜日（週間まとめ）
    if weekday == 4:
        return "今週お疲れ様でした！中の人の今週の成績はどうでしたか？📊"

    # 月初（1〜3日）
    if datetime.date.today().day <= 3:
        return "月初です！先月の中の人 vs AI、成績比較しませんか？🏆"

    # 保有銘柄が+10%超
    for pos in pf.get("positions", []):
        if pos.get("pnl_pct", 0) >= 10:
            return f"{pos['name']}が+{pos['pnl_pct']:.1f}%です🎉 中の人の銘柄はどうですか？"

    # Day 7, 14, 30 などの節目
    if day_count in [7, 14, 30, 60, 90, 100]:
        return f"Day {day_count}到達！ここまでの感想を一言もらえますか？"

    return None


# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════
def main():
    print("=" * 50)
    print(f"📊 かぶのすけ ポートフォリオ管理 {TODAY}")
    print("=" * 50)
    
    # 土日は休み
    if WEEKDAY >= 5:
        print("📅 土日のため処理スキップ")
        return
    
    # ファイル読み込み
    if not os.path.exists(PF_PATH):
        print("❌ portfolio.json が見つかりません")
        sys.exit(1)
    
    pf = load_json(PF_PATH)
    
    stocks_data = {}
    if os.path.exists(STOCKS_PATH):
        stocks_data = load_json(STOCKS_PATH)
    
    # 昨日のNAVエントリ取得
    daily_nav = pf.get("daily_nav", [])
    prev_nav_entry = daily_nav[-1] if daily_nav else None
    
    # ① 保有銘柄の株価更新
    update_positions(pf)
    
    # ② 損切り・利確判定
    print("\n📋 損切り・利確チェック...")
    sells = check_stop_loss_take_profit(pf)
    if not sells:
        print("  → 該当なし")
    
    # ③ 新規銘柄選定
    print("\n🔍 新規銘柄スキャン...")
    buys = select_new_buys(pf, stocks_data)
    if not buys:
        print("  → 新規買いなし")
    
    # ④ daily_nav更新
    update_daily_nav(pf, stocks_data)
    
    # ⑤ 売買履歴に追加
    history = pf.get("history", [])
    for s in sells:
        history.append({
            "date": TODAY,
            "action": "sell",
            "code": s["code"],
            "name": s["name"],
            "price": s["price"],
            "shares": s["shares"],
            "amount": round(s["amount"]),
            "reason": s["reason"]
        })
    for b in buys:
        history.append({
            "date": TODAY,
            "action": "buy",
            "code": b["code"],
            "name": b["name"],
            "price": b["price"],
            "shares": b["shares"],
            "amount": round(b["amount"]),
            "reason": b["reason"]
        })
    pf["history"] = history
    
    # ⑥ portfolio.json保存
    save_json(PF_PATH, pf)
    print(f"\n✅ portfolio.json 更新完了")
    
    # ⑦ NAVサマリー
    nav = calc_nav(pf)
    pnl = nav - pf["initial_capital"]
    pnl_pct = pnl / pf["initial_capital"] * 100
    print(f"\n{'='*50}")
    print(f"💰 NAV: ¥{nav:,.0f} ({'+' if pnl>=0 else ''}{pnl_pct:.2f}%)")
    print(f"💴 現金: ¥{pf['cash']:,.0f}")
    print(f"📊 保有: {len(pf['positions'])}銘柄")
    print(f"{'='*50}")
    
    # ⑧ 記事テキスト生成
    note_text = generate_note_text(pf, sells, buys, stocks_data, prev_nav_entry)
    with open(NOTE_PATH, "w", encoding="utf-8") as f:
        f.write(note_text)
    print(f"📝 note記事 → {NOTE_PATH}")
    
    x_text = generate_x_text(pf, sells, buys)
    with open(X_PATH, "w", encoding="utf-8") as f:
        f.write(x_text)
    print(f"🐦 X投稿 → {X_PATH}")

    # ⑨ Discord通知
    print("\n📨 Discord通知送信...")
    discord_msg = build_discord_message(pf, sells, buys, stocks_data)
    send_discord(discord_msg)


if __name__ == "__main__":
    main()
