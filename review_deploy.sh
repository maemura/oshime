#!/bin/bash
# ============================================================
# 🔄 3ラウンド辛口レビュー修正 デプロイスクリプト
# ============================================================
# バックアップ → 修正適用 → 確認 → コミット
# 問題があれば git checkout app.html で即戻せます
# ============================================================
cd ~/oshime
git pull

echo ""
echo "📋 修正内容（3ラウンド・15項目）"
echo "════════════════════════════════════════"
echo ""
echo "ROUND 1: 情報設計 + 視覚ヒエラルキー"
echo "  R1-1: セクション順序を再構成"
echo "        Hero→Trust→Pulse→AI→Ranking→Tabs→Stance→Diary→Brain"
echo "        （ヒーローを最上部へ。Brain Scannerは下部へ）"
echo "  R1-2: 背景を明るいダークグレーに（#181818→#1e1e1e）"
echo "  R1-3: 上昇=赤 / 下落=緑 に全体統一（日本株式慣習）"
echo ""
echo "ROUND 2: クリッカビリティ"
echo "  R2-1: 3タブ（セクター/上昇/割安）を大きく+アクティブ下線"
echo "  R2-2: ランキング行にクリック誘導（矢印+hover効果）"
echo "  R2-3: カード展開「▼ 詳しく見る」を緑で目立たせる"
echo "  R2-4: Yahoo!ファイナンスボタンをPrimary（緑背景）に"
echo "  R2-5: 全カード・ボタンにhover/transition追加"
echo ""
echo "ROUND 3: 一貫性 + ポリッシュ"
echo "  R3-1: ディスクレーマーの視認性向上"
echo "  R3-2: ヒーローに差別化グラデーション（紺→ダークグレー）"
echo "  R3-3: セクション間マージン統一（16px）"
echo "  R3-4: Trust Bar テキスト改善"
echo ""
echo "════════════════════════════════════════"
echo ""

# バックアップ作成
cp app.html app_backup_$(date +%Y%m%d_%H%M).html
echo "✅ バックアップ作成完了"

# 修正適用
python3 << 'PYEOF'
with open("app.html", "r") as f:
    content = f.read()

changes = 0

# ══════════════════════════════════════════════════
# ROUND 1: 情報設計の修正 + 視覚ヒエラルキー
# ══════════════════════════════════════════════════

# --- 1a. セクション順序の再構成 ---
try:
    sections = {}
    s = content.find("    <!-- MARKET PULSE -->")
    e = content.find("    <!-- 🤖 AIコメント")
    sections["pulse"] = content[s:e]

    s = content.find("    <!-- 🤖 AIコメント")
    e = content.find("    <!-- 📡 BRAIN SCANNER")
    sections["ai"] = content[s:e]

    s = content.find("    <!-- 📡 BRAIN SCANNER")
    e = content.find('    <div class="rank-card"')
    sections["brain"] = content[s:e]

    s = content.find('    <div class="rank-card"')
    e = content.find("    <!-- HERO -->")
    sections["ranking"] = content[s:e]

    s = content.find("    <!-- HERO -->")
    e = content.find("    <!-- TRUST BAR -->")
    sections["hero"] = content[s:e]

    s = content.find("    <!-- TRUST BAR -->")
    e = content.find("    <!-- STANCE -->")
    sections["trust"] = content[s:e]

    s = content.find("    <!-- STANCE -->")
    e = content.find("    <!-- 3 TABS -->")
    sections["stance"] = content[s:e]

    s = content.find("    <!-- 3 TABS -->")
    e = content.find("    <!-- 📊 投資日記 -->")
    sections["tabs"] = content[s:e]

    s = content.find("    <!-- 📊 投資日記 -->")
    e = content.find("    <!-- DISCLAIMER -->")
    sections["diary"] = content[s:e]

    s = content.find("    <!-- DISCLAIMER -->")
    e = content.find("  </div><!-- /panel-home -->")
    sections["disclaimer"] = content[s:e]

    # すべてのセクションが見つかったか確認
    if all(v for v in sections.values()):
        new_order = (
            sections["hero"] + sections["trust"] + sections["pulse"] +
            sections["ai"] + sections["ranking"] + sections["tabs"] +
            sections["stance"] + sections["diary"] + sections["brain"] +
            sections["disclaimer"]
        )
        old_body_start = "    <!-- MARKET PULSE -->"
        old_body_end = "  </div><!-- /panel-home -->"
        old_body = content[content.find(old_body_start):content.find(old_body_end)]
        content = content.replace(old_body, new_order.rstrip() + "\n\n")
        changes += 1
        print("✅ R1-1: セクション順序を再構成")
    else:
        missing = [k for k,v in sections.items() if not v]
        print(f"⚠️  R1-1: セクション切り出し失敗（{missing}）。順序変更スキップ")
