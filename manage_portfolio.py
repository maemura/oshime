#!/usr/bin/env python3
"""
かぶのすけ 仮想ポートフォリオ管理
stocks_data.json を読み、portfolio.json を更新
"""
import json
import os
from datetime import datetime

TODAY = datetime.now().strftime("%Y-%m-%d")

# ─── スコア計算（JS側と同等） ───
def calc_score(s):
    score = 0
    mc = s.get("market_cap_b", 0) or 0
    if mc >= 30000: score += 18
    elif mc >= 10000: score += 15
    elif mc >= 5000: score += 12
    elif mc >= 3000: score += 9
    elif mc >= 1000: score += 6
    elif mc >= 500: score += 3

    div = s.get("dividend", 0) or 0
    if div >= 4: score += 15
    elif div >= 3.5: score += 13
    elif div >= 3: score += 11
    elif div >= 2.5: score += 8
    elif div >= 2: score += 5

    ma75d = round((s.get("price",0) - s.get("ma75", s.get("price",0))) / (s.get("ma75", s.get("price",0)) or 1) * 100, 1)
    if -3 <= ma75d <= 0: score += 15
    elif -5 <= ma75d < -3: score += 12
    elif 0 < ma75d <= 3: score += 10
    elif -8 <= ma75d < -5: score += 7

    ma25d = round((s.get("price",0) - s.get("ma25", s.get("price",0))) / (s.get("ma25", s.get("price",0)) or 1) * 100, 1)
    if -3 <= ma25d <= 0: score += 10
    elif -5 <= ma25d < -3: score += 7
    elif 0 < ma25d <= 2: score += 5

    ret120 = s.get("ret120", 0) or 0
    if ret120 >= 15: score += 10
    elif ret120 >= 8: score += 8
    elif ret120 >= 3: score += 6
    elif ret120 >= 0: score += 4

    ret60 = s.get("ret60", 0) or 0
    if ret60 >= 10: score += 8
    elif ret60 >= 5: score += 6
    elif ret60 >= 0: score += 4

    ret20 = s.get("ret20", 0) or 0
    if ret20 >= 5: score += 5
    elif ret20 >= 0: score += 3

    return min(score, 100)

def get_trend_type(s):
    ma75d = round((s.get("price",0) - s.get("ma75", s.get("price",0))) / (s.get("ma75", s.get("price",0)) or 1) * 100, 1)
    ma25d = round((s.get("price",0) - s.get("ma25", s.get("price",0))) / (s.get("ma25", s.get("price",0)) or 1) * 100, 1)
    mc = s.get("market_cap_b", 0) or 0
    div = s.get("dividend", 0) or 0

    if ma75d < -8:
        return "falling"
    elif ma75d < -2 and mc >= 3000 and div >= 2.5:
        return "value_dip"
    elif -5 <= ma75d <= 3 and ma25d < -1:
        return "dip"
    elif ma75d > 0 and ma25d > 0 and mc >= 1000:
        return "momentum"
    elif ma75d >= -2 and ma25d > 0:
        return "bounce"
    else:
        return "neutral"

# ─── 売買ルール ───
# 【買い】スコア60以上、時価総額3000億以上、配当2.5%以上、最大10銘柄、1銘柄100万円
# 【損切り】買値から-15% or 75日線割れ5日連続
# 【利確】+20%で半分売却
# 【ナンピン】保有が-5%以上下落＆75日線上 → 追加50万

