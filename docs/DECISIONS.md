# 維護決策

本檔記錄 `SanHsien/SkillSpector` 這條維護線的維護決策（為什麼這樣做、限制是什麼），依時間
排序，新的加在最下面。

## 2026-09-05：建立 Windows-first 維護型 fork

**決定**：fork `NVIDIA/SkillSpector`，保留 Apache License 2.0 與完整 Git 歷史，預設分支維持
`main` 以降低與上游同步摩擦。本線聚焦繁中公開入口與 Windows 開發／驗收 gate。

**理由**：上游是一個設計完整的 AI agent skill 安全掃描器（71 條偵測樣式、17 個分類、靜態＋
LLM 兩階段分析、MCP server、Claude Code skill），符合維護者用 Claude Code 生態需要安裝前
安全審查工具的需求。缺的是 Windows 11 上可重現的開發／驗收骨架（上游 `Makefile` 是 POSIX sh
語法，Windows 原生跑不動）與繁中入口。授權是 Apache License 2.0，fork 修改同樣走 Apache 2.0
（見 `NOTICE.md`）。

**限制**：

- 不把 fork 包裝成原創專案，不移除 NVIDIA 的著作權與 Apache 2.0 標示。
- `src/skillspector/`、`tests/`、`skills/`、`contrib/`、`extensions/`、
  `docs/{ANALYSIS_RESOURCE_BOUNDS,DEVELOPMENT,SUPPRESSION,...}.md`、`Makefile`、
  `pyproject.toml`、`uv.lock`、`.github/workflows/*` 保持產品內容，不用維護索引覆寫。
- 不回貢，除非維護者在當次對話明確同意；上游要求每筆 commit 附 DCO `Signed-off-by`，回貢
  門檻因此更高。
- 上游同步自動化（水位追蹤、Dependabot、依賴新鮮度）已於同日補齊，見下方 2026-09-05
  「補齊上游同步與依賴新鮮度自動化」一則；仍缺分岔機器檢查與 pin-bounds 檢查。

## 2026-09-05：`tools/dev_check.ps1` 繞過 `Makefile`，不包裝它

**決定**：Windows 本機／CI 的 canonical gate 直接呼叫 `uv run ruff` / `uv run pytest` /
`uv run skillspector`，不透過 `make` 目標。

**理由**：上游 `Makefile` 用 `command -v`、`rm -rf`、`find` 等 POSIX sh 語法，在 Windows 原生
（非 WSL2）的 PowerShell 或 cmd 底下無法直接執行；`make` 本身在 Windows 也不是標準內建工具。
與其要求維護者額外裝 GNU Make 或切到 WSL2，不如讓 gate 腳本直接呼叫底層工具鏈，效果與
`make lint` / `make test` 等價但可在原生 Windows 跑。

**限制**：`Makefile` 本身不變（不在允許修改清單內）；`tools/dev_check.ps1` 是平行的 Windows
入口，不是 `make` 的取代品——Linux/macOS 開發者仍然用 `make`。兩者跑的底層指令若未來分岔
（例如 `Makefile` 新增一個步驟），要手動同步進 `tools/dev_check.ps1`，目前沒有機器檢查兩者
一致。

## 2026-09-05：補齊上游同步與依賴新鮮度自動化

**決定**：移植 `tools/upstream_baseline.json` + `tools/check_upstream_updates.py`
（commit／PR／issue 三軸水位，`--state all` 查詢，避免「開了又關」的工單被漏掉）、
`tools/check_dependency_freshness.py`（比對 `pyproject.toml` 宣告的 Python 依賴與
`.github/workflows/*.yml` 釘選的 GitHub Action）、`.github/dependabot.yml`
（`uv`／`github-actions`／`npm`／`docker` 四個 ecosystem）與對應的兩個排程 workflow，
把 `FORK.md` 原本列為待辦的維護自動化項目做掉。

**理由**：fork 建立當下 HEAD 剛好與 `upstream/main` 一致
（`7805bb94843d91cb9937f57264ca52642164499b`），是記錄水位起點最乾淨的時機；晚一步
再建就要回頭考古哪個 commit 才是真正的分岔點。腳本沿用 `agent-skills` 與
`agentdeck` 兩條維護線已經跑過的版本，只把依賴掃描的資料來源從
`requirements-dev.txt` 換成這個 repo 實際使用的 `pyproject.toml`
（`[project.dependencies]` 加三個 `optional-dependencies` 群組），其餘邏輯原樣移植。

