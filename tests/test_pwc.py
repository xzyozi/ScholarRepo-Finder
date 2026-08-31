"""Papers with Codeアーカイブ照合クライアントの公開契約テスト。"""

from unittest.mock import MagicMock, patch

from scholarrepo_finder.pwc import PapersWithCodeClient


@patch("httpx.Client.get")
def test_lookup_repository_prefers_official_pwc_archive_match(mock_get: MagicMock) -> None:
    """同一リポジトリの候補から公式登録を優先して返す。"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "rows": [
            {"row": {"repo_url": "https://github.com/lab/tool", "is_official": False}},
            {
                "row": {
                    "repo_url": "https://github.com/lab/tool",
                    "is_official": True,
                    "paper_url_abs": "https://arxiv.org/abs/2401.00001",
                    "paper_arxiv_id": "2401.00001",
                }
            },
        ]
    }
    mock_get.return_value = response

    match = PapersWithCodeClient().lookup_repository("https://github.com/lab/tool.git")

    assert match.lookup_status == "matched_official"
    assert match.is_official is True
    assert match.repository_url == "https://github.com/lab/tool"
    assert match.paper_url == "https://arxiv.org/abs/2401.00001"
    assert mock_get.call_args.args[0] == "https://datasets-server.huggingface.co/filter"


@patch("httpx.Client.get")
def test_lookup_repository_distinguishes_not_found_from_service_failure(mock_get: MagicMock) -> None:
    """照合対象なしと外部サービス障害を同じ未登録扱いにしない。"""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"rows": []}
    mock_get.return_value = response

    client = PapersWithCodeClient()
    assert client.lookup_repository("https://github.com/lab/missing").lookup_status == "not_found"

    response.status_code = 503
    assert client.lookup_repository("https://github.com/lab/unavailable").lookup_status == "failed"
