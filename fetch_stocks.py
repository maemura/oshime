#!/usr/bin/env python3
"""
かぶのすけ 自動スキャン — fetch_stocks.py
==========================================
GitHub Actions で毎朝 7:30 / 大引け後 16:00 に実行。
高配当・割安株をスクリーニングして stocks_data.json を出力。
"""

import json, math, datetime, time, sys, os
import numpy as np
import pandas as pd
import yfinance as yf

# ═══════════════════════════════════════
#  スキャン対象ユニバース（証券コード）
# ═══════════════════════════════════════
# 高配当・バリュー候補を幅広くカバー（約250銘柄）
UNIVERSE = [
    # === メガバンク・金融 ===
    "8306","8316","8411","8308","7186","8304","8309","8354","8355","8601",
    "8604","8630","8725","8766","8795","7172","8697",
    # === 商社 ===
    "8058","8001","8031","8002","8053","8015",
    # === 通信 ===
    "9432","9433","9434","4755","9613",
    # === 自動車・輸送機器 ===
    "7203","7267","7270","7269","7201","7211","7261","6902",
    # === 電力・ガス ===
    "9501","9502","9503","9504","9505","9506","9507","9508","9509","9531","9532",
    # === 鉄鋼・非鉄 ===
    "5401","5411","5406","5413","5020","5019","5021","5802","5801","5803",
    # === 建設・不動産 ===
    "1801","1802","1803","1812","1820","1860","1861","1878","1893","1925","1928",
    "8801","8802","8804","8830","3289","8848","3003",
    # === 食品・消費 ===
    "2914","2502","2503","2801","2802","2809","2871","2282","2269",
    # === 医薬品 ===
    "4502","4503","4506","4507","4519","4523","4568",
    # === 化学・素材 ===
    "4063","4188","4042","4183","4631","3405","4005","4021","4208",
    # === 機械・電気 ===
    "6301","6302","6305","6326","6361","6471","6501","6503","6504","6702","6752",
    "6758","6861","6981","6988","7731","7751","7752",
    # === IT・サービス ===
    "4684","4689","4751","9602","9735","2181","4331","3668","4676",
    # === 運輸 ===
    "9020","9021","9022","9064","9101","9104","9107",
    # === ゴム・その他製造 ===
    "5108","5101","7911","7912","7951",
    # === 保険 ===
    "8750","8766","8795","8630",
    # === リース ===
    "8566","8591","8593",
    # === 小売・サービス ===
    "3382","8267","8252","9843","9983","7532","2651","3088","8168",
    # === その他注目 ===
    "6178","2127","4732","9142","2163","4819","6080","6055","7164",
    "3683","3697","4412","6196","6532","7092","4755","2702","3548",
]

