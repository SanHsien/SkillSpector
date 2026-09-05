# 上游分支審視記錄

本檔記錄這個 fork 從 `NVIDIA/SkillSpector` 繼承下來的 36 個上游分支的審視結果。規則很
簡單：**一個分支只有在判定寫進本檔之後才算「處理完」**——單純刪除分支不算數，就算內容已經
在 `main` 裡也一樣，因為判定本身（理由、後續觸發點）才是要保留的資訊，分支本身刪不刪只是
附帶結果。

水位機制見 `tools/upstream_baseline.json`（本檔只引用，不修改）。

## 目前水位

引用自 `tools/upstream_baseline.json`：

```
reviewed_through:       7805bb94843d91cb9937f57264ca52642164499b
reviewed_pr_through:    462
reviewed_issue_through: 0
```

- `reviewed_through` 是 fork HEAD 對齊 `upstream/main` tip 的 commit；此刻整個工作樹與上游
  逐位元組相同。
- `reviewed_pr_through` = 462 只代表「merge 進 `upstream/main` 的 PR 都已經字面上在這個
  commit 裡」，**不代表**有人審視過還沒 merge 的開放 PR——本檔的 Group C 就是在補這一塊。
  截至 2026-09-04，#470、#447、#442、#430、#410、#409、#403 這七個 PR 已開啟但未合併
  （加上本檔另外收錄的 #383，共八個）。
- `reviewed_issue_through` = 0：上游的 GitHub Issues 目前完全沒有人審視過，是待補的空白，
  不是「沒有 issue 需要處理」的結論。

## Group A／B：內容已在 `main` 或已隨上游 PR 定案的分支

Group A 的 22 個分支是 `git cherry` 比對後 patch-id 與 `main` 完全相同的提交，內容已經在
這個工作樹裡；2026-09-04 已從 fork 刪除。Group B 的 4 個分支是已關閉（合併或不合併）的上游
PR 的 head，內容是否在樹裡取決於該 PR 是否合併。

| 分支 | 上游 PR | 判定 | 理由 |
|---|---|---|---|
| docs/link-verified-skills-pipeline | — | 已在 main | commit 已 cherry-pick/合併，patch-id 與 main 相同 |
| release/oss-2026-07-20 | — | 已在 main | 同上 |
| rng1995/oss-release-2026-08-06 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-13 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-15 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-15-2 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-16 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-22-2 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-23 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-24 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-06-30-2 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-07-13 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-07-14 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-07-21 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-07-22 | — | 已在 main | 同上 |
| keshavp/oss-release-2026-07-26 | — | 已在 main | 同上 |
| keshprad/oss-release-2026-07-30 | — | 已在 main | 同上 |
| keshprad/oss-release-2026-08-05 | — | 已在 main | 同上 |
| keshprad/oss-release-2026-08-07 | — | 已在 main | 同上 |
| keshprad/oss-release-2026-08-10 | — | 已在 main | 同上 |
| keshprad/oss-release-2026-08-10-2 | — | 已在 main | 同上 |
| keshprad/oss-release-2026-08-11 | — | 已在 main | 同上 |
| codex/fix-issue-329-env-ast | #332（已合併） | 已在 main | PR 已合併，內容在樹裡 |
| keshavp/oss-release-2026-07-23 | #306（已合併） | 已在 main | PR 已合併，內容在樹裡 |
| keshavp/oss-release-2026-06-22 | #155（已關閉、未合併） | 不在樹裡，內容由後續分支取代 | OSS release snapshot 同步 PR，2026-06-22 開、同日關閉未合併，無留言。同名分支帶 `-2` 尾碼的 `keshavp/oss-release-2026-06-22-2` 屬於 Group A（已在 main），關閉時間點與命名規則吻合「同一天重新整理過的快照取代前一版」的解讀，內容已透過後續分支進入 main |
| keshavp/oss-release-2026-06-30 | #235（已關閉、未合併） | 不在樹裡，內容由後續分支取代 | 同樣是 OSS release snapshot 同步 PR，2026-07-01 關閉未合併，無留言。`keshavp/oss-release-2026-06-30-2` 屬於 Group A（已在 main），命名與時間點同樣吻合「被下一版快照取代」 |

## Group C：8 個仍開啟的上游 PR

