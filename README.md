[English](README.en.md) ｜ 繁體中文

# SkillSpector

> **這是 [`NVIDIA/SkillSpector`](https://github.com/NVIDIA/SkillSpector) 的 Windows-first 維護型
> fork**，沿用 Apache License 2.0 與完整 Git 歷史。產品行為跟隨上游；本維護線補上繁中文件、
> Windows 開發／驗收 gate。差異見 [`FORK.md`](FORK.md)，維護決策見
> [`docs/DECISIONS.md`](docs/DECISIONS.md)。

**AI agent skills 的安全掃描器。** 在安裝 agent skill 之前，先檢出漏洞、惡意樣式與安全風險。

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## 這是什麼

AI agent skill（Claude Code、Codex CLI、Gemini CLI 等都在用）預設是隱含信任、幾乎沒有審查地
被執行。研究顯示 **26.1% 的 skill 帶有漏洞**，**5.2% 顯示出疑似惡意意圖**。

SkillSpector 回答的問題是：**「這個 skill 裝了安全嗎？」**——用靜態規則比對（regex、AST、
YARA）加上可選的 LLM 語意分析，掃描 Git repo、URL、zip 檔、目錄或單一檔案，輸出 0–100 的風險
分數與建議（`SAFE`／`CAUTION`／`DO_NOT_INSTALL`）。完整的偵測樣式清單（71 條規則、17 個分類）、
風險計分公式、環境變數與 CLI 選項見英文原版 [`README.en.md`](README.en.md)；本檔只涵蓋在
Windows 上安裝、跑起來、驗證的最短路徑。

兩個對 Claude Code 使用者最直接的入口：

- [`skills/skill-inspector/SKILL.md`](skills/skill-inspector/SKILL.md) —— 把 SkillSpector 本身
  包成一個 Claude Code skill，讓 agent 在對話裡直接呼叫掃描。
- [`src/skillspector/mcp_server.py`](src/skillspector/mcp_server.py) —— 跑成 MCP server
  （`skillspector mcp`），讓任何支援 MCP 的 agent 把掃描結果當成安裝閘門。

## 快速開始（Windows，uv）

需要 Python `>=3.12,<3.15`（已用 [uv](https://docs.astral.sh/uv/) 驗證）。

```powershell
git clone https://github.com/SanHsien/SkillSpector.git
cd SkillSpector
uv sync --all-extras          # 安裝含 dev、mcp、langgraph-dev 三個 extras
uv run skillspector --version # 應輸出 SkillSpector v2.12.0
uv run skillspector scan .\my-skill\
```

只裝 CLI、不進開發環境：

```powershell
uv tool install git+https://github.com/SanHsien/SkillSpector.git
```

要跑 `skillspector mcp`（MCP server），額外裝 `mcp` extra：

```powershell
uv tool install "skillspector[mcp] @ git+https://github.com/SanHsien/SkillSpector.git"
skillspector mcp
```

其餘安裝方式（Docker、pip 路徑）、輸出格式、LLM provider 設定、baseline 抑制誤報、MCP server
的信任模型，見英文原版 [`README.en.md`](README.en.md)。

## 驗證

上游的 `Makefile` 是 POSIX sh 語法（`command -v`、`rm -rf`、`find`），在 Windows 原生（非
WSL2）跑不動，所以本 fork 另外提供一支 PowerShell gate，**繞過 `Makefile` 直接呼叫
`uv`／`ruff`／`pytest`**，不是包裝 `make`：

```powershell
pwsh -File tools\dev_check.ps1 -Quick   # ruff check + ruff format --check + --version 煙霧測試
pwsh -File tools\dev_check.ps1          # 上面再加 pytest（排除 integration／provider 兩個 marker）
```

本機 Windows 已實測 `tools/dev_check.ps1`（上游 2.12.0）：
**15001 passed / 0 failed / 427 skipped**。上游測試對 POSIX 的假設在 Windows 上造成的紅燈，
本 fork 已逐筆處理，判準與方式見 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。跳過的測試都是
執行期能力探測的結果：symlink、FIFO、`os.geteuid`、shebang 腳本、執行權限位元，以及 2.12.0 起
產品在 Windows 上刻意拒絕 `--output` 寫檔（沒有 `O_NOFOLLOW`／`dir_fd`，請改用 stdout 導向）。
開啟 Windows 開發人員模式後 symlink 相關的測試會自動恢復執行。

> **不要從 PyPI 安裝 `skillspector`。** PyPI 上曾有冒充 NVIDIA 版本、夾帶預設開啟遙測的惡意套件
> （OSV `MAL-2026-6561`，0.0.1–2.3.10，已下架）。本 fork 一律以 git URL 釘精確 commit 安裝。

## 相關工具

這五個 repo 各自治理 AI coding 的一層，可以單獨用，也可以疊起來用：

| 層 | Repo | 做什麼 |
| --- | --- | --- |
| 供應鏈 | **SkillSpector（你在這裡）** | 裝進來之前先掃：agent skill 的漏洞與惡意樣式偵測，輸出風險分數與 `SAFE`／`CAUTION`／`DO_NOT_INSTALL` 建議 |
| 派工決策 | [agent-advisor](https://github.com/SanHsien/agent-advisor) | 風險分流路由 `solo`／`delegate`／`audit`／`full`：決定這件事要不要派工、派給誰 |
| 動作攔截 | [harness-guard](https://github.com/SanHsien/harness-guard) | agent runtime hook，在動手前後與收工時實際攔截危險指令、無證據宣稱、紅燈提交 |
| 產出品質 | [ai-quality-gates](https://github.com/SanHsien/ai-quality-gates) | 可執行規格與量化門檻：覆蓋率、突變測試、圈複雜度、依賴結構、有界 loop policy |
| 交付流程 | [paulsha-cortex](https://github.com/SanHsien/paulsha-cortex) | 多 Agent lifecycle：Candidate → Verify → Independent Review → Delivery → CompletionRecord |

相鄰但不同層：[agent-governance-toolkit](https://github.com/SanHsien/agent-governance-toolkit) 治理的是上線後自主運行的 agent——政策強制、零信任身分、沙箱執行與可稽核記錄——不是寫程式的 coding agent。[opencodex](https://github.com/SanHsien/opencodex) 是供應商代理，決定這些 agent 背後能跑哪些 LLM，本身不約束 agent 行為。

## 多 Agent 流水線

本 repo 是 [agent-relay](https://github.com/SanHsien/agent-relay) 多 Agent 派工與驗收流水線的一環（角色：技能供應鏈掃描）。與 agent-relay 的整合規劃中（Phase 3）。協定規格與所有相關 repo 的總目錄見 agent-relay。

## 授權

原始著作權 2026 NVIDIA CORPORATION & AFFILIATES，以 [Apache License 2.0](./LICENSE) 授權；
上游自己的第三方套件授權清單見 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。本 fork 的
授權與來源說明見 [`NOTICE.md`](NOTICE.md)。上游 CI 要求每筆 commit 都有 DCO sign-off
（`git commit -s`），回貢前務必確認。
