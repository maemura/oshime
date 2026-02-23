#!/usr/bin/env python3
"""
backtest.py — 過去1年バックテスト + 配点最適化
==============================================
過去52週間を1週間ずつシミュレーション:
  1. 各週の月曜にスコアリング → TOP5選定
  2. 5日後（金曜）の株価で検証
  3. 4週ごとに配点を微調整
  4. 最終的な最適配点を weights.json に出力

使い方: python3 backtest.py
所要時間: 約5〜10分（データダウンロードに時間がかかる）
"""

import json, os, math, sys, time
from datetime import datetime, timedelta
from collections import defaultdict

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("必要ライブラリ: pip3 install yfinance pandas numpy")
    sys.exit(1)

# ═══════════════════════════════════════
# 設定
# ═══════════════════════════════════════
BACKTEST_START = "2025-02-01"
BACKTEST_END   = "2026-02-21"
OPTIMIZE_EVERY = 4  # 4週ごとに配点調整
MAX_ADJ = 3         # 1回の調整で±3pt以内
TOP_N = 5           # TOP5を推薦

# 連続増配銘柄（fetch_stocks.pyと同じ）
DIVIDEND_GROWERS = {
    "4452": 15, "8566": 26, "9433": 23, "8591": 26, "4732": 14,
    "9432": 14, "8316": 14, "8593": 15, "7466": 14, "2914": 21,
    "9434": 10, "8001": 11, "8053": 11, "8058": 10, "8031": 12,
    "4502": 12, "8766": 13, "8309": 11, "6098": 11, "2124": 14,
    "9783": 14, "4967": 12, "7164": 11, "2413": 13, "9142": 12,
    "6301": 14, "7974": 12, "8795": 11, "1925": 12, "2802": 13,
    "6869": 11, "4684": 14, "7741": 10, "4543": 13, "6367": 12,
    "9020": 10, "6902": 11, "7269": 10, "4063": 10, "6273": 12,
    "4519": 10, "8697": 10, "6645": 12, "9436": 10, "3659": 11,
    "1928": 10, "2503": 10, "9303": 10, "7272": 10,
    "8306": 7, "8411": 7, "7267": 6, "7203": 6, "5108": 6,
    "6752": 5, "6758": 5, "4661": 8, "4689": 5, "6501": 6,
    "6503": 5, "7751": 7, "9984": 5, "6861": 8, "4307": 7,
    "2801": 6, "8750": 8, "9843": 5, "8354": 6, "1605": 7,
    "5401": 5, "3405": 5, "5020": 6, "5019": 6, "2502": 7,
    "7201": 5, "9613": 5, "3382": 5, "8801": 6, "8802": 6,
    "4901": 6, "3088": 5, "2768": 5, "6954": 6, "3099": 5,
    "8252": 5, "9101": 5, "9104": 5, "9107": 5,
}

# 初期配点（v3手動設定）
INITIAL_WEIGHTS = {
    "w_dividend":       20,
    "w_market_cap":     10,
    "w_div_growth":     10,
    "w_dip_zscore":     15,
    "w_pbr":             5,
    "w_ret5_vs_sector": 20,
    "w_ret5":           10,
    "w_ret10":           5,
    "w_stable_bonus":    5,
    "w_sector_penalty": -5,
}

