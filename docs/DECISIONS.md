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

## 2026-09-11：同步上游 2.11.2，`state.py` 的整體預算覆寫改採上游

**決定**：合併 `upstream/main`（`69dcdfb`，19 個 commit，含 2.11.1、2.11.2）。唯一衝突
`src/skillspector/state.py` 整份採用上游並刪除其分岔登記列；`tools/upstream_baseline.json` 的
commit 軸推進到 `69dcdfb`，PR／issue 軸不動。下游關卡的兩個預算值由 `"0"` 改為 `"86400"`。

**理由**：上游 #468 用**同一個變數名** `SKILLSPECTOR_MAX_WORKFLOW_SECONDS` 做了同一件事，
而且比本 fork `185d610` 完整——驗證有限正值，並把 transitive 預算（`cli.py` 的
`_TRANSITIVE_MAX_SECONDS`）一起接上。那一列登記時就寫了「上游若自行加了同名或同義的覆寫就刪掉本列」，
這次是照預先寫好的判準執行，不是重新判斷。但**語意不同**：上游把 `0`／負數／`nan` 視為無效、
警告後退回 600 秒預設，本 fork 原本把 `<= 0` 當成解除上限。下游關卡若維持 `"0"`，換成上游
版本後會**靜默**變成 600 秒——正是當初要消除的「看起來解除了、實際沒有」。`86400` 在兩種語意下
都代表同一件事。另外 2.11.2 是安全性版本，下游用 `requirements-security.txt` 釘在舊 commit 的
掃描器把關，等於缺修正；這是這次不等 PR 分診、先推 commit 軸的原因。

**限制**：

- PR 軸（#487 起）與 issue 軸（#486 起）**沒有**跟著推，`reviewed_*_through` 仍只表示分類到哪。
- 每檔的 `SKILLSPECTOR_MAX_STATIC_SECONDS` 仍是本 fork 獨有、`<= 0` 解除；回貢時要改成對齊上游的
  「只收正有限值」語意。
- 本機驗證要在 OneDrive 外的 venv 以 `UV_LINK_MODE=copy` 跑（見 `AGENTS.md`）；在 repo 內
  `.venv` 跑出來的紅燈可能是環境造成的，不能當成回歸證據。

## 2026-09-11（同日第二輪）：PR #488–#527 與 issue #486–#524 首輪水位

`git log upstream/main` 沒有新 commit（仍是 `69dcdfb`），commit 軸不動。PR／issue 軸用
`python tools/check_upstream_updates.py --strict` 列出 31 筆新 PR、10 筆新 issue，逐筆讀
`gh pr view --json files/body` 或 diff 後判定。

**已透過同步採用（4 筆，`git merge-base --is-ancestor <mergeCommit> HEAD` 驗證為 true）**：

| PR | mergeCommit | 說明 |
|---|---|---|
| #493 | `704bc95` | release: 2.11.1，已隨 2026-09-11 第一輪同步進 `main` |
| #507 | `a7dfab7` | fix: 修正 CI reference completeness，已在 `main` |
| #508 | `f5bb619` | fix: printf runtime path accounting，已在 `main` |
| #511 | `69dcdfb` | release: 2.11.2，即目前 `reviewed_through` 本身 |

**merge 但未進 `main`（1 筆，需要單獨判定，不算「已透過同步採用」）**：

- **#521**（`codex/linear-json-quote-scan`）：`gh pr view` 顯示已 MERGED，但
  `baseRefName` 是 `codex/fix-documentation-analysis-limits`——也就是仍 open 的 #516 的
  head branch，不是 `main`；`git merge-base --is-ancestor d3dd543... upstream/main` 回傳
  false，確認程式碼只存在於那條未合併的 stack 裡。判定：與 #516 同組，**等上游合併**
  （#516 合併時 #521 一併進來）。

**其餘 26 筆 PR 判定：等上游合併**（無一筆採用），理由分組如下：

