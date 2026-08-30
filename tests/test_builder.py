"""静的データビルダーおよびパイプラインの単体テスト."""

from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock
from scholarrepo_finder.builder import (
    build_static_repo_items,
    generate_awesome_markdown,
    save_static_json,
)
from scholarrepo_finder.models import ExtractedFeatures, RepoRaw, ScoreResult
from scholarrepo_finder.pipeline import run_pipeline


def test_build_static_repo_items() -> None:
    """build_static_repo_items のフィルタリングとソート検証."""
    now = datetime.now(timezone.utc)

    # 1. 合格高スコア
    raw1 = RepoRaw(
        repo_id="lab/repo1",
        name="repo1",
        owner="lab",
        description="Repo 1 description",
        html_url="https://github.com/lab/repo1",
        created_at=now,
        last_commit_at=now,
        primary_language="Python",
    )
    score1 = ScoreResult(
        repo_id="lab/repo1",
        hard_filter_passed=True,
        total_score=85.0,
    )
    f1 = ExtractedFeatures(repo_id="lab/repo1", has_doi_link=True)

    # 2. 合格最高スコア
    raw2 = RepoRaw(
        repo_id="lab/repo2",
        name="repo2",
        owner="lab",
        description="Repo 2 description",
        html_url="https://github.com/lab/repo2",
        created_at=now,
        last_commit_at=now,
        primary_language="Rust",
    )
    score2 = ScoreResult(
        repo_id="lab/repo2",
        hard_filter_passed=True,
        total_score=95.0,
    )
    f2 = ExtractedFeatures(repo_id="lab/repo2", is_edu_or_ac_domain=True)

    # 3. 閾値未満 (スコア 40.0)
    raw3 = RepoRaw(
        repo_id="lab/repo3",
        name="repo3",
        owner="lab",
        html_url="https://github.com/lab/repo3",
        created_at=now,
        last_commit_at=now,
    )
    score3 = ScoreResult(
        repo_id="lab/repo3",
        hard_filter_passed=True,
        total_score=40.0,
    )
    f3 = ExtractedFeatures(repo_id="lab/repo3")

    records = [(raw1, score1, f1), (raw2, score2, f2), (raw3, score3, f3)]
    items = build_static_repo_items(records)

    # raw3 は除外され、raw2 (95.0) -> raw1 (85.0) の順に並ぶ
    assert len(items) == 2
    assert items[0].id == "lab/repo2"
    assert items[0].score == 95.0
    assert items[1].id == "lab/repo1"
    assert items[1].score == 85.0
    assert items[1].paper is True


def test_save_static_json(tmp_path: Path) -> None:
    """save_static_json の出力ファイル検証."""
    now = datetime.now(timezone.utc)
    raw = RepoRaw(
        repo_id="lab/r",
        name="r",
        owner="lab",
        html_url="https://github.com/lab/r",
        created_at=now,
        last_commit_at=now,
    )
    score = ScoreResult(repo_id="lab/r", hard_filter_passed=True, total_score=75.0)
    features = ExtractedFeatures(repo_id="lab/r")

    items = build_static_repo_items([(raw, score, features)])
    out_file = tmp_path / "data" / "repos.json"
    save_static_json(items, out_file)

    assert out_file.exists()
    content = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(content) == 1
    assert content[0]["id"] == "lab/r"
    assert content[0]["score"] == 75.0


def test_generate_awesome_markdown(tmp_path: Path) -> None:
    """generate_awesome_markdown のマークダウンテーブル出力検証."""
    now = datetime.now(timezone.utc)
    raw = RepoRaw(
        repo_id="lab/r",
        name="r",
        owner="lab",
        html_url="https://github.com/lab/r",
        created_at=now,
        last_commit_at=now,
        primary_language="Python",
    )
    score = ScoreResult(repo_id="lab/r", hard_filter_passed=True, total_score=88.0)
    features = ExtractedFeatures(repo_id="lab/r", has_arxiv_link=True)

    items = build_static_repo_items([(raw, score, features)])
    md_file = tmp_path / "awesome_scholar_repos.md"
    generate_awesome_markdown(items, md_file)

    assert md_file.exists()
    md_text = md_file.read_text(encoding="utf-8")
    assert "Awesome Scholar Repositories" in md_text
    assert "[lab/r](https://github.com/lab/r)" in md_text
    assert "**88.0**" in md_text
    assert "✅ あり" in md_text


def test_run_pipeline(tmp_path: Path) -> None:
    """run_pipeline の総合結合フロー検証 (モック使用)."""
    now = datetime.now(timezone.utc)
    raw = RepoRaw(
        repo_id="mock/scholar-sim",
        name="scholar-sim",
        owner="mock",
        description="A benchmark simulation framework.",
        html_url="https://github.com/mock/scholar-sim",
        license_spdx="MIT",
        created_at=now,
        last_commit_at=now,
        primary_language="Python",
        readme_raw="A detailed benchmark simulation README text containing experimental results. Paper: https://doi.org/10.1016/j.sim.2024.01",
        file_tree=["src/sim.py", "tests/test_sim.py", "docs/index.md", ".github/workflows/ci.yml"],
        dependency_files={"requirements.txt": "numpy>=1.20\nsimpy>=4.0"},
    )

    mock_collector = MagicMock()
    mock_collector.search_repositories.return_value = [{"full_name": "mock/scholar-sim"}]
    mock_collector.fetch_repository_details.return_value = raw

    public_dir = tmp_path / "public" / "data"
    docs_dir = tmp_path / "docs"

    count = run_pipeline(
        collector=mock_collector,
        public_data_dir=public_dir,
        docs_dir=docs_dir,
        limit_per_query=1,
    )

    assert count >= 1
    assert (public_dir / "repos.json").exists()
    assert (docs_dir / "awesome_scholar_repos.md").exists()
