# Memory Frontmatter: 記憶元數據標準化系統

ClawClaw 記憶檔案的 YAML Frontmatter 規範與工具集，為記憶系統提供自描述能力。

## Core Mission

讓每一個記憶檔案都具備結構化的元數據，使 Agent 能夠：
1. **不讀全文就篩選檔案**（節省 Token）
2. **自動分類與排序**（冷熱分離基礎）
3. **追蹤記憶的生命週期**（存取頻率、新鮮度、重要性）
4. **建立記憶間的關聯**（脈絡鏈）

## YAML Schema 規範

### 完整欄位定義

```yaml
---
# === 必填欄位 ===
topic: "主題描述"                    # 簡短主題（2-8 個字）
category: episode                    # 見下方「類別定義」
created: 2026-03-26                  # 建立日期 (YYYY-MM-DD)

# === 建議填寫 ===
importance: medium                   # critical | high | medium | low
importance_score: 5                  # RICE 檢查評定的 1-10 分數（1-3=low, 4-6=medium, 7-9=high, 10=critical）
tags: [comfyui, error]               # 自由標籤，用於交叉搜尋
summary: "一句話描述此記憶的核心內容"  # 供掃描時快速預覽

# === 系統自動維護 ===
last_updated: 2026-03-26             # 最後修改日期
access_count: 0                      # 被引用次數（Agent 每次讀取時 +1）
last_accessed: null                  # 最後存取日期

# === 驗證相關 ===
confidence: medium                   # high | medium | low（見下方「信心等級」）
verified_at: null                    # 最後一次環境落地驗證日期
needs_review: false                  # 是否需要人工審核

# === 選填欄位 ===
related_files:                       # 關聯檔案路徑
  - memory/daily/2026-03-25.md
prev_event: null                     # 前因事件路徑（脈絡鏈）
next_event: null                     # 後續事件路徑（脈絡鏈）
deprecated: false                    # 是否已過時
deprecated_by: null                  # 被哪個新記憶取代
source_ref: null                     # 原始對話來源（如有）
---
```

### 類別定義 (category)

| 值 | 說明 | 對應路徑 | 預設 importance |
|---|---|---|---|
| `episode` | 日常事件記錄 | `memory/daily/` | medium |
| `milestone` | 重要里程碑、突破時刻 | `memory/moments/` | high |
| `knowledge` | 技術知識、操作標準 | `memory/topics/technical/` | medium |
| `preference` | 個人偏好、行為原則 | `memory/topics/personal/` | high |
| `insight` | 經驗教訓、通用規則、抽象概念 | `memory/insights/{technical,personal}/` | medium~high |
| `index` | 索引/導航檔案 | 各層級 *-index.md | low |
| `project_summary` | 專案總結 | `memory/daily/` | medium |

### importance 等級定義

| 等級 | 意義 | 保留策略 |
|---|---|---|
| `critical` | 核心身份、不可遺失 | 永不歸檔、永不刪除 |
| `high` | 重要偏好、教訓、里程碑 | 長期保留，進入 hot-cache |
| `medium` | 一般事件記錄、技術筆記 | 正常生命週期，可歸檔 |
| `low` | 索引、臨時筆記、冗餘紀錄 | 優先歸檔候選 |

### confidence 信心等級定義

| 等級 | 意義 | 判定條件 | Agent 引用語氣 |
|---|---|---|---|
| `high` | 經過環境驗證或 LXYA 明確確認 | 路徑用 `os.path.exists()` 驗證通過；LXYA 直接下達明確指示 | 直述句：「ComfyUI 的路徑是 E:/AI/ComfyUI」 |
| `medium` | LXYA 口頭提及但未驗證 | LXYA 在對話中說了，但 Agent 無法獨立驗證 | 帶來源：「你之前提到 ComfyUI 在 E 槽」 |
| `low` | Agent 自行推論或記憶老舊 | Agent 從上下文推測；記憶超過 90 天未更新且未驗證 | 不確定語氣：「如果沒記錯的話…」 |

**環境落地驗證（Environmental Grounding）：**
- 當前支援：路徑類事實（`os.path.exists()`、`ls` 檢查）
- 未來可擴充：版本號驗證（`python --version`）、服務狀態（`ping`）、設定值驗證
- 驗證通過 → confidence 升為 `high`，更新 `verified_at`
- 驗證失敗 → 標記 `needs_review: true`，不自行修改內容（等 LXYA 確認）

## 各類別 YAML 模板

### 日常記錄 (episode)
```yaml
---
topic: "YYYY-MM-DD 日誌"
category: episode
created: 2026-03-26
importance: medium
importance_score: 5
confidence: medium
tags: []
summary: "今日主要事項的一句話摘要"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
prev_event: memory/daily/2026-03-25.md
next_event: null
---
```

### 里程碑 (milestone)
```yaml
---
topic: "事件名稱"
category: milestone
created: 2026-03-26
importance: high
importance_score: 8
confidence: high
tags: []
summary: "這個里程碑的意義"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
related_files: []
---
```

