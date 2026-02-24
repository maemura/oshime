#!/usr/bin/env python3
"""既存stocks_data.jsonからセクタースコア＋銘柄コードリストを算出・追加"""
import json

SECTOR_JP = {
    "Financial Services": "金融",
    "Basic Materials": "素材",
    "Energy": "エネルギー",
    "Industrials": "産業",
    "Real Estate": "不動産",
    "Consumer Cyclical": "消費（景気敏感）",
    "Consumer Defensive": "消費（安定）",
    "Healthcare": "医薬・ヘルスケア",
    "Technology": "テック",
    "Communication Services": "通信・メディア",
    "Utilities": "電力・ガス",
}

d = json.load(open('stocks_data.json'))
stocks = d['stocks']

sectors = {}
for s in stocks:
    raw_sec = s.get("sector", "その他")
    sec = SECTOR_JP.get(raw_sec, raw_sec)
    if sec not in sectors:
        sectors[sec] = {"divs": [], "rets60": [], "rets120": [], "vols": [], "count": 0, "codes": []}
    sectors[sec]["divs"].append(s.get("dividend", 0) or 0)
    sectors[sec]["rets60"].append(s.get("ret60", 0) or 0)
    sectors[sec]["rets120"].append(s.get("ret120", 0) or 0)
    sectors[sec]["vols"].append(s.get("vol_r", 1) or 1)
    sectors[sec]["count"] += 1
    sectors[sec]["codes"].append(s.get("code", ""))

sector_scores = {}
for sec, data in sectors.items():
    if data["count"] < 2:
        continue
    avg_div = sum(data["divs"]) / len(data["divs"])
    avg_ret60 = sum(data["rets60"]) / len(data["rets60"])
    avg_ret120 = sum(data["rets120"]) / len(data["rets120"])
    avg_vol = sum(data["vols"]) / len(data["vols"])

    if avg_div >= 4: div_sc = 10
    elif avg_div >= 3.5: div_sc = 9
    elif avg_div >= 3: div_sc = 8
    elif avg_div >= 2.5: div_sc = 6
    elif avg_div >= 2: div_sc = 4
    elif avg_div >= 1.5: div_sc = 2
    else: div_sc = 1

    avg_ret = (avg_ret60 + avg_ret120) / 2
    if avg_ret >= 15: ret_sc = 10
    elif avg_ret >= 8: ret_sc = 8
    elif avg_ret >= 3: ret_sc = 6
    elif avg_ret >= 0: ret_sc = 4
    elif avg_ret >= -5: ret_sc = 2
    else: ret_sc = 1

    if avg_vol >= 1.5: vol_sc = 10
    elif avg_vol >= 1.3: vol_sc = 8
    elif avg_vol >= 1.1: vol_sc = 6
    elif avg_vol >= 0.9: vol_sc = 4
    else: vol_sc = 2

    total = round(div_sc * 0.4 + ret_sc * 0.3 + vol_sc * 0.3, 1)
    sector_scores[sec] = {
        "score": total,
        "avg_dividend": round(avg_div, 2),
        "avg_return_60d": round(avg_ret60, 1),
        "avg_return_120d": round(avg_ret120, 1),
        "avg_volume_ratio": round(avg_vol, 2),
        "count": data["count"],
        "codes": data["codes"],
    }

sector_scores = dict(sorted(sector_scores.items(), key=lambda x: -x[1]["score"]))

print("📊 セクタースコア:")
for i, (sec, sc) in enumerate(sector_scores.items()):
    print(f"  {i+1}. {sec}: {sc['score']} (配当{sc['avg_dividend']}% / {sc['count']}銘柄 / 例:{sc['codes'][:3]})")

d['sector_scores'] = sector_scores
json.dump(d, open('stocks_data.json', 'w'), ensure_ascii=False, indent=2)
print(f"\n✅ sector_scores追加完了（{len(sector_scores)}セクター, コードリスト付き）")
