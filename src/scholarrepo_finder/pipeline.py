"""ScholarRepo-Finder パイプライン実行エントリーポイント。"""

from pathlib import Path

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
from scholarrepo_finder.pwc import PapersWithCodeClient
from scholarrepo_finder.scorer import evaluate_repository
from scholarrepo_finder.scoring_config import DEFAULT_SCORING_CONFIG_PATH, load_scoring_config


def run_pipeline(
    collector: GitHubCollector | None = None,
    pwc_client: PapersWithCodeClient | None = None,
    public_data_dir: Path | str = "public/data",
    docs_dir: Path | str = "docs",
    config_path: Path | str = DEFAULT_SCORING_CONFIG_PATH,
    limit_per_query: int = 30,
) -> int:
    """設定検証、収集、評価、静的データ出力を順番に実行する。

    Args:
        collector: GitHubデータ収集用コレクター。未指定時は本番実装を生成する。
        pwc_client: PWCアーカイブ照合クライアント。未指定時は本番実装を生成する。
        public_data_dir: 配信用JSONと観測レポートの出力先。
        docs_dir: 自動生成Markdownの出力先。
        config_path: 検証するスコアリング設定TOMLへのパス。
        limit_per_query: シードクエリごとの収集上限。

    Returns:
        配信対象として出力したリポジトリ数。
    """
    loaded_config = load_scoring_config(config_path)
    config = loaded_config.config
    col = collector or GitHubCollector()
    pwc = pwc_client or PapersWithCodeClient()

    print(f"⚙️  [Step 0/5] スコア設定 {config.profile.id} v{config.profile.version} を検証しました。")
    print("🚀 [Step 1/5] シードリポジトリの収集を開始...")
    raw_repos = collect_seed_repositories(col, limit_per_query=limit_per_query)
    print(f"   -> {len(raw_repos)} 件のリポジトリメタデータを取得しました。")

    print("🔬 [Step 2/5] 特徴抽出とスコアリングを実行中...")
    evaluated_records: list[tuple[RepoRaw, ScoreResult, ExtractedFeatures]] = []
    for raw in raw_repos:
        raw.pwc_match = pwc.lookup_repository(raw.html_url)
        features = extract_features(raw)
        evaluated_records.append((raw, evaluate_repository(raw, features, loaded_config), features))

    print("📊 [Step 3/5] 提供形態・シードカテゴリの観測レポートを作成中...")
    observation_report = build_phase1_observation_report(evaluated_records, loaded_config)

    print("📦 [Step 4/5] 配信データの軽量化とビルド...")
    static_items = build_static_repo_items(evaluated_records, config.indexing_threshold)
    print(f"   -> 厳選基準 (Score >= {config.indexing_threshold}) をクリアした {len(static_items)} 件をインデックス化。")

    print("💾 [Step 5/5] 静的JSON、Markdown、観測レポートを出力...")
    public_path = Path(public_data_dir) / "repos.json"
    docs_path = Path(docs_dir)
    save_static_json(static_items, public_path)
    generate_awesome_markdown(
        static_items,
        docs_path / "awesome_scholar_repos.md",
        config.indexing_threshold,
        config.profile.id,
    )
    save_phase1_observation_report(observation_report, Path(public_data_dir) / "function_provider_observations.json")
    print(f"   -> JSON: {public_path}")
    print(f"   -> MD:   {docs_path / 'awesome_scholar_repos.md'}")
    print(f"   -> Analysis: {Path(public_data_dir) / 'function_provider_observations.json'}")
    print("✨ パイプラインが正常終了しました！")
    return len(static_items)


if __name__ == "__main__":
    run_pipeline()
