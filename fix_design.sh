#!/bin/bash
# ============================================================
# デザイン改善: 背景明るく / 上昇=赤統一 / ボタン視認性向上
# ============================================================
cd ~/oshime
git pull

python3 << 'PYEOF'
with open("app.html", "r") as f:
    content = f.read()

changes = 0

# ──────────────────────────────────────────────
# 1. 背景を明るいダークグレーに
#    #000→#0a0a0a, #0a0a0a→#111, #0f0f0f→#161616, #181818→#1e1e1e
# ──────────────────────────────────────────────

# CSS変数の基本背景
content = content.replace(
    "--bg:#000000; --bg2:#0a0a0a; --bg3:#0f0f0f;",
    "--bg:#0a0a0a; --bg2:#141414; --bg3:#1a1a1a;"
)
content = content.replace(
    "--border:rgba(255,255,255,0.05);",
    "--border:rgba(255,255,255,0.08);"
)
content = content.replace(
    "--text3:#555555;",
    "--text3:#666666;"
)

# Robinhood override セクションの #181818 → #1e1e1e
# html/body backgrounds
content = content.replace(
    "html{font-size:15px;background:#000}\nbody{background:#000;color:#e0e0e0}",
    "html{font-size:15px;background:#0a0a0a}\nbody{background:#0a0a0a;color:#e0e0e0}"
)
# Topbar
content = content.replace(
    ".topbar{background:rgba(0,0,0,0.88);",
    ".topbar{background:rgba(10,10,10,0.92);"
)

# 全体的に #181818 → #1e1e1e (Robinhood override内)
old_overrides = [
    ".hero{background:#181818;",
    ".trust-bar{background:#181818;",
    ".pulse-item{background:#181818!important;",
    ".rank-card{background:#181818!important;",
    ".mkt-card{background:#181818!important;",
    ".detail-panel{background:#181818;",
    ".sec-wrap{background:#181818!important;",
    ".top10-card,.sec-card{background:#181818!important;",
    ".settings-panel{background:#181818!important;",
    ".logic-modal{background:#181818!important;",
    ".watch-card{background:#181818!important;",
    ".brain-wrap{background:#181818!important;",
]
for old in old_overrides:
    new = old.replace("#181818", "#1e1e1e")
    if old in content:
        content = content.replace(old, new)

# borders もう少し見える化
content = content.replace(
    "border:1px solid rgba(255,255,255,0.07)!important;border-radius:16px",
    "border:1px solid rgba(255,255,255,0.10)!important;border-radius:16px"
)
content = content.replace(
    "border:1px solid rgba(255,255,255,0.07)!important;border-radius:14px",
    "border:1px solid rgba(255,255,255,0.10)!important;border-radius:14px"
)
content = content.replace(
    "border:1px solid rgba(255,255,255,0.07);border-radius:14px",
    "border:1px solid rgba(255,255,255,0.10);border-radius:14px"
)

# tabs & backgrounds
content = content.replace(
    ".t5-tabs{background:#0f0f0f;",
    ".t5-tabs{background:#141414;"
)
content = content.replace(
    ".t5-tab.active{background:#1a1a1a!important;",
    ".t5-tab.active{background:#252525!important;"
)

changes += 1
print("✅ 1. 背景を明るいダークグレーに変更")

# ──────────────────────────────────────────────
# 2. 上昇=赤 / 下落=緑 に統一（日本株式市場慣習）
# ──────────────────────────────────────────────

# ランキング: r-up を赤に、r-dn を緑に
content = content.replace(
    ".rank-chg.r-up{background:rgba(42,157,106,0.2);color:#4aeaaa;}",
    ".rank-chg.r-up{background:rgba(255,77,77,0.15);color:#ff7a85;}"
)
content = content.replace(
    ".rank-chg.r-dn{background:rgba(255,90,100,0.15);color:#ff7a85;}",
    ".rank-chg.r-dn{background:rgba(42,157,106,0.15);color:#4aeaaa;}"
)
content = content.replace(
    ".rank-chg.r-big-up{background:rgba(42,157,106,0.35);color:#4aeaaa;font-weight:700;}",
    ".rank-chg.r-big-up{background:rgba(255,77,77,0.3);color:#ff7a85;font-weight:700;}"
)
content = content.replace(
    ".rank-chg.r-big-dn{background:rgba(255,90,100,0.3);color:#ff7a85;font-weight:700;}",
    ".rank-chg.r-big-dn{background:rgba(42,157,106,0.3);color:#4aeaaa;font-weight:700;}"
)

