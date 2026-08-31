"""ScholarRepo-Finder 静的データビルダー。"""

import json
from pathlib import Path
from typing import Any

from scholarrepo_finder.models import ExtractedFeatures, RepoRaw, ScoreResult, StaticRepoItem
from scholarrepo_finder.scoring_config import LoadedScoringConfig

EvaluatedRecord = tuple[RepoRaw, ScoreResult, ExtractedFeatures]


def build_static_repo_items(
    evaluated_records: list[EvaluatedRecord],
    min_score: float,
) -> list[StaticRepoItem]:
    """設定された閾値以上の評価済み候補から配信項目を構築する。"""
    items: list[StaticRepoItem] = []
    for raw, score, features in evaluated_records:
        if not score.hard_filter_passed or score.total_score < min_score:
            continue

        description = (raw.description or "").strip()
        if len(description) > 200:
            description = f"{description[:197]}..."

        reusability_evidence = (
            features.public_api_evidence
            + features.module_partition_evidence
            + features.usage_evidence
            + features.configurable_io_evidence
        )
        items.append(
            StaticRepoItem(
                id=raw.repo_id,
                name=raw.name,
                desc=description,
                lang=raw.primary_language or "Unknown",
                topics=raw.topics,
                stars=raw.stars,
                updated=raw.last_commit_at.strftime("%Y-%m-%d"),
                score=score.total_score,
                score_breakdown={
                    "reusability": score.reusability_score,
                    "maintainability": score.maintainability_score,
                    "research_context": score.research_context_score,
                },
                delivery_form=features.delivery_form,
                reusability_evidence=reusability_evidence,
                paper=features.has_doi_link or features.has_arxiv_link or features.is_pwc_official,
                pwc_status=raw.pwc_match.lookup_status if raw.pwc_match else "not_checked",
                pwc_paper_url=raw.pwc_match.paper_url if raw.pwc_match else None,
                edu=features.is_edu_or_ac_domain,
                libs=features.scientific_libs_detected,
                url=raw.html_url,
            )
        )
    return sorted(items, key=lambda item: item.score, reverse=True)


def build_phase1_observation_report(
    evaluated_records: list[EvaluatedRecord],
    loaded_config: LoadedScoringConfig,
) -> dict[str, Any]:
    """提供形態・シード分類ごとの設定付き観測レポートを構築する。"""
    config = loaded_config.config
    minimum_score = config.indexing_threshold
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    evaluations: list[dict[str, Any]] = []

    for raw, score, features in evaluated_records:
        threshold_passed = score.hard_filter_passed and score.total_score >= minimum_score
        evaluations.append(
            {
                "repo_id": raw.repo_id,
                "delivery_form": features.delivery_form,
                "hard_filter_passed": score.hard_filter_passed,
                "threshold_passed": threshold_passed,
                "scores": {
                    "reusability": score.reusability_score,
                    "maintainability": score.maintainability_score,
                    "research_context": score.research_context_score,
                    "base": score.base_repo_score,
                    "total": score.total_score,
                },
            }
        )
        for seed_category in raw.seed_categories or ["unclassified"]:
            key = (seed_category, features.delivery_form)
            bucket = buckets.setdefault(
                key,
                {
                    "seed_category": seed_category,
                    "delivery_form": features.delivery_form,
                    "collected_count": 0,
                    "hard_filter_passed_count": 0,
                    "threshold_passed_count": 0,
                    "reusability_score_total": 0.0,
                    "maintainability_score_total": 0.0,
                    "research_context_score_total": 0.0,
                    "total_score_total": 0.0,
                },
            )
            bucket["collected_count"] += 1
            bucket["reusability_score_total"] += score.reusability_score
            bucket["maintainability_score_total"] += score.maintainability_score
            bucket["research_context_score_total"] += score.research_context_score
            bucket["total_score_total"] += score.total_score
            if score.hard_filter_passed:
                bucket["hard_filter_passed_count"] += 1
            if threshold_passed:
                bucket["threshold_passed_count"] += 1

    groups: list[dict[str, Any]] = []
    for key in sorted(buckets):
        bucket = buckets[key]
        collected_count = int(bucket["collected_count"])
        groups.append(
            {
                "seed_category": bucket["seed_category"],
                "delivery_form": bucket["delivery_form"],
                "collected_count": collected_count,
                "hard_filter_passed_count": bucket["hard_filter_passed_count"],
                "threshold_passed_count": bucket["threshold_passed_count"],
                "selected_count": bucket["threshold_passed_count"],
                "average_scores": {
                    "reusability": round(float(bucket["reusability_score_total"]) / collected_count, 2),
                    "maintainability": round(float(bucket["maintainability_score_total"]) / collected_count, 2),
                    "research_context": round(float(bucket["research_context_score_total"]) / collected_count, 2),
                    "total": round(float(bucket["total_score_total"]) / collected_count, 2),
                },
            }
        )

    return {
        "report_version": 2,
        "selection_score_mode": "configurable_reusability",
        "profile": {"id": config.profile.id, "version": config.profile.version},
        "config_sha256": loaded_config.sha256,
        "minimum_score": minimum_score,
        "category_counting": "A repository is counted once for every seed category that discovered it.",
        "groups": groups,
        "evaluations": evaluations,
    }


def save_phase1_observation_report(report: dict[str, Any], output_path: Path | str) -> None:
    """観測レポートをUTF-8 JSONとして書き出す。"""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def save_static_json(items: list[StaticRepoItem], output_path: Path | str) -> None:
    """GitHub Pages配信用の軽量JSONを書き出す。"""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([item.model_dump() for item in items], ensure_ascii=False, indent=2), encoding="utf-8")


def generate_awesome_markdown(
    items: list[StaticRepoItem],
    output_path: Path | str,
    minimum_score: float,
    profile_id: str,
    title: str = "Awesome Scholar Repositories",
) -> None:
    """設定プロファイルと閾値を明記した一覧Markdownを生成する。"""
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 📚 {title}",
        "> ScholarRepo-Finder が自動収集・厳選した高品質な学術研究・アルゴリズム検証用OSS一覧",
        "",
        f"- **登録リポジトリ数**: {len(items)} 件",
        f"- **選定基準**: `{profile_id}` プロファイル、Total Score >= {minimum_score}",
        "",
        "| # | リポジトリ | 総合スコア | 言語 | 論文/DOI | 最終更新 | 概要 |",
        "| :-: | :--- | :---: | :---: | :---: | :---: | :--- |",
    ]
    for index, item in enumerate(items, 1):
        paper_badge = "✅ あり" if item.paper else "-"
        lines.append(
            f"| {index} | [{item.id}]({item.url}) | **{item.score}** | `{item.lang}` | "
            f"{paper_badge} | {item.updated} | {item.desc} |"
        )
    lines.extend(["", "---", "*自動生成: [ScholarRepo-Finder](https://xzyozi.github.io/ScholarRepo-Finder/)*", ""])
    target.write_text("\n".join(lines), encoding="utf-8")
