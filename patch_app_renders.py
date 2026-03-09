#!/usr/bin/env python3
"""app.htmlに3つのrender関数を追加するパッチ"""

content = open('app.html').read()

old = '// \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\n// RENDER: STANCE'

new_code = r"""// ═══════════════════════════════════════════════
// RENDER: FOCUS (AIが自動で決める今日の注目)
// ═══════════════════════════════════════════════
function renderFocus(){
  const md=marketData;
  let title='',body='',color='var(--green)';
  if(md.vix&&md.vix>=25){
    title='\u26a0\ufe0f リスク警戒モード';color='var(--dn)';
    body='VIXが'+md.vix+'に上昇。恐怖指数が25を超えており、市場は不安定な状態です。新規購入は控えめに。';
  }else if(md.wti_oil&&md.wti_oil>=100){
    title='\ud83d\udee2\ufe0f 原油高騰アラート';color='var(--amber)';
    body='原油がWTI $'+md.wti_oil+'に高騰。エネルギーセクターに追い風、自動車・運輸に逆風。スタグフレーション懸念に注意。';
  }else if(md.nikkei_1d_chg&&md.nikkei_1d_chg<=-3){
    title='\ud83d\udcc9 急落アラート';color='var(--dn)';
    body='日経平均が'+md.nikkei_1d_chg+'%の急落。パニック売りは禁物。損切りラインに達していない限り保持を推奨。';
  }else if(md.nikkei_1d_chg&&md.nikkei_1d_chg>=2){
    title='\ud83d\udcc8 急騰シグナル';color='var(--up)';
    body='日経平均が+'+md.nikkei_1d_chg+'%の急騰。リバウンド局面の可能性。ただし飛び乗りは慎重に。';
  }else if(md.vix&&md.vix<18){
    title='\ud83d\udfe2 平穏モード';color='var(--green)';
    body='VIXが'+md.vix+'と低水準。市場は安定しています。スコア上位銘柄の買い検討タイミング。';
  }else{
    title='\ud83d\udcca 通常モード';color='var(--amber)';
    body='特段の異常値なし。セクター動向とスコアリングを参考に、個別銘柄の分析を。';
  }
  var macro=[];
  if(md.nikkei_price)macro.push('\u65e5\u7d4c '+md.nikkei_price.toLocaleString());
  if(md.vix)macro.push('VIX '+md.vix);
  if(md.wti_oil)macro.push('\u539f\u6cb9 $'+md.wti_oil);
  if(md.usdjpy)macro.push('\xa5/$ '+md.usdjpy);
  if(md.us10y)macro.push('\u7c7310Y '+md.us10y+'%');
  if(md.ny_dow)macro.push('NYDow '+md.ny_dow.toLocaleString());
  if(md.sp500)macro.push('S&P '+md.sp500.toLocaleString());
  var macroStr=macro.length?'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;">'+macro.map(function(m){return '<span style="background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:3px 8px;font-family:var(--fn);font-size:11px;color:var(--text)">'+m+'</span>';}).join('')+'</div>':'';
  var el=document.getElementById('focusBody');
  el.innerHTML='<div style="border-left:3px solid '+color+';padding-left:12px;"><div style="font-family:var(--fh);font-size:14px;font-weight:700;color:var(--text2);margin-bottom:6px;">'+title+'</div><div style="font-size:12px;color:var(--text);line-height:1.7;">'+body+'</div></div>'+macroStr;
  document.getElementById('focusDate').textContent=marketData.updated_at||'';
}

// ═══════════════════════════════════════════════
// RENDER: NEWS
// ═══════════════════════════════════════════════
var intelligenceData=null;
async function loadIntelligence(){
  try{
    var r=await fetch('market_intelligence.json?t='+Date.now());
    if(r.ok)intelligenceData=await r.json();
  }catch(e){}
}
function renderNews(){
  if(!intelligenceData){document.getElementById('newsBody').innerHTML='<div style="padding:14px;font-size:11px;color:var(--text3)">\u30c7\u30fc\u30bf\u306a\u3057</div>';return;}
  var items=[];
  var sources=[
    {key:'nikkei_headlines',icon:'\ud83d\udcf0',name:'\u65e5\u7d4c'},
    {key:'kabutan_news',icon:'\ud83d\udcca',name:'\u682a\u63a2'},
    {key:'google_news',icon:'\ud83c\udf10',name:'Google'},
    {key:'tdnet_disclosures',icon:'\ud83d\udccb',name:'TDnet'},
  ];
  sources.forEach(function(s){
    (intelligenceData[s.key]||[]).slice(0,3).forEach(function(a){
      items.push({icon:s.icon,src:s.name,title:a.title||'',url:a.url||''});
    });
  });
  items=items.slice(0,12);
  if(!items.length){document.getElementById('newsBody').innerHTML='<div style="padding:14px;font-size:11px;color:var(--text3)">\u30cb\u30e5\u30fc\u30b9\u306a\u3057</div>';return;}
  document.getElementById('newsBody').innerHTML=items.map(function(it){return '<a href="'+it.url+'" target="_blank" rel="noopener" style="display:flex;align-items:flex-start;gap:8px;padding:10px 14px;border-bottom:1px solid var(--border);text-decoration:none;color:var(--text);"><span style="flex-shrink:0">'+it.icon+'</span><div><div style="font-size:12px;line-height:1.5;color:var(--text)">'+it.title+'</div><div style="font-size:9px;color:var(--text3);margin-top:2px">'+it.src+'</div></div></a>';}).join('');
}

// ═══════════════════════════════════════════════
// RENDER: SENTIMENT
// ═══════════════════════════════════════════════
var sentimentData=null;
async function loadSentiment(){
  try{
    var r=await fetch('sentiment_latest.json?t='+Date.now());
    if(r.ok)sentimentData=await r.json();
  }catch(e){}
}
function renderSentiment(){
  if(!sentimentData||!sentimentData.channels){document.getElementById('sentimentBody').innerHTML='<div style="font-size:11px;color:var(--text3)">\u30c7\u30fc\u30bf\u306a\u3057</div>';return;}
  var chs=sentimentData.channels;
  var html=chs.map(function(ch){
    var sent=ch.sentiment||'neutral';
    var clr=sent==='bullish'?'var(--up)':sent==='bearish'?'var(--dn)':'var(--amber)';
    var lbl=sent==='bullish'?'\u5f37\u6c17':sent==='bearish'?'\u5f31\u6c17':'\u4e2d\u7acb';
    var topics=(ch.top_topics||[]).slice(0,3).join(', ');
    return '<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);">'+
      '<div style="width:8px;height:8px;border-radius:50%;background:'+clr+';flex-shrink:0;"></div>'+
      '<div style="flex:1;min-width:0;">'+
        '<div style="font-size:12px;color:var(--text2);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+ch.channel_name+'</div>'+
        '<div style="font-size:10px;color:var(--text3);margin-top:1px;">'+topics+'</div>'+
      '</div>'+
      '<div style="font-size:11px;font-weight:700;color:'+clr+';flex-shrink:0;">'+lbl+'</div>'+
    '</div>';
  }).join('');
  document.getElementById('sentimentBody').innerHTML=html;
}

// ═══════════════════════════════════════════════
// RENDER: STANCE"""

content = content.replace(old, new_code)
open('app.html','w').write(content)
print('3 render functions added successfully')
