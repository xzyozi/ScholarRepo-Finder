"""ScholarRepo-Finder データモデルおよび DTO 定義モジュール."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RepoRaw(BaseModel):
    """データ収集層 (Ingestion) で取得されるリポジトリの生メタデータ."""

    repo_id: str = Field(..., description="リポジトリ識別子 (owner/repo)")
    name: str = Field(..., description="リポジトリ名")
    owner: str = Field(..., description="所有者アカウント名")
    description: Optional[str] = Field(None, description="リポジトリ概要説明文")
    html_url: str = Field(..., description="GitHub リポジトリ URL")
    default_branch: str = Field("main", description="デフォルトブランチ名")
    stars: int = Field(0, ge=0, description="スター数")
    forks: int = Field(0, ge=0, description="フォーク数")
    created_at: datetime = Field(..., description="作成日時")
    last_commit_at: datetime = Field(..., description="最終コミット日時")
    license_spdx: Optional[str] = Field(None, description="SPDX ライセンス識別子 (例: MIT)")
    primary_language: Optional[str] = Field(None, description="主要プログラミング言語")
    topics: List[str] = Field(default_factory=list, description="トピックタグ一覧")
    readme_raw: Optional[str] = Field(None, description="README 生テキスト")
    file_tree: List[str] = Field(default_factory=list, description="リポジトリ内ファイルパス一覧")
    dependency_files: Dict[str, str] = Field(
        default_factory=dict, description="依存定義ファイル名と内容 (requirements.txt 等)"
    )
    etag: Optional[str] = Field(None, description="条件付きリクエスト用 ETag")


class ExtractedFeatures(BaseModel):
    """特徴抽出層 (Feature Extraction) で生成される特徴量ベクトル."""

    repo_id: str = Field(..., description="リポジトリ識別子 (owner/repo)")
    has_src_or_app_dir: bool = Field(False, description="src/ または app/ ディレクトリ存在フラグ")
    has_tests_dir: bool = Field(False, description="tests/ または test/ ディレクトリ存在フラグ")
    has_docs_dir: bool = Field(False, description="docs/ または doc/ ディレクトリ存在フラグ")
    has_ci_workflow: bool = Field(False, description="CI 設定ファイル存在フラグ")
    scientific_libs_detected: List[str] = Field(
        default_factory=list, description="検出された科学計算・OR系ライブラリ名一覧"
    )
    has_doi_link: bool = Field(False, description="DOI リンク (doi.org) 検出フラグ")
    has_arxiv_link: bool = Field(False, description="arXiv リンク (arxiv.org/abs) 検出フラグ")
    is_pwc_official: bool = Field(False, description="Papers with Code 公式登録フラグ")
    academic_keyword_score: float = Field(0.0, ge=0.0, le=10.0, description="学術キーワード出現スコア")
    author_email_domain: Optional[str] = Field(None, description="リポジトリ所有者のメールドメイン")
    is_edu_or_ac_domain: bool = Field(False, description="教育・研究機関ドメイン (.edu / .ac.* / .gov) フラグ")
    is_verified_org: bool = Field(False, description="GitHub 認証済み組織フラグ")
    author_account_age_years: int = Field(0, ge=0, description="所有者アカウント経過年数")


class ScoreResult(BaseModel):
    """評価・選別層 (Scoring & Filtering) の算出結果."""

    repo_id: str = Field(..., description="リポジトリ識別子 (owner/repo)")
    hard_filter_passed: bool = Field(False, description="ハードフィルター合否")
    reject_reason: Optional[str] = Field(None, description="不合格時の除外理由")
    structural_score: float = Field(0.0, ge=0.0, le=50.0, description="構造スコア (最大 50点)")
    context_score: float = Field(0.0, ge=0.0, le=50.0, description="学術文脈スコア (最大 50点)")
    base_repo_score: float = Field(0.0, ge=0.0, le=100.0, description="リポジトリ品質基礎スコア (最大 100点)")
    user_trust_multiplier: float = Field(1.0, ge=0.5, le=1.5, description="著者信頼度乗数 (0.5x〜1.5x)")
    total_score: float = Field(0.0, ge=0.0, le=150.0, description="最終総合スコア")
    evaluated_at: datetime = Field(default_factory=datetime.now, description="評価日時")


class StaticRepoItem(BaseModel):
    """GitHub Pages 配信用の超軽量リポジトリモデル (data/repos.json)."""

    id: str = Field(..., description="リポジトリ識別子 (owner/repo)")
    name: str = Field(..., description="リポジトリ名")
    desc: str = Field("", description="概要文 (最大 200 文字にトリム)")
    lang: str = Field("Unknown", description="主要プログラミング言語")
    topics: List[str] = Field(default_factory=list, description="トピック一覧")
    stars: int = Field(0, ge=0, description="スター数")
    updated: str = Field(..., description="最終コミット日 (YYYY-MM-DD)")
    score: float = Field(..., ge=0.0, description="総合スコア")
    paper: bool = Field(False, description="論文リンク有無フラグ")
    edu: bool = Field(False, description="アカデミック著者フラグ")
    libs: List[str] = Field(default_factory=list, description="検出された科学計算ライブラリ")
    url: str = Field(..., description="リポジトリ URL")