# セクター分類マッピング
SECTOR_MAP = {
    "8306":"銀行","8316":"銀行","8411":"銀行","8308":"銀行","7186":"銀行",
    "8304":"銀行","8309":"銀行","8354":"銀行","8355":"銀行",
    "8601":"証券","8604":"証券","8697":"証券",
    "8630":"保険","8725":"保険","8766":"保険","8795":"保険","8750":"保険",
    "7172":"証券",
    "8058":"商社","8001":"商社","8031":"商社","8002":"商社","8053":"商社","8015":"商社",
    "9432":"通信","9433":"通信","9434":"通信","4755":"通信","9613":"通信",
    "7203":"自動車","7267":"自動車","7270":"自動車","7269":"自動車",
    "7201":"自動車","7211":"自動車","7261":"自動車","6902":"自動車",
    "9501":"電力","9502":"電力","9503":"電力","9504":"電力","9505":"電力",
    "9506":"電力","9507":"電力","9508":"電力","9509":"電力","9531":"ガス","9532":"ガス",
    "5401":"鉄鋼","5411":"鉄鋼","5406":"鉄鋼","5413":"鉄鋼",
    "5020":"石油","5019":"石油","5021":"石油",
    "5802":"非鉄","5801":"非鉄","5803":"非鉄",
    "1801":"建設","1802":"建設","1803":"建設","1812":"建設","1820":"建設",
    "1860":"建設","1861":"建設","1878":"建設","1893":"建設","1925":"建設","1928":"建設",
    "8801":"不動産","8802":"不動産","8804":"不動産","8830":"不動産",
    "3289":"不動産","8848":"不動産","3003":"不動産",
    "2914":"食品","2502":"食品","2503":"食品","2801":"食品","2802":"食品",
    "2809":"食品","2871":"食品","2282":"食品","2269":"食品",
    "4502":"医薬品","4503":"医薬品","4506":"医薬品","4507":"医薬品",
    "4519":"医薬品","4523":"医薬品","4568":"医薬品",
    "4063":"化学","4188":"化学","4042":"化学","4183":"化学","4631":"化学",
    "3405":"化学","4005":"化学","4021":"化学","4208":"化学",
    "6301":"機械","6302":"機械","6305":"機械","6326":"機械","6361":"機械","6471":"機械",
    "6501":"電機","6503":"電機","6504":"電機","6702":"電機","6752":"電機",
    "6758":"電機","6861":"電機","6981":"電機","6988":"電機",
    "7731":"精密","7751":"精密","7752":"精密",
    "4684":"IT","4689":"IT","4751":"IT","9602":"サービス","9735":"サービス",
    "2181":"サービス","4331":"サービス","3668":"IT","4676":"メディア",
    "9020":"運輸","9021":"運輸","9022":"運輸","9064":"運輸",
    "9101":"海運","9104":"海運","9107":"海運",
    "5108":"ゴム","5101":"ゴム","7911":"その他","7912":"その他","7951":"その他",
    "8566":"リース","8591":"リース","8593":"リース",
    "3382":"小売","8267":"小売","8252":"小売","9843":"小売","9983":"小売",
    "7532":"小売","2651":"小売","3088":"小売","8168":"小売",
}

