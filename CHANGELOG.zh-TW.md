# Changelog（本 fork 維護歷史）

本檔只記錄 **本 fork（`SanHsien/SkillSpector`）自己的維護歷史**，不記錄
`NVIDIA/SkillSpector` 上游的變更——上游的產品變更記錄見既有的 [`CHANGELOG.md`](CHANGELOG.md)。

格式依循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，版本號依循
[Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Changed

- **上游 PR/issue 水位推進到 #527／#524（commit 軸不動，仍是 `69dcdfb`）。** 31 筆新 PR
  （#488–#527）、10 筆新 issue（#486–#524）逐筆讀 diff／檔案清單後判定；#493／#507／#508／
  #511 用 `git merge-base --is-ancestor` 確認已隨 2.11.1／2.11.2 同步進 `main`，其餘一律
  「等上游合併」，無一筆現在採用。逐筆判定見 [`docs/DECISIONS.md`](docs/DECISIONS.md)
  2026-09-11（同日第二輪）條目。兩筆需要特別記住：#522 用**不同名、不同語意**的環境變數
  `SKILLSPECTOR_MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT`（預設 300 秒，無「解除上限」語意）
  對應本 fork 的 `SKILLSPECTOR_MAX_STATIC_SECONDS`（預設 30 秒，`<=0` 解除上限），合併時不能
  直接刪除 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md) 對應列，需要先遷移三個下游 repo 的
  環境變數名並重新驗證；#490 是延伸本 fork 自己開的上游 PR #486（同一 file URL 轉換 bug），
  補了 Python 3.14＋POSIX 空 authority 的邊界情況，本 fork 目前踩不到，維持等待，不現在
  cherry-pick。另外 #501/#502/#503/#504/#505/#518 六筆 Windows test 修正與本 fork
  `DIVERGENCE.md` 既有分岔列高度重疊（#503／#504 手法逐字相同），合併後有機會直接刪列。

### Fixed

- **大型 acceptance test 在 Linux CI 間歇失敗。** `test_rd04_large_file_pair_detects_start_boundary_and_end` 在 run 34543263439 以 `analysis_completeness.is_complete is False` 失敗：負載下的 runner 讓第三個掃描介面用完每檔 30 秒額度。`_allow_slow_static_fixture` 原本只在 Windows 放寬，但 CI 跑在 ubuntu，放寬從未生效；上游 CI 也有同樣的失敗（run 34447095261、34442162097）。改為所有平台套用，只影響兩個 oversized fixture，產品預設不變；見 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。
- **`75bd6f3` 合併後的兩個紅燈。** `Dependency freshness` 擋在 fork 持有的 `codeql.yml`：`github/codeql-action` 釘 v4.37.9、最新 v4.38.0，升到 v4.38.0 的 commit SHA（`b96794f`）。`ruff` 在 `tools/check_dependency_freshness.py` 報 UP035（`Callable` 應從 `collections.abc` 匯入）；它沒被 gate 抓到，因為 `tools/dev_check.ps1` 的 lint 範圍只列了兩支 tools 腳本——改成整個 `tools/`，fork 持有的維護工具都在 gate 內。
- **依賴新鮮度的 Actions 查詢改帶 token。** 匿名 `api.github.com` 每小時 60 次、hosted runner 共用；
  超額後每一列 Action 的 `latest` 都變 `unknown`，整個 Actions 半邊靜默失聲（而那正是本 repo 現在唯一
  會擋 run 的一半）。`_github_json` 在有 `GITHUB_TOKEN`／`GH_TOKEN` 時送 `Authorization: Bearer`，
  workflow 檢查步驟補上 `GH_TOKEN: ${{ github.token }}`。缺陷由 `SanHsien/commerce-agents` 那條線先發現。

### Changed

- **同步上游至 2.11.2（`69dcdfb`，自 `7805bb9` 起 19 個 commit）。** 含 2.11.1 的可設定整體
  workflow 期限（上游 #468）與 2.11.2 的安全性修正。上游的 `SKILLSPECTOR_MAX_WORKFLOW_SECONDS`
  與本 fork `185d610` **同名但語意不同**：上游預設 600 秒、只收正有限值（`0`／負數／`nan`
  會警告並退回預設）；本 fork 原為預設 60 秒、`<= 0` 代表解除。唯一的合併衝突
  `src/skillspector/state.py` 依其分岔登記列的預先判準（「上游若自行加了同名或同義的覆寫就刪掉本列」）
  整份採用上游，並從 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md) 刪除該列。下游
  `agent-skills`／`book-to-skill` 的關卡原本設 `"0"`，在上游語意下會**靜默退回 600 秒**，
  已改為兩種語意都成立的 `86400`。每檔的 `SKILLSPECTOR_MAX_STATIC_SECONDS` 仍是本 fork 獨有。
- **依賴新鮮度只對 fork 持有的宣告紅燈。** `Dependency freshness` workflow 自 2026-09-05（`b02d8ae`）
  起每次都 failure，因為報告有 25 列來自上游 `pyproject.toml` 的 `REVIEW UPDATE`——而
  [`DECISIONS.md`](DECISIONS.md) 2026-09-05 那條已經判定那些對本 fork 是**資訊性**的。
  一個永遠紅、又沒有出口的月檢等於訓練大家忽略它，連真正可行動的那幾列一起忽略。
  新增 `gating_rows()`：只有**全部宣告它的 workflow 都是 fork 持有**的 Action pin 才會讓 run 失敗；
  上游持有的 workflow（`ci.yml`、`release.yml`、`scorecard.yml`、`update-pr-branches.yml`）裡的 pin
  與 `pyproject.toml` 的下限同理，照樣顯示但不擋。報告的兩個章節標題現在直說哪一半會擋。
  `UPSTREAM_WORKFLOWS` 由 `test_fork_owned_workflows_matches_git` 對 baseline commit 的
  `git ls-tree` 交叉核對，上游新增 workflow 時不會靜默失準。**這條不適用於安全性通報**，那走
  [`SECURITY.md`](SECURITY.md)。


