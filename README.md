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
uv run skillspector --version # 應輸出 SkillSpector v2.11.0
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

本機 Windows 已實測 `uv run pytest -m "not integration and not provider" tests/`：
**3953 passed / 0 failed / 39 skipped**。上游原始碼在 Windows 上有 23 筆測試紅燈（全部是
測試對 POSIX 的假設，不是產品行為錯誤），本 fork 已逐筆處理，判準與方式見
[`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。跳過的 39 筆是執行期能力探測的結果
（symlink、FIFO、`os.geteuid`、PATH 上的 shebang 腳本），開啟 Windows 開發人員模式後
symlink 相關的測試會自動恢復執行。

## 授權

原始著作權 2026 NVIDIA CORPORATION & AFFILIATES，以 [Apache License 2.0](./LICENSE) 授權；
上游自己的第三方套件授權清單見 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。本 fork 的
授權與來源說明見 [`NOTICE.md`](NOTICE.md)。上游 CI 要求每筆 commit 都有 DCO sign-off
（`git commit -s`），回貢前務必確認。
