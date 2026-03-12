#!/usr/bin/env python3
"""
かぶのすけ AIコメンタリー生成 — generate_commentary.py (Gemini版)
=====================================================
stocks_data.json + sentiment_latest.json を読み込み、
Gemini API で市場全体コメント＋個別銘柄コメントを生成。
出力: commentary.json（app.html が読み込む）

GitHub Actions で fetch_stocks.py の後に実行。
"""

import json, os, sys, datetime

# ─── Google Generative AI SDK ───
try:
    import google.generativeai as genai
except ImportError:
    print("⚠ google-generativeai パッケージがありません。pip install google-generativeai")
    sys.exit(1)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    print("⚠ GEMINI_API_KEY が未設定です")
    sys.exit(1)

genai.configure(api_key=API_KEY)
MODEL = "gemini-2.0-flash"

# ─── データ読み込み ───
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ {path} 読込失敗: {e}")
        return None


def build_prompt(stocks_data, sentiment_data):
    """Gemini API に渡すプロンプトを構築"""

    stocks = sorted(
        [s for s in stocks_data.get("stocks", []) if s.get("market_cap_b", 0) > 0],
        key=lambda s: s.get("market_cap_b", 0),
        reverse=True,
    )[:30]

    stock_lines = []
    for s in stocks:
        stock_lines.append(
            f"{s.get('code')} {s.get('name')} "
            f"現値{s.get('price')} 前日比{s.get('change_pct',0):.1f}% "
            f"RSI{s.get('rsi','-')} 配当{s.get('dividend_yield',0):.1f}% "
            f"PBR{s.get('pbr','-')} 時価総額{s.get('market_cap_b',0):.0f}B"
        )

    sentiment_text = ""
    if sentiment_data:
        macro = sentiment_data.get("macro", {})
        sentiment_text = f"""
YouTubeセンチメント:
  強気ワード: {', '.join(macro.get('word', {}).get('bull', [])[:5])}
  弱気ワード: {', '.join(macro.get('word', {}).get('bear', [])[:5])}
"""

    prompt = f"""あなたは日本株の個人投資家向けAIアナリスト「かぶのすけ」です。
以下のデータを分析し、JSONのみを返してください（前置き・説明・マークダウン不要）。

【株式データ TOP30（時価総額順）】
{chr(10).join(stock_lines)}

{sentiment_text}

【出力形式】必ずこのJSON構造のみ返すこと：
{{
  "market": {{
    "comment": "市場全体の状況を2〜3文で（かぶのすけの一人称、です・ます調）",
    "daily_feel": "sunny | sunset | storm のいずれか1語のみ（sunny=堅調、sunset=やや不安、storm=波乱）",
    "tags": ["タグ1（絵文字+短文）", "タグ2", "タグ3", "タグ4", "タグ5"]
  }},
  "stocks": {{
    "銘柄コード": {{
      "text": "個別コメント（<strong>強調</strong>タグ使用可、2〜3文）",
      "signal": "buy | watch | caution のいずれか"
    }}
  }}
}}

【分析方針】
- テンプレ的な「RSI○○で売られすぎ」だけの分析はNG。もっと踏み込む
- 「なぜこの銘柄が今注目か」を1文で説明すること
- YouTubeセンチメントに関連する銘柄があれば、投資家の温度感を必ず織り交ぜる
- 複数の指標を組み合わせた分析をする
- 「買い」「売り」の断定はせず、「面白い水準」「注意が必要」のようにヒントを出す
- 同じフレーズの使い回しを避ける
"""
    return prompt


def generate(stocks_data, sentiment_data):
    """Gemini API を呼んでコメンタリーを生成"""
    prompt = build_prompt(stocks_data, sentiment_data)

    model = genai.GenerativeModel(MODEL)
    print("🤖 Gemini API 呼び出し中...")

    response = model.generate_content(prompt)
    text = response.text.strip()

    # ```json ... ``` を除去
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

    stocks_data = load_json("stocks_data.json")
    if not stocks_data or not stocks_data.get("stocks"):
        print("⚠ stocks_data.json が空です。スキャンを先に実行してください。")
        sys.exit(1)

    sentiment_data = load_json("sentiment_latest.json")
    if not sentiment_data:
        print("⚠ sentiment_latest.json なし。YouTube情報なしで生成します。")

    try:
        result = generate(stocks_data, sentiment_data)
    except Exception as e:
        print(f'⚠️ API呼び出し失敗: {e}')
        print('📝 コメンタリー生成をスキップします')
        sys.exit(0)

    if not result:
        print("❌ 生成失敗")
        sys.exit(1)

    result["date"] = now.strftime("%Y/%m/%d %H:%M") + " 自動生成"

    with open("commentary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    market_tags = len(result.get("market", {}).get("tags", []))
    stock_comments = len(result.get("stocks", {}))
    file_size = os.path.getsize("commentary.json") / 1024

    print(f"\n✅ commentary.json 出力完了 ({file_size:.1f} KB)")
    print(f"   マーケットタグ: {market_tags}個")
    print(f"   個別コメント: {stock_comments}銘柄")
    print(f"   日時: {result['date']}")
    print(f"   daily_feel: {result.get('market', {}).get('daily_feel', 'なし')}")

    for code, cmt in result.get("stocks", {}).items():
        preview = cmt.get("text", "")[:40].replace("<strong>", "").replace("</strong>", "")
        print(f"   💬 {code}: {preview}...")


if __name__ == "__main__":
    main()