**限制**：

- 兩個新排程 workflow 用「job 失敗 + 讀 Actions Step Summary」當提醒機制，跟
  `agent-skills` 一致；不另外開 issue。
- `tools/dev_check.ps1` 只在本機跑 non-strict 的依賴新鮮度檢查（產報告，不因為連不上
  PyPI／GitHub Releases 而擋 commit）；`--strict` 只用在排程 workflow 裡。
- `tools/check_divergence.py`、`tools/check_pin_bounds.py`、
  `.github/workflows/codeql.yml` 仍未移植，留給後續 session。

## 2026-09-05：把 Windows 的 23 筆紅燈修到零，分兩類處理

**決定**：本機 Windows 全套測試從 3943 passed / 23 failed 變成 3953 passed / 0 failed /
39 skipped。處理原則寫死成兩類，逐筆登記在 [`DIVERGENCE.md`](DIVERGENCE.md)：

1. **兩個平台都成立的，改測試條件**——顯式 `encoding="utf-8"`、顯式 LF、比對 `str(Path(...))`
   而非硬寫 POSIX 分隔符、把 Windows 實際走的程式路徑（handle-based opener）也一併攔截。
   這類不損失覆蓋率，而且在 Linux 上同樣正確。
2. **平台根本沒有那個能力的，用能力探測跳過**——symlink、FIFO、`os.geteuid`、PATH 上的
   shebang 腳本。共 13 個測試。

**理由**：23 筆紅燈沒有一筆是產品在 Windows 上行為錯誤，全部是測試對 POSIX 的假設。把它們
留著紅，等於讓本機 gate 永遠無法當成完成判準——「23 紅是正常的」這種基準線一旦成立，真正的
迴歸就再也看不出來。

**限制與判準**：

- **能力探測，不是 `sys.platform` 判斷**。探測集中在 `tests/platform_support.py`（fork 新增
  檔案，不是分岔）。差別在於：Windows 開啟 Developer Mode 後 symlink 測試會自己恢復執行，
  不需要有人記得回來改碼。用 `sys.platform` 就會永久關閉。
- **只有一筆動到產品端**：`scripts/compare_scan_accuracy.py` 的 `file://` URL 轉路徑用
  `urllib.parse.unquote` 而非 `urllib.request.url2pathname`，在 Windows 上算出 `C:\C:\...`。
  這是上游的真實可攜性 bug，也是唯一值得單獨回貢的一筆（需維護者當次對話明確同意）。
- **不碰 `src/skillspector/`**。若哪天 Windows 紅燈的根因真的落在產品程式碼，先在
  `DIVERGENCE.md` 記錄現象並回報上游，不要在 fork 裡默默改產品行為。

## 2026-09-05：依賴新鮮度報告對本 fork 是資訊性的，不是待辦清單

**決定**：`tools/check_dependency_freshness.py` 對 `pyproject.toml` 的 25 列 `REVIEW UPDATE`
不視為需要行動的紅線。本 fork 的可行動範圍只有自己持有的 workflow 裡釘選的 GitHub Action。

**理由**：上游 `pyproject.toml` 宣告的是相容性**下限**（`typer>=0.23.0`、`rich>=14.3.0`……），
不是釘選版本。下限落後於 PyPI 最新版是宣告方式的必然結果，不是過期。本 fork 不持有
`pyproject.toml`，把下限往上抬等於替上游做相容性承諾——而且下一次同步就會被覆蓋回去。
真正決定本機跑什麼版本的是 `uv.lock`，而這支腳本明說不檢查 lock 檔。

**限制**：這條**不適用**於安全性通報。`pyproject.toml` 的某個依賴出現 advisory 時，照
[`SECURITY.md`](../SECURITY.md) 的流程走，必要時在 `DIVERGENCE.md` 登記一筆例外並附產物比對
證據；不要拿本條當作不處理 CVE 的理由。

## 2026-09-09：把「資訊性」寫進 gate，而不是只寫在文件裡

**決定**：`dependency-freshness` workflow 只對 **fork 持有的宣告** 失敗。實作是
`check_dependency_freshness.py` 的 `gating_rows()`：`pyproject.toml` 的所有列、以及任何出現在
上游持有 workflow（`ci.yml`、`release.yml`、`scorecard.yml`、`update-pr-branches.yml`）裡的
Action pin，一律只顯示不擋。