# 日本語銘柄名マッピング（yfinanceは英語名を返すため）
NAME_MAP = {
    # メガバンク・金融
    "8306":"三菱UFJフィナンシャル","8316":"三井住友FG","8411":"みずほFG",
    "8308":"りそなHD","7186":"コンコルディアFG","8304":"あおぞら銀行",
    "8309":"三井住友トラスト","8354":"ふくおかFG","8355":"静岡銀行",
    "8601":"大和証券G","8604":"野村HD","8697":"日本取引所G",
    "8630":"SOMPO HD","8725":"MS&AD","8766":"東京海上HD","8795":"T&D HD","8750":"第一生命HD",
    "7172":"JIA",
    # 商社
    "8058":"三菱商事","8001":"伊藤忠商事","8031":"三井物産",
    "8002":"丸紅","8053":"住友商事","8015":"豊田通商",
    # 通信
    "9432":"NTT","9433":"KDDI","9434":"ソフトバンク","4755":"楽天グループ","9613":"NTTデータG",
    # 自動車
    "7203":"トヨタ自動車","7267":"ホンダ","7270":"SUBARU","7269":"スズキ",
    "7201":"日産自動車","7211":"三菱自動車","7261":"マツダ","6902":"デンソー",
    # 電力・ガス
    "9501":"東京電力HD","9502":"中部電力","9503":"関西電力","9504":"中国電力",
    "9505":"北陸電力","9506":"東北電力","9507":"四国電力","9508":"九州電力",
    "9509":"北海道電力","9531":"東京ガス","9532":"大阪ガス",
    # 鉄鋼・石油・非鉄
    "5401":"日本製鉄","5411":"JFE HD","5406":"神戸製鋼所","5413":"日新製鋼",
    "5020":"ENEOS HD","5019":"出光興産","5021":"コスモエネルギー",
    "5802":"住友電気工業","5801":"古河電気工業","5803":"フジクラ",
    # 建設
    "1801":"大成建設","1802":"大林組","1803":"清水建設","1812":"鹿島建設",
    "1820":"西松建設","1860":"戸田建設","1861":"熊谷組","1878":"大東建託",
    "1893":"五洋建設","1925":"大和ハウス工業","1928":"積水ハウス",
    # 不動産
    "8801":"三井不動産","8802":"三菱地所","8804":"東京建物","8830":"住友不動産",
    "3289":"東急不動産HD","8848":"レオパレス21","3003":"ヒューリック",
    # 食品
    "2914":"JT","2502":"アサヒグループHD","2503":"キリンHD",
    "2801":"キッコーマン","2802":"味の素","2809":"キユーピー",
    "2871":"ニチレイ","2282":"日本ハム","2269":"明治HD",
    # 医薬品
    "4502":"武田薬品工業","4503":"アステラス製薬","4506":"住友ファーマ",
    "4507":"塩野義製薬","4519":"中外製薬","4523":"エーザイ","4568":"第一三共",
    # 化学
    "4063":"信越化学工業","4188":"三菱ケミカルG","4042":"東ソー",
    "4183":"三井化学","4631":"DIC","3405":"クラレ","4005":"住友化学",
    "4021":"日産化学","4208":"宇部興産",
    # 機械
    "6301":"小松製作所","6302":"住友重機械工業","6305":"日立建機",
    "6326":"クボタ","6361":"荏原製作所","6471":"日本精工",
    # 電機
    "6501":"日立製作所","6503":"三菱電機","6504":"富士電機","6702":"富士通",
    "6752":"パナソニックHD","6758":"ソニーG","6861":"キーエンス",
    "6981":"村田製作所","6988":"日東電工",
    # 精密
    "7731":"ニコン","7751":"キヤノン","7752":"リコー",
    # IT・サービス
    "4684":"オービック","4689":"LINEヤフー","4751":"サイバーエージェント",
    "9602":"東宝","9735":"セコム","2181":"パーソルHD",
    "4331":"テイクアンドギヴ・ニーズ","3668":"コロプラ","4676":"フジ・メディアHD",
    # 運輸
    "9020":"JR東日本","9021":"JR西日本","9022":"JR東海","9064":"ヤマトHD",
    "9101":"日本郵船","9104":"商船三井","9107":"川崎汽船",
    # ゴム・その他
    "5108":"ブリヂストン","5101":"横浜ゴム","7911":"凸版印刷",
    "7912":"大日本印刷","7951":"ヤマハ",
    # リース
    "8566":"リコーリース","8591":"オリックス","8593":"三菱HCキャピタル",
    # 小売
    "3382":"セブン&アイ","8267":"イオン","8252":"丸井グループ",
    "9843":"ニトリHD","9983":"ファーストリテイリング","7532":"パンパシHD",
    "2651":"ローソン","3088":"マツキヨココカラ","8168":"ケーヨー",
    # その他注目
    "6178":"日本郵政","2127":"日本M&Aセンター","4732":"ユー・エス・エス",
    "9142":"九州旅客鉄道","2163":"アルトナー","4819":"デジタルガレージ",
    "6080":"M&Aキャピタルパートナーズ","6055":"ジャパンマテリアル","7164":"全国保証",
    "3683":"サイバーリンクス","3697":"SHIFT","4412":"サイエンスアーツ",
    "6196":"ストライク","6532":"ベイカレント","7092":"Fast Fitness Japan",
    "2702":"日本マクドナルドHD","3548":"バロックジャパンリミテッド",
    # 半導体・防衛・その他（国策テーマ含む）
    "8035":"東京エレクトロン","6857":"アドバンテスト","6920":"レーザーテック",
    "6146":"ディスコ","6723":"ルネサスエレクトロニクス","3436":"SUMCO","6526":"ソシオネクスト",
    "7011":"三菱重工業","7012":"川崎重工業","7013":"IHI","7721":"東京計器",
    "1605":"INPEX","9984":"ソフトバンクG","9201":"JAL","9202":"ANA HD",
    "6273":"SMC","3923":"ラクス",
}

# ═══════════════════════════════════════
#  ユーティリティ関数
# ═══════════════════════════════════════

def calc_rsi(prices, period=14):
    """RSI を計算"""
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - 100.0 / (1.0 + rs), 1)