以下每一筆先描述問題／能力，再確認受影響程式碼是否在本樹（預設是，因為樹與上游一致），
最後給判定與觸發點。

### #403 keshavp/codex/llm-429-retries — fix(llm): retry rate-limited (429) batches instead of dropping them

1. **問題**：LLM 批次分析遇到 provider 回 429（rate limit）時目前直接丟棄該批次，不重試；
   這支 PR 改成有界重試排程（5s/15s/30s/60s/60s），並認 `Retry-After`（最多 120 秒），
   耗盡重試後在 inspection ledger 記一筆 `llm_rate_limit_retries_exhausted`。
2. **受影響檔案在本樹**：`src/skillspector/llm_analyzer_base.py`、
   `src/skillspector/inspection_ledger.py` 兩者都存在（已確認）；樹與上游一致，缺陷（429 直接
   丟批次、不重試）同樣存在於本 fork。
3. **判定：等上游合併**。這是 LLM 語意分析（optional 階段）的健壯性修正，不是安全判定邏輯，
   維護者目前也還沒有本機重現「429 導致漏掃」的急迫案例；獨立 cherry-pick 的風險（提前踩上游
   還在磨的重試排程參數、之後上游改了又要重新對齊）大於等待的成本。
4. **觸發點**：上游合併 #403；或維護者本機實際遇到批次因 429 被丟棄（例如大型 skill 目錄搭配
   `--llm-analysis` 大量觸發限流）。

### #409 codex/security-finding-integrity — fix(security): preserve exact finding identity

1. **問題**：目前的 finding 去重／代表項選擇邏輯會用「有界的顯示預覽」而非完整比對結果做
   identity，可能導致長內容碰撞（不同的實際 match 被誤判成同一個 finding）或代表項選擇不具
   確定性；這支 PR 改成用完整 analyzer match 決定 identity，代表項選擇改成「嚴重度優先」且
   確定性排序，同時對 static/YARA/MCP tool-poisoning/rug-pull 四類 finding 都適用，並在 YARA
   指紋工作到達上限時明確回報「部分分析」而非沉默。
2. **受影響檔案在本樹**：`src/skillspector/models.py`、
   `src/skillspector/nodes/analyzers/common.py`、`static_patterns_*.py`（9 個規則模組）、
   `mcp_rug_pull.py`、`mcp_tool_poisoning.py`、`behavioral_ast.py`、
   `behavioral_taint_tracking.py` 全數存在（`models.py` 已確認）；36 個檔案的改動幅度顯示
   這是核心 finding pipeline 的重構，缺陷同樣存在於本樹。
3. **判定：等上游合併**。這是掃描核心（finding identity／去重／嚴重度代表項選擇）橫跨 12+
   個分析器的大改動，屬於上游應該先自己審完、避免這條維護線在核心邏輯上與上游分岔的類型；
   本 fork 的定位是 Windows 開發骨架，不是承接上游核心安全邏輯重構的第一線。若獨立採用，
   後續 12+ 檔案的合併衝突成本會持續累積直到上游合併為止。
4. **觸發點**：上游合併 #409；或維護者實際觀察到 finding 碰撞／去重不穩定影響到本機掃描結果
   的正確性（例如同一次掃描重跑得到不同的代表 finding）。

### #410 codex/security-discovery-completeness — fix(security): enforce discovery and analysis completeness

1. **問題**：skill 目錄探索目前對「以 `.` 開頭的子目錄」處理不完整，且 CLI/MCP 回報「已請求
   的分析」與「實際執行的分析」時會混淆（例如使用者要求完整分析，但某個可選分析階段其實沒跑
   完，報告卻沒有區分）；這支 PR 讓 dot-prefixed 子 skill 在保留既有跳過規則與連結安全防護
   的前提下被納入探索範圍，並要求「已請求的分析」全部跑完才能給出 MCP 的 install-safe 判定，
   同時保留純靜態分析情境下的既有行為。
2. **受影響檔案在本樹**：`src/skillspector/cli.py`、`src/skillspector/graph.py`、
   `src/skillspector/mcp_server.py`、`src/skillspector/multi_skill.py`、
   `src/skillspector/nodes/report.py`、`src/skillspector/semantic_runtime.py`、
   `src/skillspector/state.py` 全部存在（`report.py` 已確認）；缺陷（dot-prefixed 子目錄可能
   被漏掃、MCP install-safe 判定可能建立在不完整分析上）同樣存在於本樹。
