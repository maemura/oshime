#!/usr/bin/env python3
"""大型高配当株をstocks_data.jsonに追加するパッチスクリプト"""
import json, sys, os
sys.path.insert(0, '.')
from fetch_stocks import fetch_one

# 追加したい大型株リスト
LARGECAP_CODES = [
    # ── あなたの保有銘柄 ──
    "1605",  # INPEX
    "7203",  # トヨタ
    "8058",  # 三菱商事
    "8031",  # 三井物産
    "8411",  # みずほFG
    "8725",  # MS&AD
    "1928",  # 積水ハウス
    "9434",  # ソフトバンク
    "5401",  # 日本製鉄
    "6758",  # ソニー
    "3003",  # ヒューリック
    "4661",  # オリエンタルランド
    "7974",  # 任天堂
    "9684",  # スクエニ
    "3635",  # コーエーテクモ
    "9508",  # 九州電力
    "6902",  # デンソー
    "5938",  # LIXIL
    "8593",  # 三菱HCキャピタル
    "9107",  # 川崎汽船
    # ── メガバンク ──
    "8306",  # 三菱UFJ
    "8316",  # 三井住友FG
    # ── 商社 ──
    "8001",  # 伊藤忠
    "8002",  # 丸紅
    "8053",  # 住友商事
    # ── 保険 ──
    "8766",  # 東京海上
    "8630",  # SOMPO
    # ── 海運 ──
    "9101",  # 日本郵船
    "9104",  # 商船三井
    # ── 鉄鋼 ──
    "5411",  # JFE
    # ── 電力 ──
    "9501",  # 東京電力
    "9503",  # 関西電力
    # ── エネルギー ──
    "5019",  # 出光興産
    "5020",  # ENEOS
    # ── リース ──
    "8591",  # オリックス
    # ── 通信 ──
    "9432",  # NTT
    "9433",  # KDDI
    # ── 信託 ──
    "8309",  # 三井住友トラスト
    # ── 建設 ──
    "1801",  # 大成建設
    "1802",  # 大林組
    # ── ガス ──
    "9531",  # 東京ガス
    "9532",  # 大阪ガス
    # ── 鉄道 ──
    "9020",  # JR東日本
    "9022",  # JR東海
    # ── 医薬 ──
    "4503",  # アステラス
    "4502",  # 武田
    # ── その他 ──
    "8604",  # 野村
    "2914",  # JT
]

d = json.load(open('stocks_data.json'))
existing_codes = {s['code'] for s in d['stocks']}
KEEP = {"code","name","sector","price","ma25","ma75","rsi","dividend",
        "pbr","per","vol_r","vol_ratio_1d","ret_1d","range_pct","trend_score",
        "score_dividend","score_value","score_rebound",
        "score_stable","score_growth","score","prev_score","market_cap_b",
        "trend_type","ma75_dev","ma25_dev","roe","closes_60d",
        "ret120","ret20","ret60","volatility"}

added = 0
for code in LARGECAP_CODES:
    if code in existing_codes:
        print(f"  ✓ {code} 既にあり")
        continue
    ticker = f"{code}.T"
    print(f"  📡 {code} 取得中...", end=" ")
    result = fetch_one(ticker)
    if result:
        filtered = {k: v for k, v in result.items() if k in KEEP}
        d['stocks'].append(filtered)
        print(f"✓ {result['name']} div={result.get('dividend',0)}% mc={result.get('market_cap_b',0)}億")
        added += 1
    else:
        print("✗ 取得失敗")

d['stocks'].sort(key=lambda x: -x.get('score', 0))
json.dump(d, open('stocks_data.json', 'w'), ensure_ascii=False, indent=2)
print(f"\n✅ {added}銘柄追加 → 合計{len(d['stocks'])}銘柄")
