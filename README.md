# ScholarRepo-Finder 🔍📚
> **Specialized Search & Discovery Engine for Academic Research and Algorithm Verification OSS (GitHub Pages & Markdown Export)**

[English](./README.md) | [日本語](./README.ja.md)

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Demo-brightgreen?logo=github)](https://xzyozi.github.io/ScholarRepo-Finder/)
[![CI](https://github.com/xzyozi/ScholarRepo-Finder/actions/workflows/ci.yml/badge.svg)](https://github.com/xzyozi/ScholarRepo-Finder/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

🌐 **Live Demo Website**: [https://xzyozi.github.io/ScholarRepo-Finder/](https://xzyozi.github.io/ScholarRepo-Finder/)

ScholarRepo-Finder is a static web platform that automatically discovers, rigorously evaluates, and indexes academic simulation and algorithm verification open-source software (OSS) from GitHub. It operates with **zero infrastructure, 100% free hosting via GitHub Pages, blazing-fast client-side search, and one-click Markdown export**.

---

## 🌟 Key Features

- **100% Serverless & Zero-Infra**: No external databases or always-on servers. Automated periodic crawling & indexing via GitHub Actions, statically hosted on GitHub Pages.
- **Curated & Ultra-Lightweight**: Only high-scoring repositories (Score >= 60.0) are indexed, keeping data size within a few MBs for instant in-browser loading.
- **Multi-Factor Academic Scoring**: Structural cleanliness (`src/`, `tests/` separation), scientific/OR library dependencies (`numpy`, `scipy`, `ortools`, `simpy`, etc.), paper links (DOI / arXiv), and verified academic author domains.
- **Instant Client-Side Search**: In-memory search (MiniSearch) enables 0ms facet filtering by language, minimum score, and paper presence.
- **One-Click Markdown Export**: Download filtered results as a Markdown summary table or copy individual repo citations directly to clipboard (ideal for Obsidian, Notion, and research notes).

---

## 📐 Architecture

```mermaid
flowchart LR
    A[GitHub / Papers with Code API] --> B[GitHub Actions Batch Ingestion]
    B --> C[Feature Extraction & Scoring]
    C --> D[Lightweight JSON Build]
    D --> E[GitHub Pages Deployment]
    E --> F[In-Browser MiniSearch UI]
    F --> G[Markdown Export / Copy]
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (Recommended)

### Development
```bash
# Sync dependencies
uv sync

# Run pipeline locally
uv run python -m scholarrepo_finder.pipeline

# Run tests
uv run pytest
```

---

## 📄 License
Released under the [MIT License](./LICENSE).
