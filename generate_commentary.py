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

    # ── マーケットインテリジェンス読み込み ──
    intel_data = load_json("market_intelligence.json")
    intel_parts = []
    if intel_data:
        # noteトレンド
        notes = intel_data.get("note_trends", [])[:5]
        if notes:
            note_lines = [f"  ♥{n['likes']} {n['title'][:50]}" for n in notes]
            intel_parts.append("noteトレンド（#日本株 人気記事）:\n" + "\n".join(note_lines))
        # 日経見出し
        headlines = intel_data.get("nikkei_headlines", [])[:8]
        if headlines:
            hl_lines = [f"  [{h['category']}] {h['title'][:50]}" for h in headlines]
            intel_parts.append("日経ニュース見出し:\n" + "\n".join(hl_lines))
        # 恐怖指数
        fg = intel_data.get("fear_greed", {})
        if fg.get("vix"):
            intel_parts.append(f"恐怖指数: VIX={fg['vix']} → {fg.get('rating_jp','不明')}（{fg.get('score',50)}pt）")
        # 株探ニュース
        kabutan = intel_data.get("kabutan_news", [])[:5]
        if kabutan:
            kb_lines = [f"  {n['title'][:50]}" for n in kabutan]
            intel_parts.append("株探ニュース:\n" + "\n".join(kb_lines))
        # TradingViewシグナル
        tv = intel_data.get("tradingview_signals", [])
        if tv:
            tv_lines = [f"  {s['code']}: {s['signal_jp']}（{s['score']:+.3f}）" for s in tv[:10]]
            intel_parts.append("TradingViewテクニカル:\n" + "\n".join(tv_lines))
        # みんかぶ予想
        mk = [b for b in intel_data.get("yahoo_board", []) if "error" not in b]
        if mk:
            mk_lines = [f"  {b['code']}: 目標{b.get('target_price','?')}円 個人={b.get('individual_rating','?')} アナリスト={b.get('analyst_rating','?')}" for b in mk]
            intel_parts.append("みんかぶ予想:\n" + "\n".join(mk_lines))
        # TDnet適時開示
        tdnet = intel_data.get("tdnet_disclosures", [])[:5]
        if tdnet:
            td_lines = [f"  {d['title'][:50]}" for d in tdnet]
            intel_parts.append("TDnet適時開示（注目）:\n" + "\n".join(td_lines))
        # Google News
        gnews = intel_data.get("google_news", [])[:5]
        if gnews:
            gn_lines = [f"  {n['title'][:50]}" for n in gnews]
            intel_parts.append("Google News（日本株関連）:\n" + "\n".join(gn_lines))
    intelligence_text = "\n\n".join(intel_parts) if intel_parts else "データなし"

    # ── 記事要約読み込み ──
    summaries_data = load_json("article_summaries_latest.json")
    summaries_text = "データなし"
    if summaries_data:
        articles = summaries_data.get("articles", [])[:8]
        if articles:
            sum_lines = [f"[{a['source']}] {a['title'][:40]}\n  {a['summary'][:100]}" for a in articles]
            summaries_text = "\n\n".join(sum_lines)

    # ── 記事要約読み込み ──
    summaries_data = load_json("article_summaries_latest.json")
    summaries_text = "データなし"
    if summaries_data:
        articles = summaries_data.get("articles", [])[:8]
        if articles:
            sum_lines = [f"[{a['source']}] {a['title'][:40]}\n  {a['summary'][:100]}" for a in articles]
            summaries_text = "\n\n".join(sum_lines)

    # コメント対象の銘柄コード（TOP30から注目度が高そうな10銘柄を選ぶ指示）
    # ── 曜日で出力モードを切り替え ──
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    weekday = now.weekday()  # 0=月 ... 6=日
    is_weekend = weekday >= 5  # 土=5, 日=6

    if is_weekend and weekday == 5:
        mode_instruction = """
## 今日は【土曜日】です。「今週の振り返り」モードで出力してください。

### market.text の書き方（200-250文字）
- 今週の市場全体の動きを振り返る（日経・為替・VIXの週間推移）
- YouTubeの投資家たちが今週何に注目していたかを総括する
- 来週に向けた注意点を1つ挙げる
- 「今週は○○な1週間でした」のような書き出しで始める

### stocks の書き方
- 今週の値動きが大きかった銘柄を中心に選ぶ
- 「今週+○%」のような週間パフォーマンス目線でコメント
- 週間で見た時のトレンド変化に言及する
"""
    elif is_weekend and weekday == 6:
        mode_instruction = """
## 今日は【日曜日】です。「来週の展望」モードで出力してください。

### market.text の書き方（200-250文字）
- 来週の注目イベント（経済指標・決算・政治）に言及する
- YouTubeの投資家たちの来週への温度感を伝える
- 地政学リスクがあればそれも必ず触れる
- 「来週は○○に注目ですね」のような書き出しで始める

### stocks の書き方
- 来週イベントがある銘柄（決算・権利日など）を優先
- テクニカル的に来週動きそうな銘柄（RSI極端・MA乖離大）
- 「来週は○○に注目」目線でコメント
"""
    else:
        mode_instruction = """
## 今日は【平日】です。通常の「今日の見立て」モードで出力してください。
"""

    prompt = f"""あなたは「かぶのすけ」というAI投資キャラクターです。
性格: データ重視、冷静、高配当×割安が好き、でも少しユーモアあり。一人称は「僕」。
{mode_instruction}
以下のデータを元に、2つのコメントを生成してください。

## 市場データ
{market_info}

## YouTube投資チャンネルの空気感
{sentiment_text}

## マーケットインテリジェンス（noteトレンド・日経見出し・恐怖指数）
{intelligence_text}

## 記事要約（株探・note等の最新記事）
{summaries_text}

## 記事要約（株探・note等の最新記事）
{summaries_text}

## 時価総額TOP30の株価データ
{stock_summary}

## 出力形式（JSONのみ出力。```json は不要）

{{
  "market": {{
    "text": "全体コメント（平日:150-200文字、週末:200-250文字。HTMLの<strong>タグで重要部分を強調。YouTubeの空気感にも必ず言及。）",
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
- 同じフレーズの使い回しを避ける。銘柄ごとに切り口を変える

"""

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
    try:
        result = generate(stocks_data, sentiment_data)
    except Exception as e:
        print(f'⚠️ API呼び出し失敗（クレジット不足？）: {e}')
        print('📝 コメンタリー生成をスキップします')
        import sys; sys.exit(0)
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