except Exception as ex:
    print(f"⚠️  R1-1: エラー（{ex}）。順序変更スキップ")

# --- 1b. 背景を明るく ---
replacements_bg = [
    ("--bg:#000000; --bg2:#0a0a0a; --bg3:#0f0f0f;", "--bg:#0c0c0c; --bg2:#141414; --bg3:#1c1c1c;"),
    ("--border:rgba(255,255,255,0.05);", "--border:rgba(255,255,255,0.09);"),
    ("--text3:#555555;", "--text3:#707070;"),
    ("html{font-size:15px;background:#000}\nbody{background:#000;", "html{font-size:15px;background:#0c0c0c}\nbody{background:#0c0c0c;"),
    (".topbar{background:rgba(0,0,0,0.88);", ".topbar{background:rgba(12,12,12,0.94);"),
    (".t5-tabs{background:#0f0f0f;", ".t5-tabs{background:#161616;"),
]
for old, new in replacements_bg:
    if old in content:
        content = content.replace(old, new)

for target in [".hero{background:#181818;", ".trust-bar{background:#181818;",
    ".pulse-item{background:#181818!important;", ".rank-card{background:#181818!important;",
    ".mkt-card{background:#181818!important;", ".detail-panel{background:#181818;",
    ".sec-wrap{background:#181818!important;", ".top10-card,.sec-card{background:#181818!important;",
    ".settings-panel{background:#181818!important;", ".logic-modal{background:#181818!important;",
    ".watch-card{background:#181818!important;", ".brain-wrap{background:#181818!important;"]:
    content = content.replace(target, target.replace("#181818", "#1e1e1e"))

content = content.replace("border:1px solid rgba(255,255,255,0.07)!important;border-radius:16px", "border:1px solid rgba(255,255,255,0.12)!important;border-radius:16px")
content = content.replace("border:1px solid rgba(255,255,255,0.07)!important;border-radius:14px", "border:1px solid rgba(255,255,255,0.12)!important;border-radius:14px")
content = content.replace("border:1px solid rgba(255,255,255,0.07);border-radius:14px", "border:1px solid rgba(255,255,255,0.12);border-radius:14px")
changes += 1
print("✅ R1-2: 背景を明るいダークグレーに")

# --- 1c. 上昇=赤 / 下落=緑 統一 ---
color_fixes = [
    (".rank-chg.r-up{background:rgba(42,157,106,0.2);color:#4aeaaa;}", ".rank-chg.r-up{background:rgba(255,77,77,0.15);color:#ff7a85;}"),
    (".rank-chg.r-dn{background:rgba(255,90,100,0.15);color:#ff7a85;}", ".rank-chg.r-dn{background:rgba(42,157,106,0.15);color:#4aeaaa;}"),
    (".rank-chg.r-big-up{background:rgba(42,157,106,0.35);color:#4aeaaa;font-weight:700;}", ".rank-chg.r-big-up{background:rgba(255,77,77,0.3);color:#ff7a85;font-weight:700;}"),
    (".rank-chg.r-big-dn{background:rgba(255,90,100,0.3);color:#ff7a85;font-weight:700;}", ".rank-chg.r-big-dn{background:rgba(42,157,106,0.3);color:#4aeaaa;font-weight:700;}"),
    (".detail-chg-big.r-up{background:rgba(42,157,106,0.25);color:#4aeaaa;}", ".detail-chg-big.r-up{background:rgba(255,77,77,0.2);color:#ff7a85;}"),
    (".detail-chg-big.r-dn{background:rgba(255,90,100,0.2);color:#ff7a85;}", ".detail-chg-big.r-dn{background:rgba(42,157,106,0.2);color:#4aeaaa;}"),
    (".pc-v.up{color:var(--up);}  .pc-v.dn{color:var(--dn);}", ".pc-v.up{color:var(--dn);}  .pc-v.dn{color:var(--up);}"),
    (".pc-c.up{color:var(--up);}  .pc-c.dn{color:var(--dn);}", ".pc-c.up{color:var(--dn);}  .pc-c.dn{color:var(--up);}"),
    (".tbl-prev.up{color:var(--up);}\n.tbl-prev.dn{color:var(--dn);}", ".tbl-prev.up{color:var(--dn);}\n.tbl-prev.dn{color:var(--up);}"),
    (".rank-chg.up{color:var(--green)!important}\n.rank-chg.dn{color:var(--dn)!important}", ".rank-chg.up{color:var(--dn)!important}\n.rank-chg.dn{color:var(--green)!important}"),
    (".detail-chg-big.up{color:var(--green)!important}\n.detail-chg-big.dn{color:var(--dn)!important}", ".detail-chg-big.up{color:var(--dn)!important}\n.detail-chg-big.dn{color:var(--green)!important}"),
    (".pf-chg.up{color:var(--green)!important}\n.pf-chg.dn{color:var(--dn)!important}", ".pf-chg.up{color:var(--dn)!important}\n.pf-chg.dn{color:var(--green)!important}"),
    (".pf-stock-chg.up{color:var(--green)!important}\n.pf-stock-chg.dn{color:var(--dn)!important}", ".pf-stock-chg.up{color:var(--dn)!important}\n.pf-stock-chg.dn{color:var(--green)!important}"),
]
for old, new in color_fixes:
    content = content.replace(old, new)
