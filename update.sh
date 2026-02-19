#!/bin/bash
DIR="$HOME/Documents/GitHub/oshime"
cd "$DIR"

echo ""
echo "========================================"
echo "  株の買い場ナビ — データ更新スタート"
echo "  $(date '+%Y/%m/%d %H:%M')"
echo "========================================"
echo ""

echo "[1/3] 株価データを取得します..."
python3 "$DIR/fetch_stocks.py"
if [ $? -ne 0 ]; then
  echo "❌ データ取得でエラーが発生しました。"
  exit 1
fi
echo "✓ データ取得完了"

echo "[2/3] GitHubにコミットします..."
git add stocks_data.json
git commit -m "data update $(date '+%Y/%m/%d %H:%M')" 2>/dev/null || echo "⚠ 変更なし"

echo "[3/3] Vercelに反映します..."
git push
if [ $? -ne 0 ]; then
  echo "❌ pushに失敗しました。"
  exit 1
fi

echo ""
echo "========================================"
echo "  ✅ 更新完了！"
echo "  https://oshime.vercel.app/app.html"
echo "========================================"
