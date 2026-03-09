#!/bin/bash
# ============================================================
# TOP30 リッチ化 + AIコメント品質向上
# ============================================================
cd ~/oshime
git pull

python3 << 'PYEOF'
with open("app.html", "r") as f:
    content = f.read()

changes = 0

# ──────────────────────────────────────────────
# 1. rankStocks にチャート・ファンダデータを追加
# ──────────────────────────────────────────────
old_rank_map = """    return{
      name:NAME_JP[s.code]||s.name||s.code,code:s.code,sector:s.sector||'',
      chg:Math.round(chg*100)/100,
      cap:formatCap(s.market_cap_b),capB:s.market_cap_b||0,
      price:s.price||0,rsi:s.rsi||0,
      ma25d:d25>=0?'+'+d25.toFixed(1)+'%':d25.toFixed(1)+'%',
      div:((s.dividend||0)).toFixed(1)+'%',
      score:s.score||0,
      kokusaku:s.kokusaku||'',
      cmt:cmt
    };"""

new_rank_map = """    return{
      name:NAME_JP[s.code]||s.name||s.code,code:s.code,sector:s.sector||'',
      chg:Math.round(chg*100)/100,
      cap:formatCap(s.market_cap_b),capB:s.market_cap_b||0,
      price:s.price||0,rsi:s.rsi||0,
      ma25d:d25>=0?'+'+d25.toFixed(1)+'%':d25.toFixed(1)+'%',
      div:((s.dividend||0)).toFixed(1)+'%',
      divNum:s.dividend||0,
      pbr:s.pbr||null,
      per:s.per||null,
      ma25:s.ma25||0,
      ma75:s.ma75||0,
      closes_60d:s.closes_60d||[],
      score:s.score||0,
      kokusaku:s.kokusaku||'',
      cmt:cmt
    };"""

if old_rank_map in content:
    content = content.replace(old_rank_map, new_rank_map)
    changes += 1
    print("✅ 1. rankStocks にチャート・ファンダデータ追加")
else:
    print("⚠️  1. rankStocks マッピングが見つかりません")

# ──────────────────────────────────────────────
# 2. showRankDetail を大幅リッチ化
#    - 60日チャート
#    - 購入金額 + 年間配当金額
#    - PBR/PER表示
#    - AIコメント改善
# ──────────────────────────────────────────────
old_detail_stats = """  panel.innerHTML=
    '<div class=\"detail-top\">'+
      '<div class=\"detail-info\"><div class=\"detail-name\">'+s.name+kokBadge+'</div>'+
      '<div class=\"detail-meta\">'+s.code+' ・ '+s.sector+' ・ '+s.cap+'</div></div>'+
      '<div class=\"detail-chg-big '+chgCls+'\">'+sign+s.chg.toFixed(1)+'%</div>'+
      '<button class=\"detail-close\" onclick=\"showRankDetail('+idx+')\">✕</button></div>'+
    '<div class=\"detail-stats\">'+
      '<div class=\"detail-stat\"><div class=\"detail-stat-val\">'+s.rsi+'</div><div class=\"detail-stat-label\">RSI</div></div>'+
      '<div class=\"detail-stat\"><div class=\"detail-stat-val\">'+s.ma25d+'</div><div class=\"detail-stat-label\">25MA乖離</div></div>'+
      '<div class=\"detail-stat\"><div class=\"detail-stat-val\">'+s.div+'</div><div class=\"detail-stat-label\">配当利回り</div></div>'+
      '<div class=\"detail-stat\"><div class=\"detail-stat-val\">'+s.score+'pt</div><div class=\"detail-stat-label\">スコア</div></div>'+
    '</div>'+cmtHtml;"""