# ── 国策テーマ（経産省・国交省の成長戦略に基づく）──
# 半導体・AI: TSMC熊本、ラピダス、AI国家戦略
# 防衛: 防衛費GDP比2%目標
# GX: グリーントランスフォーメーション、水素・アンモニア
# DX: デジタル田園都市、マイナンバー基盤
# インバウンド・観光: 観光立国推進
KOKUSAKU_THEMES = {
    # 半導体・AI
    "8035": "半導体",  # 東京エレクトロン
    "6857": "半導体",  # アドバンテスト
    "6920": "半導体",  # レーザーテック
    "6146": "半導体",  # ディスコ
    "6723": "半導体",  # ルネサス
    "4063": "半導体",  # 信越化学
    "3436": "半導体",  # SUMCO
    "6526": "半導体",  # ソシオネクスト
    "6758": "AI",      # ソニーG
    "9984": "AI",      # ソフトバンクG
    "9613": "DX",      # NTTデータG
    # 防衛
    "7011": "防衛",    # 三菱重工
    "7012": "防衛",    # 川崎重工
    "7013": "防衛",    # IHI
    "6503": "防衛",    # 三菱電機
    "7721": "防衛",    # 東京計器
    # GX・エネルギー
    "9501": "GX",      # 東京電力
    "9502": "GX",      # 中部電力
    "9503": "GX",      # 関西電力
    "9508": "GX",      # 九州電力
    "1605": "GX",      # INPEX
    "5020": "GX",      # ENEOS
    "5019": "GX",      # 出光興産
    "6501": "GX",      # 日立（送電網・GX）
    # DX・デジタル
    "9432": "DX",      # NTT
    "4689": "DX",      # Zホールディングス
    "3923": "DX",      # ラクス
    "4755": "DX",      # 楽天G
    # インバウンド・観光
    "9020": "観光",    # JR東日本
    "9021": "観光",    # JR西日本
    "9022": "観光",    # JR東海
    "9201": "観光",    # JAL
    "9202": "観光",    # ANA
    "6273": "観光",    # SMC（FA→インバウンド間接）
}

def calc_score(s):
    """かぶのすけスコア（100点満点）"""
    d25 = ((s.get("price", 0) / s.get("ma25", 1)) - 1) * 100 if s.get("ma25") else 0
    div = s.get("dividend", 0) or 0
    score = 0

    # 配当利回り（max 40）
    if div >= 5:     score += 40
    elif div >= 4.5: score += 32
    elif div >= 4:   score += 25
    elif div >= 3.5: score += 18
    elif div >= 3:   score += 10

    # PBR（max 20）
    pbr = s.get("pbr") or 99
    if pbr <= 0.7:   score += 20
    elif pbr <= 0.9: score += 15
    elif pbr <= 1.1: score += 8
    elif pbr <= 1.5: score += 3

    # 25MA乖離（max 20）
    if d25 <= -8:    score += 20
    elif d25 <= -5:  score += 14
    elif d25 <= -3:  score += 8
    elif d25 <= -1:  score += 3

    # RSI（max 15）
    rsi = s.get("rsi") or 50
    if rsi <= 30:    score += 15
    elif rsi <= 38:  score += 10
    elif rsi <= 45:  score += 5

    # PER（max 10）
    per = s.get("per") or 99
    if per <= 10:    score += 10
    elif per <= 13:  score += 6
    elif per <= 16:  score += 3

    # 国策テーマボーナス（max 5）
    code = s.get("code", "")
    if code in KOKUSAKU_THEMES:
        score += 5

    # ペナルティ: 出来高急増
    if (s.get("vol_r") or 1) >= 1.5:
        score -= 20

    # ペナルティ: 低配当
    if div < 0.5:
        score = min(score, 5)

    # ペナルティ: 小型株
    mc = s.get("market_cap_b") or 9999
    if 0 < mc < 300:
        score -= 20
    elif 0 < mc < 500:
        score -= 10

    return max(0, min(score, 100))


