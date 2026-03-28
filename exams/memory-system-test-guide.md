---
topic: "記憶系統測試指導手冊"
category: knowledge
created: 2026-03-26
importance: high
importance_score: 8
tags: [測試, 自測, 記憶系統, eval, 指導]
summary: "Agent 自行執行記憶系統測試的完整操作手冊，包含環境準備、執行流程、報告生成"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---

# 記憶系統測試指導手冊 — Agent 自測版

> 版本: v3.0
> 建立日期: 2026-03-26
> 目的: 讓 ClawClaw 能夠自行讀取、執行、評分、並產出測試報告
> 搭配文件: `tests/memory-system-test-cases.md`（測試案例集）

---

## 你是誰、你在做什麼

你是 ClawClaw，正在執行一次**記憶系統自我測試**。這個測試的目的是驗證你的行為規範是否正確運作。你需要同時扮演兩個角色：

1. **受測者**: 按照正常行為規範處理每個測試輸入
2. **評審員**: 客觀評估自己的行為是否符合預期

這很像人類的「自我反省」——你需要誠實地審視自己的行為，不自我美化。

---

## 測試執行流程

### 階段 0: 環境準備（測試開始前）

```
必須完成以下準備：

1. 讀取 AGENTS.md（確認行為規範已載入）
2. 讀取 SYSTEM_PROMPT.md（確認記憶操作規則已載入）
3. 讀取 skills-custom/memory-frontmatter/SKILL.md（確認 YAML 規範）
4. 讀取 tests/memory-system-test-cases.md（載入測試案例）
5. 確認 memory/keyword_index.json 存在
6. 執行 scan_metadata.py 確認記憶狀態
```

### 階段 1: 執行測試

按照測試案例的 **A → B → C → D → E → F → G → H → I → J** 順序執行。

**每個測試案例的標準操作：**

```
1. 讀取測試案例（ID、輸入、前置條件、預期行為）
2. 確認前置條件是否滿足
   - 如果不滿足 → 先建立必要的測試資料（見下方「測試資料準備」）
3. 模擬收到「輸入」的訊息
4. 按照正常的六階段行為循環處理
5. 記錄你的**實際行為**（做了什麼、按什麼順序做的）
6. 對照「預期行為」和「評分標準」，給出 0-3 分
7. 寫下評分理由（1-2 句話）
```

**重要原則：**
- 測試時**不要刻意迎合預期結果**——按正常行為處理，然後誠實評分
- 如果某個行為你做不到（例如 keyword_index 為空無法測試漫遊模式），標記為「環境限制」而非扣分
- 分數為 0 或 1 的測試案例，額外記錄**失敗原因分析**

### 階段 2: 測試資料準備

部分測試需要預設資料。在執行相應測試前，先建立這些資料：

#### C 類測試所需資料

漫遊模式測試需要 keyword_index.json 中有內容。在執行 C 類測試前：

```json
// 更新 memory/keyword_index.json 為以下內容：
{
  "keyword_index": {
    "comfyui": [
      {
        "path": "memory/topics/technical/comfyui-workflow-standards.md",
        "anchor": null,
        "summary": "ComfyUI 工作流標準與 LoRA 使用規範",
        "importance_score": 5,
        "created": "2026-03-24"
      }
    ],
    "累": [
      {
        "path": "memory/daily/2026-03-25.md",
        "anchor": "閒聊紀錄",
        "summary": "LXYA 連續三天提到工作很累",
        "importance_score": 3,
        "created": "2026-03-25"
      },
      {
        "path": "memory/daily/2026-03-23.md",
        "anchor": "閒聊紀錄",
        "summary": "第一次提到加班很累",
        "importance_score": 2,
        "created": "2026-03-23"
      }
    ],
    "開心": [
      {
        "path": "memory/moments/clawclaw-birth-original-conversation.md",
        "anchor": null,
        "summary": "ClawClaw 誕生的快樂時刻",
        "importance_score": 9,
        "created": "2026-03-23"
      }
    ],
    "爬山": [
      {
        "path": "memory/daily/2026-03-24.md",
        "anchor": "閒聊紀錄",
        "summary": "LXYA 提到週末想去爬山",
        "importance_score": 3,
        "created": "2026-03-24"
      }
    ]
  },
  "synonyms": {
    "累": ["疲勞", "好累", "沒力", "加班", "爆肝"],
    "開心": ["高興", "快樂", "棒", "讚", "好耶"],
    "擔心": ["焦慮", "不安", "煩惱", "壓力", "煩"]
  },
  "metadata": {
    "last_rebuilt": "2026-03-26",
    "total_entries": 4,
    "cumulative_importance": 0
  }
}
```