new_detail_stats = r"""  // 購入金額・配当金額
  var buyAmt=(s.price||0)*100;
  var buyStr=buyAmt>=10000?'約'+Math.round(buyAmt/10000)+'万円':'約'+Math.round(buyAmt/1000)+'千円';
  var annDiv=Math.round(buyAmt*(s.divNum||0)/100);
  var divAmtStr=annDiv>0?'約¥'+annDiv.toLocaleString():'—';

  // チャート
  var hasSpark=s.closes_60d&&s.closes_60d.length>10;
  var chartHtml=hasSpark?
    '<div style="padding:8px 12px;background:var(--bg2);border-radius:8px;margin-bottom:8px">'+
    '<div style="font-size:10px;font-weight:700;color:var(--text2);margin-bottom:6px">📊 60日チャート</div>'+
    '<svg class="rank-detail-chart" viewBox="0 0 320 100" style="width:100%;height:100px" data-rchart="'+s.code+'"></svg>'+
    '<div style="display:flex;gap:10px;margin-top:4px;font-size:9px;color:var(--text3)">'+
    '<span>株価 ¥'+(s.price||0).toLocaleString()+'</span>'+
    '<span style="color:#F59E0B">25日線 ¥'+(s.ma25||0).toLocaleString()+'</span>'+
    '<span style="color:#059669">75日線 ¥'+(s.ma75||0).toLocaleString()+'</span>'+
    '</div></div>':'';

  // PBR/PER
  var pbrStr=s.pbr?s.pbr.toFixed(2)+'倍':'—';
  var perStr=s.per?s.per.toFixed(0)+'倍':'—';

  panel.innerHTML=
    '<div class="detail-top">'+
      '<div class="detail-info"><div class="detail-name">'+s.name+kokBadge+'</div>'+
      '<div class="detail-meta">'+s.code+' ・ '+s.sector+' ・ '+s.cap+'</div></div>'+
      '<div class="detail-chg-big '+chgCls+'">'+sign+s.chg.toFixed(1)+'%</div>'+
      '<button class="detail-close" onclick="showRankDetail('+idx+')">✕</button></div>'+
    chartHtml+
    '<div style="padding:8px 12px;margin-bottom:8px;background:rgba(0,135,90,0.06);border-radius:8px;border:1px solid rgba(0,135,90,0.15);font-size:12px;color:var(--text)">'+
      '💰 購入に必要な金額 → <b style="font-size:15px;color:var(--green)">'+buyStr+'</b>'+
      '<span style="font-size:9px;color:var(--text3)">（100株 × ¥'+(s.price||0).toLocaleString()+'）</span>'+
      (annDiv>0?'<br>📦 年間配当金 → <b style="font-size:15px;color:var(--green)">'+divAmtStr+'</b><span style="font-size:9px;color:var(--text3)">（税引前・100株保有時）</span>':'')+
    '</div>'+
    '<div class="detail-stats">'+
      '<div class="detail-stat"><div class="detail-stat-val">'+s.rsi+'</div><div class="detail-stat-label">RSI</div></div>'+
      '<div class="detail-stat"><div class="detail-stat-val">'+s.ma25d+'</div><div class="detail-stat-label">25MA乖離</div></div>'+
      '<div class="detail-stat"><div class="detail-stat-val">'+s.div+'</div><div class="detail-stat-label">配当利回り</div></div>'+
      '<div class="detail-stat"><div class="detail-stat-val">'+s.score+'pt</div><div class="detail-stat-label">スコア</div></div>'+
      '<div class="detail-stat"><div class="detail-stat-val">'+pbrStr+'</div><div class="detail-stat-label">PBR</div></div>'+
      '<div class="detail-stat"><div class="detail-stat-val">'+perStr+'</div><div class="detail-stat-label">PER</div></div>'+
    '</div>'+cmtHtml;

  // Draw chart if available
  if(hasSpark){
    setTimeout(function(){
      var el=document.querySelector('[data-rchart="'+s.code+'"]');
      if(el)drawDetailChart(el,s.closes_60d,s.ma25,s.ma75);
    },50);
  }"""

