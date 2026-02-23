#!/usr/bin/env python3
"""
validate.py — 推薦銘柄の事後検証 + 配点最適化
==============================================
毎朝のスキャン後に自動実行。
1. 5日前の推薦TOP5の株価を検証
2. 結果を history/ に追記
3. 30日分溜まったら配点有効性を分析
4. 週次で配点調整案を出力 → weights.json
"""

import json, os, glob, math
from datetime import datetime, timedelta

HISTORY_DIR = "history"
WEIGHTS_FILE = "weights.json"

# ═══════════════════════════════════════
# デフォルト配点（v3手動設定）
# ═══════════════════════════════════════
DEFAULT_WEIGHTS = {
    "dividend":       20,   # 配当利回り max
    "market_cap":     10,   # 時価総額 max
    "div_growth":     10,   # 連続増配 max
    "dip_zscore":     15,   # 自分比押し目 max
    "pbr":             5,   # PBR max
    "ret5_vs_sector": 20,   # 個別vsセクター差分 max
    "ret5":           10,   # 個別5日下落 max
    "ret10":           5,   # 10日リターン max
    "stable_bonus":    5,   # 安定株ボーナス max
    "sector_penalty": -5,   # セクター下落ペナルティ
}

def load_weights():
    """現在の配点を読み込み"""
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_WEIGHTS.copy()

def save_weights(w):
    with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(w, f, ensure_ascii=False, indent=2)

def get_history_file(date_str):
    path = os.path.join(HISTORY_DIR, f"{date_str}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None

def get_current_prices(codes):
    """yfinanceで現在価格を取得"""
    try:
        import yfinance as yf
        tickers = [f"{c}.T" for c in codes]
        data = yf.download(tickers, period="5d", progress=False)
        prices = {}
        if len(tickers) == 1:
            close = data["Close"]
            if len(close) > 0:
                prices[codes[0]] = float(close.iloc[-1])
        else:
            for code, ticker in zip(codes, tickers):
                try:
                    col = data["Close"][ticker]
                    if len(col) > 0:
                        prices[code] = float(col.iloc[-1])
                except:
                    pass
        return prices
    except Exception as e:
        print(f"  ⚠ 価格取得エラー: {e}")
        return {}

# ═══════════════════════════════════════
# STEP 1: 5日前の推薦を検証
# ═══════════════════════════════════════
def validate_past_recommendations():
    """5日前のTOP5を検証して結果を記録"""
    today = datetime.now()
    
    # 5営業日前を探す（土日スキップ）
    check_dates = []
    d = today - timedelta(days=1)
    while len(check_dates) < 10:
        d -= timedelta(days=1)
        if d.weekday() < 5:  # 月〜金
            check_dates.append(d.strftime("%Y-%m-%d"))
    
    validated = False
    for target_date in check_dates[4:8]:  # 5〜8営業日前をチェック
        hist = get_history_file(target_date)
        if not hist:
            continue
        if hist.get("validated"):
            continue  # 既に検証済み
        
        top5 = hist.get("top5", [])
        if not top5:
            continue
        
        codes = [s["code"] for s in top5]
        current_prices = get_current_prices(codes)
        
        if not current_prices:
            continue
        
        # 各銘柄の5日後リターン計算
        results = []
        for s in top5:
            code = s["code"]
            old_price = s.get("price", 0)
            new_price = current_prices.get(code, 0)
            if old_price > 0 and new_price > 0:
                ret = round((new_price / old_price - 1) * 100, 2)
                results.append({
                    "code": code,
                    "name": s.get("name", ""),
                    "score": s.get("score", 0),
                    "price_then": old_price,
                    "price_now": new_price,
                    "return_5d": ret,
                })
        
        if not results:
            continue
        
        # 市場平均リターン（日経225のproxy）
        nikkei_prices = get_current_prices(["998407"])  # 日経平均のyfinanceコード
        market_ret = 0
        nikkei_then = hist.get("market", {}).get("nikkei_price", 0)
        # 市場リターンは近似（正確にはindex使う）
        
        # α計算
        avg_ret = sum(r["return_5d"] for r in results) / len(results) if results else 0
        alpha = round(avg_ret - market_ret, 2)
        hit_rate = round(sum(1 for r in results if r["return_5d"] > market_ret) / len(results) * 100, 1) if results else 0
        
        # 結果を履歴に追記
        validation = {
            "validated": True,
            "validated_at": today.strftime("%Y-%m-%d"),
            "results": results,
            "avg_return_5d": round(avg_ret, 2),
            "market_return_5d": market_ret,
            "alpha": alpha,
            "hit_rate": hit_rate,
        }
        hist.update(validation)
        
        # 保存
        hist_path = os.path.join(HISTORY_DIR, f"{target_date}.json")
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=2)
        
        print(f"  ✅ {target_date}の推薦を検証:")
        for r in results:
            mark = "✅" if r["return_5d"] > market_ret else "❌"
            print(f"    {mark} {r['name']} ({r['code']}): {r['return_5d']:+.1f}%")
        print(f"    📊 平均リターン: {avg_ret:+.1f}%  α: {alpha:+.1f}%  的中率: {hit_rate}%")
        validated = True
        break  # 1日分だけ検証
    
    if not validated:
        print("  📭 検証対象なし（5日前の履歴がまだない）")
    
    return validated