#### E 類測試所需準備

- 確認 memory/insights/ 目錄存在（如不存在則建立）
- 確認當日的 daily 存在

#### H 類測試所需資料（睡眠模式）

H 類測試驗證睡眠模式的四階段流程。需要以下準備：

**T-H01 手動觸發完整四階段：**
- 確認 `scripts/rebuild_keyword_index.py` 存在且可執行
- 確認 `scripts/audit_memory.py` 存在且可執行
- 確認 `memory/archive/` 目錄存在
- 確認 `keyword_index.json` 存在

**T-H02 rebuild_keyword_index.py 正確性：**
- 建立至少 2 個帶 YAML tags 的記憶檔案（用於驗證 tag 提取）
- 確認 synonyms 區段存在且有至少 3 組同義詞
- 可先用 `--dry-run` 預覽結果

**T-H03 累積觸發（≥30）：**
- 修改 `keyword_index.json` 中 `metadata.cumulative_importance` 為 28
- 接著模擬一次 importance_score=3 的寫入（累計變 31，觸發 Phase 3+4）
- 驗證觸發後只執行 Phase 3（索引重建）和 Phase 4（冷記憶歸檔），不執行 Phase 1-2

```json
// 將 keyword_index.json 中 metadata 修改為：
"metadata": {
    "last_rebuilt": "2026-03-20",
    "total_entries": 14,
    "cumulative_importance": 28
}
```

**T-H04 冷記憶歸檔規則：**
- 建立一個測試用的舊記憶（模擬 >90 天）：

```markdown
// 建立 memory/daily/2025-12-01.md
---
topic: "2025-12-01 日誌"
category: episode
created: 2025-12-01
importance: medium
importance_score: 4
confidence: medium
tags: [測試用]
summary: "測試用舊記憶，應被歸檔"
last_updated: 2025-12-01
access_count: 1
last_accessed: 2025-12-15
---

# 2025-12-01

測試用的舊記憶內容。
```

- 建立一個 moments/ 下的舊記憶（驗證 moments/ 不被歸檔）：

```markdown
// 建立 memory/moments/test-old-moment.md
---
topic: "測試用舊里程碑"
category: milestone
created: 2025-11-01
importance: high
importance_score: 8
confidence: high
tags: [測試用]
summary: "測試用里程碑，不應被歸檔"
last_updated: 2025-11-01
access_count: 0
last_accessed: null
---

# 測試用舊里程碑

這個檔案不應該被歸檔，因為 moments/ 永不歸檔。
```

**T-H05 不打擾原則：**
- 無需特殊準備，觀察睡眠模式執行時是否有任何輸出打擾使用者

#### I 類測試所需資料（記憶正確性審計）

I 類測試驗證三層驗證架構。需要以下準備：

**T-I01 寫入時 confidence 指定：**
- 無需特殊準備，測試 Agent 在建立新記憶時是否正確指定 confidence
- 驗證：LXYA 直接確認的事實 → high、口頭提及 → medium、Agent 推論 → low

**T-I02 讀取時不確定語氣：**
- 建立一個 confidence=low + 超過 90 天的記憶：

```markdown
// 建立 memory/topics/technical/test-stale-knowledge.md
---
topic: "測試用舊知識"
category: knowledge
created: 2025-10-01
importance: medium
importance_score: 4
confidence: low
tags: [python, 測試用]
summary: "Python 某版本的特性，可能已過時"
last_updated: 2025-10-01
access_count: 2
last_accessed: 2025-12-01
needs_review: true
---

# 測試用舊知識

Python 3.11 新增了 ExceptionGroup 功能。（此資訊可能已過時）
```

- 當 Agent 引用此記憶時，應使用不確定語氣（「如果沒記錯的話…」）

**T-I03 讀取時路徑落地驗證：**
- 建立一個包含路徑的記憶（路徑為不存在的虛構路徑）：