# ═══════════════════════════════════════
# STEP 1: データダウンロード
# ═══════════════════════════════════════
def download_universe():
    """バックテスト対象銘柄のデータを一括ダウンロード"""
    # 大型高配当の主要銘柄（時価総額上位+高配当）
    # 本番では1600銘柄だが、バックテストは主要200銘柄で十分
    codes = [
        # 銀行・金融
        "8306","8316","8411","8308","8309","8354","8766","8750","8795","8591","8593","8697",
        # 商社
        "8001","8002","8031","8053","8058",
        # 通信
        "9432","9433","9434",
        # 自動車
        "7203","7267","7269","7201","7270","7272",
        # 医薬品
        "4502","4503","4519","4507","4543","4568",
        # 食品
        "2914","2801","2802","2503","2502","2269",
        # 電機
        "6501","6503","6752","6758","6861","6902","6954","6645","6367","6273","6301",
        # 不動産
        "8801","8802","8830",
        # エネルギー
        "5020","5019","1605",
        # 素材・化学
        "5401","3405","4063","4901","4452",
        # 建設
        "1925","1928","1802","1803",
        # サービス
        "9020","9021","9022","2124","2413","2181","6098","9783","4661","4689",
        # IT
        "9984","4684","3659","7741","7751","4307","9613","3382",
        # その他
        "5108","7974","9843","7164","7172","9142","9303","9436","9101","9104","9107",
        "3088","3099","8252","2768","4732","4967","7466","8566",
    ]
    
    tickers = [f"{c}.T" for c in codes]
    print(f"📡 {len(codes)}銘柄の過去1年データをダウンロード中...")
    
    # 一括ダウンロード（高速）
    start = (datetime.strptime(BACKTEST_START, "%Y-%m-%d") - timedelta(days=60)).strftime("%Y-%m-%d")
    data = yf.download(tickers, start=start, end=BACKTEST_END, progress=True)
    
    print(f"✅ ダウンロード完了: {data.shape}")
    return codes, data

def get_stock_info_bulk(codes):
    """銘柄の静的情報（配当、セクター、時価総額等）を取得"""
    print(f"📡 銘柄情報を取得中（{len(codes)}銘柄）...")
    info_map = {}
    
    for i, code in enumerate(codes):
        try:
            t = yf.Ticker(f"{code}.T")
            info = t.info
            info_map[code] = {
                "sector": info.get("sector", "その他"),
                "dividend": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "market_cap_b": round(info.get("marketCap", 0) / 1e8) if info.get("marketCap") else 0,
                "pbr": info.get("priceToBook", 0) or 0,
                "per": info.get("trailingPE", 0) or 0,
                "name": info.get("shortName", code),
                "div_growth_years": DIVIDEND_GROWERS.get(code, 0),
            }
            if (i + 1) % 20 == 0:
                print(f"  ... {i+1}/{len(codes)}")
                time.sleep(1)  # レート制限対策
        except Exception as e:
            info_map[code] = {
                "sector": "その他", "dividend": 0, "market_cap_b": 0,
                "pbr": 0, "per": 0, "name": code,
                "div_growth_years": DIVIDEND_GROWERS.get(code, 0),
            }
    
    print(f"✅ 銘柄情報取得完了: {len(info_map)}件")
    return info_map

# ═══════════════════════════════════════
# STEP 2: スコアリング関数
# ═══════════════════════════════════════
def calc_indicators(code, price_data, date_idx, info):
    """特定の日付における各種指標を計算"""
    try:
        closes = price_data[:date_idx + 1]
        if len(closes) < 26:
            return None
        
        price = float(closes.iloc[-1])
        if price <= 0 or math.isnan(price):
            return None
        
        # MA25
        ma25 = float(closes.iloc[-25:].mean())
        
        # ボラティリティ（20日）
        rets = closes.pct_change().iloc[-20:]
        vol = float(rets.std()) if len(rets) >= 10 else 0.01
        if vol <= 0 or math.isnan(vol):
            vol = 0.01
        
        # dip_zscore
        dev = (price - ma25) / ma25
        dip_zscore = round(dev / vol, 2) if vol > 0 else 0
        
        # ret5, ret10
        ret5 = round((price / float(closes.iloc[-6]) - 1) * 100, 2) if len(closes) >= 6 else 0
        ret10 = round((price / float(closes.iloc[-11]) - 1) * 100, 2) if len(closes) >= 11 else 0
        
        if math.isnan(ret5): ret5 = 0
        if math.isnan(ret10): ret10 = 0
        if math.isnan(dip_zscore): dip_zscore = 0
        
        return {
            "code": code,
            "price": price,
            "ma25": ma25,
            "dip_zscore": dip_zscore,
            "ret5": ret5,
            "ret10": ret10,
            "volatility": round(vol * 100, 2),
            **info,
        }
    except:
        return None