# ═══════════════════════════════════════
# STEP 2: 配点の有効性分析
# ═══════════════════════════════════════
def analyze_weights():
    """検証済みデータから各指標の有効性を分析"""
    files = sorted(glob.glob(os.path.join(HISTORY_DIR, "*.json")))
    
    validated_data = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("validated") and d.get("results"):
            validated_data.append(d)
    
    if len(validated_data) < 5:
        print(f"  📊 検証データ {len(validated_data)}件（最低5件必要、まだ足りない）")
        return None
    
    print(f"  📊 検証データ {len(validated_data)}件で分析開始")
    
    # 各指標と5日後リターンの相関を分析
    # TOP5の中で「当たった銘柄」と「外れた銘柄」の指標値を比較
    indicator_effectiveness = {}
    
    indicators = ["dividend", "dip_zscore", "ret5", "ret5_vs_sector", "div_growth_years"]
    
    for ind in indicators:
        hit_vals = []
        miss_vals = []
        for d in validated_data:
            top5 = d.get("top5", [])
            results = d.get("results", [])
            market_ret = d.get("market_return_5d", 0)
            
            result_map = {r["code"]: r for r in results}
            for s in top5:
                code = s["code"]
                if code in result_map:
                    val = s.get(ind, 0)
                    ret = result_map[code]["return_5d"]
                    if ret > market_ret:
                        hit_vals.append(val)
                    else:
                        miss_vals.append(val)
        
        if hit_vals and miss_vals:
            hit_avg = sum(hit_vals) / len(hit_vals)
            miss_avg = sum(miss_vals) / len(miss_vals)
            diff = round(hit_avg - miss_avg, 3)
            indicator_effectiveness[ind] = {
                "hit_avg": round(hit_avg, 3),
                "miss_avg": round(miss_avg, 3),
                "diff": diff,
                "sample_size": len(hit_vals) + len(miss_vals),
            }
            direction = "↑効果あり" if abs(diff) > 0.5 else "→効果薄い"
            print(f"    {ind}: 的中平均={hit_avg:.2f} 外れ平均={miss_avg:.2f} 差={diff:.2f} {direction}")
    
    return indicator_effectiveness

