"""Papers with Code公開アーカイブのリポジトリ照合クライアント。"""

from urllib.parse import urlsplit

import httpx

from scholarrepo_finder.models import PapersWithCodeMatch

PWC_ARCHIVE_DATASET = "pwc-archive/links-between-paper-and-code"
PWC_DATASET_FILTER_URL = "https://datasets-server.huggingface.co/filter"


def _repository_url_variants(repository_url: str) -> list[str]:
    """GitHub URLの末尾スラッシュと.git差を吸収した照合候補を返す。"""
    parsed = urlsplit(repository_url)
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    canonical = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    return [canonical, f"{canonical}/", f"{canonical}.git"]


class PapersWithCodeClient:
    """Hugging Face上のPWC最終公開アーカイブを参照するクライアント。"""

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    def lookup_repository(self, repository_url: str) -> PapersWithCodeMatch:
        """GitHubリポジトリURLに紐づくPWC登録を照合する。"""
        variants = _repository_url_variants(repository_url)
        escaped_variants = [value.replace("'", "''") for value in variants]
        where = " OR ".join(f"repo_url = '{value}'" for value in escaped_variants)
        params: dict[str, str | int] = {
            "dataset": PWC_ARCHIVE_DATASET,
            "config": "default",
            "split": "train",
            "where": where,
            "offset": 0,
            "length": 100,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(PWC_DATASET_FILTER_URL, params=params)
        except httpx.HTTPError:
            return PapersWithCodeMatch(lookup_status="failed")

        if response.status_code != 200:
            return PapersWithCodeMatch(lookup_status="failed")

        data = response.json()
        rows = data.get("rows", []) if isinstance(data, dict) else []
        records = [row.get("row", row) for row in rows if isinstance(row, dict)]
        if not records:
            return PapersWithCodeMatch(lookup_status="not_found")

        selected = next((record for record in records if record.get("is_official") is True), records[0])
        is_official = bool(selected.get("is_official"))
        return PapersWithCodeMatch(
            lookup_status="matched_official" if is_official else "matched_unofficial",
            is_official=is_official,
            repository_url=variants[0],
            paper_url=selected.get("paper_url_abs") or selected.get("paper_url"),
            arxiv_id=selected.get("paper_arxiv_id"),
        )
