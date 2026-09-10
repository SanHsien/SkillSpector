# AGENTS.md

本檔是所有 AI coding agent（Claude Code、Cursor、Copilot 等）在 `SanHsien/SkillSpector` 這個
fork 工作時的**單一真相源**。`CLAUDE.md` 只放一段指回本檔的薄指標，不重複這裡的規則；上游
`NVIDIA/SkillSpector` 沒有 `AGENTS.md` 或 `CLAUDE.md`，兩者都是這條維護線自己建立的。

## 這個 repo 是什麼

AI agent skill 的安全掃描器：對 Git repo、URL、zip 檔、目錄或單一檔案跑一個以
[LangGraph](https://github.com/langchain-ai/langgraph) 定義的分析流程，輸出風險分數
（0–100）、嚴重度與建議（`SAFE`／`CAUTION`／`DO_NOT_INSTALL`），格式為 terminal／JSON／
Markdown／SARIF 2.1.0。兩階段分析：Stage 1 靜態（11 個 regex 分析器 + AST 行為分析 +
YARA 簽章 + OSV.dev 即時 CVE 查詢），Stage 2 可選的 LLM 語意分析（過濾誤報、給人類可讀解釋）。
完整介面說明見 [`README.en.md`](README.en.md)（上游持有的原檔）、
[`README.md`](README.md)（本 fork 的繁中版）與 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
（架構深入）。

### 目錄速查

- `src/skillspector/graph.py`：LangGraph 工作流程入口（`resolve_input` → 平行分析器 →
  `meta_analyzer`（LLM）→ report）。
- `src/skillspector/nodes/`：各分析器節點；`state.py` 定義流程間傳遞的 `SkillspectorState`。
- `src/skillspector/cli.py`：`skillspector` CLI（`scan`、`baseline` 等子命令）。
- `src/skillspector/mcp_server.py`：`skillspector mcp` 的 MCP server 實作，讓任何 MCP-capable
  agent 把掃描結果當安裝閘門。
- `src/skillspector/providers/`：各 LLM provider 的介接（`openai`／`anthropic`／`bedrock`／
  `nv_build`／`claude_cli`／`codex_cli` 等）與各自的 `model_registry.yaml`。
- `skills/skill-inspector/SKILL.md`：把 SkillSpector 包成 Claude Code skill 的入口。
- `contrib/batch_scan/`：平行批次掃描一整個目錄的 skill。
- `tests/`：`unit/`、`integration/`（標記 `integration`，可能呼叫 LLM）、`provider/`
  （標記 `provider`，打真實 provider endpoint）；`pyproject.toml` 的 `addopts` 預設排除
  這兩個 marker。
- `docs/`：`DEVELOPMENT.md`（架構深入）、`ANALYSIS_RESOURCE_BOUNDS.md`、`SUPPRESSION.md`
  （baseline 抑制誤報）、`INFERENCE_USAGE.md`（LLM 用量遙測契約）等。

### 慣例（沿用上游，不因本 fork 改變）

- Python `>=3.12,<3.15`；`ruff`（設定在 `pyproject.toml` 的 `[tool.ruff]`，非獨立
  `ruff.toml`）；`mypy`（`disallow_untyped_defs = true`）；`pydantic` schema。
- 新增的 `.py` 檔案要有 SPDX 授權表頭（`SPDX-FileCopyrightText`／
  `SPDX-License-Identifier: Apache-2.0`），見任一既有原始檔開頭。
- 測試用 `pytest`，`asyncio_mode = "auto"`；`integration`／`provider` 兩個 marker 預設不跑
  （見 `pyproject.toml` 的 `addopts`）。
- 上游 CI 要求每筆 commit 附 DCO `Signed-off-by`（`git commit -s`），見
  [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## Fork 維護規則（SanHsien 維護線）

> 本節只適用於 `SanHsien/SkillSpector`（本 fork）。上游 `NVIDIA/SkillSpector` 沒有這一節。

- **對外只打 `origin`**：commit、push、release 一律指向 `SanHsien/SkillSpector`，唯一例外是
  維護者在**當次對話**明確同意回貢上游。`gh` 在 fork clone 的預設 repo 就是上游，先
  `gh repo set-default SanHsien/SkillSpector`；`.cursor/rules/no-upstream-pr.mdc` 有機器可讀
  版本。
- **不開分支、不開 PR**：日常修改驗證通過後直接推 `origin/main`；`upstream/main` 只 fetch、
  不推送、不 force-push、不刪除。
- **Windows 開發環境**：`uv sync --all-extras` 裝好含 `dev`／`mcp`／`langgraph-dev` 三個
  extras 的完整開發環境。上游的 `Makefile` 是 POSIX sh 語法（`command -v`、`rm -rf`、
  `find`），在 Windows 原生（非 WSL2）跑不動；本 fork 的 canonical gate 是
  [`tools/dev_check.ps1`](tools/dev_check.ps1)，繞過 `Makefile` 直接呼叫
  `uv`／`ruff`／`pytest`。
- **Windows 本機與 CI 的 canonical gate**：`tools/dev_check.ps1 -Quick` 跑
  Ruff check／format → CLI version smoke → 分岔登記與鎖定依賴邊界檢查 →
  dependency freshness report；不帶 `-Quick` 的完整模式再加
  `uv run pytest -m "not integration and not provider" tests/ -q`。
- **⚠️ 虛擬環境放在 OneDrive 外，並用複製模式安裝**：本 repo 位於 OneDrive 底下，`.venv`
  的目錄會變成 Files On-Demand 佔位目錄（`ReparsePoint`），版本號一變，`uv sync` 刪舊
  `dist-info` 時就 `存取被拒 (os error 5)`；uv 預設的硬連結安裝還會讓快取檔被雲端過濾器認領，
  之後連 OneDrive 外的 venv 也裝不上（`os error 396`），留下「有 metadata、沒模組」的半殘
  套件（2026-09-11 實測 `jsonpatch`，pytest 收集階段 75 個錯誤）。**不要**用 `setx` 設全域
  `UV_PROJECT_ENVIRONMENT`——2026-09-06 就是全域值讓所有 uv 專案共用一個 venv，假造出 23 筆
  與程式碼無關的紅燈（該全域值已移除）。每個指令前面帶上
  `UV_PROJECT_ENVIRONMENT='C:\tmp\skillspector-fork-venv' UV_LINK_MODE=copy`，例：
  `UV_PROJECT_ENVIRONMENT='C:\tmp\skillspector-fork-venv' UV_LINK_MODE=copy uv run --python 3.13 pytest -m "not integration and not provider" tests/ -q`。
  套件半殘時用 `uv sync --all-extras --reinstall-package <名稱>` 修。在這個環境以外跑出的紅燈
  可能是環境造成的，不能直接當成回歸證據。
- **Windows 全綠是完成判準**：本機 Windows 執行
  `uv run pytest -m "not integration and not provider" tests/` 目前為
  **4009 passed / 0 failed / 39 skipped / 38 deselected / 4 xfailed**（2026-09-11，上游 2.11.2）。原本的 23 筆紅燈已全部處理，逐筆判準登記於
  [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。**不要接受任何新的紅燈**：出現紅燈就是回歸，
  不是「已知的 Windows 落差」。跳過的 39 筆全部由 `tests/platform_support.py` 的能力探測
  決定（symlink／FIFO／`os.geteuid`／PATH 上的 shebang 腳本），不是 `sys.platform` 硬判。
- **產品內容以上游為準**：`src/skillspector/`、`tests/`、`skills/`、`contrib/`、
  `extensions/`、`docs/{ANALYSIS_RESOURCE_BOUNDS,DEVELOPMENT,SUPPRESSION,...}.md`、
  `Makefile`、`pyproject.toml`、`uv.lock`、`LICENSE`、`SECURITY.md`、`CONTRIBUTING.md`、
  `CHANGELOG.md`、`THIRD_PARTY_NOTICES.md`、`.github/workflows/*` 不因本線維護需求改寫，
  除非有已記錄在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md) 的 fork 修正。
- **文件語言**：本 fork 新增的維護文件（本檔、`FORK.md`、`NOTICE.md`、`README.md`、
  `CHANGELOG.zh-TW.md`、`docs/DECISIONS.md` 等）用繁體中文；產品程式碼、CLI 輸出、測試的
  語言跟隨上游（英文），不因本線需求翻譯。
- **測試綠了才准提交**：`pytest -m "not integration and not provider" tests/ -q`、
  `ruff check src/ tests/`、`ruff format --check src/ tests/` 都通過，才能 `git commit` 再
  `git push origin main`；不可用 `;` 把驗證與 commit 串成一行繞過檢查。已知的 Windows
  平台落差（見上）在登記於 `docs/DIVERGENCE.md` 前不算「綠燈」的例外理由。
- **上游同步**：水位追蹤已機器化。`uv run python tools/check_upstream_updates.py` 讀
  `tools/upstream_baseline.json` 的 commit／PR／issue 三軸水位並輸出
  `upstream-review-report.md`；`.github/workflows/upstream-check.yml` 每週排程一次。
  決策記錄見 [`docs/DECISIONS.md`](docs/DECISIONS.md)，流程見 [`FORK.md`](FORK.md)。