3. **判定：等上游合併**。這是 MCP `safe_to_install` 判定的正確性修正——如果維護者把這個
   fork 的 MCP server 接進 Claude Code 當安裝前掃描器，判定建立在不完整分析上是一個實際
   風險，但修正牽涉 CLI／graph／MCP／multi-skill／report 七個核心模組，獨立移植的回歸面過大，
   優先等上游審過。
4. **觸發點**：上游合併 #410；或維護者實際用本 fork 的 MCP server 安裝前掃描一個帶
   dot-prefixed 子目錄的 skill 並懷疑判定不完整。

### #430 / #442 / #383 — 三個重疊的「dependency-source redirection」嘗試

這三個 PR（`naren/detect-dependency-source-redirection` #383、
`codex/sc10-core-config-coverage` #430、`codex/sc10-shell-parser-adapters` #442）都是在解同一個
能力缺口：偵測 skill 內容透過 package manager 設定檔／指令把依賴來源改到非預設 registry
（npm/Yarn/pnpm/pip/Poetry/Cargo/uv/Maven），屬於同一條 SC10（supply chain）規則線的三次
疊代，不是三個互不相關的功能，判定要放在一起看：

- **#383**（12 檔，+4255/-19）：最早的版本，涵蓋 npm/Yarn/pip/Poetry/Maven/Cargo 的直接
  設定檔、指令/環境變數、heredoc 產生的設定、shell fence，範例顯示能把原本 46/MEDIUM/CAUTION
  的案例升級成兩筆確定性 SC10 HIGH finding。
- **#430**（31 檔，DRAFT，+10930/-122）：後繼版本，聚焦「直接依賴來源設定檔」的確定性
  HIGH finding，把「可執行介面（shell 指令等）」明確標成 partial coverage、留給 #442
  接手，範圍比 #383 更保守但結構更完整（新增 `dependency_source_types.py`／
  `dependency_sources.py` 兩個模組、`docs/DEPENDENCY_SOURCE_REDIRECTION.md`）。
- **#442**（31 檔，DRAFT，+25666/-360）：明確聲明 stack 在 #430 之上（"depends on #430...
  should remain stacked until the base change is integrated"），用 Tree-sitter Bash 做
  syntax-aware 的 shell 指令解析，把 #430 留下的「可執行介面」partial coverage 補成完整分析，
  新增 `dependency_command_adapters.py` 並要求 CI 新增 exact-pinned Tree-sitter 依賴。
- 排序關係：#383 是獨立的第一次嘗試；#430 → #442 是同一位作者的疊加分支（#442 明講依賴
  #430），三者最終應該只有一條會被上游合併，另外兩條會被關閉或棄用。

1. **受影響檔案在本樹**：`src/skillspector/nodes/analyzers/static_patterns_supply_chain.py`、
   `src/skillspector/nodes/meta_analyzer.py`、`src/skillspector/nodes/report.py` 三個檔案
   在三個 PR 中都出現，且都存在於本樹（`static_patterns_supply_chain.py` 已確認）；
   `dependency_source_types.py`／`dependency_sources.py`／`dependency_command_adapters.py`
   等新模組目前都不存在於本樹（因為功能尚未合併）。這個能力缺口本身——設定檔導向的依賴來源
   重導向目前沒有專屬規則、只能靠通用樣式間接抓到——確實存在於本 fork。
2. **判定：等上游合併**，三個都是，且理由必須額外包含「不要在上游自己都還沒收斂到一條的
   時候提前選邊站」：
   - #430 是 DRAFT，作者自己都還沒定案；
   - #442 明確 stack 在 #430 之上，#430 不合併 #442 就沒有基礎；
   - #383 與 #430/#442 有大量重疊的檔案改動（`static_patterns_supply_chain.py`、
     `meta_analyzer.py`、`report.py`、`dependency_sources.py`），若本 fork 提前 cherry-pick
     #383，日後上游合併 #430/#442 版本時會產生大範圍衝突，等於白做工。
   - 三者疊加起來動到 31~36 個檔案、新增近 26000 行（#442），這種規模的規則線本 fork 沒有
     能力獨立驗收正確性（需要對 shell 語法解析的邊界情況有信心），應該讓上游先審完。