| PR | 對應 issue | 一句話理由 |
|---|---|---|
| #488 / #489 | #487 | YARA webshell 樣式誤判（德文 "behindert"／"WSO " 散文），兩筆疊加嘗試，上游還沒收斂到一條 |
| #490 | #485 | 見下方專節——延伸本 fork 自己開的 #486 |
| #491 | — | 12+ 個 static analyzer 檔的樣式跨段落誤連修正，核心規則橫向改動，跟 #409 同類型風險 |
| #492 | — | E2 子行程環境變數豁免，單一分析器規則調整，範圍小但仍是核心偵測邏輯 |
| #496 | #494 | Gemini provider 功能新增（20+ 檔），本 fork 定位是 Windows 骨架不承接功能擴充，與 NIM provider（`upstream-review/feature-nvidia-nim-integration`）同一類判定 |
| #497 | — | 24 個檔案的 Python 執行介面 shell truthiness 覆蓋率修正，核心分析器大改動 |
| #498 | — | 新增一整個 "offline security inspection plugin"（80+ 檔，含 runtime/drift/policy），大型功能擴充，不適用 |
| #499 | #495 | recursive scan 靜默跳過 symlinked skill 但回報 `analysis_completeness: complete`，MCP 判定正確性問題，範圍小（2 檔）但仍是核心邏輯 |
| #501–#505、#518 | — | 見下方專節——直接對應本 fork 已登記的 Windows test 分岔列 |
| #506 | #500 | AS3 誤判 skill 自我參照，規則檔小範圍修正 |
| #509 | — | 過大檔案不得產生零 finding 報告（LLM 階段納入＋AE7 覆蓋率 finding），核心 ledger／build_context 邏輯 |
| #513 | #512 | P6 誤判 HTML「輸出規則」文件標題，8 檔（含新增 `llm_utils.py` 邏輯） |
| #514 | — | printf 重建保持不完整，7 檔，runtime reconstruction 核心邏輯 |
| #516 / #521 | #515 | 文件裡的 code span／JSON placeholder 誤觸發不完整分析，11 檔＋疊加的 #521，同一條 stack |
| #517 | — | `__dict__` subscript 應標記為 reflective attribute access，2 檔小範圍 |
| #520 | #519 | LLM 呼叫在動態 deadline 下每次重建 client 導致 httpx pool 洩漏／`Event loop is closed`，健壯性修正 |
| #522 | — | 見下方專節 |
| #525 | #524 | 引號包住的版本號被誤判成缺檔參照，2 檔小範圍 |
| #526 | #510 | 無法解析的參照不該擋住 `safe_to_install`，2 檔小範圍 |
| #527 | — | 環境變數選擇的 Bedrock provider 未被視為可用 LLM，3 檔 provider 邏輯修正 |

判定理由統一套用 `FORK.md`「回貢判準」與本檔既有原則：核心分析器／掃描 pipeline／provider
邏輯一律等上游合併（風險與 `#409`/`#410` 同類）；功能擴充（#496 Gemini、#498 offline plugin）
不承接，理由與 NIM provider 判定一致；只有測試檔／維護工具且能證明本 fork 已踩到同一缺陷的
才落入可採用的例外，而這一輪唯一落在例外範圍內的候選（#501–#505、#518）判定為「等合併」而非
立即採用，理由見下方專節。

### #522 `codex/configurable-static-analysis-budget` vs. 本 fork `SKILLSPECTOR_MAX_STATIC_SECONDS`

**不是同名變數，語意也不同**——這是本輪最需要記住的一筆：

| | 本 fork（`static_runner.py` 既有分岔） | 上游 #522 |
|---|---|---|
| 環境變數名 | `SKILLSPECTOR_MAX_STATIC_SECONDS` | `SKILLSPECTOR_MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT` |
| 預設值 | 30 秒（不變） | **300 秒**（上調 10 倍） |
| 無效／`<=0`／非有限值 | 視為「解除上限」，實作成 86400 秒 | 一律警告後退回預設（300 秒），**沒有「解除上限」這個概念** |
| 影響範圍 | `static_runner.py` + `static_yara.py` 共用同一個模組層級常數 | 同左，做法（模組匯入時讀環境變數）相同 |

