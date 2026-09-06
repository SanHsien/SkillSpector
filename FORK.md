# Fork 維護說明

本 repo fork 自 [`NVIDIA/SkillSpector`](https://github.com/NVIDIA/SkillSpector)，沿用
Apache License 2.0 與完整 Git 歷史。

## 為什麼維護 fork

- 保留上游持續更新的 AI agent skill 安全掃描器（71 條偵測樣式、17 個分類、靜態分析＋可選
  LLM 語意分析、MCP server、Claude Code skill）。
- 採 Windows-first 維護：Windows 11 + PowerShell 是主要開發、除錯與驗收環境；上游的
  `Makefile` 是 POSIX sh 語法，在 Windows 原生（非 WSL2）跑不動。
- 公開入口改以繁體中文為主，英文原文鏡像放 `README.en.md`。
- 建立可重現的 Windows 開發 gate（`tools/dev_check.ps1`），繞過 `Makefile` 直接呼叫
  `uv`／`ruff`／`pytest`。
- 產品程式碼（`src/skillspector/`）、測試（`tests/`）、`skills/`、`Makefile`、
  `pyproject.toml`、`uv.lock`、`.github/workflows/*` 仍以上游為準，不因本線需求改寫。

**回貢判準：修的是上游的 bug 就送回去；這裡獨創的文件與 Windows 維護骨架留在這裡。**

## 與上游的差異

| 項目 | 說明 |
|---|---|
| `README.md` | 繁中主檔；英文原文在 `README.en.md`（`git mv` 保留，只加了一行語言列） |
| `CLAUDE.md` | 新增：薄指標檔，指向 `AGENTS.md` 為單一真相源。上游沒有這個檔案 |
| `AGENTS.md` | 新增：AI agent 的單一真相源，含專案速覽與本 fork 的維護規則。上游沒有這個檔案 |
| `NOTICE.md` | 新增：來源、Apache-2.0 授權說明；`THIRD_PARTY_NOTICES.md` 是上游既有的第三方套件授權清單，本檔不取代它，只互相指路 |
| `CHANGELOG.zh-TW.md` | 新增：只記本 fork 自己的維護歷史；上游既有的 `CHANGELOG.md` 是上游自己的產品變更記錄，不動它 |
| `CODE_OF_CONDUCT.md` | 新增：上游沒有這個檔案，短版，針對本 fork 的維護範圍 |
| `.editorconfig` / `.gitattributes` | 新增：2 空格（`.py`／`.ps1` 4 空格）、LF 換行；上游都沒有這兩個檔案 |
| `.cursor/rules/no-upstream-pr.mdc` | 新增：機器可讀的「對外只打 origin」規則 |
| `tools/dev_check.ps1` | 新增：Windows 本機一鍵 gate（`ruff check` → `ruff format --check` → `-Quick` 到此為止；完整模式再加 `pytest`），繞過 `Makefile` 直接呼叫 `uv` |
| `docs/DECISIONS.md` | 新增：本 fork 的維護決策記錄骨架 |
| `docs/DIVERGENCE.md` | 新增：逐檔登記本 fork 對上游持有檔案的修改的骨架（目前為空表） |
| `.gitignore` | 修改：append 一個 fork 區塊，忽略 `.venv/`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`htmlcov/` 與兩份生成報告 |
| `.github/dependabot.yml` | 新增：`uv`（`pyproject.toml`/`uv.lock`）、`github-actions`、`npm`（`package.json`）、`docker`（`Dockerfile`）四個 ecosystem，每週檢查 |
| `tools/upstream_baseline.json` | 新增：上游同步水位（commit／PR／issue 三軸），起點為 fork 建立當下與上游 main 一致的 commit |
| `tools/check_upstream_updates.py` | 新增：讀三軸水位，`git fetch` 比對新 commit，`gh pr/issue list --state all` 比對新工單，輸出 `upstream-review-report.md` |
| `tools/check_dependency_freshness.py` | 新增：比對 `pyproject.toml` 宣告的 Python 依賴（PyPI）與 `.github/workflows/*.yml` 釘選的 GitHub Action（GitHub Releases API），支援 `# freshness-hold:` 與 `.github/dependency-deferrals.json`，輸出 `dependency-freshness-report.md` |
| `.github/workflows/upstream-check.yml`、`.github/workflows/dependency-freshness.yml` | 新增：每週排程 + `workflow_dispatch`，報告寫入 `$GITHUB_STEP_SUMMARY`，有待處理項目就讓 job 失敗（不開 issue） |
| `tools/dev_check.ps1` | 修改：append 一步跑 `check_dependency_freshness.py`（non-strict，只產報告不擋 commit） |

產品 `src/skillspector/`、`tests/`、`skills/`、`contrib/`、`extensions/`、
`docs/{ANALYSIS_RESOURCE_BOUNDS,DEVELOPMENT,SUPPRESSION,...}.md`、`Makefile`、
`pyproject.toml`、`uv.lock`、`LICENSE`、`SECURITY.md`、`CONTRIBUTING.md`、`CHANGELOG.md`、
`THIRD_PARTY_NOTICES.md`、`.github/workflows/*` 以上游為準，本 fork 目前沒有對它們做任何修改；
一旦有已記錄的 fork 修正，登記在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。

## 已建立的維護自動化

2026-09-05～06 補齊上游同步、依賴新鮮度、分岔、pin bounds 與 CodeQL：

- **上游同步水位**：`tools/upstream_baseline.json` 記錄 commit（`reviewed_through`，完整
  40 碼 SHA）、PR（`reviewed_pr_through`）、issue（`reviewed_issue_through`）三軸水位；
  `tools/check_upstream_updates.py` 讀三軸、`git fetch upstream` 比對新 commit、
  `gh pr/issue list --repo NVIDIA/SkillSpector --state all` 比對新工單，輸出
  `upstream-review-report.md`。`.github/workflows/upstream-check.yml` 每週一排程 +
  `workflow_dispatch` 跑一次，報告寫入 Actions Step Summary，有待審視項目就讓 job 失敗
  （不開 issue，讀 Step Summary 即可）。
- **依賴新鮮度**：`tools/check_dependency_freshness.py` 比對 `pyproject.toml` 宣告的
  Python 依賴（含 `mcp`、`langgraph-dev`、`dev` 三個 optional-dependencies 群組，PyPI 查
  最新版）與 `.github/workflows/*.yml` 釘選的 GitHub Action（GitHub Releases API），支援
  逐行 `# freshness-hold: <理由>` 標記與 `.github/dependency-deferrals.json`（`deferredLatest`
  過期即失效）兩種正當跳過方式。`.github/workflows/dependency-freshness.yml` 每月排程 +
  `workflow_dispatch`，額外列出目前開啟的 Dependabot PR。`tools/dev_check.ps1` 本機 gate
  也會跑一次（non-strict，只產 `dependency-freshness-report.md` 給人看，不因外部 API 連不上
  而擋 commit）。
- **Dependabot**：`.github/dependabot.yml` 涵蓋 `uv`（`pyproject.toml`/`uv.lock`）、
  `github-actions`、`npm`（`package.json`，pi extension 的 peer dependencies）、`docker`
  （`Dockerfile` 的 digest-pin base image）四個 ecosystem，每週檢查。
- **分岔與 pin bounds**：`tools/check_divergence.py` 強制 11 筆上游檔案分岔與
  `docs/DIVERGENCE.md` 一致；`tools/check_pin_bounds.py` 驗證 `uv.lock` 的直接依賴版本仍落在
  `pyproject.toml` 宣告範圍。兩者都進 `tools/dev_check.ps1`。
- **CodeQL**：`.github/workflows/codeql.yml` 對 Python 與 JavaScript/TypeScript 跑
  `security-extended`，push／PR／每週排程都啟用，權限限於讀內容與寫入 security events。

## 分支與 remote

- `origin/main`：SanHsien 維護線，也是唯一長期分支。
- 日常修改直接推 `origin/main`。不開功能分支、不開 PR；這是單人維護 fork，分支與 PR 沒有第二
  審查者，只增加同步成本。
- `upstream/main`：NVIDIA 原始專案，只追蹤、不推送、不 force-push、不刪除。

不要 `git push upstream`，不要 `gh pr create` 對 `NVIDIA/SkillSpector`。

## 上游同步怎麼做

`.github/workflows/upstream-check.yml` 每週一自動跑 `tools/check_upstream_updates.py`，
把新 commit／PR／issue 寫進 Actions Step Summary；有待審視項目時 job 會失敗，讀 Summary
即可，不需要另外開 issue。人工同步流程不變：

1. `git fetch upstream`（或直接跑 `python tools/check_upstream_updates.py` 看本機報告）。
2. `git log --oneline main..upstream/main` 看新 commit；上游有 GitHub Issues／PR，用
   `gh pr list --repo NVIDIA/SkillSpector --state all` 與 `gh issue list --repo
   NVIDIA/SkillSpector --state all` 輔助檢視。
3. 對每一筆決定「引用」或「不引用」，理由寫進 [`docs/DECISIONS.md`](docs/DECISIONS.md)。
4. 引用的話，`git cherry-pick` 或手動移植，保留原作者署名；跑完整驗證
   （`pwsh -File tools\dev_check.ps1`）再推。
5. 每一筆都決定完之後，更新 `tools/upstream_baseline.json` 的 `reviewed_through`
   （完整 40 碼 SHA，不可用縮寫）、`reviewed_pr_through`、`reviewed_issue_through`、
   `reviewed_date`，讓水位反映實際審視到的位置——只推進部分軸會讓另一軸的報告失真。

上游要求每筆 commit 附 DCO `Signed-off-by`（`git commit -s`），見
[`CONTRIBUTING.md`](CONTRIBUTING.md)；回貢上游時同樣要照做。

## 換一台電腦怎麼開發

```powershell
git clone https://github.com/SanHsien/SkillSpector.git
cd SkillSpector
uv sync --all-extras
pwsh -File tools\dev_check.ps1
```

只想跑 CLI、不開發維護工具時，見 [`README.md`](README.md) 的「快速開始」章節。