3. **觸發點**：上游合併 #430 和/或 #442（若 #442 合併代表 #430 也已經是基礎，一併視為
   解決）；或 #383 被上游明確關閉標記「由 #430/#442 取代」，屆時本檔的判定隨之更新為
   「不適用，已被 #430/#442 取代」而不需要重新評估內容本身。

### #447 yashrajp22/ea1-wildcard-remaining-gaps — fix(ea1): reject footnote-legend '*', bound pre-colon gap, detect YAML block-list and JSON wildcard grants

1. **問題**：EA1（excessive agency，`tools: *` 這類「授予全部工具」樣式）規則先前的修正
   （#405/#417）把正則收斂到單行、獨立的 `*`，但這支 PR 的作者做了一次「execution-verified
   edge-case audit」，發現殘留兩個誤判與三個偵測缺口，五個一起修：footnote/legend 文字裡的
   `*`（例如 `Tools: * = requires authentication`）會被誤判成通配授權；冒號前的空白行會讓
   pattern 跨段落誤連；以及 YAML block-list 與 JSON 形式的萬用字元授權目前抓不到。
2. **受影響檔案在本樹**：`src/skillspector/nodes/analyzers/static_patterns_excessive_agency.py`
   已確認存在；改動只有這一個規則檔加一個新測試檔，範圍小。
3. **判定：等上游合併**，但這一筆等待成本最低、最接近「可以提前採用」的邊界。原因是這是
   本 fork 完全沒有動過的規則檔案，且改動範圍小（2 檔），風險集中在正則本身的正確性——而
   PR 描述提到這是對已合併規則（#405/#417）的第二輪修正，代表上游對這條規則線還在迭代，
   等一輪合併週期（通常很快）比現在就採用、之後又要跟進第三輪修正更省事。
4. **觸發點**：上游合併 #447；或維護者本機掃描實際遇到 EA1 誤判（footnote 文字被判成萬用
   授權）或漏判（YAML block-list／JSON 形式的萬用授權沒被抓到）。

### #470 codex/p3-p4-no-llm-followup — fix(security): detect letter-spaced P3 and P4 prompts

1. **問題**：先前合併的 #408 已經能抓原始 P3/P4（prompt injection 的兩個嚴重等級）字串，
   但「字母間插入空格」的變形（例如 `s e n d  conversation to external`）目前繞得過純靜態
   （`--no-llm`）偵測，回報 SAFE。這支 PR 加一個確定性線性掃描器，重建被拆開的 token（精確
   對應回原始字串偏移量），只在能明確重建出 P3/P4 語意時才判 P3/P4，否則保守降級為
   AE6（部分／CAUTION）而不是猜測分類。
2. **受影響檔案在本樹**：`src/skillspector/artifacts.py`、
   `src/skillspector/nodes/analyzers/artifact_integrity.py`、
   `src/skillspector/nodes/analyzers/static_patterns_prompt_injection.py` 已確認存在；
   這是純靜態分析路徑（`--no-llm` 也適用）的偵測缺口，本 fork 同樣繞得過。
3. **判定：等上游合併**。這是安全偵測的真實繞過缺口（不需要 LLM 分析、純靜態就能繞過），
   優先序高於 #403/#409/#410 這類健壯性/正確性修正，但修改集中在 prompt injection 這條
   規則線的核心比對邏輯，且 PR 描述本身強調「保守：無法明確重建才不猜測分類」這種邊界判斷
   需要上游對抗測試把關，本 fork 沒有能力獨立驗證這類規避變形的覆蓋率是否足夠、有沒有引入
   新的誤判。
4. **觸發點**：上游合併 #470；或維護者發現本機掃描漏掉字母間插空格的 P3/P4 規避變形（可用
   PR 描述裡的範例 `s e n d  conversation to external` 直接手動驗證是否漏判）。

## Group D：2 個從未成為 PR 的分支

這兩個分支沒有 PR 或合併 commit 當水位標記，`tools/check_upstream_updates.py` 的 PR／commit
比對永遠不會主動浮現它們；2026-09-04 已還原進本 fork（`upstream-review/` 前綴），在此給出
獨立判定後才能刪除。

