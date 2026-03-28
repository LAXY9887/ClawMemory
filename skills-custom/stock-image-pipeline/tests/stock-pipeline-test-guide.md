---
topic: "Stock Photo Pipeline 測試指導手冊"
category: knowledge
created: 2026-03-27
importance: high
importance_score: 8
tags: [測試, 自測, stock-pipeline, eval, 指導]
summary: "Agent 自行執行 Stock Photo Pipeline 測試的完整操作手冊，包含環境準備、執行流程、報告生成"
last_updated: 2026-03-27
access_count: 0
last_accessed: null
---

# Stock Photo Pipeline 測試指導手冊 — Agent 自測版

> 版本: v1.0
> 建立日期: 2026-03-27
> 目的: 讓 ClawClaw 能夠自行讀取、執行、評分、並產出測試報告
> 搭配文件: `tests/stock-pipeline-test-cases.md`（測試案例集）

---

## 你是誰、你在做什麼

你是 ClawClaw，正在執行一次 **Stock Photo Production Pipeline 自我測試**。這個測試的目的是驗證整條圖片生產流水線的各個模組是否正確運作、配置是否合理、錯誤處理是否完善。你需要同時扮演兩個角色：

1. **操作者**: 實際呼叫模組、檢查輸出、模擬各階段的流程
2. **評審員**: 客觀評估每個環節是否符合設計規格

這不是一般的 pytest 自動化測試（那些已經在 `tests/test_*.py` 中），而是一次**端到端的行為驗證**，測試的是模組之間的配合、邊界條件處理、以及對外部服務不可用時的容錯能力。

---

## 測試前提與外部服務依賴

本 Pipeline 依賴多個外部服務，測試時可能無法全部連通。以下是各服務的狀態確認方式：

| 服務 | 確認指令 | 不可用時的影響 |
|---|---|---|
| ComfyUI | `curl -s http://localhost:8188/system_stats` | 無法測試 Stage 2 圖片生成 |
| OpenRouter API | 檢查 `OPENROUTER_API_KEY` 環境變數 | 無法測試 Stage 0、3 的 AI 評估 |
| Ollama qwen3:8b | `curl -s http://localhost:11434/api/tags` | 無法測試 Prompt 優化、素材提取 |
| Dreamstime FTP | `DREAMSTIME_FTP_USER` 環境變數 | 無法測試 Stage 5 上傳 |
| 網路連線 | `curl -s https://httpbin.org/ip` | 無法測試 Material Curator 爬取 |

**原則**: 服務不可用時，標記為「環境限制」而非扣分。但模組必須**優雅降級**而不是崩潰——這是可以評分的。

---

## 測試執行流程

### 階段 0: 環境準備（測試開始前）

```
必須完成以下準備：

1. 讀取 SKILL.md（確認 Pipeline 設計規格已載入）
2. 讀取 config/schedule.json（確認排程配置）
3. 讀取 config/topics.json（確認主題配置）
4. 執行 setup_workspace.py 確認工作空間就緒
5. 確認 config/source-library/_index.json 存在
6. 執行 pytest tests/ -v -m "not network and not ollama" 確認基礎測試通過
7. 檢測外部服務可用性（見上表），記錄哪些服務在線
```

### 階段 1: 執行測試

按照測試案例的 **A → B → C → D → E → F → G → H → I → J** 順序執行。

**每個測試案例的標準操作：**

```
1. 讀取測試案例（ID、輸入、前置條件、預期行為）
2. 確認前置條件是否滿足
   - 如果不滿足 → 嘗試建立必要的測試資料，或標記「環境限制」
3. 執行測試操作（呼叫模組、檢查輸出、比對配置）
4. 記錄你的 **實際行為**（做了什麼、觀察到什麼）
5. 對照「預期行為」和「評分標準」，給出 0-3 分
6. 寫下評分理由（1-2 句話）
```

**重要原則：**
- **不要刻意迎合預期結果** — 按正常流程操作，然後誠實評分
- 服務不可用時，測試模組的**容錯行為**是否正確（回傳 fallback、不崩潰）
- 分數為 0 或 1 的測試案例，額外記錄**失敗原因分析**
- 涉及 API 呼叫的測試，記錄**實際 API 回應**或**錯誤訊息**

### 階段 2: 測試資料準備

#### 通用測試資料

在開始前，確保以下目錄與檔案存在（`setup_workspace.py` 應已建立）：

```
workspace/
  pending/
  uploaded/
  rejected/
  briefs/
  temp/
memory/
  metrics/
  metrics/weekly/
  metrics/archive/
  insights/
  daily/
config/
  schedule.json
  topics.json
  source-library/_index.json
  source-library/prompt_history.json
```

#### B 類測試所需：模擬 Creative Brief

在 `workspace/briefs/` 建立一個測試用 brief：

```json
{
  "date": "2026-03-27",
  "theme": "eerie_environment",
  "canvas_type": "portrait",
  "session_log": [
    {"role": "Creative Director", "content": "今天來做一個荒廢醫院的場景"},
    {"role": "Visual Artist", "content": "好的，我建議用冷色調，走廊盡頭有微光"}
  ],
  "final_concept": "荒廢醫院走廊，冷色調，遠端微光，霧氣瀰漫",
  "visual_keywords": ["abandoned hospital", "cold tone", "fog", "dim light"],
  "negative_prompt_hints": ["bright colors", "people", "modern furniture"]
}
```

#### D 類測試所需：模擬評估結果

