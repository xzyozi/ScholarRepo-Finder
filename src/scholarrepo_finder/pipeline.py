"""ScholarRepo-Finder パイプライン実行エントリーポイント."""

from pathlib import Path
from typing import List, Tuple

from scholarrepo_finder.builder import (
    build_phase1_observation_report,
    build_static_repo_items,
    generate_awesome_markdown,
    save_phase1_observation_report,
    save_static_json,
)
from scholarrepo_finder.collector import GitHubCollector, collect_seed_repositories
from scholarrepo_finder.extractor import extract_features
from scholarrepo_finder.models import ExtractedFeatures, RepoRaw, ScoreResult
from scholarrepo_finder.scorer import evaluate_repository


def run_pipeline(
    collector: GitHubCollector | None = None,
    public_data_dir: Path | str = "public/data",
    docs_dir: Path | str = "docs",
    limit_per_query: int = 30,
) -> int:
    """データ収集、既存選定、Phase 1観測、静的データ出力を順番に実行する."""
    col = collector or GitHubCollector()

    print("🚀 [Step 1/5] シードリポジトリの収集を開始...")
    raw_repos = collect_seed_repositories(col, limit_per_query=limit_per_query)
    print(f"   -> {len(raw_repos)} 件のリポジトリメタデータを取得しました。")

    print("🔬 [Step 2/5] 特徴抽出とスコアリングを実行中...")
    evaluated_records: List[Tuple[RepoRaw, ScoreResult, ExtractedFeatures]] = []
    for raw in raw_repos:
        features = extract_features(raw)
        score = evaluate_repository(raw, features)
        evaluated_records.append((raw, score, features))

    print("📊 [Step 3/5] 提供形態・シードカテゴリの観測レポートを作成中...")
    observation_report = build_phase1_observation_report(evaluated_records)

    print("📦 [Step 4/5] 配信データの軽量化とビルド...")
    static_items = build_static_repo_items(evaluated_records)
    print(f"   -> 厳選基準 (Score >= 60.0) をクリアした {len(static_items)} 件をインデックス化。")

    print("💾 [Step 5/5] 静的JSON、Markdown、観測レポートを出力...")
    public_path = Path(public_data_dir) / "repos.json"
    docs_path = Path(docs_dir)
    md_path = docs_path / "awesome_scholar_repos.md"
    observation_path = Path(public_data_dir) / "function_provider_observations.json"

    save_static_json(static_items, public_path)
    generate_awesome_markdown(static_items, md_path)
    save_phase1_observation_report(observation_report, observation_path)
    print(f"   -> JSON: {public_path}")
    print(f"   -> MD:   {md_path}")
    print(f"   -> Analysis: {observation_path}")
    print("✨ パイプラインが正常終了しました！")
    return len(static_items)


if __name__ == "__main__":
    run_pipeline()
