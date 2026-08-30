"""ScholarRepo-Finder 特徴抽出モジュール (Feature Extraction)."""

import re
from typing import List, Set

from scholarrepo_finder.models import ExtractedFeatures, RepoRaw

# 検出対象の科学計算・OR・シミュレーション系代表ライブラリ一覧
TARGET_SCIENTIFIC_LIBS: Set[str] = {
    "numpy",
    "scipy",
    "simpy",
    "networkx",
    "ortools",
    "pulp",
    "cvxpy",
    "pyomo",
    "pettingzoo",
    "gymnasium",
    "gym",
    "torch",
    "pytorch",
    "jax",
    "tensorflow",
    "pandas",
    "polars",
    "scikit-learn",
    "sklearn",
    "ndarray",
    "mesa",
    "deap",
}

# 学術識別子 (DOI / arXiv) 正規表現パターン
DOI_PATTERN = re.compile(r"doi\.org/10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE)
ARXIV_PATTERN = re.compile(r"arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}", re.IGNORECASE)

# 学術文脈キーワード
ACADEMIC_KEYWORDS = [
    "benchmark",
    "baseline",
    "reproduce",
    "reproducibility",
    "experimental results",
    "dataset",
    "simulation",
    "formulation",
    "operations research",
    "vehicle routing",
    "algorithm evaluation",
]

# アカデミックドメイン接尾辞パターン
EDU_DOMAIN_PATTERN = re.compile(r"\.(?:edu|ac\.[a-z]{2,3}|gov)(?:\.[a-z]{2})?$", re.IGNORECASE)


def detect_scientific_libraries(dependency_files: dict[str, str], topics: List[str]) -> List[str]:
    """依存定義ファイルや Topics から科学計算・OR系ライブラリを抽出する."""
    detected: Set[str] = set()

    # 1. Topics からの検出
    for topic in topics:
        clean_topic = topic.lower().strip()
        if clean_topic in TARGET_SCIENTIFIC_LIBS:
            detected.add(clean_topic)

    # 2. 依存ファイルテキストからの検出
    for file_content in dependency_files.values():
        content_lower = file_content.lower()
        for lib in TARGET_SCIENTIFIC_LIBS:
            # 単語境界または依存構文としてマッチ (例: "numpy>=", "import numpy", "numpy==")
            pattern = rf"(?<![a-zA-Z0-9_-]){re.escape(lib)}(?![a-zA-Z0-9_])"
            if re.search(pattern, content_lower):
                detected.add(lib)

    return sorted(list(detected))


def calculate_academic_keyword_score(text: str) -> float:
    """README 等のテキスト内の学術キーワード出現頻度からスコア (0.0〜10.0) を算出する."""
    if not text:
        return 0.0

    text_lower = text.lower()
    matched_count = 0

    for kw in ACADEMIC_KEYWORDS:
        if kw in text_lower:
            # 出現回数を最大3回までカウントして合算
            count = min(text_lower.count(kw), 3)
            matched_count += count

    # スコア正規化 (10キーワード × 重み -> 最大 10.0点)
    score = min(matched_count * 1.5, 10.0)
    return round(score, 2)


def is_academic_email_domain(email_or_domain: str | None) -> bool:
    """メールアドレスまたはドメインが教育・研究機関 (.edu / .ac.* / .gov) か判定する."""
    if not email_or_domain:
        return False

    domain = email_or_domain.split("@")[-1].strip().lower()
    return bool(EDU_DOMAIN_PATTERN.search(domain))


def extract_features(
    raw: RepoRaw,
    is_pwc: bool = False,
    is_verified_org: bool = False,
    author_email: str | None = None,
    author_account_age_years: int = 0,
) -> ExtractedFeatures:
    """RepoRaw メタデータから ExtractedFeatures 特徴量ベクトルを構築する."""
    tree = [p.lower() for p in raw.file_tree]
    readme = raw.readme_raw or ""

    # 1. 構造判定
    has_src = any(p.startswith("src/") or p.startswith("app/") or p in ["src", "app"] for p in tree)
    has_tests = any(
        p.startswith("tests/") or p.startswith("test/") or p in ["tests", "test"] for p in tree
    )
    has_docs = any(
        p.startswith("docs/") or p.startswith("doc/") or p in ["docs", "doc"] for p in tree
    )
    has_ci = any(
        p.startswith(".github/workflows")
        or p in [".travis.yml", ".circleci/config.yml", "azure-pipelines.yml"]
        for p in tree
    )

    # 2. 依存ライブラリ検出
    scientific_libs = detect_scientific_libraries(raw.dependency_files, raw.topics)

    # 3. 論文リンク (DOI / arXiv) 検出
    has_doi = bool(DOI_PATTERN.search(readme))
    has_arxiv = bool(ARXIV_PATTERN.search(readme))

    # 4. 学術キーワードスコア
    keyword_score = calculate_academic_keyword_score(readme + " " + (raw.description or ""))

    # 5. 著者情報
    email_domain = author_email.split("@")[-1].strip().lower() if author_email else None
    is_edu = is_academic_email_domain(author_email)

    return ExtractedFeatures(
        repo_id=raw.repo_id,
        has_src_or_app_dir=has_src,
        has_tests_dir=has_tests,
        has_docs_dir=has_docs,
        has_ci_workflow=has_ci,
        scientific_libs_detected=scientific_libs,
        has_doi_link=has_doi,
        has_arxiv_link=has_arxiv,
        is_pwc_official=is_pwc,
        academic_keyword_score=keyword_score,
        author_email_domain=email_domain,
        is_edu_or_ac_domain=is_edu,
        is_verified_org=is_verified_org,
        author_account_age_years=author_account_age_years,
    )