**合併時本 fork 必須做的事**：

1. **不能只採用上游版本了事**。三個下游 repo（`agent-skills`／`book-to-skill`／
   `marketingskills`）目前設的是 `SKILLSPECTOR_MAX_STATIC_SECONDS=86400` 或 `300`。上游版本
   讀的是不同的變數名，若照上游整份取代，下游那個環境變數會被**靜默忽略**、有效值退回
   300 秒預設——這正是 2026-09-11 第一輪同步處理 `SKILLSPECTOR_MAX_WORKFLOW_SECONDS` 時
   要避免的「看起來解除了、實際沒有」的同一種失效模式，只是這次連變數名都對不上，比那次
   更隱蔽。
   - 若三個下游目前設的是 `300`：數值本身與上游新預設一致，改用新變數名還算安全，但仍需要
     三個下游各自把環境變數名同步成 `SKILLSPECTOR_MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT`。
   - 若設的是 `86400`（本 fork 為了 OneDrive 慢速儲存的「解除上限」用法）：上游沒有解除上限
     的概念，`86400` 在上游語意下就是「一個很大的正有限值」，效果等價，但**變數名必須換**，
     否則會退回 300 秒——300 秒是否夠 OneDrive 冷啟動需要重新實測，不能假設。
2. 合併後 `docs/DIVERGENCE.md` 的 `static_runner.py` 那一列**不能直接刪除**（不像
   `SKILLSPECTOR_MAX_WORKFLOW_SECONDS` 那次），因為變數名不同、語意也不同，是「上游新增了
   一個相近但不相容的機制」，不是「上游做了同名同義的事」。需要重新寫一列，記錄改用上游
   變數名的遷移步驟，而不是單純刪除。
3. **觸發點**：上游合併 #522；屆時第一步是重跑三個下游 repo 的環境變數設定並用實際 OneDrive
   環境驗證 300 秒（或下游各自設定的值）是否足夠，再決定 DIVERGENCE.md 該列怎麼改寫。

### #490 `codex/fix-editable-file-url-conversion` vs. 本 fork 已開的 #486

**#490 明確建立在本 fork 自己的 #486 之上**——PR 內文寫「This builds on #486 and preserves
the original author attribution while closing the compatibility gap found during validation.
Fixes #485」，作者掛名 "Codex on behalf of Mohit Gupta"（NVIDIA 端）。差異：#486（本 fork
提交）用 `urllib.request.url2pathname(parsed.path)`；#490 額外處理「空 authority、以 `//`
開頭」的 POSIX file URL 形式（`file:////two-leading-slash-path`），因為 `url2pathname` 需要
保留這個分隔符，且 Python 3.14 對這個轉換的行為與更早版本不同——這是 #486 沒有覆蓋的邊界
情況，屬於 Python 3.14 + POSIX 的組合，本 fork 的 Windows-only 開發／驗收環境不會踩到，
也沒有本機證據顯示現有 `main` 上的 #486 版本在本 fork 實際使用場景下有缺陷。

**判定：不現在採用 #490 的診斷改動**——`scripts/compare_scan_accuracy.py` 雖然是
maintenance-tooling-only（符合可採用例外的檔案範圍），但「本 fork demonstrably hits this
defect」這個前提不成立（本機是 Windows、Python 3.13 開發環境，摸不到這個 POSIX+3.14 邊界
情況），現在 cherry-pick 等於在上游還在验证同一份改動時提前分岔，之後 #490 合併還要重新对齐。

**對本 fork 自己 #486 的建議**：

1. **不要現在關閉或修改 #486**——維護者尚未在本次對話同意回貢層級的改動，且 #490 本身也還
   是 open，上游尚未定案要不要直接合併 #490 取代 #486，或是要求 #486 補上同樣的邊界情況。
