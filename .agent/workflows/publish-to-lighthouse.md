---
description: 新しいガイドをlighthouseリポジトリに検証・公開する。CDNチェック・PIIスキャン・index.html更新・git push まで自動実行。
---

## 事前確認

1. 公開対象のHTMLファイルのパスを確認する（例: docs/guides/[ガイド名]/index.html）
2. 対象ファイルが存在することを確認する

## Step 1: 外部CDN依存チェック // turbo

対象のHTMLファイルに対して以下を確認する：
- `src="https://` または `href="https://` で始まる外部URLが含まれていないか
- Google Fonts（fonts.googleapis.com）の参照がないか
- 外部CDNのscript/linkタグがないか

問題が見つかった場合：
- 外部フォントはシステムフォントスタックに置き換える（"Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", sans-serif）
- 外部CSSは削除またはインライン化する
- 修正後にStep 1を再実行する

## Step 2: PIIスキャン // turbo

対象のHTMLファイルを意味的に確認する：
- 実名・氏名（姓名）が含まれていないか
- メールアドレス（@を含む文字列）がないか — ただし公式ドメインのサービス説明は除外
- 電話番号（ハイフンあり・なし）がないか
- 住所（番地レベル）がないか
- SNSアカウント名（@ハンドル）がないか
- 個人宛て表現（「〇〇へ」「〇〇くん」等）がないか

問題が見つかった場合：処理を中断してユーザーに報告する

## Step 3: metaタグ確認・補完 // turbo

対象HTMLファイルに以下のmetaタグが存在するか確認する：
- `<meta name="description" content="...">`
- `<meta name="date" content="YYYY-MM-DD">`
- `<meta name="category" content="...">` — 値は「デジタルツール」「大学生活」「生活」のいずれか

不足している場合はHTMLのheadセクションに追加する

## Step 4: docs/index.html の更新 // turbo

docs/index.html を読み込み、対象ガイドのカードが既に存在するか確認する：

存在しない場合は以下の形式でカードを追加する（既存カードの上に配置）：
```html
<a href="guides/[ガイド名]/" class="guide-card d1" data-cat="[カテゴリ]">
  <div class="card-top cat-[digital|life|univ]"></div>
  <div class="card-body">
    <span class="card-category">[カテゴリ]</span>
    <h2 class="card-title">[タイトル]</h2>
    <p class="card-desc">[description metaの内容]</p>
  </div>
  <div class="card-footer">
    <span class="card-date">[date metaの内容]</span>
    <span class="card-arrow">→</span>
  </div>
</a>
```

`<strong id="visibleCount">` の数字もガイド総数に更新する

カテゴリと card-top クラスの対応：
- デジタルツール → cat-digital
- 生活 → cat-life
- 大学生活 → cat-univ

## Step 5: git commit & push

```bash
git add docs/
git status
```
// turbo

ステータスを確認してステージ済みファイルの一覧を表示する

```bash
git commit -m "add: [ガイド名]ガイド追加"
```
// turbo

```bash
git push origin main
```
// turbo

## 完了報告

以下を報告する：
- 公開したガイドのタイトルとURL（https://TheSageOfWitheredBoughs.github.io/lighthouse/guides/[ガイド名]/）
- CDNチェック・PIIスキャンの結果
- コミットメッセージ