# 詳細パネル: r-up を赤に
content = content.replace(
    ".detail-chg-big.r-up{background:rgba(42,157,106,0.25);color:#4aeaaa;}",
    ".detail-chg-big.r-up{background:rgba(255,77,77,0.2);color:#ff7a85;}"
)
content = content.replace(
    ".detail-chg-big.r-dn{background:rgba(255,90,100,0.2);color:#ff7a85;}",
    ".detail-chg-big.r-dn{background:rgba(42,157,106,0.2);color:#4aeaaa;}"
)

# マーケットパルス: .pc-v.up / .pc-c.up を赤に
content = content.replace(
    ".pc-v.up{color:var(--up);}  .pc-v.dn{color:var(--dn);}",
    ".pc-v.up{color:var(--dn);}  .pc-v.dn{color:var(--up);}"
)
content = content.replace(
    ".pc-c.up{color:var(--up);}  .pc-c.dn{color:var(--dn);}",
    ".pc-c.up{color:var(--dn);}  .pc-c.dn{color:var(--up);}"
)

# tbl-prev（テーブル内の前日比）を日本式に
content = content.replace(
    ".tbl-prev.up{color:var(--up);}\n.tbl-prev.dn{color:var(--dn);}",
    ".tbl-prev.up{color:var(--dn);}\n.tbl-prev.dn{color:var(--up);}"
)

# Robinhood override内の色も修正
content = content.replace(
    ".rank-chg.up{color:var(--green)!important}\n.rank-chg.dn{color:var(--dn)!important}",
    ".rank-chg.up{color:var(--dn)!important}\n.rank-chg.dn{color:var(--green)!important}"
)
content = content.replace(
    ".detail-chg-big.up{color:var(--green)!important}\n.detail-chg-big.dn{color:var(--dn)!important}",
    ".detail-chg-big.up{color:var(--dn)!important}\n.detail-chg-big.dn{color:var(--green)!important}"
)
# ポートフォリオ内の chg も統一
content = content.replace(
    ".pf-chg.up{color:var(--green)!important}\n.pf-chg.dn{color:var(--dn)!important}",
    ".pf-chg.up{color:var(--dn)!important}\n.pf-chg.dn{color:var(--green)!important}"
)
content = content.replace(
    ".pf-stock-chg.up{color:var(--green)!important}\n.pf-stock-chg.dn{color:var(--dn)!important}",
    ".pf-stock-chg.up{color:var(--dn)!important}\n.pf-stock-chg.dn{color:var(--green)!important}"
)

changes += 1
print("✅ 2. 上昇=赤 / 下落=緑 に統一（日本式）")

# ──────────────────────────────────────────────
# 3. 押せる場所をわかりやすく
# ──────────────────────────────────────────────