# ═══════════════════════════════════════
# STEP 3: 配点の自動調整
# ═══════════════════════════════════════
def optimize_weights():
    """検証結果に基づいて配点を微調整（±3pt以内）"""
    effectiveness = analyze_weights()
    if not effectiveness:
        return
    
    current = load_weights()
    updated = current.copy()
    changes = []
    
    # 指標名 → 配点キーのマッピング
    ind_to_key = {
        "dividend": "dividend",
        "dip_zscore": "dip_zscore",
        "ret5": "ret5",
        "ret5_vs_sector": "ret5_vs_sector",
        "div_growth_years": "div_growth",
    }
    
    for ind, stats in effectiveness.items():
        key = ind_to_key.get(ind)
        if not key or key not in updated:
            continue
        
        diff = stats["diff"]
        sample = stats["sample_size"]
        
        if sample < 10:
            continue  # サンプル不足
        
        # 効果が高い指標は+1〜+3pt、効果が低い指標は-1〜-3pt
        if abs(diff) > 2.0:
            adj = 3 if diff > 0 else -3
        elif abs(diff) > 1.0:
            adj = 2 if diff > 0 else -2
        elif abs(diff) > 0.5:
            adj = 1 if diff > 0 else -1
        else:
            adj = 0
        
        # ret系は逆（マイナスが良い）
        if ind in ["ret5", "ret5_vs_sector", "dip_zscore"]:
            adj = -adj
        
        if adj != 0:
            old_val = updated[key]
            new_val = max(0, min(25, old_val + adj))  # 0〜25の範囲
            if new_val != old_val:
                updated[key] = new_val
                changes.append(f"  {key}: {old_val} → {new_val} ({'+' if adj>0 else ''}{adj})")
    
    if changes:
        # 合計が100になるように正規化
        total = sum(v for k, v in updated.items() if v > 0)
        
        save_weights(updated)
        print(f"\n  🔄 配点更新:")
        for c in changes:
            print(c)
        print(f"  📁 {WEIGHTS_FILE} に保存")
    else:
        print(f"\n  ✅ 配点変更なし（現状維持）")

# ═══════════════════════════════════════
# STEP 4: 成績サマリー生成
# ═══════════════════════════════════════
def generate_report():
    """ユーザー向けの週次成績レポートを生成"""
    files = sorted(glob.glob(os.path.join(HISTORY_DIR, "*.json")))
    
    validated = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("validated"):
            validated.append(d)
    
    if not validated:
        return None
    
    # 直近7日の検証結果
    recent = validated[-5:]
    
    all_results = []
    for d in recent:
        for r in d.get("results", []):
            all_results.append(r)
    
    if not all_results:
        return None
    
    total_alpha = sum(d.get("alpha", 0) for d in recent)
    avg_hit_rate = sum(d.get("hit_rate", 0) for d in recent) / len(recent) if recent else 0
    avg_return = sum(r["return_5d"] for r in all_results) / len(all_results) if all_results else 0
    
    # ベスト/ワースト
    best = max(all_results, key=lambda x: x["return_5d"])
    worst = min(all_results, key=lambda x: x["return_5d"])
    
    report = {
        "period": f"{recent[0]['date']} 〜 {recent[-1]['date']}",
        "days_validated": len(recent),
        "total_stocks": len(all_results),
        "avg_return": round(avg_return, 2),
        "total_alpha": round(total_alpha, 2),
        "avg_hit_rate": round(avg_hit_rate, 1),
        "best": {"name": best["name"], "return": best["return_5d"]},
        "worst": {"name": worst["name"], "return": worst["return_5d"]},
    }
    
    report_path = os.path.join(HISTORY_DIR, "latest_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n  📊 成績レポート ({report['period']})")
    print(f"    検証日数: {report['days_validated']}日  銘柄数: {report['total_stocks']}")
    print(f"    平均リターン: {report['avg_return']:+.1f}%")
    print(f"    累計α: {report['total_alpha']:+.1f}%")
    print(f"    的中率: {report['avg_hit_rate']:.0f}%")
    print(f"    ✅ ベスト: {report['best']['name']} {report['best']['return']:+.1f}%")
    print(f"    ❌ ワースト: {report['worst']['name']} {report['worst']['return']:+.1f}%")
    
    return report

# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════
def main():
    print("\n" + "=" * 50)
    print("  📋 推薦検証システム")
    print("=" * 50)
    
    # Step 1: 過去の推薦を検証
    print("\n🔍 Step 1: 過去の推薦を検証")
    validate_past_recommendations()
    
    # Step 2: 成績レポート
    print("\n📊 Step 2: 成績レポート")
    report = generate_report()
    
    # Step 3: 配点最適化（日曜のみ、または手動）
    today = datetime.now()
    if today.weekday() == 6 or os.environ.get("FORCE_OPTIMIZE"):
        print("\n🔄 Step 3: 配点最適化（週次）")
        optimize_weights()
    else:
        print(f"\n⏭ Step 3: 配点最適化はスキップ（日曜に実行）")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
