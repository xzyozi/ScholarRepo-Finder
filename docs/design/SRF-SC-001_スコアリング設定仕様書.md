# SRF-SC-001 スコアリング設定仕様書

- **文書番号**: SRF-SC-001
- **作成日**: 2026-08-31
- **ステータス**: 設計・検討中 (Proposed)
- **対象**: `config/scoring.json`, `scorer.py`, `pipeline.py`, `builder.py`

## 1. 目的と単一設定源

評価に用いる配点、上限、ハードフィルター、掲載閾値、信頼度乗数は、リポジトリ管理する `config/scoring.json` を唯一の設定源とする。既定プロファイルは `reusability-v1` とし、再利用性を評価の中心に置く。検出器の実装詳細（言語別の公開API検出規則、科学系ライブラリ一覧、キーワード一覧）はコード管理とし、配点設定とは分離する。

設定読込時に未知キー、必須キー欠落、数値範囲外、評価軸の上限超過、またはJSON構文エラーを検出した場合、評価処理は開始しない。暗黙の既定値へのフォールバックは行わない。

## 2. 設定ファイル形式

```json
{
  "schema_version": 1,
  "profile": {"id": "reusability-v1", "version": 1},
  "hard_filters": {"max_inactive_years": 5, "min_readme_char_length": 100},
  "indexing_threshold": 60.0,
  "scores": {
    "reusability": {"maximum": 30, "delivery_form": {"library": 12, "modular_application": 8, "executable_application": 2, "unknown": 0}, "public_api_evidence": {"per_item": 4, "maximum": 8}, "module_partition_evidence": {"per_item": 2.5, "maximum": 5}, "usage_evidence": {"per_item": 1, "maximum": 3}, "configurable_io_evidence": {"per_item": 1, "maximum": 2}},
    "maintainability": {"maximum": 20, "directory_count": {"1": 4, "2": 7, "3": 10}, "ci_workflow": 10},
    "research_context": {"maximum": 50, "paper_link": 35, "academic_keyword": {"per_item": 1.5, "maximum": 15}},
    "trust_multiplier": {"academic_domain": 1.5, "verified_organization": 1.3, "account_age_years": 3, "experienced_account": 1.1, "default": 1.0}
  }
}
```

## 3. 評価規則

| 提供形態                 | 初期点 | 意図                                               |
| :----------------------- | -----: | :------------------------------------------------- |
| `library`                |     12 | 他プログラムから直接利用できる提供物を最優先する。 |
| `modular_application`    |      8 | 実行入口を持つが、再利用可能なモジュールを備える。 |
| `executable_application` |      2 | 除外せず、再利用性の不確実さを点差で表す。         |
| `unknown`                |      0 | 根拠不足のため加点しない。                         |

基礎スコアは `reusability + maintainability + research_context` とし、ハードフィルター通過時のみ信頼度乗数を適用する。各評価軸は設定された最大値で上限化し、総合スコアは小数第2位に丸める。科学計算・MLライブラリおよびPapers with Codeは検索・表示属性であり、直接加点しない。

## 4. 再現性と移行

観測レポートには、適用したプロファイルID、プロファイル版、設定ファイルのSHA-256、掲載閾値、評価軸別内訳を記録する。実装導入時は旧配点と `reusability-v1` の結果を同一入力で比較し、提供形態別・シードカテゴリ別の掲載件数と通過率を確認してから既定プロファイルを採用する。
