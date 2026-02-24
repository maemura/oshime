#!/usr/bin/env python3
"""
かぶのすけ X自動投稿
stocks_data.json → ツイート生成 → X API v2で投稿
"""
import json
import os
import sys
import hmac
import hashlib
import time
import urllib.parse
import base64
import uuid
import requests

# ─── X API認証（OAuth 1.0a） ───
API_KEY = os.environ.get("X_API_KEY", "")
API_SECRET = os.environ.get("X_API_SECRET", "")
ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
ACCESS_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "")

def oauth_sign(method, url, params):
    """OAuth 1.0a署名を生成"""
    oauth = {
        "oauth_consumer_key": API_KEY,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = {**oauth, **params}
    param_str = "&".join(f"{urllib.parse.quote(k,'~')}={urllib.parse.quote(str(v),'~')}"
                         for k, v in sorted(all_params.items()))
    base = f"{method}&{urllib.parse.quote(url,'~')}&{urllib.parse.quote(param_str,'~')}"
    key = f"{urllib.parse.quote(API_SECRET,'~')}&{urllib.parse.quote(ACCESS_SECRET,'~')}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    auth_header = "OAuth " + ", ".join(
        f'{k}="{urllib.parse.quote(v,"~")}"' for k, v in sorted(oauth.items()))
    return auth_header

def post_tweet(text):
    """X API v2でツイート投稿"""
    url = "https://api.twitter.com/2/tweets"
    auth = oauth_sign("POST", url, {})
    headers = {"Authorization": auth, "Content-Type": "application/json"}
    body = {"text": text}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    if r.status_code in (200, 201):
        data = r.json()
        tweet_id = data.get("data", {}).get("id", "?")
        print(f"✅ 投稿成功! ID: {tweet_id}")
        print(f"   https://x.com/i/web/status/{tweet_id}")
        return True
    else:
        print(f"❌ 投稿失敗: {r.status_code}")
        print(f"   {r.text}")
        return False

# ─── ツイート文生成 ───
def generate_tweet():
    """stocks_data.jsonからツイート文を生成"""
    try:
        with open("stocks_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ stocks_data.json が見つかりません")
        sys.exit(1)

    stocks = data.get("stocks", [])
    sector_scores = data.get("sector_scores", {})
    updated = data.get("updated_at", "")
    nikkei = data.get("nikkei_price", 0)
    nikkei_chg = data.get("nikkei_1d_chg", 0)

    if not stocks:
        print("❌ 銘柄データなし")
        sys.exit(1)

    # ── スコア計算（JS側と同等の簡易版）──
    def calc_score(s):
        score = 0
        # 時価総額（18pt）
        mc = s.get("market_cap_b", 0) or 0
        if mc >= 30000: score += 18
        elif mc >= 10000: score += 15
        elif mc >= 5000: score += 12
        elif mc >= 3000: score += 9
        elif mc >= 1000: score += 6
        elif mc >= 500: score += 3

        # 配当（15pt）
        div = s.get("dividend", 0) or 0
        if div >= 4: score += 15
        elif div >= 3.5: score += 13
        elif div >= 3: score += 11
        elif div >= 2.5: score += 8
        elif div >= 2: score += 5

        # MA75乖離（15pt）
        ma75d = s.get("ma75_dev", 0) or 0
        if -3 <= ma75d <= 0: score += 15
        elif -5 <= ma75d < -3: score += 12
        elif 0 < ma75d <= 3: score += 10
        elif -8 <= ma75d < -5: score += 7

        # リターン系（簡易）
        ret120 = s.get("ret120", 0) or 0
        if ret120 >= 15: score += 10
        elif ret120 >= 5: score += 7
        elif ret120 >= 0: score += 4

        return min(score, 100)

    # スコア付与
    scored = []
    for s in stocks:
        sc = calc_score(s)
        # タイプ判定
        ma75d = s.get("ma75_dev", 0) or 0
        ma25d = s.get("ma25_dev", 0) or 0
        if ma75d < -5:
            t = "falling"
        elif -5 <= ma75d <= 3 and ma25d < -1:
            t = "dip"
        elif ma75d > 0 and ma25d > 0:
            t = "momentum"
        else:
            t = "neutral"
        scored.append({**s, "score": sc, "trend_type": t})

    scored.sort(key=lambda x: -x["score"])

    # 割安TOP3
    dips = [s for s in scored if s["trend_type"] == "dip"][:3]
    # 上昇TOP3
    moms = [s for s in scored if s["trend_type"] == "momentum"
            and (s.get("market_cap_b", 0) or 0) >= 1000][:3]
    # セクターTOP3
    sec_top3 = list(sector_scores.items())[:3]

    # ── ツイート組み立て ──
    lines = []
    lines.append("📊 かぶのすけ 今日の分析")
    if nikkei:
        chg_str = f"+{nikkei_chg}" if nikkei_chg >= 0 else str(nikkei_chg)
        lines.append(f"日経 ¥{nikkei:,.0f}（{chg_str}%）")
    lines.append("")

    if dips:
        lines.append("📉 割安チャンス")
        for s in dips:
            div_str = f" 💰{s.get('dividend',0):.1f}%" if (s.get('dividend',0) or 0) >= 2.5 else ""
            lines.append(f"  {s['name']}（{s['score']}pt）{div_str}")

    if moms:
        lines.append("📈 上昇中")
        for s in moms:
            lines.append(f"  {s['name']}（{s['score']}pt）")

    if sec_top3:
        sec_names = "・".join(name for name, _ in sec_top3)
        lines.append(f"🏆 注目セクター：{sec_names}")

    lines.append("")
    lines.append("https://oshime.vercel.app/app.html")
    lines.append("#かぶのすけ #株 #高配当 #投資")

    tweet = "\n".join(lines)

    # 280文字制限チェック（日本語は2文字カウント）
    # X APIは280文字だが日本語は1文字=2。実質140文字。安全マージン確保
    if len(tweet) > 260:
        # 長すぎる場合は上昇中をカット
        lines = [l for l in lines if not l.startswith("📈") and not (l.startswith("  ") and moms)]
        tweet = "\n".join(lines)

    return tweet


# ─── メイン ───
if __name__ == "__main__":
    tweet_text = generate_tweet()

    print("=" * 50)
    print("📝 投稿内容:")
    print("=" * 50)
    print(tweet_text)
    print("=" * 50)
    print(f"文字数: {len(tweet_text)}")

    # API認証情報チェック
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET]):
        print("\n⚠ X API認証情報が未設定。ドライラン（投稿なし）。")
        print("  GitHub Secrets に以下を設定してください:")
        print("  - X_API_KEY")
        print("  - X_API_SECRET")
        print("  - X_ACCESS_TOKEN")
        print("  - X_ACCESS_TOKEN_SECRET")
        sys.exit(0)

    # 投稿
    success = post_tweet(tweet_text)
    sys.exit(0 if success else 1)