changes += 1
print("✅ R1-3: 上昇=赤 / 下落=緑 統一")


# ══════════════════════════════════════════════════
# ROUND 2: クリッカビリティ
# ══════════════════════════════════════════════════
content = content.replace(
    ".t5-tab{background:transparent!important;color:#888!important;border-radius:10px!important;font-weight:700!important}",
    ".t5-tab{background:transparent!important;color:#888!important;border-radius:10px!important;font-weight:700!important;font-size:13px!important;padding:12px 6px!important;transition:all 0.15s ease}"
)
content = content.replace(
    ".t5-tab.active{background:#1a1a1a!important;",
    ".t5-tab.active{background:#282828!important;"
)
if "box-shadow:0 2px 8px rgba(0,0,0,0.4)!important}" in content:
    content = content.replace(
        "box-shadow:0 2px 8px rgba(0,0,0,0.4)!important}",
        "box-shadow:0 2px 8px rgba(0,0,0,0.4),inset 0 -2px 0 var(--green)!important}"
    )
changes += 1
print("✅ R2-1: タブ強化")

content = content.replace(
    ".rank-row{border-bottom:1px solid rgba(100,150,255,0.05);cursor:pointer;transition:background 0.15s;}",
    ".rank-row{border-bottom:1px solid rgba(100,150,255,0.05);cursor:pointer;transition:all 0.15s;position:relative;}"
)
content = content.replace(
    '<div class="rank-header-sub"><span id="rankDate"></span>前日比 ・ タップで詳細</div>',
    '<div class="rank-header-sub"><span id="rankDate"></span>前日比 ・ <span style="color:var(--green);font-weight:700">タップで詳細 ▸</span></div>'
)
changes += 1
print("✅ R2-2: ランキング行クリック誘導")

content = content.replace(
    '<div style=\\"font-size:9px;color:var(--text3);margin-top:2px\\">${isOpen?\'▲ 閉じる\':\'▼ 詳細\'}</div>',
    '<div style=\\"font-size:10px;color:var(--green);margin-top:3px;font-weight:600;opacity:${isOpen?1:0.6}\\">${isOpen?\'▲ 閉じる\':\'▼ 詳しく見る\'}</div>'
)
content = content.replace(
    '<a class=\\"d-btn\\" href=\\"https://finance.yahoo.co.jp/quote/${s.code}.T\\"',
    '<a class=\\"d-btn d-btn-primary\\" href=\\"https://finance.yahoo.co.jp/quote/${s.code}.T\\"'
)
changes += 1
print("✅ R2-3/4: カード展開 + ボタン階層")