- **依賴新鮮度漏看了每一個 CodeQL pin。** `_USES_RE` 只匹配 `owner/repo@`，而
  `github/codeql-action/init`／`/analyze` 是三段路徑，所以 `codeql.yml` 的兩個 pin 從來沒進過報告。
  路徑改為允許子目錄，查 Releases 時以 `action_repository()` 截回擁有 tag 的 repo。
- **無法比較的 latest 不再報 OK。** `github/codeql-action` 的 `releases/latest` 回
  `codeql-bundle-v2.26.4`，與 workflow 釘的 `v4.37.9` 不同編號系統，解析不出數字就一路報 OK。
  現在解析失敗會改查 tag 列表取最新可解析版本；真的比不了就記 `CHECK FAILED`——不會失敗的檢查不是檢查。
  三筆新測試釘住上述行為（突變驗證：把 regex 改回 `owner/repo` 會讓其中三筆變紅）。
- **`src/skillspector/state.py` 補登記進 `docs/DIVERGENCE.md`。** `SKILLSPECTOR_MAX_WORKFLOW_SECONDS`
  覆寫（commit `185d610`）動到上游持有檔卻沒登記，`tools/check_divergence.py` 因此紅燈；
  它與已登記的 `static_runner.py` 那列是同一個問題的兩半。
- **`tools/check_dependency_freshness.py` 補跑 `ruff format`**（在本次改動之前就已不符格式，
  讓 gate 的 `Ruff format --check` 步驟紅燈）。

### Added

- 建立 fork 維護鷹架：繁中 `README.md`（英文原檔保留為 `README.en.md`）、`AGENTS.md`、
  `CLAUDE.md`（指向 `AGENTS.md` 的薄指標）、`NOTICE.md`、`FORK.md`、`CODE_OF_CONDUCT.md`、
  本檔（`CHANGELOG.zh-TW.md`）。
- `.editorconfig`、`.gitattributes`：統一縮排（2 空格，`.py`／`.ps1` 4 空格）與換行（LF）；
  上游都沒有這兩個檔案。
- `.cursor/rules/no-upstream-pr.mdc`：機器可讀的「對外只打 origin」規則。
- `tools/dev_check.ps1`：Windows 本機一鍵 gate，繞過上游 `Makefile`（POSIX sh 語法，Windows
  原生跑不動）直接呼叫 `uv`／`ruff`／`pytest`。`-Quick` 模式跑 `ruff check` + `ruff format
  --check` + `skillspector --version` 煙霧測試；完整模式再加 `pytest`。
- `docs/DECISIONS.md`、`docs/DIVERGENCE.md`：維護決策記錄與分岔登記表。
- 上游同步與依賴新鮮度自動化：`tools/upstream_baseline.json` +
  `tools/check_upstream_updates.py`（commit／PR／issue 三軸水位）、
  `tools/check_dependency_freshness.py`（`pyproject.toml` 對 PyPI、workflow 釘選的 Action
  對 GitHub Releases）、`.github/dependabot.yml`（uv／github-actions／npm／docker）、
  `.github/workflows/{upstream-check,dependency-freshness}.yml` 兩個排程 workflow。
- `tests/platform_support.py`：POSIX 專屬檔案系統能力的執行期探測
  （symlink、FIFO、`os.geteuid`、PATH 上的 shebang 腳本），供測試用能力而非 `sys.platform`
  決定是否跳過。

### Fixed

- 修好 Windows 本機全套測試的 23 筆紅燈：**3943 passed / 23 failed / 26 skipped**
  → **3953 passed / 0 failed / 39 skipped**。全部是測試對 POSIX 的假設，不是產品在 Windows
  上行為錯誤；逐筆判準與處理方式登記在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。
- `scripts/compare_scan_accuracy.py`：`file://` URL 轉本機路徑改用
  `urllib.request.url2pathname`，取代 `Path(urllib.parse.unquote(...))`。後者在 Windows 上
  把 `/C:/Users/...` 的前導斜線當成根，算出 `C:\C:\Users\...`。這是上游的真實可攜性 bug，
  也是本 fork 唯一動到產品端的一筆分岔。**已回貢上游**：
  [issue #485](https://github.com/NVIDIA/SkillSpector/issues/485) →
  [PR #486](https://github.com/NVIDIA/SkillSpector/pull/486)。

### Notes

- 仍未移植：`tools/check_divergence.py`、`tools/check_pin_bounds.py`、
  `.github/workflows/codeql.yml`，見 [`FORK.md`](FORK.md)。
- 已知上游測試隔離問題（非本 fork 引入）：
  `tests/nodes/test_security_end_to_end.py::test_nine_case_contract_across_public_surfaces`
  單獨執行時紅、整包跑時綠。詳見 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。

## [0.1.0] - 2026-09-05

### Added

- 建立 fork：`git clone` 自 `NVIDIA/SkillSpector`，設定 `origin` 為
  `SanHsien/SkillSpector`、`upstream` 為 `NVIDIA/SkillSpector`，保留 Apache License 2.0
  與完整 Git 歷史。

[Unreleased]: https://github.com/SanHsien/SkillSpector/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SanHsien/SkillSpector/releases/tag/v0.1.0
