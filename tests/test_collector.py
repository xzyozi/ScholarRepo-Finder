"""データ収集モジュールの単体テスト (モック検証)."""

import base64
from unittest.mock import MagicMock, patch
from scholarrepo_finder.collector import GitHubCollector, collect_seed_repositories


@patch("httpx.Client.get")
def test_search_repositories_success(mock_get: MagicMock) -> None:
    """search_repositories の正常系レスポンスパース検証."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {"full_name": "owner/repo1", "name": "repo1"},
            {"full_name": "owner/repo2", "name": "repo2"},
        ]
    }
    mock_get.return_value = mock_resp

    collector = GitHubCollector(token="dummy_token")
    results = collector.search_repositories("topic:simulation")
    assert len(results) == 2
    assert results[0]["full_name"] == "owner/repo1"


@patch("httpx.Client.get")
def test_fetch_readme_base64(mock_get: MagicMock) -> None:
    """fetch_readme での Base64 デコード動作検証."""
    readme_text = "# Test Repository\nThis is a simulation benchmark."
    encoded = base64.b64encode(readme_text.encode("utf-8")).decode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": encoded,
        "encoding": "base64",
    }
    mock_get.return_value = mock_resp

    collector = GitHubCollector(token="dummy_token")
    result = collector.fetch_readme("owner/repo")
    assert result == readme_text


@patch("httpx.Client.get")
def test_fetch_file_tree(mock_get: MagicMock) -> None:
    """fetch_file_tree のパース検証."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "tree": [
            {"path": "src/main.py", "type": "blob"},
            {"path": "tests/test_main.py", "type": "blob"},
            {"path": "README.md", "type": "blob"},
        ]
    }
    mock_get.return_value = mock_resp

    collector = GitHubCollector(token="dummy_token")
    tree = collector.fetch_file_tree("owner/repo")
    assert "src/main.py" in tree
    assert "tests/test_main.py" in tree


@patch.object(GitHubCollector, "fetch_readme")
@patch.object(GitHubCollector, "fetch_file_tree")
@patch.object(GitHubCollector, "fetch_dependency_files")
def test_fetch_repository_details(
    mock_dep: MagicMock, mock_tree: MagicMock, mock_readme: MagicMock
) -> None:
    """fetch_repository_details による RepoRaw 構築検証."""
    mock_readme.return_value = "# Repo\nSimulation content."
    mock_tree.return_value = ["src/app.py", "requirements.txt"]
    mock_dep.return_value = {"requirements.txt": "numpy>=1.20"}

    repo_data = {
        "full_name": "lab/sim-opt",
        "name": "sim-opt",
        "owner": {"login": "lab"},
        "description": "Simulation and Optimization toolkit",
        "html_url": "https://github.com/lab/sim-opt",
        "default_branch": "main",
        "stargazers_count": 42,
        "forks_count": 5,
        "created_at": "2024-01-01T00:00:00Z",
        "pushed_at": "2024-06-01T12:00:00Z",
        "license": {"spdx_id": "MIT"},
        "language": "Python",
        "topics": ["simulation", "optimization"],
    }

    collector = GitHubCollector(token="dummy")
    raw = collector.fetch_repository_details(repo_data)
    assert raw is not None
    assert raw.repo_id == "lab/sim-opt"
    assert raw.stars == 42
    assert raw.license_spdx == "MIT"
    assert "numpy>=1.20" in raw.dependency_files.get("requirements.txt", "")
