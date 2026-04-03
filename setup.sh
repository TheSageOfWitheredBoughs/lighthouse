#!/bin/bash
# setup.sh — lighthouse pre-commitフック設置スクリプト
# 使用方法: bash setup.sh（リポジトリルートで実行）

set -e

HOOK_PATH=".git/hooks/pre-commit"

echo "🔧 lighthouse セットアップを開始します..."

# .gitディレクトリの存在確認
if [ ! -d ".git" ]; then
  echo "❌ エラー: .gitディレクトリが見つかりません。"
  echo "   リポジトリのルートディレクトリで実行してください。"
  exit 1
fi

# pre-commitフックを作成
cat > "$HOOK_PATH" << 'EOF'
#!/bin/bash
# lighthouse pre-commit hook
# 外部CDN依存と基本的なPIIパターンをチェックします

set -e

echo "🔍 pre-commitチェックを実行中..."

STAGED_HTML=$(git diff --cached --name-only --diff-filter=ACM | grep '\.html$' || true)

if [ -z "$STAGED_HTML" ]; then
  echo "✅ HTMLファイルの変更なし。チェックをスキップします。"
  exit 0
fi

ERRORS=0

for FILE in $STAGED_HTML; do

  # --- 外部CDN依存チェック ---
  if grep -qE 'src="https?://|href="https?://' "$FILE" 2>/dev/null; then
    echo ""
    echo "⚠️  外部依存の可能性: $FILE"
    grep -nE 'src="https?://|href="https?://' "$FILE" | head -5
    echo "   → 外部CDN依存はself-containedHTMLのルール違反です。"
    echo "     ただしClaude Codeによる意味的確認を優先します。"
  fi

  # --- 基本PIIパターンチェック（メールアドレス） ---
  if grep -qE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "$FILE" 2>/dev/null; then
    echo ""
    echo "🚨 PIIの可能性（メールアドレス）: $FILE"
    grep -nE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "$FILE" | head -5
    echo "   → push前にClaude Codeによる意味的PIIチェックを実施してください。"
    ERRORS=$((ERRORS + 1))
  fi

  # --- 電話番号パターンチェック ---
  if grep -qE '0[0-9]{1,4}-[0-9]{2,4}-[0-9]{4}|0[0-9]{9,10}' "$FILE" 2>/dev/null; then
    echo ""
    echo "🚨 PIIの可能性（電話番号）: $FILE"
    grep -nE '0[0-9]{1,4}-[0-9]{2,4}-[0-9]{4}|0[0-9]{9,10}' "$FILE" | head -5
    echo "   → push前にClaude Codeによる意味的PIIチェックを実施してください。"
    ERRORS=$((ERRORS + 1))
  fi

done

echo ""

if [ $ERRORS -gt 0 ]; then
  echo "🚨 PIIの可能性が検出されました。"
  echo "   Claude Codeによる意味的チェックを実施し、問題がないことを確認してからpushしてください。"
  echo "   チェック済みで問題なければ: git commit --no-verify"
  exit 1
fi

echo "✅ pre-commitチェック完了。問題は検出されませんでした。"
exit 0
EOF

chmod +x "$HOOK_PATH"

echo ""
echo "✅ セットアップ完了"
echo "   pre-commitフックを設置しました: $HOOK_PATH"
echo ""
echo "📋 フック機能:"
echo "   - 外部CDN依存の警告"
echo "   - メールアドレスパターンの検出"
echo "   - 電話番号パターンの検出"
echo "   ※ 日本語氏名等の意味的チェックはClaude Code自身が担当します"
echo ""
echo "🚀 lighthouseの準備が整いました。"
