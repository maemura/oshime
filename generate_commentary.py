#!/usr/bin/env python3
"""
かぶのすけ AIコメンタリー生成 — generate_commentary.py
=====================================================
stocks_data.json + sentiment_latest.json を読み込み、
Claude API で市場全体コメント＋個別銘柄コメントを生成。
出力: commentary.json（app.html が読み込む）

GitHub Actions で fetch_stocks.py の後に実行。
"""

import json, os, sys, datetime

# ─── Anthropic SDK ───
try:
    import anthropic
except ImportError:
    print("⚠ anthropic パッケージがありません。pip install anthropic")
    sys.exit(1)

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not API_KEY:
    print("⚠ ANTHROPIC_API_KEY が未設定です")
    sys.exit(1)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4000

# ─── データ読み込み ───
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ {path} 読込失敗: {e}")
        return None


def build_prompt(stocks_data, sentiment_data):
    """Claude API に渡すプロンプトを構築"""

    # TOP30 を時価総額順に抽出
    stocks = sorted(
        [s for s in stocks_data.get("stocks", []) if s.get("market_cap_b", 0) > 0],
        key=lambda s: s.get("market_cap_b", 0),
        reverse=True,
    )[:30]

    # 株データサマリー
    stock_lines = []
    for s in stocks:
        c = s.get("closes_60d", [])
        chg = 0
        if len(c) >= 2:
            chg = round(((c[-1] - c[-2]) / c[-2]) * 100, 2)
        d25 = 0
        if s.get("ma25") and s.get("price"):
            d25 = round(((s["price"] / s["ma25"]) - 1) * 100, 1)
        stock_lines.append(
            f"{s.get('code','?')} {s.get('name','?')}: "
            f"前日比{chg:+.1f}% RSI={s.get('rsi','-')} "
            f"25MA乖離={d25:+.1f}% 配当={s.get('dividend',0):.1f}% "
            f"PBR={s.get('pbr','-')} スコア={s.get('score','-')}pt "
            f"時価総額={s.get('market_cap_b',0):.0f}億"
        )
    stock_summary = "\n".join(stock_lines)

    # 市場データ
    market_info = (
        f"日経平均: {stocks_data.get('nikkei_price','N/A')} "
        f"(前日比{stocks_data.get('nikkei_1d_chg','N/A')}%) "
        f"VIX: {stocks_data.get('vix','N/A')} "
        f"USD/JPY: {stocks_data.get('usdjpy','N/A')} "
        f"米10年債: {stocks_data.get('us10y','N/A')}%"
    )

    # YouTube センチメント
    sentiment_text = "データなし"
    if sentiment_data:
        parts = []
        for layer in ["macro", "institutional", "retail"]:
            items = sentiment_data.get(layer, [])
            if items:
                words = [f"{w['word']}({w['mood']})" for w in items[:8]]
                layer_jp = {"macro": "マクロ", "institutional": "機関投資家", "retail": "個人投資家"}
                parts.append(f"{layer_jp.get(layer, layer)}: {', '.join(words)}")
        sentiment_text = "\n".join(parts)

    # コメント対象の銘柄コード（TOP30から注目度が高そうな10銘柄を選ぶ指示）
    prompt = f"""あなたは「かぶのすけ」というAI投資キャラクターです。
性格: データ重視、冷静、高配当×割安が好き、でも少しユーモアあり。一人称は「僕」。

以下のデータを元に、2つのコメントを生成してください。

## 市場データ
{market_info}

## YouTube投資チャンネルの空気感
{sentiment_text}

## 時価総額TOP30の株価データ
{stock_summary}

## 出力形式（JSONのみ出力。```json は不要）

{{
  "market": {{
    "text": "全体コメント（150-200文字。HTMLの<strong>タグで重要部分を強調。YouTubeの空気感にも必ず言及。）",
    "tags": [
      {{"type": "bullish|bearish|hot|neutral", "label": "🟢|🔴|🟠|⚪ 短いラベル"}}
    ],
    "sources": ["📺 YouTube分析", "📰 ニュース", "📊 テクニカル指標"]
  }},
  "stocks": {{
    "証券コード": {{
      "text": "個別コメント（80-120文字。<strong>で強調。YouTubeの話題やRSI・配当・スコアを織り交ぜる）",
      "sources": ["yt", "news", "tech", "score"]
    }}
  }}
}}

## ルール
1. marketのtagsは3-5個。bullish/bearish/hot/neutralを混ぜる
2. stocksは注目度が高い8-12銘柄を選ぶ（前日比が大きい、RSIが極端、YouTubeで話題、スコアが高いなど）
3. 全銘柄にコメントを書く必要はない。書かない銘柄はstocksに含めない
4. sourcesは実際にコメント内で言及したソースのみ（yt=YouTube, news=ニュース, tech=テクニカル, score=スコア）
5. かぶのすけ口調で書く。丁寧すぎず、データに基づいた分析。時々「…」や「ですね」を使う
6. JSONのみ出力。それ以外のテキストは一切不要

## 重要: 個別銘柄コメントの質について
- テンプレ的な「RSI○○で売られすぎ」だけの分析はNG。もっと踏み込む
- 「なぜこの銘柄が今注目か」を1文で説明すること（業績、テーマ、需給、イベントなど）
- YouTubeセンチメントに関連する銘柄があれば、投資家の温度感を必ず織り交ぜる
- 複数の指標を組み合わせた分析をする（例:「RSI30×配当4.5%×PBR0.8倍のトリプル好条件」）
- 「買い」「売り」の断定はせず、「面白い水準」「注意が必要」のようにヒントを出す
- 同じフレーズの使い回しを避ける。銘柄ごとに切り口を変える"""

    return prompt