2. **觸發點**：#490 合併後，`#486` 大機率會被上游關閉並註記「由 #490 取代」（因為 #490 已經
   吸收了原作者署名並涵蓋 #486 的全部範圍再加上邊界修正）——屆時本 fork 只需要
   `git fetch upstream && git merge` 正常同步吸收 #490 的內容，`docs/DIVERGENCE.md` 裡
   `scripts/compare_scan_accuracy.py` 那一列即可比照 2026-09-11 `state.py` 的處理方式整份
   改採上游版本並刪除分岔列；若上游反而要求 #486 自行補齊邊界情況，則維護者需要決定是否
   在 #486 分支上再推一個 commit（屬於回貢層級的改動，需要當次對話明確同意）。

### #501–#505、#518：與本 fork 既有 Windows test 分岔幾乎逐字重複

這六筆全部只改測試檔，且改法與本 fork `docs/DIVERGENCE.md` 已登記的分岔幾乎一致：

| 上游 PR | 改的檔案 | 與本 fork 分岔列的關係 |
|---|---|---|
| #501 | `tests/nodes/test_build_context.py` | symlink 測試改成 `try/except OSError: pytest.skip(...)`，與本 fork 的 `@pytest.mark.skipif` 能力探測目的相同，手法不同（try/except vs. 前置探測） |
| #502 | 同上 | FIFO 測試加 `if not hasattr(os, "mkfifo"): pytest.skip(...)`，與本 fork 手法幾乎一致 |
| #503 | `tests/nodes/test_build_context.py`、`tests/unit/test_input_handler.py` | 同時攔截 `os.open` 與 `_open_regular_file_from_windows_handle`——**與本 fork 現有分岔列逐字同構**，連函式名稱都一樣 |
| #504 | `tests/nodes/analyzers/test_static_yara.py` | 加 `encoding="utf-8"`，與本 fork 分岔列完全相同的一行改動 |
| #505、#518 | `tests/nodes/test_build_context.py` | 用逐處 `newline="\n"` / `write_bytes`／`read_bytes` 取代本 fork `tests/conftest.py` 的全域 autouse fixture `pin_fixture_newlines_to_lf`，達成同一效果（釘住 LF）但手法不同（局部 vs. 全域） |

**判定：等上游合併**，不現在採用——本 fork 已經有等效的本機修正在跑（4009 全綠），現在
cherry-pick 上游版本沒有淨收益，只會在上游合併時製造衝突。

**明確的分岔列刪除觸發點**（`FORK.md`「A PR that would let the fork delete a divergence row
is worth calling out explicitly」）：

- #501＋#502 合併 → `tests/nodes/test_build_context.py` 的 symlink／FIFO skipif 分岔列可刪除
  （若上游手法與本 fork 探測方式不同，改採上游版本、刪除本 fork 對應 marker）。
- #503 合併 → `tests/unit/test_input_handler.py` 分岔列可**直接刪除**，因為手法逐字相同。
- #504 合併 → `tests/nodes/analyzers/test_static_yara.py` 分岔列可**直接刪除**，同上理由。
- #505＋#518 合併 → `tests/nodes/test_build_context.py` 裡與 LF 相關的斷言不再需要
  `tests/conftest.py` 的 `pin_fixture_newlines_to_lf`（但要先確認該 autouse fixture有沒有
  被其他測試檔依賴，若有，只能縮小適用範圍不能整個刪除）。

### 下一步（優先序）

1. **#490**：追蹤是否合併、#486 是否被上游關閉並註記「由 #490 取代」；合併後正常同步即可，
   不需要單獨移植。
2. **#522**：追蹤是否合併；合併後第一件事是重跑三個下游 repo（`agent-skills`／
   `book-to-skill`／`marketingskills`）的環境變數遷移與 OneDrive 實測，再改寫
   `docs/DIVERGENCE.md` 對應列（不是刪除）。
3. **#501/#502/#503/#504/#505/#518**：追蹤是否合併；合併後逐一比對能不能刪除
   `docs/DIVERGENCE.md` 對應列。
4. **#516/#521（documentation 誤判分析限制）**：與 #515 對應，維護者若實際遇到文件掃描誤判
   可提前確認 up-to-date 進度，否則按序等待。
5. 其餘 22 筆維持「等上游合併」，無本機證據顯示已影響維護者實際掃描結果。