**理由**：上一條（2026-09-05）已經判定那 25 列是資訊性的，但**判定只寫在文件裡，gate 沒有跟著改**，
於是 workflow 從 `b02d8ae` 起每次都紅。一個永遠紅又沒有出口的檢查，實際效果是訓練所有人忽略它——
包含那幾列真正可行動的。上游 workflow 裡的 pin 與 `pyproject.toml` 的下限是同一種東西：不是本 fork
的承諾，改了下次同步也會被蓋回去。

**限制**：不適用於安全性通報（照 [`../SECURITY.md`](../SECURITY.md)）。`UPSTREAM_WORKFLOWS` 是常數，
靠 `test_fork_owned_workflows_matches_git` 對 baseline commit 的 `git ls-tree` 交叉核對防止漂移；
該測試在拿不到 baseline commit 的 checkout 會 skip，不會假綠。

## 2026-09-06：補齊 divergence、pin-bounds 與 CodeQL

**決定**：新增兩支 stdlib／既有依賴即可執行的維護 gate，並納入 `tools/dev_check.ps1`：
`check_divergence.py` 對 baseline SHA 的上游持有檔案做集合相等檢查；`check_pin_bounds.py` 用
`packaging.Requirement` 驗證 `uv.lock` 中 28 個直接依賴版本符合 `pyproject.toml`。另新增 Python
與 JavaScript/TypeScript 的 CodeQL `security-extended` workflow。

**理由**：人工 divergence 表會漂移；依賴下限與實際 lock 版本是兩種不同承諾；Scorecard 只上傳
自己的 SARIF，不能取代 CodeQL。三者各補一個既有 gate 沒有覆蓋的面向。

**限制**：divergence 只掃 baseline 已存在的上游檔案，fork 新增檔不登記；pin-bounds 只驗直接
依賴，不替代 `uv lock --check` 或 CVE 掃描；CodeQL 不啟用自動修復或寫入 repo。

## 2026-09-06：PR #463–#486 與 issue #2–#485 首輪水位

15 筆新 PR 全部讀過檔案範圍；除 #486 已在本 fork 採用外，其餘仍 open，維持等待上游合併：

| PR | 判定 | 範圍／觸發點 |
|---|---|---|
| #463 | 等上游 | CLI provider registry override；合併後同步，對應 issue #459 |
| #465 | 等上游 | bare shell variable parse bounds；對應 #464 |
| #466 | 等上游後重解 | 新增上游 `CLAUDE.md`，會碰本 fork 的薄指標政策 |
| #467 | 等上游 | recursive JSON stdout；對應 #449 |
| #468 | 等上游 | configurable workflow deadline；對應 #460；本 fork 僅在 oversized tests 注入測試額度 |
| #469 | 等上游 | `--fail-on-findings`；對應 #448 |
| #470 | 等上游 | letter-spaced P3/P4 靜態繞過，維持安全高優先 |
| #471 | 等上游 | SKILL.md BOM 與多處 analyzer 邊界 |
| #473 | 等上游 | 非 Markdown bidi control（CVE-2021-42574） |
| #474 | 等上游 | RP3 manifest version projection；對應 #472 |
| #476 | 等上游 | README 的 AS1–AS3 文件 |
| #480 | 等上游 | JS module／PHP suffix executable classification |
| #483 | 等上游 | E2 grep flags／quoting；對應 #482 |
| #484 | 等上游 | Windows 8.3 short path 展開；對應 #481 |
| #486 | 已採用 | `file://` editable dependency 改用 `url2pathname`；本 fork 既有分岔，對應 #485 |

issue 水位不是以「看過標題」草率歸零：截至 #485 共 190 筆，137 筆已由 upstream 關閉
（134 `COMPLETED`；#48、#109、#199 為 `NOT_PLANNED`），其餘 53 筆仍 open，依責任面完整列號：

- provider／LLM：#8、#10、#69、#90、#129、#296、#303、#304、#334、#433、#435、#456、
  #459、#460。
- static／security：#171、#181、#268、#297、#363、#367、#389、#413、#419、#440、#441、
  #444、#445、#446、#458、#464、#472、#475、#477、#478、#479、#482。
- CLI／report／platform／產品方向：#33、#37、#72、#121、#130、#212、#226、#271、#277、
  #314、#326、#335、#448、#449、#450、#481、#485。

這 53 筆不是 fork 待辦清單：核心產品以上游為準；與 open PR 對應者等合併，其餘在上游狀態或
head 改變、或本 fork 實際重現時再評估。水位推進只表示本輪已分類，不表示問題已解決。
