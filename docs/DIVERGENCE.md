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
| 本表所列分岔套用後（2026-09-11，同步上游 2.11.2） | 同上（OneDrive 外 venv、`UV_LINK_MODE=copy`，分兩批） | **4009 passed / 0 failed / 39 skipped / 38 deselected / 4 xfailed** |
| 同步上游到 `c13f70e` 後（2026-09-17） | 同上，分三批：`tests/unit`、`tests/nodes`（大型 e2e 檔另跑）、其餘 | **unit 1563 passed／29 skipped；nodes 3822 passed／11 skipped／4 xfailed；其餘 182 passed／16 skipped；`test_security_end_to_end.py` 98 passed** |

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
| `tests/test_bundled_execution_surface_acceptance.py` | `subprocess.run(..., text=True)`，無 `encoding` | 加 `encoding="utf-8"` | CLI 輸出 UTF-8，`text=True` 用 locale codec 解碼，cp950 在 reader thread 丟 `UnicodeDecodeError`。這是 warning 不是 failure，所以在紅燈統計裡看不到，但輸出會被截斷 | **保留** |
| `tests/unit/test_create_github_release.py` | 3 個測試用 `#!/usr/bin/env python3` + `chmod 0o755` 造 `gh` stub 放上 PATH；1 個測試斷言 `"docs/release/..."` 出現在 stderr；5 處 `text=True` 無 encoding | 3 個測試加 shebang-stub 能力探測 skip；斷言改成比對 `str(Path("docs/release/..."))`；5 處加 `encoding="utf-8"` | Windows `CreateProcessW` 對無副檔名的指令只會補 `.exe`，PATH 上的 shebang 腳本永遠找不到，stub 完全不生效。分隔符那筆則是腳本用平台分隔符印路徑，斷言硬寫 POSIX 形式 | 分隔符與 encoding 兩筆**保留**（兩平台皆正確）。stub skip 保留到上游把 `gh` 執行檔改成可注入（例如讀 `GH_BINARY` 環境變數）為止——那之後 Windows 就能跑，刪掉 marker |
| `tests/nodes/analyzers/test_json_container_ownership.py` | `test_unproven_json_or_fence_structure_grants_no_quote_ownership` 的 parametrize 沒給 `ids`，兩個超長 payload（`_MAX_JSON_QUOTE_CONTAINER_CHARS` 長度）直接變成測試 id | parametrize 加 `ids=`，超過 200 字元的 payload 改用 `payload-<長度>-chars` 當 id；測試內容不變 | 上游 `b5c5d8e`（2026-09-17 同步進來）新增。pytest 會把測試 id 寫進環境變數 `PYTEST_CURRENT_TEST`，Windows 環境變數上限 32,767 字元，兩個案例在 setup 就丟 `ValueError`（本機 4 個 error）。縮短 id 後 71 passed，兩個平台都成立 | **保留**，值得回貢——這是無條件的可攜性改善。上游自行加上短 id 就刪除本列 |
| `tests/unit/test_cli.py` | `test_discovered_files_tree_renders_untrusted_names_literally` 用含終端跳脫序列的檔名（結尾是 `\`，帶一個反斜線）組成 `Path("folder") / name` | 加 `@pytest.mark.skipif(not BACKSLASH_IS_FILENAME_CHAR, ...)`，探測放在 `tests/platform_support.py` | 上游 #565（2026-09-17 同步進來）新增的測試假設反斜線是普通檔名字元。Windows 上反斜線是路徑分隔符，檔名被拆成兩層，樹狀輸出變成資料夾加檔案，字面斷言失敗；Windows 也根本不能建立含反斜線的檔名，所以這條斷言在 Windows 上沒有可對應的情境。產品的跳脫處理在同檔其餘測試仍涵蓋 | **保留**，直到上游讓該測試改用不含反斜線的跳脫序列，或自行加上平台守衛；那之後刪除本列 |
| `tests/unit/test_compare_scan_accuracy.py` | 3 個測試斷言 `st_uid == os.geteuid()` | 加 `@pytest.mark.skipif(not HAS_GETEUID, ...)` | Windows 沒有 `os.geteuid`，也沒有等價的數值 uid 概念。這 3 個測試驗的是 POSIX 檔案擁有權語意，在 Windows 上沒有可對應的斷言 | **永久保留**。`scripts/compare_scan_accuracy.py` 是 POSIX-only 的維護者基準測試工具（fresh-HOME worktree + 擁有權檢查），不打算 Windows 化 |
| `scripts/compare_scan_accuracy.py` | `Path(urllib.parse.unquote(parsed.path))` 把 `file://` URL 轉路徑 | 改用 `urllib.request.url2pathname(parsed.path)`，並補 `import urllib.request` | **這是上游的真實可攜性 bug，不是測試假設**：Windows 的 file URL path 是 `/C:/Users/...`，前導斜線讓 `Path()` 當成根，算出 `C:\C:\Users\...` 然後 `resolve(strict=True)` 丟 `WinError 123`。`url2pathname` 是標準函式庫給這件事的正解 **已回貢**：[issue #485](https://github.com/NVIDIA/SkillSpector/issues/485) →
[PR #486](https://github.com/NVIDIA/SkillSpector/pull/486)（branch `fix/windows-file-url-editable-dependency`，帶 DCO sign-off）。**上游 merge 後就從本表刪掉這一列**，改成同步上游即可。2026-09-17：#486 已於 2026-09-15 由上游維護者 yashrajp22 關閉，改由上游 [PR #490](https://github.com/NVIDIA/SkillSpector/pull/490)（建立在 #486 之上並補 Python 3.14 的空 authority 情境）接手，#490 仍未合併；觸發條件改為 #490 合併 |
| `.gitignore` | 上游版本 | 檔尾追加 fork 區塊（`.ruff_cache/`、`.mypy_cache/`、兩份生成報告） | 本 fork 的維護工具會在工作區產生報告檔，不加就會被 `git add -A` 收進去 | **保留**。上游變更照常合併，追加區塊在檔尾，衝突機率低 |
| `README.md` | 英文說明文件 | `git mv` 成 `README.en.md`（內容原封不動，只在頂部加一行語言列），另新寫繁中 `README.md` | README 是上游最常動的檔。就地翻譯會讓每次同步整檔衝突；改名保留鏡像，同步時 `README.en.md` 可以直接吃上游的 diff | **保留**。同步上游時：`git checkout upstream/main -- README.md && git mv -f README.md README.en.md`，重加語言列，再人工判斷繁中 `README.md` 要不要跟著更新 |
| `tests/nodes/test_security_end_to_end.py` | 大型安全 fixture 使用產品的每檔預算（上游 #522 起預設 300 秒，可由 `SKILLSPECTOR_MAX_STATIC_ANALYSIS_SECONDS_PER_ARTIFACT` 覆寫）、YARA 載入 5 秒與 SC8 traversal 5 秒上限（後兩者寫死） | 只在兩個 oversized acceptance tests（rd04、nine_case）將每檔額度調為 600 秒、YARA／SC8 調為 60 秒、整體 workflow 調為 900 秒，**所有平台都套用** | Windows 冷啟動與 Linux CI 負載下都會命中 runtime limit（本 fork run 34543263439、上游 run 34447095261、34442162097）。2026-09-17 同步上游到 `c13f70e` 時先改取上游版本實測：上游已把每檔預設提高到 300 秒，但 `test_nine_case_contract_across_public_surfaces` 在本機 Windows 仍以 `analysis_completeness.is_complete` 失敗，所以放寬 helper 重新套回上游版本 | **保留到上游讓 YARA 載入與 SC8 兩個預算也可注入，或縮短 fixture 成本**；不得因此放寬產品預設。每檔那一個上游已由 #522 解決 |
| `tests/unit/test_input_handler.py` | `test_secure_open_traverses_search_only_ancestors` 測試時 `os.chmod(parent, 0o111)` 且 finally `0o755` | 改為僅 owner 搜尋權限 `0o100` 與清理權限 `0o700` | 消除 CodeQL 警報 #5、#6（`py/overly-permissive-file`）。測試以 owner 執行，`0o100` 完全滿足 search-only 驗證目的，不對 world/group 過度開放 | **保留**。可回饋上游；上游修復後可刪除此列 |
| `tests/unit/test_input_handler_ssrf.py` | `TestAllowlistConfiguration` 使用 `assert "<domain>" in ALLOWED_*_HOSTS` | 改為集合子集斷言 `assert {"<domain>", ...}.issubset(ALLOWED_*_HOSTS)` | 消除 CodeQL 警報 #1~#4（`py/incomplete-url-substring-sanitization` 誤報）。CodeQL 靜態分析誤將 frozenset 成員檢查當成未解析 URL 字串包含；改用 `issubset` 完全消除誤報 | **保留**。可回饋上游；上游修復後可刪除此列 |
| `uv.lock` | 鎖定 `cryptography==49.0.0` 與 `setuptools==82.0.1` | 升級至 `cryptography==50.0.1` 與 `setuptools==84.0.0` | 消除 Dependabot alerts #1、#2（CVE-2026-69247 高風險 Bleichenbacher oracle 漏洞與 CVE-2026-59890 中風險 Unicode 規範化衝突），且完全符合 direct pin bounds | **保留或隨上游更新**。若上游後續釋出更新包含安全版本，則直接同步覆蓋 |

## 已知但**不**登記為分岔的上游問題

| 現象 | 判斷 |
|---|---|
| `tests/nodes/test_security_end_to_end.py` 的大型案例在冷啟動或 CI 負載下可能耗盡 SC8 或 YARA 載入的 5 秒上限（每檔預算上游 #522 起預設 300 秒）（整體上限自上游 2.11.1 起為 600 秒，已不是瓶頸）；上游自己的 Linux CI 也因此間歇失敗 | fork 只對兩個 oversized acceptance tests 在所有平台注入寬裕額度；產品限制不變。上游若提供每檔／YARA／SC8 的正式 test-budget 注入點就改用並刪除本分岔 |
| `tools/check_dependency_freshness.py` 對 `pyproject.toml` 的 Python 依賴回報 25 列 `REVIEW UPDATE` | `pyproject.toml` 是上游持有檔，宣告的是相容性下限（`>=`）不是釘選。本 fork 不動它，這些列對本 fork 是**資訊性**的；真正可行動的是 fork 持有的 workflow 裡釘選的 GitHub Action。詳見 [`DECISIONS.md`](DECISIONS.md) |
