#!/usr/bin/env python3
"""
押し目ハンター — 株価データ取得スクリプト
Mac用 / Python初心者向け

使い方:
  1. このファイルと同じフォルダに移動
  2. python3 fetch_stocks.py
  3. stocks_data.json が生成されます
  4. stocks_data.json を押し目ハンター.html と同じフォルダに置く
"""

import json
import sys
from datetime import datetime, timedelta

# ライブラリのインポート（なければエラーメッセージを表示）
try:
    import yfinance as yf
except ImportError:
    print("❌ yfinance がインストールされていません。")
    print("   ターミナルで以下を実行してください:")
    print("   pip3 install yfinance pandas")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("❌ pandas / numpy がインストールされていません。")
    print("   pip3 install pandas numpy")
    sys.exit(1)

# =============================================
# スキャン対象銘柄リスト（東証）
# 安定・高配当・ローリスク中心
# =============================================
WATCHLIST = [
    # 銀行
    ("8306.T", "三菱UFJフィナンシャル", "銀行"),
    ("8316.T", "三井住友FG", "銀行"),
    ("8411.T", "みずほFG", "銀行"),
    # 通信
    ("9432.T", "NTT", "通信"),
    ("9433.T", "KDDI", "通信"),
    ("9434.T", "ソフトバンク", "通信"),
    # 商社
    ("8058.T", "三菱商事", "商社"),
    ("8001.T", "伊藤忠商事", "商社"),
    ("8031.T", "三井物産", "商社"),
    ("8053.T", "住友商事", "商社"),
    # 食品・消費財
    ("2914.T", "JT（日本たばこ）", "食品"),
    ("2502.T", "アサヒグループHD", "食品"),
    # 医薬品
    ("4502.T", "武田薬品工業", "医薬品"),
    ("4519.T", "中外製薬", "医薬品"),
    # 自動車
    ("7203.T", "トヨタ自動車", "自動車"),
    ("7267.T", "本田技研工業", "自動車"),
    # 電力・ガス
    ("9503.T", "関西電力", "電力"),
    ("9531.T", "東京ガス", "ガス"),
    # 鉄道・インフラ
    ("9020.T", "JR東日本", "鉄道"),
    ("9022.T", "JR東海", "鉄道"),
    # 素材・化学
    ("5108.T", "ブリヂストン", "ゴム"),
    ("4063.T", "信越化学工業", "化学"),
    # 保険
    ("8750.T", "第一生命HD", "保険"),
    ("8725.T", "MS&ADインシュアランス", "保険"),
    # 不動産
    ("8801.T", "三井不動産", "不動産"),
    ("8830.T", "住友不動産", "不動産"),
]

def calc_rsi(prices, period=14):
    """RSI計算"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_stock(ticker, name, sector):
    """1銘柄のデータを取得・計算"""
    try:
        print(f"  取得中: {name} ({ticker})", end="", flush=True)
        
        # 90日分の株価を取得
        stock = yf.Ticker(ticker)
        hist = stock.history(period="90d")
        
        if hist.empty or len(hist) < 30:
            print(" ⚠ データ不足、スキップ")
            return None
        
        closes = hist["Close"]
        
        # 現在値
        price = round(float(closes.iloc[-1]), 0)
        
        # 移動平均
        ma25 = round(float(closes.rolling(25).mean().iloc[-1]), 0)
        ma75_series = closes.rolling(75).mean()
        ma75 = round(float(ma75_series.iloc[-1]) if not pd.isna(ma75_series.iloc[-1]) else ma25 * 1.02, 0)
        
        # MA乖離率
        dev25 = round((price - ma25) / ma25 * 100, 1)
        dev75 = round((price - ma75) / ma75 * 100, 1)
        
        # RSI
        rsi_series = calc_rsi(closes)
        rsi = round(float(rsi_series.iloc[-1]), 0) if not pd.isna(rsi_series.iloc[-1]) else 50
        
        # 出来高比率（直近5日 vs 20日平均）
        vol5 = hist["Volume"].iloc[-5:].mean()
        vol20 = hist["Volume"].iloc[-20:].mean()
        vol_ratio = round(vol5 / vol20, 2) if vol20 > 0 else 1.0
        
        # 財務情報（配当・PBR・PER）
        info = stock.info
        raw_div = float(info.get("dividendYield", 0) or 0)
        # yfinanceは小数(0.03=3%)で返すが稀に100倍の値が来る場合がある
        dividend = round(raw_div if raw_div < 10 else raw_div / 100, 2)
        pbr = round(float(info.get("priceToBook", 0) or 0), 2)
        per = round(float(info.get("trailingPE", 0) or 0), 1)
        
        # コード（末尾の.Tを除去）
        code = ticker.replace(".T", "")
        
        print(f" ✓ ¥{price:,.0f} / 配当{dividend}% / RSI{rsi}")
        
        return {
            "code": code,
            "name": name,
            "sector": sector,
            "price": price,
            "ma25": ma25,
            "ma75": ma75,
            "dev25": dev25,
            "dev75": dev75,
            "rsi": int(rsi),
            "dividend": dividend,
            "pbr": pbr,
            "per": per,
            "vol_r": vol_ratio,
        }
        
    except Exception as e:
        print(f" ✗ エラー: {e}")
        return None

def main():
    print("=" * 55)
    print("  押し目ハンター — 株価データ取得")
    print(f"  実行日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}")
    print("=" * 55)
    print(f"\n{len(WATCHLIST)}銘柄のデータを取得します...\n")
    
    results = []
    errors = []
    
    for ticker, name, sector in WATCHLIST:
        data = fetch_stock(ticker, name, sector)
        if data:
            results.append(data)
        else:
            errors.append(name)
    
    # 結果を保存
    output = {
        "updated_at": datetime.now().strftime("%Y/%m/%d %H:%M"),
        "total": len(results),
        "stocks": results,
    }
    
    with open("stocks_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 55)
    print(f"  ✅ 完了！ {len(results)}銘柄取得 / {len(errors)}銘柄スキップ")
    if errors:
        print(f"  スキップ: {', '.join(errors)}")
    print(f"  📁 stocks_data.json を保存しました")
    print("=" * 55)
    print("\n次のステップ:")
    print("  stocks_data.json を 押し目ハンター.html と")
    print("  同じフォルダに置いてブラウザで開いてください。")

if __name__ == "__main__":
    main()