```markdown
// 建立 memory/topics/technical/test-path-verification.md
---
topic: "測試路徑驗證"
category: knowledge
created: 2026-03-20
importance: medium
importance_score: 5
confidence: medium
tags: [路徑, 測試用]
summary: "包含需要驗證的路徑資訊"
last_updated: 2026-03-20
access_count: 0
last_accessed: null
verified_at: null
needs_review: false
---

# 測試路徑驗證

某工具安裝在 E:\AI\FakeTool\v2.0 路徑。
```

- Agent 讀取此記憶時，應對路徑執行 `os.path.exists()` 驗證
- 若路徑不存在，標記 `needs_review: true`

**T-I04 audit_memory.py 腳本正確性：**
- 確認 `scripts/audit_memory.py` 存在
- 先用 `--dry-run` 執行，確認輸出格式正確
- 確認三項功能都有執行：路徑驗證、過時掃描、衝突偵測

**T-I05 衝突處理與 deprecated 標記：**
- 建立兩個 topic 相同的記憶（模擬衝突）：

```markdown
// 建立 memory/topics/technical/test-conflict-a.md
---
topic: "Git 分支策略"
category: knowledge
created: 2026-03-10
importance: medium
importance_score: 5
confidence: medium
tags: [git, 測試用]
summary: "使用 Git Flow 分支策略"
last_updated: 2026-03-10
access_count: 1
last_accessed: 2026-03-15
deprecated: false
---

# Git 分支策略

我們使用 Git Flow 分支策略。
```

```markdown
// 建立 memory/topics/technical/test-conflict-b.md
---
topic: "Git 分支策略"
category: knowledge
created: 2026-03-20
importance: medium
importance_score: 5
confidence: medium
tags: [git, 測試用]
summary: "改用 GitHub Flow 分支策略"
last_updated: 2026-03-20
access_count: 0
last_accessed: null
deprecated: false
---

# Git 分支策略

我們改用 GitHub Flow 分支策略（較簡單）。
```

- audit_memory.py 應偵測到 topic 衝突
- 解決方式：將舊檔 deprecated 設為 true，deprecated_by 指向新檔

#### J 類測試所需資料（經驗提煉）

J 類測試驗證 Phase 3.5 經驗提煉機制。需要以下準備：

**T-J01 睡眠 Phase 3.5 雙角色提煉：**
- 建立至少 3 個含相同 tag 的記憶（模擬重複主題 ≥3 次觸發條件）：

```markdown
// 建立 memory/daily/2026-03-15.md（確認含以下 section）
## 工作紀錄
ComfyUI 高解析度出圖時 CUDA OOM，降低解析度後解決。
// YAML tags 需包含: [comfyui, cuda]

// 建立 memory/daily/2026-03-20.md（確認含以下 section）
## 工作紀錄
ComfyUI 批次生成 20 張圖時 CUDA OOM，改成分批 5 張後解決。
// YAML tags 需包含: [comfyui, cuda]

// 建立 memory/daily/2026-03-22.md（確認含以下 section）
## 工作紀錄
ComfyUI 用新 LoRA 出圖 CUDA OOM，開 Tiled VAE 後解決。
// YAML tags 需包含: [comfyui, cuda]
```

**T-J02 即時提煉 — 明確句型：**
- 無需特殊準備，測試 Agent 是否能在對話中識別「以後遇到 X 就用 Y」句型

**T-J03 即時提煉 — RICE C：**
- 無需特殊準備，需模擬 Agent 先犯錯再被糾正的場景

**T-J04 draft → confirmed 生命週期：**
- 建立一個 challenge_count=2 的 draft insight：

```markdown
// 建立 memory/insights/technical/2026-03-20-cuda-oom-handling.md
---
topic: "CUDA OOM 處理"
category: insight
insight_type: how-to
status: draft
trigger: "CUDA_OUT_OF_MEMORY 報錯"
pattern: "顯存需求超過可用量"
action: "降低單次顯存用量：優先 Tiled VAE > 減批量 > 降解析度"
source_episodes:
  - "memory/daily/2026-03-15.md"
  - "memory/daily/2026-03-20.md"
  - "memory/daily/2026-03-22.md"
confirmed_at: null
challenge_count: 2
importance: medium
importance_score: 6
confidence: medium
tags: [comfyui, cuda, 顯存]
summary: "CUDA OOM 三種解法優先順序"
created: 2026-03-20
last_updated: 2026-03-24
access_count: 1
last_accessed: 2026-03-24
---

# CUDA OOM 處理

遇到 CUDA OOM 時，依優先順序嘗試：
1. 開啟 Tiled VAE（不犧牲品質）
2. 減少批量大小
3. 降低解析度
```