def fetch_stock_data(code, retries=2):
    """1銘柄のデータを取得"""
    ticker_str = f"{code}.T"
    for attempt in range(retries + 1):
        try:
            tk = yf.Ticker(ticker_str)
            # 90日分の日足データ
            hist = tk.history(period="90d")
            if hist.empty or len(hist) < 5:
                return None

            info = tk.info or {}
            closes = hist["Close"].dropna().values.tolist()
            volumes = hist["Volume"].dropna().values.tolist()

            price = round(closes[-1], 1)

            # 移動平均
            ma25 = round(np.mean(closes[-25:]), 1) if len(closes) >= 25 else round(np.mean(closes), 1)
            ma75 = round(np.mean(closes[-75:]), 1) if len(closes) >= 75 else round(np.mean(closes), 1)

            # RSI
            rsi = calc_rsi(closes)

            # 出来高比率（直近5日平均 / 20日平均）
            vol_r = 1.0
            if len(volumes) >= 20:
                avg5 = np.mean(volumes[-5:])
                avg20 = np.mean(volumes[-20:])
                if avg20 > 0:
                    vol_r = round(avg5 / avg20, 2)

            # ファンダメンタル
            dividend = info.get("dividendYield")
            if dividend and dividend > 0:
                # yfinanceは通常小数(0.044=4.4%)で返すが、
                # 日本株で稀にパーセント値(4.4)で返る場合がある
                if dividend > 1:
                    dividend = round(dividend, 2)
                else:
                    dividend = round(dividend * 100, 2)
            else:
                # フォールバック: trailingAnnualDividendYield
                dividend = info.get("trailingAnnualDividendYield")
                if dividend and dividend > 0:
                    if dividend > 1:
                        dividend = round(dividend, 2)
                    else:
                        dividend = round(dividend * 100, 2)
                else:
                    dividend = 0.0

            # 最終サニティチェック: 現実的に配当利回り20%超はありえない
            if dividend > 20:
                dividend = round(dividend / 100, 2) if dividend > 100 else 0.0

            pbr = info.get("priceToBook")
            if pbr:
                pbr = round(pbr, 2)
            else:
                pbr = None

            per = info.get("trailingPE") or info.get("forwardPE")
            if per:
                per = round(per, 1)
            else:
                per = None

            market_cap = info.get("marketCap", 0)
            market_cap_b = round(market_cap / 1e8, 0) if market_cap else None  # 億円

            name = NAME_MAP.get(code)
            if not name:
                # フォールバック: yfinanceから取得（英語名の場合あり）
                name = info.get("shortName") or info.get("longName") or code
                name = name.replace("Corporation", "").replace("Co., Ltd.", "").replace("Co.,Ltd.", "").strip()

            # sparkline用の終値60日分
            closes_60d = [round(c, 1) for c in closes[-60:]]

            sector = SECTOR_MAP.get(code, "その他")

            return {
                "code": code,
                "name": name,
                "sector": sector,
                "kokusaku": KOKUSAKU_THEMES.get(code, ""),
                "price": price,
                "ma25": ma25,
                "ma75": ma75,
                "rsi": rsi,
                "dividend": dividend,
                "pbr": pbr,
                "per": per,
                "vol_r": vol_r,
                "market_cap_b": market_cap_b,
                "closes_60d": closes_60d,
            }
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"  ⚠ {code}: {e}", file=sys.stderr)
                return None
    return None


def fetch_market_data():
    """市場全体のデータを取得"""
    market = {}
    try:
        # 日経平均
        nk = yf.Ticker("^N225")
        nk_hist = nk.history(period="30d")
        if not nk_hist.empty and len(nk_hist) >= 2:
            nk_closes = nk_hist["Close"].dropna().values
            market["nikkei_price"] = round(float(nk_closes[-1]), 0)
            market["nikkei_1d_chg"] = round(((nk_closes[-1] / nk_closes[-2]) - 1) * 100, 2)
            if len(nk_closes) >= 25:
                market["nikkei_ma25"] = round(float(np.mean(nk_closes[-25:])), 0)
    except Exception as e:
        print(f"  ⚠ 日経平均取得失敗: {e}", file=sys.stderr)

    try:
        # NASDAQ
        nq = yf.Ticker("^IXIC")
        nq_hist = nq.history(period="5d")
        if not nq_hist.empty and len(nq_hist) >= 2:
            nq_closes = nq_hist["Close"].dropna().values
            market["nasdaq_1d_chg"] = round(((nq_closes[-1] / nq_closes[-2]) - 1) * 100, 2)
    except:
        pass

    try:
        # VIX
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        if not vix_hist.empty:
            market["vix"] = round(float(vix_hist["Close"].dropna().values[-1]), 1)
    except:
        pass

    try:
        # USD/JPY
        fx = yf.Ticker("JPY=X")
        fx_hist = fx.history(period="5d")
        if not fx_hist.empty:
            market["usdjpy"] = round(float(fx_hist["Close"].dropna().values[-1]), 2)
    except:
        pass

    try:
        # 米国10年債
        tnx = yf.Ticker("^TNX")
        tnx_hist = tnx.history(period="5d")
        if not tnx_hist.empty:
            market["us10y"] = round(float(tnx_hist["Close"].dropna().values[-1]), 2)
    except:
        pass

    # デフォルト値
    market.setdefault("geo_risk", 0)
    market.setdefault("rate_cut_flag", 0)
    market.setdefault("prev_buy_count", 0)

    return market


