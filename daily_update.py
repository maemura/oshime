#!/usr/bin/env python3
"""
かぶのすけ 全保有銘柄の終値更新 & 自動コミット
- yfinanceで全保有銘柄(positions + holdings)の終値を取得
- portfolio.json の current_price / pnl_pct / total_asset を更新
- daily_nav を追記
- git add / commit / push まで自動実行
"""

import json, os, sys, subprocess, datetime, time

# ── パス ──
BASE = os.path.dirname(os.path.abspath(__file__))
PF_PATH = os.path.join(BASE, "portfolio.json")

TODAY = datetime.date.today().strftime("%Y-%m-%d")
TODAY_SHORT = datetime.date.today().strftime("%Y/%m/%d")


def load_portfolio():
    with open(PF_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolio(pf):
    with open(PF_PATH, "w", encoding="utf-8") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)
    print("✅ portfolio.json 保存完了")


def fetch_close_price(code):
    """yfinanceで終値を取得"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{code}.T")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        info = ticker.fast_info
        price = info.get("lastPrice", 0) or info.get("last_price", 0)
        if price and price > 10:
            return float(price)
    except Exception as e:
        print(f"  ⚠️ {code} 取得失敗: {e}")
    return None


def update_positions(positions):
    """positionsリストの終値を更新、更新数を返す"""
    updated = 0
    for pos in positions:
        code = pos["code"]
        price = fetch_close_price(code)
        time.sleep(0.3)
        if price is None:
            print(f"  ❌ {code} {pos.get('name', '')} — 取得失敗（スキップ）")
            continue
        old_price = pos.get("current_price", pos.get("buy_price", 0))
        pos["current_price"] = price
        buy = pos.get("buy_price", 0)
        if buy and buy > 0:
            pos["pnl_pct"] = round((price - buy) / buy * 100, 1)
        print(f"  📊 {code} {pos.get('name', '')}: ¥{old_price:,.0f} → ¥{price:,.0f} ({pos.get('pnl_pct', 0):+.1f}%)")
        updated += 1
    return updated


def calc_total_asset(pf):
    """総資産を再計算
    cash にはpositions購入前の金額が入っているため、
    positions のコストを差し引いてから時価を加算する。
    """
    cash = pf.get("cash", 0)
    pos_cost = sum(
        p.get("cost", p.get("buy_price", 0) * p.get("shares", 0))
        for p in pf.get("positions", [])
    )
    pos_value = sum(
        p.get("current_price", p.get("buy_price", 0)) * p.get("shares", 0)
        for p in pf.get("positions", [])
    )
    hold_value = sum(
        h.get("current_price", h.get("buy_price", 0)) * h.get("shares", 0)
        for h in pf.get("holdings", [])
    )
    actual_cash = cash - pos_cost
    total = actual_cash + pos_value + hold_value
    return total, pos_value + hold_value


def update_daily_nav(pf, total, positions_value):
    """daily_navに本日分を追記（既存なら上書き）"""
    # actual cash = cash - positions cost
    pos_cost = sum(
        p.get("cost", p.get("buy_price", 0) * p.get("shares", 0))
        for p in pf.get("positions", [])
    )
    actual_cash = pf.get("cash", 0) - pos_cost
    nav_entry = {
        "date": TODAY,
        "nav": total,
        "cash": actual_cash,
        "positions_value": positions_value,
    }
    daily_nav = pf.get("daily_nav", [])
    # 同日エントリがあれば上書き
    for i, entry in enumerate(daily_nav):
        if entry.get("date") == TODAY:
            daily_nav[i] = nav_entry
            return
    daily_nav.append(nav_entry)


def git_commit_push(pf, total):
    """git add / commit / push"""
    day = pf.get("day", "?")
    initial = pf.get("initial_capital", 10000000)
    pnl = (total - initial) / initial * 100

    msg = f"📊 portfolio: Day{day} {TODAY_SHORT} 全銘柄終値更新 総資産{pnl:+.1f}%"
    print(f"\n🔄 Git: {msg}")

    subprocess.run(["git", "add", "portfolio.json"], cwd=BASE, check=True)
    subprocess.run(["git", "commit", "-m", msg], cwd=BASE, check=True)
    subprocess.run(["git", "push"], cwd=BASE, check=True)
    print("✅ push完了")


def main():
    print(f"📊 かぶのすけ 終値更新 {TODAY}")
    print("=" * 50)

    pf = load_portfolio()

    # ① 全保有銘柄の終値取得 & 更新
    updated = 0
    if pf.get("positions"):
        print("\n【positions】")
        updated += update_positions(pf["positions"])
    if pf.get("holdings"):
        print("\n【holdings】")
        updated += update_positions(pf["holdings"])

    if updated == 0:
        print("\n⚠️ 更新された銘柄がありません。終了します。")
        sys.exit(1)

    # ② 総資産再計算
    total, positions_value = calc_total_asset(pf)
    initial = pf.get("initial_capital", 10000000)
    pnl_pct = round((total - initial) / initial * 100, 2)

    pf["total_asset"] = total
    pf["pnl_pct"] = pnl_pct
    pf["date"] = TODAY

    update_daily_nav(pf, total, positions_value)
    save_portfolio(pf)

    # 結果表示
    print("\n" + "=" * 50)
    print(f"💰 総資産: ¥{total:,.0f}")
    print(f"📈 開始来損益: {pnl_pct:+.2f}%")
    print(f"🔄 更新銘柄数: {updated}")
    print("=" * 50)

    # ③ git add / commit / push
    git_commit_push(pf, total)


if __name__ == "__main__":
    main()