def score_stock(s, weights):
    """配点に基づいてスコアを計算"""
    div = s.get("dividend", 0)
    mc = s.get("market_cap_b", 0)
    if div < 2 or mc < 500:
        return 0
    
    score = 0
    W = weights
    
    # 配当利回り
    w = W.get("w_dividend", 20)
    score += (w if div >= 5 else w*0.85 if div >= 4.5 else w*0.7 if div >= 4
              else w*0.55 if div >= 3.5 else w*0.4 if div >= 3 else w*0.25 if div >= 2.5
              else w*0.1 if div >= 2 else 0)
    
    # 時価総額
    w = W.get("w_market_cap", 10)
    score += (w if mc >= 50000 else w*0.9 if mc >= 10000 else w*0.8 if mc >= 5000
              else w*0.6 if mc >= 1000 else w*0.3 if mc >= 500 else 0)
    
    # 増配ボーナス
    w = W.get("w_div_growth", 10)
    dgy = s.get("div_growth_years", 0)
    score += (w if dgy >= 15 else w*0.7 if dgy >= 10 else w*0.5 if dgy >= 7
              else w*0.3 if dgy >= 5 else 0)
    
    # 自分比押し目度
    w = W.get("w_dip_zscore", 15)
    z = s.get("dip_zscore", 0)
    score += (w if z <= -3.0 else w*0.8 if z <= -2.0 else w*0.6 if z <= -1.5
              else w*0.4 if z <= -1.0 else w*0.2 if z <= -0.5 else 0)
    
    # PBR
    w = W.get("w_pbr", 5)
    pbr = s.get("pbr", 99)
    score += (w if pbr <= 0.7 else w*0.8 if pbr <= 0.9 else w*0.6 if pbr <= 1.2
              else w*0.2 if pbr <= 1.5 else 0)
    
    # 個別vsセクター差分
    w = W.get("w_ret5_vs_sector", 20)
    diff5 = s.get("ret5_vs_sector", 0)
    score += (w if diff5 <= -5 else w*0.75 if diff5 <= -3 else w*0.5 if diff5 <= -1.5
              else w*0.25 if diff5 <= -0.5 else 0)
    
    # セクターペナルティ
    sec_r5 = s.get("sector_ret5", 0)
    if sec_r5 <= -3:
        score += W.get("w_sector_penalty", -5)
    
    # 個別5日下落
    w = W.get("w_ret5", 10)
    r5 = s.get("ret5", 0)
    score += (w if r5 <= -5 else w*0.7 if r5 <= -3 else w*0.4 if r5 <= -1.5
              else w*0.1 if r5 <= -0.5 else 0)
    
    # 10日リターン
    w = W.get("w_ret10", 5)
    r10 = s.get("ret10", 0)
    score += (w if r10 <= -8 else w*0.6 if r10 <= -5 else w*0.4 if r10 <= -2
              else w*0.2 if r10 <= -1 else 0)
    
    # 安定株ボーナス
    w = W.get("w_stable_bonus", 5)
    if s.get("per", 0) > 0 and div >= 2 and mc >= 5000:
        score += w
    elif s.get("per", 0) > 0 and div >= 2 and mc >= 1000:
        score += w * 0.6
    
    return max(0, min(round(score, 1), 100))

