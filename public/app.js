// ScholarRepo-Finder クライアントサイド検索 & UI ロジック

let allRepos = [];
let miniSearch = null;

// DOM Elements
const searchInput = document.getElementById("searchInput");
const langSelect = document.getElementById("langSelect");
const scoreRange = document.getElementById("scoreRange");
const scoreVal = document.getElementById("scoreVal");
const paperCheck = document.getElementById("paperCheck");
const eduCheck = document.getElementById("eduCheck");
const sortSelect = document.getElementById("sortSelect");
const resetFiltersBtn = document.getElementById("resetFiltersBtn");
const exportMdBtn = document.getElementById("exportMdBtn");

const repoList = document.getElementById("repoList");
const emptyState = document.getElementById("emptyState");
const totalRepoCount = document.getElementById("totalRepoCount");
const filteredRepoCount = document.getElementById("filteredRepoCount");
const resultCountLabel = document.getElementById("resultCountLabel");
const toast = document.getElementById("toast");
const toastMsg = document.getElementById("toastMsg");

// 1. 初期化 & データ読み込み
async function initApp() {
  try {
    const res = await fetch("./data/repos.json");
    if (!res.ok) throw new Error("Failed to load repos.json");
    allRepos = await res.json();
  } catch (e) {
    console.warn("Using sample fallback data:", e);
    allRepos = getSampleFallbackData();
  }

  setupMiniSearch();
  populateLanguageFilter();
  renderResults();

  totalRepoCount.textContent = `${allRepos.length} 件`;
}

// 2. MiniSearch インデックス構築
function setupMiniSearch() {
  miniSearch = new MiniSearch({
    fields: ["id", "name", "desc", "lang", "topics", "libs"],
    storeFields: ["id"],
    searchOptions: {
      boost: { name: 2, topics: 1.5, id: 1.2 },
      fuzzy: 0.2,
      prefix: true
    }
  });
  miniSearch.addAll(allRepos);
}

// 3. 言語フィルター一覧の生成
function populateLanguageFilter() {
  const languages = [...new Set(allRepos.map(r => r.lang).filter(Boolean))].sort();
  languages.forEach(lang => {
    const opt = document.createElement("option");
    opt.value = lang;
    opt.textContent = lang;
    langSelect.appendChild(opt);
  });
}

// 4. 検索＆フィルタリング実行
function getFilteredRepos() {
  const query = searchInput.value.trim();
  const selectedLang = langSelect.value;
  const minScore = parseFloat(scoreRange.value);
  const requirePaper = paperCheck.checked;
  const requireEdu = eduCheck.checked;
  const sortBy = sortSelect.value;

  let results = allRepos;

  // MiniSearch による全文検索
  if (query && miniSearch) {
    const matchedIds = new Set(miniSearch.search(query).map(res => res.id));
    results = results.filter(r => matchedIds.has(r.id));
  }

  // ファセットフィルター
  results = results.filter(r => {
    if (selectedLang && r.lang !== selectedLang) return false;
    if (r.score < minScore) return false;
    if (requirePaper && !r.paper) return false;
    if (requireEdu && !r.edu) return false;
    return true;
  });

  // ソート
  results.sort((a, b) => {
    if (sortBy === "score_desc") return b.score - a.score;
    if (sortBy === "stars_desc") return b.stars - a.stars;
    if (sortBy === "updated_desc") return new Date(b.updated) - new Date(a.updated);
    return 0;
  });

  return results;
}