if old_detail_stats in content:
    content = content.replace(old_detail_stats, new_detail_stats)
    changes += 1
    print("✅ 2. showRankDetail にチャート・購入金額・配当金額・PBR/PER追加")
else:
    print("⚠️  2. showRankDetail が見つかりません")

# ──────────────────────────────────────────────
# 3. 自動コメント（commentary.jsonがない時）を大幅改善
# ──────────────────────────────────────────────
old_autotext = """    // Auto-generate comment from data
    var autoText='';
    var rsi=s.rsi||0;
    var divN=parseFloat(s.div)||0;
    var sc=s.score||0;
    if(rsi<=30)autoText+='<strong>RSI'+rsi+'で売られすぎ水準</strong>。押し目チャンスかも。';
    else if(rsi>=70)autoText+='RSI'+rsi+'で過熱気味。利確タイミングに注意。';
    else autoText+='RSI'+rsi+'で中立圏。';
    if(divN>=4)autoText+='配当'+s.div+'は魅力的な高配当水準だね。';
    else if(divN>=2.5)autoText+='配当'+s.div+'で安定感あり。';
    if(sc>=60)autoText+='スコア'+sc+'ptは僕の基準クリア✨';
    else if(sc>=45)autoText+='スコア'+sc+'ptでまずまず。もう少し押したら面白い。';
    else autoText+='スコア'+sc+'pt。今は様子見かな。';
    var autoSrc=['tech','score'].map(function(t){
      var srcLabels={tech:'📊 テクニカル',score:'⭐ スコア'};
      return'<span class=\"src-tag '+t+'\">'+(srcLabels[t]||t)+'</span>';
    }).join('');"""

new_autotext = r"""    // Auto-generate comment from data（リッチ版）
    var autoText='';
    var rsi=s.rsi||0;
    var divN=parseFloat(s.div)||0;
    var sc=s.score||0;
    var d25val=parseFloat(s.ma25d)||0;
    var pbrV=s.pbr||0;
    var perV=s.per||0;
    var chgV=s.chg||0;

    // 1. 値動きの状況
    if(chgV>=3)autoText+='<strong>前日比+'+chgV.toFixed(1)+'%と大幅上昇</strong>。材料が出た可能性あり。';
    else if(chgV<=-3)autoText+='<strong>前日比'+chgV.toFixed(1)+'%と大幅下落</strong>。ネガティブ材料に注意…ただし押し目の可能性も。';
    else if(chgV>=1)autoText+='前日比+'+chgV.toFixed(1)+'%と堅調。';
    else if(chgV<=-1)autoText+='前日比'+chgV.toFixed(1)+'%とやや軟調。';

    // 2. テクニカル分析（RSI + MA乖離を組合せ）
    if(rsi<=30&&d25val<=-5)autoText+='RSI'+rsi+'×25MA乖離'+d25val.toFixed(1)+'%で<strong>ダブルの売られすぎシグナル</strong>。反発狙いには面白い水準。';
    else if(rsi<=30)autoText+='RSI'+rsi+'で売られすぎ水準。自律反発に期待できるゾーン。';
    else if(rsi>=70)autoText+='RSI'+rsi+'で過熱圏。短期的な利確売りに注意。';
    else if(d25val<=-5)autoText+='25MA乖離'+d25val.toFixed(1)+'%で移動平均から大きく下振れ。反発候補。';
    else if(d25val>=5)autoText+='25MAを+'+d25val.toFixed(1)+'%上回り上昇トレンド継続中。';

    // 3. ファンダメンタル（配当+PBR+PERを組合せ）
    if(divN>=4.5&&pbrV>0&&pbrV<=1.0)autoText+='配当'+s.div+'×PBR'+pbrV.toFixed(2)+'倍の<strong>高配当×割安の好条件</strong>。下値は限定的。';
    else if(divN>=4)autoText+='配当'+s.div+'は高配当水準。長期保有でインカム狙いなら◎。';
    else if(divN>=2.5)autoText+='配当'+s.div+'で安定感あり。';
    if(pbrV>0&&pbrV<=0.7&&divN<4)autoText+='PBR'+pbrV.toFixed(2)+'倍で<strong>解散価値割れ</strong>。理論上の下値は固い。';
    if(perV>0&&perV<=10)autoText+='PER'+perV.toFixed(0)+'倍は割安水準。';

    // 4. 総合判定
    if(sc>=60)autoText+='総合'+sc+'ptで<strong>僕の基準をしっかりクリア</strong>✨';
    else if(sc>=45)autoText+='総合'+sc+'pt。あと一押しで狙い目に。';
    else if(sc>=30)autoText+='総合'+sc+'pt。今は様子見が無難かな。';
    else autoText+='総合'+sc+'pt。積極的には動きにくい水準。';

    // 国策テーマ
    if(s.kokusaku)autoText+='<br>🏛️ 国策テーマ「'+s.kokusaku+'」関連で中長期の追い風あり。';

    var autoSources=['tech','score'];
    if(divN>=2.5)autoSources.push('yt');
    var autoSrc=autoSources.map(function(t){
      var srcLabels={tech:'📊 テクニカル',score:'⭐ スコア',yt:'📺 データ分析'};
      return'<span class="src-tag '+t+'">'+(srcLabels[t]||t)+'</span>';
    }).join('');"""