### 技術知識 (knowledge)
```yaml
---
topic: "技術主題"
category: knowledge
created: 2026-03-26
importance: medium
importance_score: 5
confidence: medium
tags: []
summary: "這份知識的核心要點"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
verified_at: null
source_ref: null
---
```

### 個人偏好 (preference)
```yaml
---
topic: "偏好主題"
category: preference
created: 2026-03-26
importance: high
importance_score: 7
confidence: medium
tags: []
summary: "LXYA 的具體偏好描述"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---
```

### 經驗提煉 (insight)
```yaml
---
topic: "經驗主題"
category: insight
insight_type: how-to              # how-to | pattern | preference | observation
status: draft                     # draft | confirmed
trigger: ""                       # 觸發因子（無則空字串）
pattern: ""                       # 共通模式（無則空字串）
action: ""                        # 對策/結論（無則空字串）
source_episodes:                  # 來源記憶檔案路徑
  - "memory/daily/2026-03-15.md"
confirmed_at: null                # status 變 confirmed 時填入日期
challenge_count: 0                # 連續未被修改的睡眠次數，達 3 則晉升
importance: medium
importance_score: 6
confidence: medium
tags: []
summary: "這條經驗的一句話摘要"
created: 2026-03-26
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---
```

**insight_type 定義：**

| 類型 | 說明 | trigger/pattern/action 用法 |
|---|---|---|
| `how-to` | 操作型經驗：遇到 X 做 Y | 三欄位都填 |
| `pattern` | 模式辨識型：X 通常伴隨 Y | trigger + pattern 填，action 可空 |
| `preference` | 偏好概念型：LXYA 偏好 X | pattern 填偏好描述，trigger/action 可空 |
| `observation` | 觀察型：注意到 X 現象 | pattern 填觀察，trigger/action 可空 |

**生命週期：**
- `status: draft` → 睡眠 Phase 3.5 每次審閱無矛盾 → `challenge_count` +1 → 達 3 晉升 `confirmed`
- 產出時機：睡眠 Phase 3.5（同 tag/topic ≥3 次）或即時提煉（LXYA 明確句型 / RICE C）
- 檔案路徑：`memory/insights/{technical,personal}/YYYY-MM-DD-[主題].md`

### 索引檔案 (index)
```yaml
---
topic: "索引名稱"
category: index
created: 2026-03-26
importance: low
last_updated: 2026-03-26
---
```

（索引檔案不需要 importance_score，因為索引本身不由 RICE 觸發產生。）

## Agent 行為規範

### 建立新記憶時
1. **必須**在檔案最頂部加入 YAML frontmatter
2. **必須**填寫所有「必填欄位」
3. **建議**填寫 `summary`（方便未來掃描）
4. **建議**填寫 `tags`（方便交叉搜尋）
5. 若此記憶與前一事件有因果關係，填寫 `prev_event`

### 讀取記憶時
1. 優先使用 `scan_metadata.py` 掃描 YAML 摘要
2. 確定目標檔案後才讀取全文
3. 讀取後將 `access_count` +1、更新 `last_accessed`
（注意：access_count 更新在 openClaw 環境中由 Agent 手動執行或由心跳任務批次更新）

### 記憶衝突時
1. 新記憶與舊記憶衝突 → 在舊檔 YAML 中設 `deprecated: true`
2. 填寫 `deprecated_by: [新檔案路徑]`
3. 不直接刪除舊檔案

## Scripts 使用說明

### validate_frontmatter.py — 規範驗證
```bash
# 驗證所有記憶檔案
python scripts/validate_frontmatter.py

# 驗證特定檔案
python scripts/validate_frontmatter.py --file memory/daily/2026-03-26.md

# JSON 格式輸出
python scripts/validate_frontmatter.py --format json
```

### scan_metadata.py — 元數據掃描
```bash
# 掃描所有記憶，輸出 YAML 摘要
python scripts/scan_metadata.py

# 按重要性篩選
python scripts/scan_metadata.py --importance high

# 按類別篩選
python scripts/scan_metadata.py --category episode

# 找出冷記憶（90天未存取）
python scripts/scan_metadata.py --cold

# 輸出為 JSON（供其他腳本使用）
python scripts/scan_metadata.py --format json
```

## 與其他 Skills 的整合

- **memory-backup**: 備份時自動跑一次 validate，確保品質
- **school-learning**: 同步學習成果時，新檔案自動帶 YAML
- **home-review**: 還原時驗證 YAML 完整性
- **睡眠模式**: 基於 `importance` + `category` + `access_count` 決定歸檔策略
- **記憶審計**: 基於 `confidence` + `verified_at` + `needs_review` 進行正確性驗證
- **audit_memory.py**: 路徑類記憶環境落地驗證腳本

---

**讓每一條記憶都有自己的身份證！** 🦞📋