# ═══════════════════════════════════════
#  メイン処理
# ═══════════════════════════════════════

def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    print(f"📊 かぶのすけスキャン開始: {now.strftime('%Y/%m/%d %H:%M JST')}")
    print(f"   対象: {len(UNIVERSE)} 銘柄")

    # --- 市場データ ---
    print("\n🌐 市場データ取得中...")
    market = fetch_market_data()
    print(f"   日経: {market.get('nikkei_price','N/A')} / VIX: {market.get('vix','N/A')} / USD/JPY: {market.get('usdjpy','N/A')}")

    # --- 個別銘柄データ ---
    print(f"\n🔍 個別銘柄スキャン中...")
    stocks = []
    errors = 0
    # 重複排除
    unique_codes = list(dict.fromkeys(UNIVERSE))

    for i, code in enumerate(unique_codes):
        if (i + 1) % 20 == 0:
            print(f"   ... {i+1}/{len(unique_codes)} 完了")
        data = fetch_stock_data(code)
        if data:
            # スコア計算
            data["score"] = calc_score(data)
            stocks.append(data)
        else:
            errors += 1
        # レート制限回避
        if (i + 1) % 10 == 0:
            time.sleep(1)

    print(f"\n✅ 取得完了: {len(stocks)} 銘柄成功 / {errors} 銘柄失敗")

    # --- スコアでソート ---
    stocks.sort(key=lambda s: s.get("score", 0), reverse=True)

    # --- 出来高ランキング ---
    vol_ranking = sorted(
        [s for s in stocks if s.get("vol_r", 0) > 1.2],
        key=lambda s: s.get("vol_r", 0), reverse=True
    )[:20]
    vol_ranking_out = [
        {"code": s["code"], "name": s["name"], "vol_r": s["vol_r"]}
        for s in vol_ranking
    ]

    # --- トレンドランキング（75MA上方 & 25MA上方）---
    trend_ranking = sorted(
        [s for s in stocks if s.get("ma75") and s["price"] > s["ma75"] and s["price"] > s.get("ma25", 0)],
        key=lambda s: ((s["price"] / s["ma75"]) - 1) * 100, reverse=True
    )[:20]
    trend_ranking_out = [
        {"code": s["code"], "name": s["name"],
         "ma75d": round(((s["price"] / s["ma75"]) - 1) * 100, 1)}
        for s in trend_ranking
    ]

    # --- セクタースコア ---
    sector_scores = {}
    for s in stocks:
        sec = s.get("sector", "その他")
        if sec not in sector_scores:
            sector_scores[sec] = {"count": 0, "total_score": 0, "buy_count": 0}
        sector_scores[sec]["count"] += 1
        sector_scores[sec]["total_score"] += s.get("score", 0)
        if s.get("score", 0) >= 60:
            sector_scores[sec]["buy_count"] += 1

    sector_out = {}
    for sec, v in sector_scores.items():
        avg = round(v["total_score"] / v["count"], 1) if v["count"] > 0 else 0
        sector_out[sec] = {"avg_score": avg, "count": v["count"], "buy_count": v["buy_count"]}

    # --- JSON出力 ---
    output = {
        "updated_at": now.strftime("%Y/%m/%d %H:%M"),
        "total": len(stocks),
        "stocks": stocks,
        "vol_ranking": vol_ranking_out,
        "trend_ranking": trend_ranking_out,
        "sector_scores": sector_out,
        **market,
    }

    with open("stocks_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)

    file_size = os.path.getsize("stocks_data.json") / 1024
    print(f"\n📁 stocks_data.json 出力完了 ({file_size:.0f} KB)")

    # サマリー
    top5 = stocks[:5]
    print("\n🏆 スコア TOP5:")
    for s in top5:
        print(f"   {s['code']} {s['name'][:10]:　<10} スコア:{s['score']} 配当:{s['dividend']}% RSI:{s['rsi']}")

    buy_count = len([s for s in stocks if s.get("score", 0) >= 60])
    print(f"\n📊 買い圏: {buy_count}銘柄 / 注意圏: {len([s for s in stocks if 35 <= s.get('score',0) < 60])}銘柄")


if __name__ == "__main__":
    main()