# 既存の Robinhood override の最後（</style> の前）に追加
clickability_css = """
/* ═══════════════════════════════════════
   CLICKABILITY IMPROVEMENTS
   ═══════════════════════════════════════ */

/* ── クリッカブルカードに hover エフェクト ── */
.top10-card:hover{background:#252525!important;border-color:rgba(0,220,130,0.2)!important;transform:translateY(-1px);transition:all 0.15s ease}
.top10-card{transition:all 0.15s ease}

.sec-tile:hover{background:#252525!important;border-color:rgba(0,220,130,0.2)!important;transform:translateY(-1px);transition:all 0.15s ease}
.sec-tile{transition:all 0.15s ease}

.rank-row:hover{background:rgba(0,220,130,0.04)!important}
.rank-row.active{background:rgba(0,220,130,0.08)!important}

/* ── ボタン類を目立たせる ── */
.btn-topbar{border:1px solid rgba(0,220,130,0.2)!important;color:var(--green)!important;font-weight:700!important;transition:all 0.15s ease}
.btn-topbar:hover{background:rgba(0,220,130,0.12)!important;border-color:rgba(0,220,130,0.35)!important}

.d-btn{border:1px solid rgba(0,220,130,0.2)!important;transition:all 0.15s ease}
.d-btn:hover{background:rgba(0,220,130,0.1)!important;border-color:rgba(0,220,130,0.35)!important;transform:translateY(-1px)}

.pf-note-link{transition:all 0.15s ease}
.pf-note-link:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,220,130,0.15)!important}

/* ── タブに hover インジケータ ── */
.t5-tab{transition:all 0.15s ease}
.t5-tab:hover:not(.active){background:rgba(255,255,255,0.05)!important;color:#aaa!important}

.nav-tab{transition:all 0.15s ease}
.nav-tab:hover:not(.active){background:rgba(255,255,255,0.04)}

.nav-item{transition:color 0.15s ease}
.nav-item:hover:not(.active){color:#888!important}

/* ── ランキング行にクリック可能感 ── */
.rank-row{transition:background 0.1s ease;position:relative}
.rank-row::after{content:'▸';position:absolute;right:8px;top:50%;transform:translateY(-50%);font-size:9px;color:rgba(255,255,255,0.1);transition:color 0.15s}
.rank-row:hover::after{color:rgba(0,220,130,0.4)}

/* ── TOP10カードの展開インジケータを見やすく ── */
.top10-card .top10-right div[style*="詳細"]{color:var(--green)!important;opacity:0.6}
.top10-card:hover .top10-right div[style*="詳細"]{opacity:1}

/* ── ウォッチリスト行 ── */
.watch-row{transition:all 0.15s ease}
.watch-row:hover{background:#252525!important;border-color:rgba(0,220,130,0.15)!important}

/* ── 設定ボタン ── */
.setting-opt{transition:all 0.12s ease}
.setting-opt:hover:not(.active){border-color:rgba(255,255,255,0.2)!important;background:rgba(255,255,255,0.06)!important}
.settings-save{transition:all 0.15s ease}
.settings-save:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,220,130,0.2)}

/* ── テーブル行のhover ── */
.stock-table tr.tbl-row:hover{background:#1e1e1e!important}
.stock-table tr.tbl-row{cursor:pointer;transition:background 0.1s}

/* ── フィルター設定 ── */
.filter-tab{transition:all 0.12s ease}
.filter-tab:hover:not(.active){border-color:rgba(255,255,255,0.15);background:rgba(255,255,255,0.06)}
"""

# </style> の直前に追加
if "CLICKABILITY IMPROVEMENTS" not in content:
    content = content.replace("</style>\n</head>", clickability_css + "\n</style>\n</head>")
    changes += 1
    print("✅ 3. クリッカブル要素のUI改善追加")
else:
    print("ℹ️  3. CLICKABILITY IMPROVEMENTS（既に追加済み）")

# 保存
with open("app.html", "w") as f:
    f.write(content)
print(f"\n✅ app.html: {changes}件のデザイン変更を保存")
PYEOF

echo ""
echo "=== 変更差分 ==="
git diff --stat
echo ""

read -p "コミット＆プッシュしますか？ (y/n): " yn
if [ "$yn" = "y" ]; then
  git add app.html
  git commit -m "🎨 デザイン改善: 背景明るく / 上昇=赤統一 / ボタン視認性UP

- ボックス背景: #181818 → #1e1e1e、ボーダー視認性向上
- 日本株式慣習: 上昇=赤 / 下落=緑 を全セクション統一
  (ランキング・パルス・テーブル・詳細パネル)
- クリッカブル要素: hover時にリフト・ボーダー発光・矢印表示
- タブ・ボタン: hover状態を明確化"
  git push
  echo ""
  echo "✅ デプロイ完了！"
else
  echo "キャンセル。git diff で確認してください。"
fi