# ═══════════════════════════════════════
# STEP 3: バックテスト実行
# ═══════════════════════════════════════
def run_backtest():
    print("=" * 60)
    print("  🔬 かぶのすけ バックテスト（過去1年シミュレーション）")
    print("=" * 60)
    
    codes, price_data = download_universe()
    info_map = get_stock_info_bulk(codes)
    
    # 日付リストを作成（月曜日のみ）
    close_data = price_data["Close"]
    dates = close_data.index
    
    start_dt = pd.Timestamp(BACKTEST_START)
    end_dt = pd.Timestamp(BACKTEST_END)
    
    mondays = [d for d in dates if d >= start_dt and d <= end_dt and d.weekday() == 0]
    
    if not mondays:
        # 月曜がない場合、各週の最初の営業日を使う
        mondays = []
        d = start_dt
        while d <= end_dt:
            week_days = [dd for dd in dates if dd >= d and dd < d + timedelta(days=5)]
            if week_days:
                mondays.append(week_days[0])
            d += timedelta(days=7)
    
    print(f"\n📅 バックテスト期間: {BACKTEST_START} 〜 {BACKTEST_END}")
    print(f"📊 対象週数: {len(mondays)}週")
    print(f"🏦 対象銘柄: {len(codes)}銘柄\n")
    
    weights = INITIAL_WEIGHTS.copy()
    weekly_results = []
    all_validations = []
    
    for week_idx, monday in enumerate(mondays):
        date_idx = dates.get_loc(monday)
        
        # 各銘柄のインジケーター計算
        stocks = []
        sector_ret5 = defaultdict(list)
        
        for code in codes:
            ticker = f"{code}.T"
            try:
                col = close_data[ticker] if ticker in close_data.columns else None
                if col is None:
                    continue
                info = info_map.get(code, {})
                indicators = calc_indicators(code, col, date_idx, info)
                if indicators:
                    sector_ret5[indicators["sector"]].append(indicators["ret5"])
                    stocks.append(indicators)
            except:
                continue
        
        if not stocks:
            continue
        
        # セクター平均計算
        sector_avg = {k: round(sum(v)/len(v), 2) if v else 0 for k, v in sector_ret5.items()}
        for s in stocks:
            sec = s.get("sector", "その他")
            s["sector_ret5"] = sector_avg.get(sec, 0)
            s["ret5_vs_sector"] = round(s.get("ret5", 0) - s["sector_ret5"], 2)
        
        # スコアリング
        for s in stocks:
            s["score"] = score_stock(s, weights)
        
        stocks.sort(key=lambda x: -x["score"])
        top5 = stocks[:TOP_N]
        
        if not top5:
            continue
        
        # 5日後の検証
        future_idx = min(date_idx + 5, len(dates) - 1)
        if future_idx <= date_idx:
            continue
        
        results = []
        for s in top5:
            ticker = f"{s['code']}.T"
            try:
                col = close_data[ticker]
                future_price = float(col.iloc[future_idx])
                current_price = s["price"]
                if current_price > 0 and not math.isnan(future_price):
                    ret = round((future_price / current_price - 1) * 100, 2)
                    results.append({
                        "code": s["code"],
                        "score": s["score"],
                        "return_5d": ret,
                        "dividend": s.get("dividend", 0),
                        "dip_zscore": s.get("dip_zscore", 0),
                        "ret5": s.get("ret5", 0),
                        "ret5_vs_sector": s.get("ret5_vs_sector", 0),
                        "div_growth_years": s.get("div_growth_years", 0),
                    })
            except:
                continue
        
        if not results:
            continue
        
        # 全銘柄平均（ベンチマーク）
        all_rets = []
        for s in stocks:
            ticker = f"{s['code']}.T"
            try:
                col = close_data[ticker]
                fp = float(col.iloc[future_idx])
                cp = s["price"]
                if cp > 0 and not math.isnan(fp):
                    all_rets.append((fp / cp - 1) * 100)
            except:
                continue
        
        market_avg = round(sum(all_rets) / len(all_rets), 2) if all_rets else 0
        top5_avg = round(sum(r["return_5d"] for r in results) / len(results), 2)
        alpha = round(top5_avg - market_avg, 2)
        hit_rate = round(sum(1 for r in results if r["return_5d"] > market_avg) / len(results) * 100, 1)
        
        week_result = {
            "week": week_idx + 1,
            "date": monday.strftime("%Y-%m-%d"),
            "top5_avg": top5_avg,
            "market_avg": market_avg,
            "alpha": alpha,
            "hit_rate": hit_rate,
            "weights_snapshot": weights.copy(),
            "results": results,
        }
        weekly_results.append(week_result)
        all_validations.extend(results)
        
        mark = "✅" if alpha > 0 else "❌"
        print(f"  Week {week_idx+1:2d} ({monday.strftime('%m/%d')}): TOP5={top5_avg:+5.1f}% 市場={market_avg:+5.1f}% α={alpha:+5.1f}% 的中{hit_rate:4.0f}% {mark}")
        
        # 4週ごとに配点最適化
        if (week_idx + 1) % OPTIMIZE_EVERY == 0 and len(all_validations) >= 20:
            weights = optimize_from_data(all_validations, weights)
            print(f"  🔄 配点更新 (Week {week_idx+1})")
    
    # ═══ 最終結果 ═══
    print("\n" + "=" * 60)
    print("  📊 バックテスト最終結果")
    print("=" * 60)
    
    if not weekly_results:
        print("  ❌ 結果なし")
        return
    
    total_alpha = sum(w["alpha"] for w in weekly_results)
    avg_alpha = total_alpha / len(weekly_results)
    avg_hit = sum(w["hit_rate"] for w in weekly_results) / len(weekly_results)
    win_weeks = sum(1 for w in weekly_results if w["alpha"] > 0)
    
    print(f"  期間: {weekly_results[0]['date']} 〜 {weekly_results[-1]['date']}")
    print(f"  週数: {len(weekly_results)}週")
    print(f"  累計α: {total_alpha:+.1f}%")
    print(f"  平均α/週: {avg_alpha:+.2f}%")
    print(f"  勝ち週: {win_weeks}/{len(weekly_results)} ({win_weeks/len(weekly_results)*100:.0f}%)")
    print(f"  平均的中率: {avg_hit:.0f}%")
    
    # 最適化後の配点
    print(f"\n  📐 最適化後の配点:")
    for k, v in sorted(weights.items()):
        init = INITIAL_WEIGHTS.get(k, 0)
        diff = v - init
        arrow = f"({'+'if diff>0 else''}{diff})" if diff != 0 else "(変更なし)"
        print(f"    {k}: {v} {arrow}")
    
    # weights.json に保存
    with open("weights.json", "w", encoding="utf-8") as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 weights.json に最適配点を保存")
    
    # 全結果をbacktest_result.jsonに保存
    output = {
        "backtest_period": f"{BACKTEST_START} 〜 {BACKTEST_END}",
        "weeks": len(weekly_results),
        "total_alpha": round(total_alpha, 2),
        "avg_alpha_per_week": round(avg_alpha, 2),
        "win_rate_weeks": round(win_weeks / len(weekly_results) * 100, 1),
        "avg_hit_rate": round(avg_hit, 1),
        "final_weights": weights,
        "initial_weights": INITIAL_WEIGHTS,
        "weekly_results": weekly_results,
    }
    with open("backtest_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  📁 backtest_result.json に全結果を保存")
    
    print("=" * 60)