def generate(stocks_data, sentiment_data):
    """Claude API を呼んでコメンタリーを生成"""
    prompt = build_prompt(stocks_data, sentiment_data)

    client = anthropic.Anthropic(api_key=API_KEY)
    print("🤖 Claude API 呼び出し中...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    # レスポンスからテキスト抽出
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    # JSON パース
    text = text.strip()
    # ```json ... ``` を除去（念のため）
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠ JSON パース失敗: {e}")
        print(f"レスポンス先頭200文字: {text[:200]}")
        return None

    return result


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    print(f"📝 コメンタリー生成開始: {now.strftime('%Y/%m/%d %H:%M JST')}")

    # データ読み込み
    stocks_data = load_json("stocks_data.json")
    if not stocks_data or not stocks_data.get("stocks"):
        print("⚠ stocks_data.json が空です。スキャンを先に実行してください。")
        sys.exit(1)

    sentiment_data = load_json("sentiment_latest.json")
    if not sentiment_data:
        print("⚠ sentiment_latest.json なし。YouTube情報なしで生成します。")

    # 生成
    result = generate(stocks_data, sentiment_data)
    if not result:
        print("❌ 生成失敗")
        sys.exit(1)

    # 日付を追加
    result["date"] = now.strftime("%Y/%m/%d %H:%M") + " 自動生成"

    # 出力
    with open("commentary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # サマリー
    market_tags = len(result.get("market", {}).get("tags", []))
    stock_comments = len(result.get("stocks", {}))
    file_size = os.path.getsize("commentary.json") / 1024

    print(f"\n✅ commentary.json 出力完了 ({file_size:.1f} KB)")
    print(f"   マーケットタグ: {market_tags}個")
    print(f"   個別コメント: {stock_comments}銘柄")
    print(f"   日時: {result['date']}")

    # コメント付き銘柄を表示
    for code, cmt in result.get("stocks", {}).items():
        preview = cmt.get("text", "")[:40].replace("<strong>", "").replace("</strong>", "")
        print(f"   💬 {code}: {preview}...")


if __name__ == "__main__":
    main()