if old_autotext in content:
    content = content.replace(old_autotext, new_autotext)
    changes += 1
    print("✅ 3. 自動コメントをリッチ化")
else:
    print("⚠️  3. 自動コメントが見つかりません")

# ──────────────────────────────────────────────
# 4. 配当利回りサニティチェック（データ読込時）
# ──────────────────────────────────────────────
old_load = "      STOCKS=j.stocks;"
new_load = """      STOCKS=j.stocks.map(s=>{
        if(s.dividend>20) s.dividend=s.dividend>100?Math.round(s.dividend/100*100)/100:0;
        return s;
      });"""

if old_load in content and "s.dividend>20" not in content:
    content = content.replace(old_load, new_load, 1)
    changes += 1
    print("✅ 4. 配当利回りサニティチェック追加")
else:
    print("ℹ️  4. サニティチェック（既存 or 該当なし）")

# ──────────────────────────────────────────────
# 5. TOP10展開詳細にも年間配当金額を追加
# ──────────────────────────────────────────────
old_buy_block = """        💰 購入に必要な金額 → <b style="font-size:16px;color:var(--green)">約${((s.price||0)*100)>=10000?Math.round((s.price||0)*100/10000)+'万':Math.round((s.price||0)*100/1000)+'千'}円</b><span style="font-size:10px;color:var(--text3)">（100株 × ¥${(s.price||0).toLocaleString()}）</span>"""

new_buy_block = """        💰 購入に必要な金額 → <b style="font-size:16px;color:var(--green)">約${((s.price||0)*100)>=10000?Math.round((s.price||0)*100/10000)+'万':Math.round((s.price||0)*100/1000)+'千'}円</b><span style="font-size:10px;color:var(--text3)">（100株 × ¥${(s.price||0).toLocaleString()}）</span>
        ${(s.dividend||0)>0?`<br>📦 年間配当金 → <b style="font-size:16px;color:var(--green)">約¥${Math.round((s.price||0)*100*(s.dividend||0)/100).toLocaleString()}</b><span style="font-size:10px;color:var(--text3)">（税引前・100株保有時）</span>`:``}"""

if old_buy_block in content and "年間配当金" not in content:
    content = content.replace(old_buy_block, new_buy_block, 1)
    changes += 1
    print("✅ 5. TOP10展開詳細にも年間配当金額追加")
elif "年間配当金" in content:
    print("ℹ️  5. 年間配当金（既に追加済み）")
else:
    print("⚠️  5. 購入金額ブロックが見つかりません")