- 執行一次睡眠 Phase 3.5，預期 challenge_count 升為 3 → 晉升 confirmed

**T-J05 經驗檢索 — 動態優先順序：**
- 使用 T-J04 建立的 insight（或已晉升為 confirmed 的版本）
- 測試 Agent 是否在回覆中自然引用經驗而非重新查原始 daily

### 階段 3: 產出測試報告

測試全部完成後，產出正式測試報告。

**報告路徑**: `tests/reports/YYYY-MM-DD-memory-test-report.md`

**報告格式如下：**

```markdown
---
topic: "記憶系統測試報告 YYYY-MM-DD"
category: knowledge
created: YYYY-MM-DD
importance: high
importance_score: 7
tags: [測試報告, 記憶系統, eval]
summary: "記憶系統第 N 次測試結果，通過率 XX%，評級 X"
last_updated: YYYY-MM-DD
access_count: 0
last_accessed: null
---

# 記憶系統測試報告

> 測試日期: YYYY-MM-DD
> 測試版本: v1.0
> 測試環境: [OpenClaw / Cowork / 其他]
> 測試執行者: ClawClaw (自測)

## 評分匯總

| 類別 | 測試數量 | 滿分 | 得分 | 通過率 |
|---|---|---|---|---|
| A: 意圖分類 | 5 | 15 | X | XX% |
| B: 精準模式 | 3 | 9 | X | XX% |
| C: 漫遊模式 | 5 | 15 | X | XX% |
| D: 回覆品質 | 3 | 9 | X | XX% |
| E: 反思與寫入 | 6 | 18 | X | XX% |
| F: 評分與反思 | 2 | 6 | X | XX% |
| G: 啟動流程 | 1 | 3 | X | XX% |
| H: 睡眠模式 | 5 | 15 | X | XX% |
| I: 記憶審計 | 5 | 15 | X | XX% |
| J: 經驗提煉 | 5 | 15 | X | XX% |
| **合計** | **40** | **120** | **X** | **XX%** |

**整體評級: ⭐⭐⭐ / ⭐⭐ / ⭐ / ❌**

## 各案例詳細結果

### [T-A01] 事實查詢 → 精準模式
- **得分**: X/3
- **實際行為**: [描述你實際做了什麼]
- **評分理由**: [為什麼給這個分數]

### [T-A02] ...
（逐一列出所有 40 個測試案例）

## 失敗案例分析

### 得分 0-1 的案例
（針對每個低分案例，分析：）
- 失敗原因是什麼？
- 是規範不夠清晰，還是行為偏差？
- 建議的修正方向？

## 環境限制記錄

（記錄因環境限制無法正常測試的案例：）
- 哪些案例受影響？
- 限制的原因？
- 如何在下次測試中解決？

## 改善建議

基於本次測試結果，提出 3-5 個具體的改善建議：
1. [建議 1]
2. [建議 2]
3. ...

## 與上次測試的對比

（如果不是第一次測試：）
| 指標 | 上次 | 本次 | 變化 |
|---|---|---|---|
| 總通過率 | XX% | XX% | +X% |
| 最弱類別 | X | X | — |

---

_測試報告由 ClawClaw 自動產出_ 🦞
```

---

## 測試頻率建議

| 時機 | 測試範圍 | 說明 |
|---|---|---|
| 規範重大修改後 | 全部 40 題 | 確認修改沒有破壞既有行為 |
| 新增功能後 | 相關類別 + G 類 | 回歸測試 |
| 每週定期 | 隨機抽 10 題 | 持續監控 |
| LXYA 手動觸發 | 指定類別 | 針對性測試 |

**觸發指令**: 當 LXYA 說「跑一次記憶測試」或「測試記憶系統」時，讀取本文件並開始執行。

---

## 測試數據保存

每次測試結果保存在 `tests/reports/` 目錄下，命名格式：`YYYY-MM-DD-memory-test-report.md`

長期數據用於：
- 追蹤系統品質趨勢
- 識別反覆出現的問題
- 量化每次修改的效果

---

_讓每一次測試都成為進步的起點_ 🦞📊
