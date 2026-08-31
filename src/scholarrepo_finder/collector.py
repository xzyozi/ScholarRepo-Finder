"""ScholarRepo-Finder データ収集モジュール (Data Ingestion)."""

import base64
from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional

import httpx

from scholarrepo_finder.models import RepoRaw

DEFAULT_SEED_TOPICS = [
    # 数理最適化・OR
    "operations-research",
    "vehicle-routing",
    "combinatorial-optimization",
    "linear-programming",
    "integer-programming",
    "mixed-integer-linear-programming",
    "mathematical-optimization",
    "constraint-programming",
    # シミュレーション & モデリング
    "discrete-event-simulation",
    "agent-based-modeling",
    "multi-agent-systems",
    "traffic-simulation",
    "supply-chain-optimization",
    "cellular-automata",
    "complex-systems",
    "monte-carlo-simulation",
    "stochastic-simulation",
    # アルゴリズム検証 & 機械学習/科学計算
    "reinforcement-learning",
    "deep-reinforcement-learning",
    "graph-neural-networks",
    "scientific-computing",
    "computational-physics",
    "numerical-simulation",
    "evolutionary-algorithms",
    "genetic-algorithm",
    "bayesian-optimization",
    "surrogate-modeling",
    "finite-element-analysis",
    "computational-fluid-dynamics",
]

DEFAULT_SEED_QUERIES = [
    '"arxiv.org/abs" "simulation"',
    '"doi.org" "benchmark"',
    '"baseline algorithm" "reproduce"',
    '"operations research" "algorithm" "benchmark"',
    '"agent-based" "simulation" "benchmark"',
    '"combinatorial optimization" "dataset"',
    '"reinforcement learning" "environment" "simulation"',
    '"discrete-event" "simulation" "python"',
]

DEPENDENCY_FILE_CANDIDATES = [
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "Pipfile",
    "Cargo.toml",
    "package.json",
    "CMakeLists.txt",
]

SEED_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "operations_research": [
        "operations research",
        "operations-research",
        "vehicle-routing",
        "combinatorial-optimization",
        "linear-programming",
        "integer-programming",
        "mathematical-optimization",
        "constraint-programming",
    ],
    "simulation": [
        "simulation",
        "agent-based",
        "multi-agent",
        "traffic",
        "cellular-automata",
        "monte-carlo",
        "stochastic",
        "discrete-event",
    ],
    "numerical_computing": [
        "scientific-computing",
        "computational-physics",
        "numerical",
        "finite-element",
        "computational-fluid",
    ],
    "machine_learning": [
        "reinforcement-learning",
        "reinforcement learning",
        "graph-neural",
        "evolutionary-algorithms",
        "genetic-algorithm",
        "bayesian-optimization",
        "surrogate-modeling",
    ],
}


def classify_seed_categories(seed: str) -> List[str]:
    """シードトピックまたは検索クエリから分野カテゴリを判定する."""
    normalized_seed = seed.lower()
    categories = [
        category
        for category, keywords in SEED_CATEGORY_KEYWORDS.items()
        if any(keyword in normalized_seed for keyword in keywords)
    ]
    return categories or ["unclassified"]