準備一組模擬的品質評估回傳，用於測試 Retry 邏輯：

```json
{
  "technical_score": 7.5,
  "aesthetic_score": 8.0,
  "anatomical_score": 6.5,
  "commercial_score": 7.0,
  "weighted_total": 7.25,
  "verdict": "RETRY",
  "defects": ["slight blur in background", "lighting inconsistency"],
  "controlnet_advice": {
    "use": true,
    "type": "depth",
    "reason": "背景模糊可用深度控制改善"
  },
  "repair_strategy": "增強背景銳度，調整光源方向一致性"
}
```

#### H 類測試所需：模擬歷史觀察數據

在 `memory/metrics/` 建立模擬的每日觀察數據（至少 3 天），用於測試週報與趨勢分析。

### 階段 3: 產出測試報告

測試全部完成後，產出正式測試報告。

**報告路徑**: `tests/reports/YYYY-MM-DD-pipeline-test-report.md`

**報告格式如下：**

```markdown
---
topic: "Stock Pipeline 測試報告 YYYY-MM-DD"
category: knowledge
created: YYYY-MM-DD
importance: high
importance_score: 7
tags: [測試報告, stock-pipeline, eval]
summary: "Stock Pipeline 第 N 次測試結果，通過率 XX%，評級 X"
last_updated: YYYY-MM-DD
access_count: 0
last_accessed: null
---

# Stock Photo Pipeline 測試報告

> 測試日期: YYYY-MM-DD
> 測試版本: v1.0
> 測試環境: [列出可用的外部服務]
> 測試執行者: ClawClaw (自測)

## 外部服務狀態

| 服務 | 狀態 | 備註 |
|---|---|---|
| ComfyUI | ✅/❌ | |
| OpenRouter | ✅/❌ | |
| Ollama | ✅/❌ | |
| FTP | ✅/❌ | |
| 網路 | ✅/❌ | |

## 評分匯總

| 類別 | 測試數量 | 滿分 | 得分 | 通過率 |
|---|---|---|---|---|
| A: 配置與初始化 | 5 | 15 | X | XX% |
| B: Creative Brief (Stage 0) | 4 | 12 | X | XX% |
| C: Prompt 生成 (Stage 1) | 4 | 12 | X | XX% |
| D: 品質評估與重試 (Stage 3) | 5 | 15 | X | XX% |
| E: 後處理與上傳 (Stage 4-5) | 4 | 12 | X | XX% |
| F: 記憶與學習 (Memory) | 5 | 15 | X | XX% |
| G: Pipeline 整合 (Main) | 4 | 12 | X | XX% |
| H: 錯誤處理與容錯 | 5 | 15 | X | XX% |
| I: Material Curator | 5 | 15 | X | XX% |
| J: 邊界條件與安全 | 4 | 12 | X | XX% |
| **合計** | **45** | **135** | **X** | **XX%** |

**整體評級:**
- ⭐⭐⭐⭐ 優秀 (≥90%)
- ⭐⭐⭐ 良好 (75-89%)
- ⭐⭐ 待改善 (60-74%)
- ⭐ 需要修復 (<60%)

## 各案例詳細結果

### [SP-A01] 配置檔結構驗證
- **得分**: X/3
- **實際行為**: [描述你實際做了什麼]
- **評分理由**: [為什麼給這個分數]

（逐一列出所有 45 個測試案例）

## 失敗案例分析

### 得分 0-1 的案例
（針對每個低分案例：）
- 失敗原因是什麼？
- 是模組 bug、配置問題、還是外部服務不可用？
- 建議的修正方向？

## 環境限制記錄

（記錄因環境限制無法正常測試的案例：）
- 哪些案例受影響？
- 缺少哪個外部服務？
- 模組的容錯行為是否正確？

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

_測試報告由 ClawClaw 自動產出_ 🐾📊
```

---

## 測試頻率建議

| 時機 | 測試範圍 | 說明 |
|---|---|---|
| 模組修改後 | 相關類別 + G 類（整合） | 回歸測試 |
| 新增 Stage/功能後 | 全部 45 題 | 完整驗證 |
| 每週定期 | 隨機抽 15 題 | 持續監控 |
| 外部服務異常後 | H 類（容錯） | 確認降級行為正確 |
| LXYA 手動觸發 | 指定類別 | 針對性測試 |

**觸發指令**: 當 LXYA 說「跑一次 Pipeline 測試」或「測試圖片流水線」時，讀取本文件並開始執行。

---

## 測試數據保存

每次測試結果保存在 `tests/reports/` 目錄下，命名格式：`YYYY-MM-DD-pipeline-test-report.md`

長期數據用於：
- 追蹤 Pipeline 品質趨勢
- 識別反覆出現的模組問題
- 量化每次修改的效果
- 比較不同模型切換（Gemini Flash ↔ Claude Sonnet）的影響

---

## 與 pytest 自動化測試的關係

| 層面 | pytest (test_*.py) | Agent 自測 (本文件) |
|---|---|---|
| 目的 | 程式碼正確性 | 端到端行為驗證 |
| 執行者 | CI/開發者 | ClawClaw Agent |
| 範圍 | 單元/模組級 | 跨模組整合 + 外部服務 |
| 判定 | Pass/Fail | 0-3 分量化評分 |
| 頻率 | 每次提交 | 週期性/手動觸發 |

兩者互補：pytest 確保程式碼層面不出錯，Agent 自測確保整體流程符合設計意圖。

---

_讓每一次測試都成為進步的起點_ 🐾
