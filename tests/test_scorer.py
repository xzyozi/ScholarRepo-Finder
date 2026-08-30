"""スコアリング＆フィルターモジュールの単体テスト."""

from datetime import datetime, timedelta, timezone
from scholarrepo_finder.models import ExtractedFeatures, RepoRaw
from scholarrepo_finder.scorer import (
    calculate_context_score,
    calculate_structural_score,
    calculate_user_trust_multiplier,
    check_hard_filters,
    evaluate_repository,
)


def create_sample_raw(
    license_spdx: str | None = "MIT",
    days_ago: int = 30,
    readme: str = "This is a sufficiently long README text containing detailed descriptions, benchmarks, algorithm formulations, and usage guides for simulation experiments.",
) -> RepoRaw:
    """テスト用サンプル RepoRaw を生成する."""
    now = datetime.now(timezone.utc)
    commit_time = now - timedelta(days=days_ago)
    return RepoRaw(
        repo_id="test/repo",
        name="repo",
        owner="test",
        description="A test repo",
        html_url="https://github.com/test/repo",
        stars=10,
        forks=2,
        created_at=now - timedelta(days=365),
        last_commit_at=commit_time,
        license_spdx=license_spdx,
        primary_language="Python",
        readme_raw=readme,
    )


def test_check_hard_filters_pass() -> None:
    """正常リポジトリのハードフィルター通過検証."""
    raw = create_sample_raw()
    passed, reason = check_hard_filters(raw)
    assert passed is True
    assert reason is None


def test_check_hard_filters_no_license() -> None:
    """ライセンス欠如によるハードフィルター除外検証."""
    raw = create_sample_raw(license_spdx=None)
    passed, reason = check_hard_filters(raw)
    assert passed is False
    assert "ライセンス" in (reason or "")


def test_check_hard_filters_inactive() -> None:
    """5年以上更新がないことによる陳腐化除外検証."""
    raw = create_sample_raw(days_ago=365 * 6)
    passed, reason = check_hard_filters(raw)
    assert passed is False
    assert "5年以上" in (reason or "")


def test_check_hard_filters_small_readme() -> None:
    """README極小による情報不足除外検証."""
    raw = create_sample_raw(readme="Short")
    passed, reason = check_hard_filters(raw)
    assert passed is False
    assert "README" in (reason or "")


def test_calculate_structural_score() -> None:
    """構造スコアの算出検証."""
    features = ExtractedFeatures(
        repo_id="test/repo",
        has_src_or_app_dir=True,
        has_tests_dir=True,
        has_docs_dir=True,
        scientific_libs_detected=["numpy", "scipy"],
        has_ci_workflow=True,
    )
    score = calculate_structural_score(features)
    # 15 (dir) + 20 (libs) + 15 (ci) = 50.0
    assert score == 50.0


def test_calculate_context_score() -> None:
    """学術文脈スコアの算出検証."""
    features = ExtractedFeatures(
        repo_id="test/repo",
        has_doi_link=True,
        is_pwc_official=True,
        academic_keyword_score=8.5,
    )
    score = calculate_context_score(features)
    # 30 (doi) + 20 (pwc) + 8.5 (keywords) = 58.5 -> min(50.0) = 50.0
    assert score == 50.0


def test_calculate_user_trust_multiplier() -> None:
    """著者信頼度乗数の算出検証."""
    # 1. 教育機関
    f_edu = ExtractedFeatures(repo_id="t/r", is_edu_or_ac_domain=True)
    assert calculate_user_trust_multiplier(f_edu) == 1.5

    # 2. Verified Org
    f_org = ExtractedFeatures(repo_id="t/r", is_verified_org=True)
    assert calculate_user_trust_multiplier(f_org) == 1.3

    # 3. 熟練開発者
    f_senior = ExtractedFeatures(repo_id="t/r", author_account_age_years=4)
    assert calculate_user_trust_multiplier(f_senior) == 1.1

    # 4. 標準
    f_default = ExtractedFeatures(repo_id="t/r")
    assert calculate_user_trust_multiplier(f_default) == 1.0


def test_evaluate_repository_comprehensive() -> None:
    """evaluate_repository による総合評価・スコア算出検証."""
    raw = create_sample_raw()
    features = ExtractedFeatures(
        repo_id="test/repo",
        has_src_or_app_dir=True,
        has_tests_dir=True,
        has_ci_workflow=True,
        scientific_libs_detected=["numpy"],
        has_arxiv_link=True,
        academic_keyword_score=5.0,
        is_edu_or_ac_domain=True,
    )
    # 構造: 10(dir) + 15(lib) + 15(ci) = 40
    # 文脈: 30(arxiv) + 5(kw) = 35
    # Base: 75.0
    # Multiplier: 1.5
    # Total: 75.0 * 1.5 = 112.5
    result = evaluate_repository(raw, features)
    assert result.hard_filter_passed is True
    assert result.structural_score == 40.0
    assert result.context_score == 35.0
    assert result.base_repo_score == 75.0
    assert result.user_trust_multiplier == 1.5
    assert result.total_score == 112.5
