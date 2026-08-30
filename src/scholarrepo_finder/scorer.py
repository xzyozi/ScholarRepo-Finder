"""ScholarRepo-Finder スコアリング＆フィルタリングモジュール (Scoring & Filtering)."""

from datetime import datetime, timezone
from typing import Tuple

from scholarrepo_finder.models import ExtractedFeatures, RepoRaw, ScoreResult

# ハードフィルター基準定数
MAX_INACTIVE_YEARS = 5
MIN_README_CHAR_LENGTH = 100
INDEXING_THRESHOLD_SCORE = 60.0


def check_hard_filters(raw: RepoRaw, now: datetime | None = None) -> Tuple[bool, str | None]:
    """リポジトリがハードフィルター基準を満たしているか判定する.

    Returns:
        (合格フラグ, 不合格時の理由)
    """
    # 1. ライセンスチェック
    if not raw.license_spdx or raw.license_spdx.strip() == "":
        return False, "OSSライセンスが明記されていないか不正です。"

    # 2. 陳腐化チェック (最終コミットから5年以上経過)
    current_time = now or datetime.now(timezone.utc)
    commit_time = raw.last_commit_at
    if commit_time.tzinfo is None:
        commit_time = commit_time.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    days_since_last_commit = (current_time - commit_time).days
    if days_since_last_commit > MAX_INACTIVE_YEARS * 365:
        return False, f"最終コミットから5年以上が経過しています ({days_since_last_commit // 365}年前)。"

    # 3. README 文字数チェック (100文字以下)
    readme_len = len((raw.readme_raw or "").strip())
    if readme_len < MIN_README_CHAR_LENGTH:
        return False, f"READMEの文字数が極小（{readme_len}文字）のため情報が不足しています。"

    return True, None


def calculate_structural_score(features: ExtractedFeatures) -> float:
    """Repo Structural Score (構造スコア: 最大 50点) を算出する."""
    score = 0.0

    # 1. ディレクトリ分離度 (最大 15点)
    dir_count = sum(
        [features.has_src_or_app_dir, features.has_tests_dir, features.has_docs_dir]
    )
    if dir_count == 3:
        score += 15.0
    elif dir_count == 2:
        score += 10.0
    elif dir_count == 1:
        score += 5.0

    # 2. 科学計算・OR系ライブラリの依存関係 (最大 20点)
    if len(features.scientific_libs_detected) >= 2:
        score += 20.0
    elif len(features.scientific_libs_detected) == 1:
        score += 15.0

    # 3. 自動テスト / CI ワークフロー (最大 15点)
    if features.has_ci_workflow:
        score += 15.0

    return min(score, 50.0)


def calculate_context_score(features: ExtractedFeatures) -> float:
    """Repo Context Score (学術文脈スコア: 最大 50点) を算出する."""
    score = 0.0

    # 1. 論文識別子 (DOI / arXiv リンク) (最大 30点)
    if features.has_doi_link or features.has_arxiv_link:
        score += 30.0

    # 2. Papers with Code 公式連携 (最大 20点)
    if features.is_pwc_official:
        score += 20.0

    # 3. 学術キーワード頻度スコア (最大 10点)
    score += min(features.academic_keyword_score, 10.0)

    return min(score, 50.0)


def calculate_user_trust_multiplier(features: ExtractedFeatures) -> float:
    """User Trust Multiplier (著者信頼度乗数: 0.5x〜1.5x) を算出する."""
    # 教育・研究機関ドメイン保有者
    if features.is_edu_or_ac_domain:
        return 1.5

    # 認証済み組織 (Verified Organization)
    if features.is_verified_org:
        return 1.3

    # 一般熟練開発者 (3年以上のアカウント)
    if features.author_account_age_years >= 3:
        return 1.1

    # 標準
    return 1.0


def evaluate_repository(
    raw: RepoRaw,
    features: ExtractedFeatures,
    now: datetime | None = None,
) -> ScoreResult:
    """リポジトリの総合スコアリングとハードフィルター判定を実行する."""
    passed, reject_reason = check_hard_filters(raw, now)

    structural_score = calculate_structural_score(features)
    context_score = calculate_context_score(features)
    base_repo_score = structural_score + context_score
    user_multiplier = calculate_user_trust_multiplier(features)

    # ハードフィルター通過時のみ乗数を乗算して総合スコアを計算
    if passed:
        total_score = round(base_repo_score * user_multiplier, 2)
    else:
        total_score = 0.0

    return ScoreResult(
        repo_id=raw.repo_id,
        hard_filter_passed=passed,
        reject_reason=reject_reason,
        structural_score=structural_score,
        context_score=context_score,
        base_repo_score=base_repo_score,
        user_trust_multiplier=user_multiplier,
        total_score=total_score,
        evaluated_at=now or datetime.now(),
    )
