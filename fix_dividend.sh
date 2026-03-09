#!/bin/bash
cd ~/oshime

# ============================================
# 1. バックエンド修正: fetch_stocks.py
# ============================================
python3 << 'PYEOF'
with open("fetch_stocks.py", "r") as f:
    content = f.read()

# パターン1: 修正済み版（前回の修正が当たっていた場合）
old1 = """            # ファンダメンタル
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

# パターン2: 未修正版（オリジナル）
old2 = """            # ファンダメンタル
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

new = """            # ファンダメンタル
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

if old1 in content:
    print("✅ fetch_stocks.py: 既に修正済み（スキップ）")
elif old2 in content:
    content = content.replace(old2, new)
    with open("fetch_stocks.py", "w") as f:
        f.write(content)
    print("✅ fetch_stocks.py: 配当利回り計算を修正")
else:
    print("⚠️  fetch_stocks.py: 該当箇所が見つかりません（手動確認してください）")
    import sys; sys.exit(1)
PYEOF

# ============================================
# 2. フロントエンド修正: app.html
#    - データ読込時のサニティチェック追加
#    - 年間配当金額の表示追加
# ============================================
python3 << 'PYEOF'
with open("app.html", "r") as f:
    content = f.read()

changes = 0

# --- 2a. データ読込時に配当利回りをサニタイズ ---
old_load = "      STOCKS=j.stocks;"
new_load = """      STOCKS=j.stocks.map(s=>{
        // 配当利回りサニティチェック（yfinanceの返り値ブレ対応）
        if(s.dividend>20) s.dividend=s.dividend>100?Math.round(s.dividend/100*100)/100:0;
        return s;
      });"""

if old_load in content and "サニティチェック" not in content:
    content = content.replace(old_load, new_load, 1)
    changes += 1
    print("✅ app.html: データ読込時のサニティチェック追加")
else:
    print("ℹ️  app.html: サニティチェック（既存 or 該当なし）")

# --- 2b. 年間配当金額を購入金額の横に追加 ---
old_buy = """        💰 購入に必要な金額 → <b style="font-size:16px;color:var(--green)">約${((s.price||0)*100)>=10000?Math.round((s.price||0)*100/10000)+'万':Math.round((s.price||0)*100/1000)+'千'}円</b><span style="font-size:10px;color:var(--text3)">（100株 × ¥${(s.price||0).toLocaleString()}）</span>"""

new_buy = """        💰 購入に必要な金額 → <b style="font-size:16px;color:var(--green)">約${((s.price||0)*100)>=10000?Math.round((s.price||0)*100/10000)+'万':Math.round((s.price||0)*100/1000)+'千'}円</b><span style="font-size:10px;color:var(--text3)">（100株 × ¥${(s.price||0).toLocaleString()}）</span>
        ${(s.dividend||0)>0?`<br>📦 年間配当金 → <b style="font-size:16px;color:var(--green)">約¥${Math.round((s.price||0)*100*(s.dividend||0)/100).toLocaleString()}</b><span style="font-size:10px;color:var(--text3)">（税引前・100株保有時）</span>`:''}\
"""

if old_buy in content:
    content = content.replace(old_buy, new_buy, 1)
    changes += 1
    print("✅ app.html: 年間配当金額の表示を追加")
else:
    print("⚠️  app.html: 購入金額セクションが見つかりません")

if changes > 0:
    with open("app.html", "w") as f:
        f.write(content)
    print(f"✅ app.html: {changes}件の変更を保存")
else:
    print("ℹ️  app.html: 変更なし")
PYEOF

# ============================================
# 3. 差分確認 → コミット → プッシュ
# ============================================
echo ""
echo "=== 変更差分 ==="
git diff --stat
echo ""
git diff fetch_stocks.py | head -60
echo ""
git diff app.html | head -60
echo ""

read -p "この内容でコミットしますか？ (y/n): " yn
if [ "$yn" = "y" ]; then
  git add fetch_stocks.py app.html
  git commit -m "🐛 配当利回りバグ修正 + 年間配当金額の表示追加

- yfinance日本株の返り値ブレ対応（>1ならパーセント値として扱う）
- フロントエンドでも20%超をサニタイズ
- 購入金額の下に年間配当金額（税引前）を表示"
  git push
  echo "✅ デプロイ完了！"
else
  echo "キャンセルしました。手動で確認してください。"
fi