class GitHubCollector:
    """GitHub API から学術・シミュレーションリポジトリを収集するクライアント."""

    def __init__(self, token: Optional[str] = None, timeout: float = 15.0) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.timeout = timeout
        self.headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "ScholarRepo-Finder/0.1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def search_repositories(
        self, query: str, sort: str = "stars", order: str = "desc", per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GitHub Search API を用いてリポジトリ候補を検索する."""
        url = "https://api.github.com/search/repositories"
        params: dict[str, str | int] = {"q": query, "sort": sort, "order": order, "per_page": per_page}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("items", [])
            elif resp.status_code == 403:
                # Rate limit
                return []
            return []

    def fetch_readme(self, repo_id: str) -> Optional[str]:
        """リポジトリの README テキストを取得する."""
        url = f"https://api.github.com/repos/{repo_id}/readme"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", "")
                encoding = data.get("encoding", "")
                if encoding == "base64":
                    try:
                        return base64.b64decode(content).decode("utf-8", errors="replace")
                    except Exception:
                        return None
                return content
            return None

    def fetch_file_tree(self, repo_id: str, default_branch: str = "main") -> List[str]:
        """リポジトリのファイルツリーを取得する (Git Trees API)."""
        url = f"https://api.github.com/repos/{repo_id}/git/trees/{default_branch}?recursive=1"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self.headers)
            if resp.status_code == 200:
                tree_data = resp.json().get("tree", [])
                return [item.get("path", "") for item in tree_data if "path" in item]
            return []

    def fetch_dependency_files(self, repo_id: str, file_tree: List[str]) -> Dict[str, str]:
        """主要な依存定義ファイルの内容を取得する."""
        dep_files: Dict[str, str] = {}
        target_files = [f for f in file_tree if os.path.basename(f) in DEPENDENCY_FILE_CANDIDATES]

        with httpx.Client(timeout=self.timeout) as client:
            for filepath in target_files[:5]:  # 最大5ファイルまでに制限
                url = f"https://api.github.com/repos/{repo_id}/contents/{filepath}"
                resp = client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("content", "")
                    encoding = data.get("encoding", "")
                    if encoding == "base64":
                        try:
                            dep_files[filepath] = base64.b64decode(content).decode("utf-8", errors="replace")
                        except Exception:
                            pass
        return dep_files

    def fetch_repository_details(self, repo_data: Dict[str, Any]) -> Optional[RepoRaw]:
        """検索結果の 1 レコードから詳細な RepoRaw オブジェクトを構築する."""
        repo_id = repo_data.get("full_name", "")
        if not repo_id:
            return None

        default_branch = repo_data.get("default_branch", "main")
        readme = self.fetch_readme(repo_id)
        file_tree = self.fetch_file_tree(repo_id, default_branch)
        dep_files = self.fetch_dependency_files(repo_id, file_tree)

        created_at_str = repo_data.get("created_at")
        updated_at_str = repo_data.get("pushed_at") or repo_data.get("updated_at")

        created_at = (
            datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime.now(timezone.utc)
        )
        last_commit_at = (
            datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            if updated_at_str
            else datetime.now(timezone.utc)
        )

        license_info = repo_data.get("license") or {}
        license_spdx = license_info.get("spdx_id") if isinstance(license_info, dict) else None

        owner_info = repo_data.get("owner") or {}
        owner_name = owner_info.get("login", "") if isinstance(owner_info, dict) else ""

        return RepoRaw(
            repo_id=repo_id,
            name=repo_data.get("name", ""),
            owner=owner_name,
            description=repo_data.get("description"),
            html_url=repo_data.get("html_url", f"https://github.com/{repo_id}"),
            default_branch=default_branch,
            stars=repo_data.get("stargazers_count", 0),
            forks=repo_data.get("forks_count", 0),
            created_at=created_at,
            last_commit_at=last_commit_at,
            license_spdx=license_spdx,
            primary_language=repo_data.get("language"),
            topics=repo_data.get("topics", []),
            readme_raw=readme,
            file_tree=file_tree,
            dependency_files=dep_files,
        )


def collect_seed_repositories(
    collector: GitHubCollector,
    topics: Optional[List[str]] = None,
    queries: Optional[List[str]] = None,
    limit_per_query: int = 10,
) -> List[RepoRaw]:
    """定義済みシードから候補を収集し、候補ごとのシードカテゴリを保持する."""
    target_topics = topics or DEFAULT_SEED_TOPICS
    target_queries = queries or DEFAULT_SEED_QUERIES
    collected_repos: Dict[str, RepoRaw] = {}

    def collect_items(items: List[Dict[str, Any]], seed_categories: List[str]) -> None:
        """検索結果を重複排除しつつ、見つかったシードカテゴリを候補へ統合する."""
        for item in items:
            repo_id = item.get("full_name")
            if not repo_id:
                continue

            existing = collected_repos.get(repo_id)
            if existing:
                existing.seed_categories = sorted(set(existing.seed_categories) | set(seed_categories))
                continue

            raw = collector.fetch_repository_details(item)
            if raw:
                raw.seed_categories = sorted(set(seed_categories))
                collected_repos[repo_id] = raw

    for topic in target_topics:
        items = collector.search_repositories(f"topic:{topic}", per_page=limit_per_query)
        collect_items(items, classify_seed_categories(topic))

    for query in target_queries:
        items = collector.search_repositories(query, per_page=limit_per_query)
        collect_items(items, classify_seed_categories(query))

    return list(collected_repos.values())
