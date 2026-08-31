---
title: "学術研究・アルゴリズム検証用OSS特化型検索モジュール 詳細設計書"
document_type: "detailed_design"
version: "1.2"
created_at: "2026-08-31"
updated_at: "2026-08-31"
author: "ScholarRepo-Finder 開発チーム"
purpose: "GitHub Actions による自動クロール・静的データビルド処理手順、および GitHub Pages クライアントサイド検索・MarkdownエクスポートUIの制御仕様を定義するため"
related_documents:
  - "SRF-BD-001_基本設計書.md"
  - "SRF-DS-001_データ構造仕様書.md"
---

# 詳細設計書（機能・モジュール制御仕様）
**ScholarRepo-Finder GitHub Actions バッチ & Pages クライアント検索・エクスポート仕様**

| 項目           | 内容                                                           |
| :------------- | :------------------------------------------------------------- |
| 文書番号       | SRF-DD-001                                                     |
| ドキュメント名 | 学術研究・アルゴリズム検証用OSS特化型検索モジュール 詳細設計書 |
| 版数           | Rev.1.2 (Markdownエクスポート制御仕様追加)                     |
| 改訂日         | 2026-08-31                                                     |
| 作成日         | 2026-08-31                                                     |
| 作成者         | ScholarRepo-Finder 開発チーム                                  |

---

## 1. 概要とSSOT境界

### 1.1 モジュールの目的
本書は、以下の4大コンポーネントの具象ロジック、データパッシング、エラーハンドリング、およびシーケンス制御を規定する：
1. **`pipeline` (GitHub Actions クロール＆スコアリングバッチ)**
2. **`builder` (静的 JSON & サマリーMarkdown生成モジュール)**
3. **`client` (GitHub Pages クライアントサイド検索 Web UI)**
4. **`exporter` (ブラウザ内 Markdown 生成・ダウンロード制御)**

---

## 2. 処理シーケンス・パイプラインフロー (Mermaid 図)

### 2.1 クライアントサイド検索 & Markdown エクスポートフロー

```mermaid
sequenceDiagram
    autonumber
    participant Browser as ユーザーブラウザ
    participant Engine as MiniSearch インメモリ検索
    participant Exporter as Markdown Exporter (Blob)
    participant Clipboard as Clipboard API

    Browser->>Engine: キーワード入力 / ファセット変更
    Engine-->>Browser: 絞り込み結果リスト返却
    Browser->>Browser: 画面描画 (リポジトリカード一覧)

    alt 一括 Markdown ダウンロード要求
        Browser->>Exporter: Export to Markdown クリック (現在絞り込み中の全件)
        Exporter->>Exporter: テーブル形式 Markdown 文字列生成
        Exporter->>Browser: Blob オブジェクト生成 & <a download> トリガー
        Note over Browser: scholar_repos_export.md ダウンロード完了
    else 個別 Markdown 引用コピー要求
        Browser->>Clipboard: Copy as Markdown クリック
        Clipboard-->>Browser: クリップボードへコピー完了 (トースト通知表示)
    end
```

### 2.2 関数提供型候補の選定フロー（目標仕様・未実装）

1. **シード分類**: 収集クエリとトピックを、OR、シミュレーション、数値計算、MLなどのカテゴリへ分類し、カテゴリ別の候補数を記録する。
2. **提供形態の抽出**: 言語ごとに公開APIの根拠を抽出する。例としてC/C++は公開ヘッダ、Pythonはimport可能なパッケージ、Rustは`lib.rs`、JavaScript/TypeScriptは公開exportを確認する。
3. **モジュール境界の抽出**: 実行入口とドメインロジックが分離されているか、責務別のモジュールが存在するかを確認する。
4. **再利用性の評価**: 公開API、モジュール分割、利用例、設定可能な入出力をスコア根拠として保存する。ML・科学計算ライブラリ数は加点根拠に使用しない。
5. **観測値の出力**: 提供形態別・シードカテゴリ別に、収集数、ハードフィルター通過数、閾値通過数、最終掲載数、およびスコア内訳を出力する。

このフローは [SRF-FEAT-003](../features/FEAT_function_oriented_repository_selection.md) の実装時に導入する。現行のパイプライン動作は変更しない。

---

## 3. クライアント側 Markdown エクスポート制御仕様

### 3.1 一括ダウンロード機能 (`exportToMarkdown`)
- **処理手順**:
  1. 現在の検索条件（キーワード、言語、スコア範囲、論文有無）および該当リポジトリリスト（最大 1,000 件）を取得。
  2. [SRF-DS-001_データ構造仕様書.md](./SRF-DS-001_データ構造仕様書.md) のテンプレートに沿って Markdown 文字列を動的構築。
  3. `new Blob([markdownText], { type: 'text/markdown;charset=utf-8' })` を生成。
  4. `URL.createObjectURL(blob)` を用いて一時リンクを生成し、自動クリックでダウンロード（ファイル名: `scholar_repos_{YYYYMMDD_HHMMSS}.md`）。
  5. オブジェクト URL を解放 (`URL.revokeObjectURL`)。

### 3.2 個別引用コピー機能 (`copyItemMarkdown`)
- **処理手順**:
  1. 対象リポジトリのメタデータから 1 件分の引用 Markdown 文字列を構築。
  2. `navigator.clipboard.writeText(markdownText)` を実行。
  3. UI 上に「コピー完了」のトースト通知を表示。

---

## 4. GitHub Actions ワークフロー仕様

### 4.1 ワークフロー定義 (`.github/workflows/crawl-and-deploy.yml`)
- **トリガー**: `schedule` (毎週月曜 00:00 UTC) / `workflow_dispatch` (手動実行)
- **実行ステップ**:
  1. リポジトリのチェックアウト
  2. Python & `uv` 環境セットアップ
  3. クローラー＆スコアリング実行 (`uv run python -m src.pipeline`)
  4. 静的データ生成 (`uv run python -m src.builder`)
     - `public/data/repos.json` 出力
     - `docs/awesome_scholar_repos.md` 自動出力
  5. 静的サイトビルド & GitHub Pages デプロイ (`actions/deploy-pages`)

---

## 5. 改訂履歴 (Change Log)

| 版数    | 改訂日     | 変更者                        | 変更内容・変更理由 (Why)                            |
| :------ | :--------- | :---------------------------- | :-------------------------------------------------- |
| Rev.1.0 | 2026-08-31 | ScholarRepo-Finder 開発チーム | 新規作成（初版制定）                                |
| Rev.1.1 | 2026-08-31 | ScholarRepo-Finder 開発チーム | GitHub Actions & Pages クライアント検索仕様への移行 |
| Rev.1.2 | 2026-08-31 | ScholarRepo-Finder 開発チーム | クライアント側 Markdown エクスポート制御仕様の追加  |