// 5. 描画処理
function renderResults() {
  const repos = getFilteredRepos();
  filteredRepoCount.textContent = `${repos.length} 件`;
  resultCountLabel.textContent = repos.length;

  repoList.innerHTML = "";

  if (repos.length === 0) {
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");

  repos.forEach(repo => {
    const card = document.createElement("div");
    card.className = "bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-indigo-500/50 p-5 rounded-2xl transition duration-200 shadow-sm flex flex-col space-y-3";

    // バッジ群
    const paperBadge = repo.paper ? '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">📄 論文/DOI</span>' : '';
    const eduBadge = repo.edu ? '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">🎓 学術機関</span>' : '';
    const langBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-slate-300">${repo.lang}</span>`;
    
    // トピック
    const topicTags = (repo.topics || []).slice(0, 5).map(t => `<span class="text-xs text-slate-400 bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800">#${t}</span>`).join(" ");

    card.innerHTML = `
      <div class="flex items-start justify-between gap-4">
        <div>
          <div class="flex items-center space-x-2 flex-wrap gap-y-1">
            <a href="${repo.url}" target="_blank" rel="noopener noreferrer" class="text-base font-bold text-indigo-300 hover:text-indigo-200 hover:underline">
              ${repo.id}
            </a>
            ${langBadge}
            ${paperBadge}
            ${eduBadge}
          </div>
          <p class="text-xs text-slate-400 mt-1.5 leading-relaxed">${repo.desc || "概要説明なし"}</p>
        </div>
        <div class="text-right flex-shrink-0">
          <div class="text-xs text-slate-400">総合スコア</div>
          <div class="text-xl font-black bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">${repo.score.toFixed(1)}</div>
        </div>
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-slate-700/40 text-xs text-slate-400 flex-wrap gap-2">
        <div class="flex items-center space-x-4">
          <span>⭐ ${repo.stars} stars</span>
          <span>📅 最終更新: ${repo.updated}</span>
          ${repo.libs && repo.libs.length ? `<span>🧪 ${repo.libs.join(", ")}</span>` : ""}
        </div>
        <div class="flex items-center space-x-2">
          ${topicTags}
          <button onclick="copyItemMarkdown('${repo.id}')" class="ml-2 px-2.5 py-1 rounded bg-slate-700/60 hover:bg-slate-700 text-slate-300 hover:text-white transition" title="Markdown引用をコピー">
            📋 Copy MD
          </button>
        </div>
      </div>
    `;

    repoList.appendChild(card);
  });
}

// 6. Markdown 一括ダウンロード機能 (Blob API)
function exportToMarkdown() {
  const repos = getFilteredRepos();
  if (repos.length === 0) {
    showToast("エクスポート対象のリポジトリがありません");
    return;
  }

  const query = searchInput.value.trim() || "なし";
  const lang = langSelect.value || "すべて";
  const minScore = scoreRange.value;
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");

  let md = `# ScholarRepo-Finder 検索結果エクスポート\n`;
  md += `- **検索クエリ**: \`${query}\`\n`;
  md += `- **適用フィルター**: 言語: \`${lang}\`, 最低スコア: \`${minScore}\`, 論文必須: \`${paperCheck.checked}\`\n`;
  md += `- **出力件数**: ${repos.length} 件\n`;
  md += `- **出力日時**: ${now}\n\n`;

  md += `| # | リポジトリ | 総合スコア | 言語 | 論文/DOI | 最終更新 | 概要 |\n`;
  md += `| :-: | :--- | :---: | :---: | :---: | :---: | :--- |\n`;

  repos.forEach((r, idx) => {
    const paperBadge = r.paper ? "✅ あり" : "-";
    const desc = (r.desc || "").replace(/\|/g, "/");
    md += `| ${idx + 1} | [${r.id}](${r.url}) | **${r.score.toFixed(1)}** | \`${r.lang}\` | ${paperBadge} | ${r.updated} | ${desc} |\n`;
  });

  md += `\n---\n*Generated by [ScholarRepo-Finder](https://xzyozi.github.io/ScholarRepo-Finder/)*\n`;

  const blob = new Blob([md], { type: "text/markdown;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `scholar_repos_${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);

  showToast(`Markdown ファイル (${repos.length}件) をダウンロードしました！`);
}

// 7. 個別リポジトリ引用コピー (Clipboard API)
window.copyItemMarkdown = function(repoId) {
  const repo = allRepos.find(r => r.id === repoId);
  if (!repo) return;

  const md = `- **[${repo.id}](${repo.url})** (Score: ${repo.score.toFixed(1)}, Lang: \`${repo.lang}\`)\n  - 概要: ${repo.desc}\n  - 関連タグ: \`${repo.topics.join(", ")}\`\n  - 論文/DOI: ${repo.paper ? "あり" : "なし"}`;
  
  navigator.clipboard.writeText(md).then(() => {
    showToast(`[${repo.name}] のMarkdown引用をコピーしました`);
  });
};

function showToast(message) {
  toastMsg.textContent = message;
  toast.classList.remove("translate-y-20", "opacity-0");
  setTimeout(() => {
    toast.classList.add("translate-y-20", "opacity-0");
  }, 2500);
}

// Event Listeners
searchInput.addEventListener("input", renderResults);
langSelect.addEventListener("change", renderResults);
scoreRange.addEventListener("input", (e) => {
  scoreVal.textContent = `${e.target.value}.0 点`;
  renderResults();
});
paperCheck.addEventListener("change", renderResults);
eduCheck.addEventListener("change", renderResults);
sortSelect.addEventListener("change", renderResults);
exportMdBtn.addEventListener("click", exportToMarkdown);

resetFiltersBtn.addEventListener("click", () => {
  searchInput.value = "";
  langSelect.value = "";
  scoreRange.value = "60";
  scoreVal.textContent = "60.0 点";
  paperCheck.checked = false;
  eduCheck.checked = false;
  sortSelect.value = "score_desc";
  renderResults();
});

// 初期サンプルフォールバックデータ
function getSampleFallbackData() {
  return [
    {
      id: "stanford-lab/cvrp-deep-solver",
      name: "cvrp-deep-solver",
      desc: "A benchmark deep reinforcement learning simulation toolkit for solving large-scale CVRP instances.",
      lang: "Python",
      topics: ["vehicle-routing", "reinforcement-learning", "simulation"],
      stars: 128,
      updated: "2024-05-10",
      score: 112.5,
      paper: true,
      edu: true,
      libs: ["numpy", "torch", "ortools"],
      url: "https://github.com/stanford-lab/cvrp-deep-solver"
    },
    {
      id: "mit-or/discrete-event-platform",
      name: "discrete-event-platform",
      desc: "High-performance discrete-event simulation platform for supply chain and manufacturing operations research.",
      lang: "Rust",
      topics: ["simulation", "operations-research", "discrete-event"],
      stars: 84,
      updated: "2024-04-22",
      score: 98.0,
      paper: true,
      edu: true,
      libs: ["ndarray"],
      url: "https://github.com/mit-or/discrete-event-platform"
    },
    {
      id: "Mominyar/emergency-dispatch-simulation-system",
      name: "emergency-dispatch-simulation-system",
      desc: "A turn-based emergency response dispatch simulation designed for algorithmic evaluation and baseline comparison.",
      lang: "C",
      topics: ["simulation", "dispatch", "c-programming"],
      stars: 15,
      updated: "2024-05-12",
      score: 85.5,
      paper: false,
      edu: true,
      libs: [],
      url: "https://github.com/Mominyar/emergency-dispatch-simulation-system"
    }
  ];
}

// Start App
initApp();
