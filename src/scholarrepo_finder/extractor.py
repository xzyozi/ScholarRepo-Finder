"""ScholarRepo-Finder 特徴抽出モジュール (Feature Extraction)."""

import re
from typing import List, Set

from scholarrepo_finder.models import ExtractedFeatures, RepoRaw

# 検出対象の科学計算・OR・シミュレーション系代表ライブラリ一覧
TARGET_SCIENTIFIC_LIBS: Set[str] = {
    # 科学計算・数値解析
    "numpy",
    "scipy",
    "pandas",
    "polars",
    "ndarray",
    "symengine",
    "sympy",
    "eigen",
    "mumps",
    # 最適化 & OR
    "ortools",
    "pulp",
    "cvxpy",
    "pyomo",
    "scip",
    "gurobi",
    "cplex",
    "casadi",
    "optuna",
    "deap",
    # グラフ・ネットワーク
    "networkx",
    "igraph",
    "graph-tool",
    # シミュレーション & モデリング
    "simpy",
    "mesa",
    "fenics",
    "openfoam",
    # 強化学習 & 機械学習
    "torch",
    "pytorch",
    "jax",
    "tensorflow",
    "scikit-learn",
    "sklearn",
    "gym",
    "gymnasium",
    "pettingzoo",
    "stable-baselines3",
    "sb3",
    "ray",
    # 量子 & バイオインフォマティクス
    "qiskit",
    "cirq",
    "pennylane",
    "biopython",
    "rdkit",
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


def _matching_c_cpp_stems(tree: List[str]) -> Set[str]:
    """公開ヘッダと実装ファイルの両方を持つ C/C++ モジュール名を返す."""
    header_stems = {path.rsplit(".", 1)[0] for path in tree if path.endswith((".h", ".hpp"))}
    source_stems = {path.rsplit(".", 1)[0] for path in tree if path.endswith((".c", ".cc", ".cpp", ".cxx"))}
    return header_stems & source_stems


def extract_public_api_evidence(raw: RepoRaw) -> List[str]:
    """ファイルツリーとパッケージ定義から公開APIの根拠を抽出する."""
    tree = [path.lower() for path in raw.file_tree]
    evidence: List[str] = []
    package_content = "\n".join(
        content.lower() for path, content in raw.dependency_files.items() if path.lower().endswith("package.json")
    )

    if any(path.startswith("src/") and path.endswith("/__init__.py") for path in tree):
        evidence.append("python_src_package")
    if any(not path.startswith(("tests/", "test/")) and path.endswith("/__init__.py") for path in tree):
        evidence.append("python_package_initializer")
    if "src/lib.rs" in tree:
        evidence.append("rust_library_crate")
    if package_content and any(key in package_content for key in ('"exports"', '"main"', '"module"')):
        evidence.append("javascript_package_export")

    c_cpp_stems = sorted(_matching_c_cpp_stems(tree))
    if c_cpp_stems:
        evidence.append(f"c_cpp_header_implementation_pairs:{len(c_cpp_stems)}")

    return evidence


def extract_module_partition_evidence(raw: RepoRaw) -> List[str]:
    """責務別モジュールへの分割を示すファイル構造上の根拠を抽出する."""
    tree = [path.lower() for path in raw.file_tree]
    evidence: List[str] = []
    c_cpp_stems = _matching_c_cpp_stems(tree)
    source_suffixes = (".c", ".cc", ".cpp", ".cxx", ".py", ".rs", ".js", ".ts")
    source_modules = {
        path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        for path in tree
        if path.endswith(source_suffixes)
        and not path.startswith(("tests/", "test/"))
        and path.rsplit("/", 1)[-1] not in {"main.c", "main.cpp", "main.py", "main.rs", "index.js", "index.ts"}
    }

    if len(c_cpp_stems) >= 2:
        evidence.append(f"c_cpp_responsibility_modules:{len(c_cpp_stems)}")
    if len(source_modules) >= 3:
        evidence.append(f"multiple_source_modules:{len(source_modules)}")

    return evidence


def extract_usage_evidence(raw: RepoRaw) -> List[str]:
    """README から導入・利用方法の説明を示す根拠を抽出する."""
    readme = (raw.readme_raw or "").lower()
    evidence: List[str] = []

    for label, markers in {
        "installation": ("installation", "install", "セットアップ", "導入"),
        "usage": ("usage", "how to use", "使い方", "利用方法"),
        "examples": ("example", "examples", "usage example", "使用例"),
        "quick_start": ("quick start", "getting started", "クイックスタート"),
    }.items():
        if any(marker in readme for marker in markers):
            evidence.append(label)

    return evidence


def extract_configurable_io_evidence(raw: RepoRaw) -> List[str]:
    """設定ファイルまたはREADMEから設定可能な入出力の根拠を抽出する."""
    tree = [path.lower() for path in raw.file_tree]
    readme = (raw.readme_raw or "").lower()
    evidence: List[str] = []

    if any("config" in path or "settings" in path or "options" in path for path in tree):
        evidence.append("configuration_file")
    if any(marker in readme for marker in ("configuration", "configure", "command line", "arguments", "設定", "引数")):
        evidence.append("configurable_interface_documented")

    return evidence


def classify_delivery_form(
    raw: RepoRaw,
    public_api_evidence: List[str],
    module_partition_evidence: List[str],
) -> str:
    """再利用性の根拠と実行入口からリポジトリの提供形態を推定する."""
    tree = [path.lower() for path in raw.file_tree]
    executable_names = {"main.c", "main.cc", "main.cpp", "main.cxx", "main.py", "main.rs", "cli.py"}
    has_executable_entrypoint = any(
        path.rsplit("/", 1)[-1] in executable_names or path.endswith("/__main__.py") for path in tree
    )
    has_language_library = any(
        evidence in {"python_src_package", "python_package_initializer", "rust_library_crate", "javascript_package_export"}
        for evidence in public_api_evidence
    )
    has_c_cpp_library = any(evidence.startswith("c_cpp_header_implementation_pairs") for evidence in public_api_evidence)

    if has_language_library or (has_c_cpp_library and not has_executable_entrypoint):
        return "library"
    if module_partition_evidence:
        return "modular_application"
    if has_executable_entrypoint:
        return "executable_application"
    return "unknown"


def extract_features(
    raw: RepoRaw,
    is_pwc: bool = False,
    is_verified_org: bool = False,
    author_email: str | None = None,
    author_account_age_years: int = 0,
) -> ExtractedFeatures:
    """RepoRaw メタデータから ExtractedFeatures 特徴量ベクトルを構築する."""
    tree = [path.lower() for path in raw.file_tree]
    readme = raw.readme_raw or ""

    has_src = any(path.startswith("src/") or path.startswith("app/") or path in ["src", "app"] for path in tree)
    has_tests = any(path.startswith("tests/") or path.startswith("test/") or path in ["tests", "test"] for path in tree)
    has_docs = any(path.startswith("docs/") or path.startswith("doc/") or path in ["docs", "doc"] for path in tree)
    has_ci = any(
        path.startswith(".github/workflows") or path in [".travis.yml", ".circleci/config.yml", "azure-pipelines.yml"]
        for path in tree
    )
    scientific_libs = detect_scientific_libraries(raw.dependency_files, raw.topics)
    public_api_evidence = extract_public_api_evidence(raw)
    module_partition_evidence = extract_module_partition_evidence(raw)
    usage_evidence = extract_usage_evidence(raw)
    configurable_io_evidence = extract_configurable_io_evidence(raw)
    delivery_form = classify_delivery_form(raw, public_api_evidence, module_partition_evidence)
    has_doi = bool(DOI_PATTERN.search(readme))
    has_arxiv = bool(ARXIV_PATTERN.search(readme))
    keyword_score = calculate_academic_keyword_score(readme + " " + (raw.description or ""))
    email_domain = author_email.split("@")[-1].strip().lower() if author_email else None
    is_edu = is_academic_email_domain(author_email)

    return ExtractedFeatures(
        repo_id=raw.repo_id,
        has_src_or_app_dir=has_src,
        has_tests_dir=has_tests,
        has_docs_dir=has_docs,
        has_ci_workflow=has_ci,
        scientific_libs_detected=scientific_libs,
        delivery_form=delivery_form,
        public_api_evidence=public_api_evidence,
        module_partition_evidence=module_partition_evidence,
        usage_evidence=usage_evidence,
        configurable_io_evidence=configurable_io_evidence,
        has_doi_link=has_doi,
        has_arxiv_link=has_arxiv,
        is_pwc_official=is_pwc,
        academic_keyword_score=keyword_score,
        author_email_domain=email_domain,
        is_edu_or_ac_domain=is_edu,
        is_verified_org=is_verified_org,
        author_account_age_years=author_account_age_years,
    )
