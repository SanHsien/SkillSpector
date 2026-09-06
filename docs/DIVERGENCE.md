# 分岔登記表

本檔登記本 fork 對**上游持有檔案**的每一筆修改——上游原本就有這個檔案，本 fork 動了它。
新增的檔案（上游沒有對應版本，例如 `AGENTS.md`、`FORK.md`、`tests/platform_support.py`、
`tools/` 底下的維護工具）不算分岔，不登記在這裡；那些檔案的清單見 [`FORK.md`](../FORK.md)。

## 維護契約

**改動任何一個上游持有的檔案，就必須在這裡加一列。** `tools/check_divergence.py` 以
`tools/upstream_baseline.json` 的完整 SHA 為基準，比對 working tree 與本節唯一表格；新增但
上游不存在的 fork 檔案不算分岔。比對明確停用 rename detection，所以上游檔案改名仍會以原路徑
刪除列入分岔。這一步已納入 `tools/dev_check.ps1`，缺列或過期列都會擋下 gate。

最後一欄「跟進上游時怎麼處理」是這張表的重點：寫成**可執行的判準**，讓日後同步上游時不必
重新評估一次判斷，照著欄位裡的規則做決定即可。

## Windows 測試現況

| 時間 | 指令 | 結果 |
|---|---|---|
| fork 當下（未改任何檔） | `uv run pytest -m "not integration and not provider" tests/` | 3943 passed / **23 failed** / 26 skipped |
| 本表所列分岔套用後 | 同上 | **3959 passed / 0 failed / 39 skipped / 38 deselected / 4 xfailed** |

23 筆紅燈全部是**測試對 POSIX 的假設**，不是產品在 Windows 上的行為錯誤。處理原則分兩類：

- **能在兩個平台都成立的，改測試條件**（顯式 UTF-8、顯式 LF、比對 `Path` 而非硬寫 POSIX 分隔
  符、把 Windows 實際走的程式路徑也一併攔截）。這類不損失覆蓋率。
- **平台根本沒有那個能力的，用能力探測跳過**（symlink、FIFO、`os.geteuid`、PATH 上的
  shebang 腳本）。用探測不用 `sys.platform`：Windows 開了 Developer Mode 之後 symlink 測試
  會自己恢復執行，不需要改碼。探測集中在 `tests/platform_support.py`。

## 分岔清單