# 保存
with open("app.html", "w") as f:
    f.write(content)
print(f"\n✅ app.html: {changes}件の変更を保存")
PYEOF

echo ""
echo "=== app.html 変更完了 ==="
echo ""

# ──────────────────────────────────────────────
# 6. generate_commentary.py のプロンプト改善
# ──────────────────────────────────────────────
python3 << 'PYEOF'
with open("generate_commentary.py", "r") as f:
    content = f.read()

old_prompt_rules = """## ルール
1. marketのtagsは3-5個。bullish/bearish/hot/neutralを混ぜる
2. stocksは注目度が高い8-12銘柄を選ぶ（前日比が大きい、RSIが極端、YouTubeで話題、スコアが高いなど）
3. 全銘柄にコメントを書く必要はない。書かない銘柄はstocksに含めない
4. sourcesは実際にコメント内で言及したソースのみ（yt=YouTube, news=ニュース, tech=テクニカル, score=スコア）
5. かぶのすけ口調で書く。丁寧すぎず、データに基づいた分析。時々「…」や「ですね」を使う
6. JSONのみ出力。それ以外のテキストは一切不要"""

new_prompt_rules = """## ルール
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

if old_prompt_rules in content:
    content = content.replace(old_prompt_rules, new_prompt_rules)
    with open("generate_commentary.py", "w") as f:
        f.write(content)
    print("✅ 6. generate_commentary.py プロンプト改善")
else:
    print("⚠️  6. generate_commentary.py のルール部分が見つかりません")
PYEOF

echo ""
echo "=== generate_commentary.py 変更完了 ==="
echo ""

# ──────────────────────────────────────────────
# 7. fetch_stocks.py 配当利回りバグ修正
# ──────────────────────────────────────────────
python3 << 'PYEOF'
with open("fetch_stocks.py", "r") as f:
    content = f.read()

old_div = """            # ファンダメンタル
            dividend = info.get("dividendYield")
            if dividend and dividend > 0:
                dividend = round(dividend * 100, 2)  # yfinance returns as decimal
            else:
                # フォールバック: trailingAnnualDividendYield
                dividend = info.get("trailingAnnualDividendYield")
                if dividend and dividend > 0:
                    dividend = round(dividend * 100, 2)
                else:
                    dividend = 0.0"""

new_div = """            # ファンダメンタル
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
                dividend = round(dividend / 100, 2) if dividend > 100 else 0.0"""

if old_div in content:
    content = content.replace(old_div, new_div)
    with open("fetch_stocks.py", "w") as f:
        f.write(content)
    print("✅ 7. fetch_stocks.py 配当利回りバグ修正")
elif "最終サニティチェック" in content:
    print("ℹ️  7. fetch_stocks.py（既に修正済み）")
else:
    print("⚠️  7. fetch_stocks.py 該当箇所が見つかりません")
PYEOF

echo ""
echo "=== 全変更差分 ==="
git diff --stat
echo ""
git diff app.html | head -100
echo ""

read -p "コミット＆プッシュしますか？ (y/n): " yn
if [ "$yn" = "y" ]; then
  git add app.html fetch_stocks.py generate_commentary.py
  git commit -m "✨ TOP30リッチ化 + AIコメント品質向上 + 配当バグ修正

- TOP30詳細: 60日チャート・購入金額・年間配当金額・PBR/PER追加
- 自動コメント: テンプレ脱却→複数指標組合せ分析+国策テーマ言及
- AIプロンプト: 銘柄理解深掘り・SNSデータ活用・切り口多様化を指示
- 配当利回り: yfinance日本株の返り値ブレ対応+フロントサニタイズ
- TOP10展開詳細にも年間配当金額を追加"
  git push
  echo ""
  echo "✅ デプロイ完了！次回スキャンから反映されます。"
else
  echo "キャンセル。手動でgit diffを確認してください。"
fi
