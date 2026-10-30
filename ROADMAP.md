# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-10-29 依 `main` `b0e7b1c0b572` 查的快照，開工前先重查 GitHub。

## 現況
SkillSpector 是 skill 安裝前的供應鏈掃描器，提供靜態分析與選配 LLM 分析，fork 維持 Windows 驗收與明列的分岔（[AGENTS](AGENTS.md)、[分岔登記](docs/DIVERGENCE.md)）。2026-10-29 `gh` 查詢顯示 CI、CodeQL、Upstream check 最近成功，Dependabot／Code scanning 均為 0。2026-10-30 完成 release 軸審查與 PR／issue 分流（[維護決策](docs/DECISIONS.md)）：查核上游 v2.13.0–v2.13.2 為獨立維護分支未合入 main，主線維持對齊 `upstream/main`；52 筆 commit（至 `54921c8c`）整批延後、未逐筆裁決，commit 水位維持 `d7338f58`，待中期 fingerprint 協調（PR #903–#952 共 31 筆、issue #902–#951 共 18 筆已分流），`-Quick` 閘門通過，分岔登記 14 筆維持一致。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 逐筆裁決 `d7338f58..54921c8c` 的 52 筆 commit | 2026-10-30 審查將 52 筆整批延後、未逐筆裁決；commit 水位仍是 `d7338f58` | 清冊逐筆裁決（commit SHA 或對應 PR → 裁決 → 涉及的掃描契約，如 OH1／P2／PE3／MP3／TP4）；裁決寫入 docs/DECISIONS.md；採用者通過 Quick 與完整 Windows gate 才推進 commit 水位 | Codex | docs/DECISIONS.md「2026-10-30」第 2 點；docs/UPSTREAM.md |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 配合新掃描器版本安排下游 pin 與 fingerprint 驗收 | 決定採用會改版本或掃描契約的上游更新 | 向 agent-skills、book-to-skill、agent-marketing-skills 維護者提供版本與原因碼差異；各下游在自己的任務核對可取得的精確 commit、重產 fingerprint，正常 gate 通過，不在本 repo 代改 | Codex | docs/DECISIONS.md:448-450 |
| 上游涵蓋 fork 修補後解除分岔 | 上游合併對應產品／測試修正或鎖檔含必要安全版本 | 逐列按解除條件取上游版本，`check_divergence.py` 與 `check_pin_bounds.py` 通過，完整 Windows gate 無新增失敗，不擴大 skip | Codex | [分岔登記](docs/DIVERGENCE.md)；docs/DECISIONS.md:423-444 |
| 對實際 provider／MCP 路徑做有限驗收 | 維護者要採用該整合，並備妥登入或付費後端 | 先約定單一測試 skill 與用量上限；確認掃描建議、完整性欄位與 MCP 回傳可用，未呼叫的 provider 不宣稱已驗證 | 維護者 | AGENTS.md「tests」「canonical gate」；src/skillspector/mcp_server.py |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 為 Windows 便利放寬安全寫檔或以平台名稱全面跳過測試 | `--output` 拒絕與能力探測是既有安全契約，見 docs/DECISIONS.md:437-439 | 上游提供 Windows 安全寫檔實作並有回歸證據 |
| 從同名 PyPI 套件安裝，或任意提高上游依賴下限 | 安裝來源與相容性理由見 README.md、docs/DECISIONS.md、docs/DIVERGENCE.md | 有已驗證的官方發行來源；依賴變更需上游同步或已登記安全修補 |
| 沿用舊 code scanning 告警作為仍開放的修復工作 | 2026-10-29 `gh` 查詢已無 open 告警，不能猜測解除原因 | `gh api repos/SanHsien/SkillSpector/code-scanning/alerts?state=open` 再次回報告警 |
| 為無共同祖先改寫歷史或自動發布 fork | FORK.md 已有內容差異同步程序，未要求獨立發版 | 維護者另行授權政策變更 |

## 維護方式
每週依 [FORK.md](FORK.md) 從已審水位審上游，衝突依 [分岔登記](docs/DIVERGENCE.md) 判斷；每月檢視新鮮度，安全公告另查 `gh api repos/SanHsien/SkillSpector/dependabot/alerts?state=open`。
Windows 驗證先跑 `pwsh -NoProfile -File tools/dev_check.ps1 -Quick`，產品同步再跑完整模式；沿用 AGENTS.md 的獨立環境與 copy 安裝，勿設全域共用虛擬環境。