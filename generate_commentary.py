#!/usr/bin/env python3
"""
かぶのすけ AIコメンタリー生成 — generate_commentary.py (Gemini版)
"""

import json, os, sys, datetime

try:
    from google import genai
except ImportError:
    print("⚠ google-genai パッケージがありません。pip3 install google-genai")
    sys.exit(1)

API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    print("⚠ GEMINI_API_KEY が未設定です")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)
MODEL = "models/gemini-2.0-flash"

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠ {path} 読込失敗: {e}")
        return None


def build_prompt(stocks_data, sentiment_data):
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
        macro = sentiment_data.get("macro", [])
        if isinstance(macro, list):
            bull_words = [m["word"] for m in macro if m.get("mood") in ("greed", "hope", "calm")][:5]
            bear_words = [m["word"] for m in macro if m.get("mood") in ("fear", "panic")][:5]
        else:
            bull_words = macro.get("word", {}).get("bull", [])[:5]
            bear_words = macro.get("word", {}).get("bear", [])[:5]
        sentiment_text = f"""
YouTubeセンチメント:
  強気ワード: {", ".join(bull_words)}
  弱気ワード: {", ".join(bear_words)}
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
  }},
  "interview": [
    {{"q": "ねえおにいちゃん、今日の相場ってどう見てるの？", "a": "かぶのすけの答え（20〜40文字、です・ます口調）"}},
    {{"q": "今日SNSとかで何が話題になってたの？", "a": "かぶのすけの答え（YouTubeセンチメントを踏まえて20〜50文字）"}},
    {{"q": "気になってる銘柄とかニュースあった？", "a": "かぶのすけの答え（個別銘柄ニュースを1つ取り上げて30〜50文字）"}},
    {{"q": "今って無理して買わない方がいい感じ？", "a": "かぶのすけの答え（20〜50文字）"}},
    {{"q": "来週どうなりそう？おにいちゃん的には？", "a": "かぶのすけの答え（○○次第ですね、という形で20〜50文字）"}},
    {{"q": "じゃあ今日は何の日って感じ？", "a": "かぶのすけの答え（一言で今日を表現、20〜40文字）"}},
    {{"q": "最後に一言！", "a": "かぶのすけの答え（励まし・共感・たぶん大丈夫です。たぶん。で締めてもOK）"}}
  ]
}}

【分析方針】
- テンプレ的な「RSI○○で売られすぎ」だけの分析はNG。もっと踏み込む
- 「なぜこの銘柄が今注目か」を1文で説明すること
- YouTubeセンチメントに関連する銘柄があれば、投資家の温度感を必ず織り交ぜる
- 複数の指標を組み合わせた分析をする
- 「買い」「売り」の断定はせず、「面白い水準」「注意が必要」のようにヒントを出す
- 同じフレーズの使い回しを避ける
- interviewのqはかぶ子（妹キャラ）の口調。くだけた日本語、「おにいちゃん」と呼ぶ、初心者っぽい素朴な疑問
- interviewのaはかぶのすけのです・ます口調。怖い時は正直に。SNSや銘柄ニュースを具体的に織り込む
- interviewは必ずかぶのすけの一人称・話し言葉で。「〜ですね」「〜と思います」など自然な口語で
- interviewの「来週どうなりそう？」は必ず「〇〇次第ですね」という形で締める
- interviewは感情が伝わるように。怖い時は怖い、強気な時は強気と正直に
"""
    return prompt


def build_fallback(stocks_data):
    """Gemini API が不安定なときに返す固定テキストのフォールバック"""
    stocks = sorted(
        [s for s in stocks_data.get("stocks", []) if s.get("market_cap_b", 0) > 0],
        key=lambda s: s.get("market_cap_b", 0),
        reverse=True,
    )[:5]

    # 簡易的な市場全体の方向感を計算
    changes = [s.get("change_pct", 0) for s in stocks_data.get("stocks", []) if s.get("change_pct") is not None]
    avg_change = sum(changes) / len(changes) if changes else 0
    up_count = sum(1 for c in changes if c > 0)
    down_count = sum(1 for c in changes if c < 0)

    if avg_change > 1:
        daily_feel = "sunny"
        mood = "全体的にしっかりした展開です。無理せず、流れに乗っていきましょう。"
    elif avg_change < -1:
        daily_feel = "storm"
        mood = "今日はちょっと荒れ模様です。こういう日は静かに見守るのも立派な戦略だと思います。"
    else:
        daily_feel = "sunset"
        mood = "方向感に乏しい一日ですね。焦らず、次のチャンスをじっくり待ちましょう。"

    comment = (
        f"本日は値上がり{up_count}銘柄・値下がり{down_count}銘柄でした。"
        f"{mood}"
        f"（※ AI解説は一時的にお休み中です。データは最新のものを表示しています）"
    )

    stock_comments = {}
    for s in stocks:
        code = s.get("code", "")
        name = s.get("name", "")
        chg = s.get("change_pct", 0)
        if chg > 0:
            text = f"<strong>{name}</strong>は前日比+{chg:.1f}%。引き続き注目しています。"
            signal = "watch"
        elif chg < -3:
            text = f"<strong>{name}</strong>は前日比{chg:.1f}%と大きめの下落。慎重に見極めたいところです。"
            signal = "caution"
        else:
            text = f"<strong>{name}</strong>は前日比{chg:.1f}%。大きな動きはありませんが、引き続きウォッチしていきます。"
            signal = "watch"
        stock_comments[str(code)] = {"text": text, "signal": signal}

    return {
        "market": {
            "comment": comment,
            "daily_feel": daily_feel,
            "tags": ["📡データ更新済", "🤖AI一時休止", "📊自動集計", "🔍銘柄監視中", "☕ひと休み"],
        },
        "stocks": stock_comments,
        "interview": [
            {"q": "ねえおにいちゃん、今日の相場ってどう見てるの？", "a": "すみません、今日はAIの調子が悪くて詳しい分析ができていません。データだけは最新ですので参考にしてください。"},
            {"q": "今日SNSとかで何が話題になってたの？", "a": "ちょっと情報収集がうまくいかなかったです。また明日しっかりお届けしますね。"},
            {"q": "気になってる銘柄とかニュースあった？", "a": "今日はお休みをいただいています。銘柄データは最新のものが反映されていますよ。"},
            {"q": "今って無理して買わない方がいい感じ？", "a": "判断材料が揃っていない日は、無理しないのが一番です。"},
            {"q": "来週どうなりそう？おにいちゃん的には？", "a": "AIの回復次第ですね。明日にはちゃんと分析をお届けできると思います。"},
            {"q": "じゃあ今日は何の日って感じ？", "a": "かぶのすけ、充電中の日です。"},
            {"q": "最後に一言！", "a": "ご心配おかけしてすみません。データは動いていますので安心してください。たぶん大丈夫です。たぶん。"},
        ],
    }


def generate(stocks_data, sentiment_data):
    prompt = build_prompt(stocks_data, sentiment_data)
    print("🤖 Gemini API 呼び出し中...")

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    text = response.text.strip()

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
        print(f"⚠️ Gemini API呼び出し失敗: {e}")
        result = None

    if not result:
        print("🔄 フォールバック: 固定テキストで commentary.json を生成します")
        result = build_fallback(stocks_data)

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