| 上游檔案 | 上游原狀 | 本 fork 狀態 | 為什麼分岔 | 跟進上游時怎麼處理 |
|---|---|---|---|---|
| `tests/conftest.py` | 只有 `mock_resolve_context_length` 一個 autouse fixture | 加 `pin_fixture_newlines_to_lf`：Windows 上把 `Path.write_text` 的預設 newline 釘成 `\n` | `Path.write_text` 在 Windows 預設把 `\n` 轉成 `\r\n`，fixture 寫進磁碟的位元組與 Linux CI 不同，12 個斷言檔案內容的測試在本機紅、CI 綠。釘 LF 是把平台從**輸入**拿掉，不是放寬斷言 | **保留**。上游若自己加了 newline 處理就移除本 fixture；上游 conftest 有其他變更時照常合併，本 fixture 是獨立追加的區塊，衝突機率低 |
| `tests/nodes/test_build_context.py` | 6 個測試直接呼叫 `os.mkfifo` / `Path.symlink_to`，無平台守衛；read-error 測試只攔 `os.open` | 6 個測試加 `@pytest.mark.skipif` 能力探測；read-error 測試同時攔 `_open_regular_file_from_windows_handle` | 同檔第 984 行與第 1001 行上游**自己就有**同樣的守衛（`hasattr(os, "mkfifo")`、`try/except OSError`），只是沒有套用到全部。Windows 走 handle-based opener，不經過 `os.open`，所以原測試在 Windows 上讀取成功、斷言反向失敗 | **保留**，且這是最有機會回貢上游的一筆——它只是把上游既有的守衛模式補齊。上游若自行補齊就刪掉本 fork 的 marker |
| `tests/unit/test_input_handler.py` | `test_resolve_file_open_failure_does_not_create_temp_dir` 只攔 `os.open` | 同時攔 `_open_regular_file_from_windows_handle`，並讓它丟 `_FileOpenError`（Windows 分支 CreateFileW 失敗時實際會丟的型別） | 同上：Windows 不走 `os.open`。用 `_FileOpenError` 而非裸 `OSError`，是因為包裝發生在被 patch 掉的函式**內部**，patch 整個函式就必須自己丟出包裝後的型別，否則測的是假的失敗形狀 | **保留**。上游若把 gh/opener 抽象成單一注入點，改攔那個點 |
| `tests/nodes/analyzers/test_static_yara.py` | `(tmp_path / "bad.yar.b64").write_text(payload)`，無 `encoding` | 加 `encoding="utf-8"` | 參數化 payload 含 `é`；沒給 encoding 就用 locale codec，本機是 cp950，直接 `UnicodeEncodeError`。CI 的 locale 是 UTF-8 所以看不到 | **保留**。顯式 encoding 在兩個平台都正確，屬於無條件改善 |
| `tests/test_bundled_execution_surface_acceptance.py` | `subprocess.run(..., text=True)`，無 `encoding` | 加 `encoding="utf-8"` | CLI 輸出 UTF-8，`text=True` 用 locale codec 解碼，cp950 在 reader thread 丟 `UnicodeDecodeError`。這是 warning 不是 failure，所以在紅燈統計裡看不到，但輸出會被截斷 | **保留** |
| `tests/unit/test_create_github_release.py` | 3 個測試用 `#!/usr/bin/env python3` + `chmod 0o755` 造 `gh` stub 放上 PATH；1 個測試斷言 `"docs/release/..."` 出現在 stderr；5 處 `text=True` 無 encoding | 3 個測試加 shebang-stub 能力探測 skip；斷言改成比對 `str(Path("docs/release/..."))`；5 處加 `encoding="utf-8"` | Windows `CreateProcessW` 對無副檔名的指令只會補 `.exe`，PATH 上的 shebang 腳本永遠找不到，stub 完全不生效。分隔符那筆則是腳本用平台分隔符印路徑，斷言硬寫 POSIX 形式 | 分隔符與 encoding 兩筆**保留**（兩平台皆正確）。stub skip 保留到上游把 `gh` 執行檔改成可注入（例如讀 `GH_BINARY` 環境變數）為止——那之後 Windows 就能跑，刪掉 marker |
| `tests/unit/test_compare_scan_accuracy.py` | 3 個測試斷言 `st_uid == os.geteuid()` | 加 `@pytest.mark.skipif(not HAS_GETEUID, ...)` | Windows 沒有 `os.geteuid`，也沒有等價的數值 uid 概念。這 3 個測試驗的是 POSIX 檔案擁有權語意，在 Windows 上沒有可對應的斷言 | **永久保留**。`scripts/compare_scan_accuracy.py` 是 POSIX-only 的維護者基準測試工具（fresh-HOME worktree + 擁有權檢查），不打算 Windows 化 |
| `scripts/compare_scan_accuracy.py` | `Path(urllib.parse.unquote(parsed.path))` 把 `file://` URL 轉路徑 | 改用 `urllib.request.url2pathname(parsed.path)`，並補 `import urllib.request` | **這是上游的真實可攜性 bug，不是測試假設**：Windows 的 file URL path 是 `/C:/Users/...`，前導斜線讓 `Path()` 當成根，算出 `C:\C:\Users\...` 然後 `resolve(strict=True)` 丟 `WinError 123`。`url2pathname` 是標準函式庫給這件事的正解 **已回貢**：[issue #485](https://github.com/NVIDIA/SkillSpector/issues/485) →
[PR #486](https://github.com/NVIDIA/SkillSpector/pull/486)（branch `fix/windows-file-url-editable-dependency`，帶 DCO sign-off）。**上游 merge 後就從本表刪掉這一列**，改成同步上游即可 |
| `.gitignore` | 上游版本 | 檔尾追加 fork 區塊（`.ruff_cache/`、`.mypy_cache/`、兩份生成報告） | 本 fork 的維護工具會在工作區產生報告檔，不加就會被 `git add -A` 收進去 | **保留**。上游變更照常合併，追加區塊在檔尾，衝突機率低 |
| `README.md` | 英文說明文件 | `git mv` 成 `README.en.md`（內容原封不動，只在頂部加一行語言列），另新寫繁中 `README.md` | README 是上游最常動的檔。就地翻譯會讓每次同步整檔衝突；改名保留鏡像，同步時 `README.en.md` 可以直接吃上游的 diff | **保留**。同步上游時：`git checkout upstream/main -- README.md && git mv -f README.md README.en.md`，重加語言列，再人工判斷繁中 `README.md` 要不要跟著更新 |
| `tests/nodes/test_security_end_to_end.py` | 大型安全 fixture 使用產品的每檔 30 秒、YARA 載入 5 秒與 SC8 traversal 5 秒上限 | 只在兩個 oversized acceptance tests 將每檔額度調為 600 秒、YARA／SC8 調為 60 秒 | Windows 冷啟動實測會分別命中 static 與 `static_patterns_supply_chain_bytecode` runtime limit；產品預設與一般測試均不變 | **保留到上游讓測試 budget 可注入或縮短 fixture 成本**；不得因此放寬產品預設。下一列的環境變數就是那個注入點，兩者可合併後刪除本列 |
| `src/skillspector/nodes/analyzers/static_runner.py` | `MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT = 30.0` 寫死，無任何覆寫途徑 | 加 `SKILLSPECTOR_MAX_STATIC_SECONDS` 環境變數覆寫（**預設值不變**；`<= 0` 代表取消上限）。新增 `tests/nodes/analyzers/test_static_runner_time_budget.py` 5 筆測試釘住行為 | 30 秒是防病態輸入的上限，不是「正常檔案該花多久」的宣告。慢速儲存（OneDrive）上一個 25 KB reference 檔會壓線，**同一棵樹會因為當下機器負載而時綠時紅**——實測 `marketingskills/skills/ad-creative` 在背景有工作時 `exit 2`／`execution_successful: false`，機器閒下來就過。掃描關卡若建在這種訊號上等於沒有關卡。覆寫讓呼叫端可以用時間換完整結果 | **保留，值得回貢**（`SKILLSPECTOR_OSV_TIMEOUT`、`SKILLSPECTOR_MAX_LLM_CONCURRENCY` 已是同一種寫法，這只是補齊第三個）。上游若自行加了同名或同義的覆寫就刪掉本列 |

## 已知但**不**登記為分岔的上游問題

| 現象 | 判斷 |
|---|---|
| `tests/nodes/test_security_end_to_end.py` 的大型案例在冷啟動時可能耗盡 SC8 5 秒、每檔 30 秒或整體 60 秒上限 | fork 只對兩個 oversized acceptance tests 注入寬裕額度；產品限制不變。上游若提供正式 test-budget 注入點就改用並刪除本分岔 |
| `tools/check_dependency_freshness.py` 對 `pyproject.toml` 的 Python 依賴回報 25 列 `REVIEW UPDATE` | `pyproject.toml` 是上游持有檔，宣告的是相容性下限（`>=`）不是釘選。本 fork 不動它，這些列對本 fork 是**資訊性**的；真正可行動的是 fork 持有的 workflow 裡釘選的 GitHub Action。詳見 [`DECISIONS.md`](DECISIONS.md) |