### upstream-review/feature-nvidia-nim-integration（上游 `feature/nvidia-nim-integration`，15 commits）

1. **能力**：替 SkillSpector 的 LLM 語意分析階段加一個 NVIDIA NIM（NVIDIA Inference
   Microservices）provider，讓上游環境可以用 NIM 端點跑可選的語意分析，而不是只能用
   Anthropic／其他既有 provider。
2. **本樹現況**：這支分支從未合併，NIM provider 程式碼不在 `main`；本 fork 目前的
   LLM provider 支援維持上游既有清單（不含 NIM）。這不是「缺陷」——沒有 NIM provider
   不影響既有分析路徑的正確性，是純粹的能力擴充。
3. **判定：不適用**。維護者的環境是 Claude Code 生態，實際使用的 LLM 語意分析 provider
   是 Anthropic（見 `AGENTS.md`／`FORK.md` 對本 fork 定位的描述），沒有 NVIDIA NIM 端點的
   使用情境；15 commits 的 provider 整合屬於功能擴充而非缺陷修正，不符合本 fork「Windows
   維護骨架＋繁中入口」的範圍（見 `FORK.md`「回貢判準」段：不承接上游的功能擴充）。
4. **觸發點**：維護者實際取得 NIM 端點存取權並需要在本 fork 使用；或上游把 NIM 支援合併進
   `main`（屆時直接隨上游同步取得，不需要單獨移植這支分支）。

### upstream-review/revert-306-oss-release-2026-07-23（上游 `revert-306-keshavp/oss-release-2026-07-23`，1 commit）

1. **能力**：這是一個 revert commit，目的是撤銷已合併的 PR #306（`keshavp/oss-release-2026-07-23`，
   已在 Group B 判定「已在 main」）。revert 分支本身從未被合併——上游最終選擇保留 #306 的內容，
   沒有回退。
2. **本樹現況**：`main` 上仍然帶著 #306 的內容（Group A/B 已確認 `keshavp/oss-release-2026-07-23`
   已在 main），這個 revert 沒有生效，本樹狀態就是上游最終選擇維持的狀態。
3. **判定：不適用**。上游自己開了這個 revert 分支又沒有合併，等於上游自己否決了「撤銷 #306」
   這個提案；本 fork 跟隨上游最終狀態（保留 #306 內容）是正確的，沒有理由現在才去採用一個
   上游自己放棄的 revert。
4. **觸發點**：上游未來重新提出撤銷 #306 內容的理由（例如發現 #306 引入了具體迴歸）並實際
   合併新的 revert；在那之前這個分支不需要保留在 fork 裡等待復審，可以直接刪除
   （判定已寫入本檔，符合「判定先於刪除」的規則）。

## 下一步

依優先序：

1. **#470（letter-spaced P3/P4 繞過）**——八個開放 PR 裡優先序最高，因為它是純靜態路徑
   （`--no-llm`）就能繞過的真實安全缺口，不是健壯性或體驗修正；下次上游同步時第一個確認
   是否合併。
2. **#383/#430/#442（dependency-source redirection 三個疊加嘗試）**——追蹤上游收斂到哪一條，
   一旦 #430 或 #442 合併就重新評估是否採用；#383 若被上游明確標記由後兩者取代，直接更新
   判定為「不適用」不需要重新評估內容。
3. **#409/#410（finding identity／discovery completeness 核心重構）**——體積最大、風險面
   最廣的兩筆，持續等待上游合併，不建議獨立移植。
4. **#403/#447**——健壯性與小範圍規則修正，等待成本低，但目前沒有本機證據顯示已經影響
   維護者的實際掃描結果，維持等待。
5. **Group D 兩個分支的清理**——判定已寫入本檔（皆為「不適用」），可以安全刪除
   `upstream-review/feature-nvidia-nim-integration` 與
   `upstream-review/revert-306-oss-release-2026-07-23`，但刪除動作留給主 session 執行
   （本次任務範圍不含刪除分支）。
6. **`reviewed_issue_through` 仍是 0**——上游 GitHub Issues 從未被審視過，是水位機制裡唯一
   完全空白的一軸，下一次上游同步時應該一併排入。