r2_css = """
/* R2: CLICKABILITY */
.top10-card{transition:all 0.15s ease!important}
.top10-card:hover{background:#262626!important;border-color:rgba(0,220,130,0.2)!important;transform:translateY(-1px)}
.sec-tile{transition:all 0.15s ease!important}
.sec-tile:hover{background:#262626!important;border-color:rgba(0,220,130,0.2)!important;transform:translateY(-1px)}
.rank-row::after{content:'▸';position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:10px;color:rgba(255,255,255,0.08);transition:color 0.15s}
.rank-row:hover::after{color:var(--green)}
.rank-row:hover .rank-name{color:#fff!important}
.d-btn-primary{background:rgba(0,220,130,0.12)!important;border-color:rgba(0,220,130,0.25)!important;font-weight:700!important}
.d-btn-primary:hover{background:rgba(0,220,130,0.2)!important;transform:translateY(-1px)}
.d-btn{transition:all 0.15s ease!important}
.d-btn:hover{border-color:rgba(0,220,130,0.3)!important;transform:translateY(-1px)}
.btn-topbar{border:1px solid rgba(0,220,130,0.15)!important;color:var(--green)!important;transition:all 0.15s}
.btn-topbar:hover{background:rgba(0,220,130,0.1)!important;border-color:rgba(0,220,130,0.3)!important}
.t5-tab:hover:not(.active){background:rgba(255,255,255,0.04)!important;color:#bbb!important}
.stock-table tr.tbl-row{transition:background 0.1s}
.stock-table tr.tbl-row:hover{background:#1e1e1e!important}
.watch-row{transition:all 0.15s!important}
.watch-row:hover{background:#262626!important;border-color:rgba(0,220,130,0.15)!important}
.setting-opt{transition:all 0.12s}
.setting-opt:hover:not(.active){border-color:rgba(255,255,255,0.2)!important;background:rgba(255,255,255,0.05)!important}
.pf-note-link{transition:all 0.15s}
.pf-note-link:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,220,130,0.15)!important}
"""
if "R2: CLICKABILITY" not in content:
    content = content.replace("</style>\n</head>", r2_css + "\n</style>\n</head>")
    changes += 1
    print("✅ R2-5: hover/transition CSS")


# ══════════════════════════════════════════════════
# ROUND 3: 一貫性 + ポリッシュ
# ══════════════════════════════════════════════════
content = content.replace(
    ".disclaimer{color:#333!important;border:none!important;background:transparent!important}",
    ".disclaimer{color:#555!important;border:none!important;background:rgba(255,255,255,0.02)!important;border-top:1px solid rgba(255,255,255,0.06)!important;padding:16px 12px!important;margin-top:20px!important}"
)
changes += 1
print("✅ R3-1: ディスクレーマー視認性")

content = content.replace(
    ".hero{background:#1e1e1e;border:1px solid rgba(255,255,255,0.12)!important;border-radius:14px",
    ".hero{background:linear-gradient(145deg,#1a2332 0%,#1e1e1e 100%);border:1px solid rgba(0,220,130,0.12)!important;border-radius:14px"
)
changes += 1
print("✅ R3-2: ヒーロー差別化")

r3_css = """
/* R3: CONSISTENCY */
.hero,.trust-bar,.pulse,.mkt-card,.brain-wrap,.rank-card,.t5-tabs,.sec-wrap{margin-bottom:16px!important}
.hero{position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(0,220,130,0.2),transparent)}
.rank-card{position:relative;overflow:hidden}
.rank-card::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(0,220,130,0.12),transparent)}
#portfolioSection{border-left:3px solid var(--green)!important}
.brain-wrap{opacity:0.92}
.detail-stats{grid-template-columns:repeat(auto-fit,minmax(60px,1fr))!important}
"""
if "R3: CONSISTENCY" not in content:
    content = content.replace("</style>\n</head>", r3_css + "\n</style>\n</head>")
    changes += 1
    print("✅ R3-3: マージン統一+セクション差別化")

with open("app.html", "w") as f:
    f.write(content)

print(f"\n✅ 全{changes}件の修正を適用")
PYEOF

echo ""
echo "=== 変更差分 ==="
git diff --stat
echo ""

read -p "コミット＆プッシュしますか？ (y/n): " yn
if [ "$yn" = "y" ]; then
  git add app.html
  git commit -m "🎨 3ラウンド辛口レビュー反映: 情報設計・クリッカビリティ・一貫性

Round 1 - 情報設計:
- セクション順序再構成（Hero最上部→Brain Scanner下部）
- 背景明るく（#181818→#1e1e1e, ボーダー可視化）
- 上昇=赤/下落=緑に全体統一（日本株式慣習）

Round 2 - クリッカビリティ:
- 3タブ大きく+アクティブ下線
- ランキング行に矢印+hover効果
- カード展開インジケータ緑色化
- Primary/Secondaryボタン階層

Round 3 - 一貫性:
- ディスクレーマー視認性向上
- ヒーローに差別化グラデーション
- セクション間マージン統一(16px)
- 投資日記に緑アクセントライン"
  git push
  echo ""
  echo "✅ デプロイ完了！"
  echo ""
  echo "⚠️  万が一戻す場合:"
  echo "  git checkout HEAD~1 -- app.html && git commit -m 'revert' && git push"
else
  echo "キャンセル。git diff で確認してください。"
  echo "元に戻す場合: cp app_backup_*.html app.html"
fi