def optimize_from_data(validations, current_weights):
    """検証データから配点を微調整"""
    weights = current_weights.copy()
    
    # 各指標で「リターンが高かった株」と「低かった株」を比較
    median_ret = sorted(v["return_5d"] for v in validations)[len(validations)//2]
    
    indicator_map = {
        "dividend": "w_dividend",
        "dip_zscore": "w_dip_zscore",
        "ret5": "w_ret5",
        "ret5_vs_sector": "w_ret5_vs_sector",
        "div_growth_years": "w_div_growth",
    }
    
    for ind, wkey in indicator_map.items():
        high_ret = [v[ind] for v in validations if v["return_5d"] > median_ret and ind in v]
        low_ret = [v[ind] for v in validations if v["return_5d"] <= median_ret and ind in v]
        
        if not high_ret or not low_ret:
            continue
        
        high_avg = sum(high_ret) / len(high_ret)
        low_avg = sum(low_ret) / len(low_ret)
        diff = high_avg - low_avg
        
        # ret系はマイナスが良いので逆
        if ind in ["dip_zscore", "ret5", "ret5_vs_sector"]:
            diff = -diff
        
        # 調整量を決定
        if abs(diff) > 2.0:
            adj = MAX_ADJ if diff > 0 else -MAX_ADJ
        elif abs(diff) > 1.0:
            adj = 2 if diff > 0 else -2
        elif abs(diff) > 0.5:
            adj = 1 if diff > 0 else -1
        else:
            adj = 0
        
        if adj != 0 and wkey in weights:
            new_val = max(0, min(25, weights[wkey] + adj))
            weights[wkey] = new_val
    
    return weights

# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════
if __name__ == "__main__":
    run_backtest()