def run():
    # データ読み込み
    if not os.path.exists("stocks_data.json"):
        print("❌ stocks_data.json なし")
        return
    if not os.path.exists("portfolio.json"):
        print("❌ portfolio.json なし")
        return

    with open("stocks_data.json") as f:
        stock_data = json.load(f)
    with open("portfolio.json") as f:
        pf = json.load(f)

    stocks = stock_data.get("stocks", [])
    if not stocks:
        print("❌ 銘柄データなし")
        return

    # 既に今日処理済みなら最終NAVだけ更新
    if pf["daily_nav"] and pf["daily_nav"][-1]["date"] == TODAY:
        print(f"📅 {TODAY} は処理済み。NAV更新のみ。")

    # 全銘柄にスコア付与
    stock_map = {}
    for s in stocks:
        s["_score"] = calc_score(s)
        s["_type"] = get_trend_type(s)
        stock_map[s["code"]] = s

    actions = []
    cash = pf["cash"]
    positions = pf["positions"]
    held_codes = {p["code"] for p in positions}

    # ── 売り判定 ──
    new_positions = []
    for p in positions:
        s = stock_map.get(p["code"])
        if not s:
            new_positions.append(p)
            continue

        current_price = s.get("price", p["buy_price"])
        p["current_price"] = current_price
        pnl_pct = (current_price - p["buy_price"]) / p["buy_price"] * 100

        # 損切り: -15%
        if pnl_pct <= -15:
            sell_amount = current_price * p["shares"]
            cash += sell_amount
            actions.append({
                "date": TODAY, "action": "sell_loss", "code": p["code"],
                "name": p["name"], "price": current_price, "shares": p["shares"],
                "pnl_pct": round(pnl_pct, 1),
                "reason": f"損切り {pnl_pct:.1f}%。ルール通り。"
            })
            held_codes.discard(p["code"])
            continue

        # 75日線割れ（ma75乖離 < -5%が5日以上）
        ma75d = round((s.get("price",0) - s.get("ma75", s.get("price",0))) / (s.get("ma75", s.get("price",0)) or 1) * 100, 1)
        if ma75d < -5:
            p["below_ma75_days"] = p.get("below_ma75_days", 0) + 1
            if p["below_ma75_days"] >= 5:
                sell_amount = current_price * p["shares"]
                cash += sell_amount
                actions.append({
                    "date": TODAY, "action": "sell_loss", "code": p["code"],
                    "name": p["name"], "price": current_price, "shares": p["shares"],
                    "pnl_pct": round(pnl_pct, 1),
                    "reason": f"75日線割れ{p['below_ma75_days']}日。撤退。"
                })
                held_codes.discard(p["code"])
                continue
        else:
            p["below_ma75_days"] = 0

        # 利確: +20%で半分売却
        if pnl_pct >= 20 and not p.get("half_sold"):
            half = p["shares"] // 2
            if half > 0:
                sell_amount = current_price * half
                cash += sell_amount
                p["shares"] -= half
                p["half_sold"] = True
                actions.append({
                    "date": TODAY, "action": "sell_profit", "code": p["code"],
                    "name": p["name"], "price": current_price, "shares": half,
                    "pnl_pct": round(pnl_pct, 1),
                    "reason": f"+{pnl_pct:.1f}%達成。半分利確。残りホールド。"
                })

        p["pnl_pct"] = round(pnl_pct, 1)
        new_positions.append(p)

    positions = new_positions

    # ── 買い判定 ──
    if len(positions) < 10:
        candidates = [s for s in stocks if
                      s["_score"] >= 60 and
                      (s.get("market_cap_b", 0) or 0) >= 3000 and
                      (s.get("dividend", 0) or 0) >= 2.5 and
                      s["code"] not in held_codes and
                      s["_type"] in ("dip", "value_dip")]
        candidates.sort(key=lambda x: -x["_score"])

        for s in candidates[:3]:  # 1日最大3銘柄
            if len(positions) >= 10:
                break
            if cash < 500000:  # 最低50万は残す
                break

            price = s.get("price", 0)
            if price <= 0:
                continue

            # 1銘柄100万円まで。100株単位
            budget = min(1000000, cash - 500000)
            shares = (budget // (price * 100)) * 100
            if shares <= 0:
                # 高い株は1単元(100株)で
                if price * 100 <= budget:
                    shares = 100
                else:
                    continue

            cost = price * shares
            if cost > cash:
                continue

            cash -= cost
            positions.append({
                "code": s["code"],
                "name": s.get("name", s["code"]),
                "buy_date": TODAY,
                "buy_price": price,
                "shares": shares,
                "cost": cost,
                "current_price": price,
                "pnl_pct": 0,
                "below_ma75_days": 0,
                "half_sold": False,
            })
            held_codes.add(s["code"])
            div_str = f"配当{s.get('dividend',0):.1f}%" if s.get("dividend") else ""
            actions.append({
                "date": TODAY, "action": "buy", "code": s["code"],
                "name": s.get("name", s["code"]),
                "price": price, "shares": shares,
                "reason": f"スコア{s['_score']}。{div_str}。{s['_type']}。"
            })

    # ── ナンピン判定 ──
    for p in positions:
        s = stock_map.get(p["code"])
        if not s:
            continue
        pnl_pct = p.get("pnl_pct", 0)
        ma75d = round((s.get("price",0) - s.get("ma75", s.get("price",0))) / (s.get("ma75", s.get("price",0)) or 1) * 100, 1)
        if pnl_pct <= -5 and ma75d > -5 and not p.get("nanpin_done") and cash >= 500000:
            price = s.get("price", p["buy_price"])
            budget = min(500000, cash - 300000)
            shares = (budget // (price * 100)) * 100
            if shares >= 100:
                cost = price * shares
                # 平均買い付け価格を再計算
                total_shares = p["shares"] + shares
                avg_price = (p["buy_price"] * p["shares"] + price * shares) / total_shares
                p["buy_price"] = round(avg_price)
                p["shares"] = total_shares
                p["cost"] += cost
                p["nanpin_done"] = True
                cash -= cost
                actions.append({
                    "date": TODAY, "action": "nanpin", "code": p["code"],
                    "name": p["name"], "price": price, "shares": shares,
                    "reason": f"{pnl_pct:.1f}%下落でナンピン。75日線上。"
                })

    # ── NAV計算 ──
    positions_value = sum(
        (stock_map.get(p["code"], {}).get("price", p.get("current_price", p["buy_price"])) * p["shares"])
        for p in positions
    )
    nav = cash + positions_value

    nikkei = stock_data.get("nikkei_price")

    # ── 保存 ──
    pf["cash"] = round(cash)
    pf["positions"] = positions
    pf["history"] = pf.get("history", []) + actions

    # daily_nav追加（同日なら上書き）
    nav_entry = {
        "date": TODAY,
        "nav": round(nav),
        "cash": round(cash),
        "positions_value": round(positions_value),
        "nikkei": nikkei,
    }
    if pf["daily_nav"] and pf["daily_nav"][-1]["date"] == TODAY:
        pf["daily_nav"][-1] = nav_entry
    else:
        pf["daily_nav"].append(nav_entry)

    with open("portfolio.json", "w") as f:
        json.dump(pf, f, ensure_ascii=False, indent=2)

    # ── レポート ──
    pnl = nav - pf["initial_capital"]
    pnl_pct = pnl / pf["initial_capital"] * 100
    print(f"\n{'='*50}")
    print(f"📊 かぶのすけ投資日記 Day {len(pf['daily_nav'])}")
    print(f"{'='*50}")
    print(f"💰 資産: ¥{nav:,.0f}（{'+' if pnl>=0 else ''}{pnl_pct:.2f}%）")
    print(f"   現金: ¥{cash:,.0f} / 株式: ¥{positions_value:,.0f}")
    print(f"📋 保有: {len(positions)}銘柄")
    for p in positions:
        pct = p.get("pnl_pct", 0)
        print(f"   {p['name']}({p['code']}) {'+' if pct>=0 else ''}{pct:.1f}% @¥{p['buy_price']:,} x{p['shares']}株")

    if actions:
        print(f"\n🔔 今日の売買:")
        for a in actions:
            icon = "🟢" if a["action"] == "buy" else "🔴" if "sell" in a["action"] else "🟡"
            label = {"buy":"買い","sell_loss":"損切り","sell_profit":"利確","nanpin":"ナンピン"}.get(a["action"], a["action"])
            print(f"   {icon} {label} {a['name']} @¥{a['price']:,} x{a['shares']}株")
            print(f"     → {a['reason']}")
    else:
        print(f"\n😴 今日の売買: なし（様子見）")

    print(f"{'='*50}")

if __name__ == "__main__":
    run()
