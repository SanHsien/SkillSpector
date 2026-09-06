# Changelog（本 fork 維護歷史）

本檔只記錄 **本 fork（`SanHsien/SkillSpector`）自己的維護歷史**，不記錄
`NVIDIA/SkillSpector` 上游的變更——上游的產品變更記錄見既有的 [`CHANGELOG.md`](CHANGELOG.md)。

格式依循 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)，版本號依循
[Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

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
