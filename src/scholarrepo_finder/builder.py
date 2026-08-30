"""ScholarRepo-Finder 静的データビルダー (Static Builder)."""

import json
from pathlib import Path
from typing import List, Tuple

from scholarrepo_finder.models import ExtractedFeatures, RepoRaw, ScoreResult, StaticRepoItem
from scholarrepo_finder.scorer import INDEXING_THRESHOLD_SCORE


def build_static_repo_items(
    evaluated_records: List[Tuple[RepoRaw, ScoreResult, ExtractedFeatures]],
    min_score: float = INDEXING_THRESHOLD_SCORE,
) -> List[StaticRepoItem]:
    """評価済みレコード群から、閾値以上の配信用 StaticRepoItem リストを生成する."""
    items: List[StaticRepoItem] = []

    for raw, score, features in evaluated_records:
        if not score.hard_filter_passed or score.total_score < min_score:
            continue

        desc = (raw.description or "").strip()
        if len(desc) > 200:
            desc = desc[:197] + "..."

        updated_str = raw.last_commit_at.strftime("%Y-%m-%d")
        has_paper = features.has_doi_link or features.has_arxiv_link or features.is_pwc_official

        items.append(
            StaticRepoItem(
                id=raw.repo_id,
                name=raw.name,
                desc=desc,
                lang=raw.primary_language or "Unknown",
                topics=raw.topics,
                stars=raw.stars,
                updated=updated_str,
                score=score.total_score,
                paper=has_paper,
                edu=features.is_edu_or_ac_domain,
                libs=features.scientific_libs_detected,
                url=raw.html_url,
            )
        )

    # 総合スコア降順ソート
    items.sort(key=lambda x: x.score, reverse=True)
    return items


def save_static_json(items: List[StaticRepoItem], output_path: Path | str) -> None:
    """GitHub Pages 配信用の軽量 repos.json を書き出す."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    data = [item.model_dump() for item in items]
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_awesome_markdown(
    items: List[StaticRepoItem], output_path: Path | str, title: str = "Awesome Scholar Repositories"
) -> None:
    """リポジトリ内閲覧用のまとめ Markdown ドキュメントを自動生成する."""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# 📚 {title}",
        "> ScholarRepo-Finder が自動収集・厳選した高品質な学術研究・アルゴリズム検証用OSS一覧",
        "",
        f"- **登録リポジトリ数**: {len(items)} 件",
        "- **選定基準**: 構造品質スコア ＋ 学術文脈スコア (Total Score >= 60.0)",
        "",
        "| # | リポジトリ | 総合スコア | 言語 | 論文/DOI | 最終更新 | 概要 |",
        "| :-: | :--- | :---: | :---: | :---: | :---: | :--- |",
    ]

    for idx, item in enumerate(items, 1):
        paper_badge = "✅ あり" if item.paper else "-"
        link = f"[{item.id}]({item.url})"
        lines.append(
            f"| {idx} | {link} | **{item.score}** | `{item.lang}` | {paper_badge} | {item.updated} | {item.desc} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("*自動生成: [ScholarRepo-Finder](https://xzyozi.github.io/ScholarRepo-Finder/)*")
    lines.append("")

    target.write_text("\n".join(lines), encoding="utf-8")
