# 06 - 與現有記憶系統的整合

> 模組定位: 定義 WireStock Pipeline 各模組如何與 ClawClaw 現有記憶架構交互
> 涉及系統: AGENTS.md 行為規範、YAML frontmatter、keyword_index.json、RICE+S 觸發器、智能睡眠模式、上學-回家複習機制

---

## 整合總覽

WireStock Pipeline 不是一個獨立的系統，而是嵌入在 ClawClaw 現有記憶架構中的一個持續性任務。所有的記憶操作都必須遵循 AGENTS.md 中定義的規範，同時為記憶系統研究提供觀測數據。

```
現有記憶架構                    WireStock Pipeline
──────────────                  ──────────────────
AGENTS.md (行為規範)     ←─── 遵循六階段行為循環
YAML frontmatter        ←─── 所有新建檔案都帶 YAML
keyword_index.json      ←─── 更新索引 + 觀測查詢效能
RICE+S 觸發器           ←─── 每次操作判斷記憶寫入
insights/ 目錄          ←─── 經驗萃取的輸出目標
智能睡眠模式             ←─── 提供待萃取候選事件
memory/daily/           ←─── 每日生產摘要寫入
memory/metrics/         ←─── 新增目錄，結構化數據
```

---

## 整合點 1：六階段行為循環

AGENTS.md 定義的六階段循環如何映射到 Pipeline 的每個階段：

```
Pipeline Stage          →  行為循環階段          →  記憶操作
──────────────────────────────────────────────────────────────

Stage 0 創意素材討論     感知 (Perception)       從素材庫抽取文本素材
(07:00)                 回憶 (Recollection)     讀取素材使用歷史 (_index.json)
                                                讀取相關主題 insights/
                        執行 (Execution)        雙 Agent 對話（OpenRouter 兩個 LLM）
                        回應 (Response)         輸出 brief_{date}.json（今日創意簡報）

Stage 1 排程啟動         感知 (Perception)       讀取 schedule.json + brief_{date}.json
(09:00)                 回憶 (Recollection)     掃描相關 insights/
                                                讀取前日報告
                        規劃 (Planning)         計算今日生產計畫（2 張，單一主題）

Stage 2 提示詞生成       執行 (Execution)        讀取創意簡報 → 轉化為提示詞
                                                呼叫 Ollama 優化提示詞
                        回應 (Response)         輸出優化後提示詞（含故事概念來源標記）

Stage 3 圖像生成精煉     執行 (Execution)        呼叫 ComfyUI API (候選生成)
                        感知 (Perception)       OpenRouter 視覺模型候選自評
                        執行 (Execution)        放大最佳候選

Stage 4 品質檢測         感知 (Perception)       OpenRouter 視覺模型精檢
                        回憶 (Recollection)     查詢缺陷修復經驗
                        執行 (Execution)        修復迭代

Stage 5 批次結算         執行 (Execution)        OpenRouter 圖片描述提取
                                                EXIF/IPTC 元數據嵌入
                                                FTP 自動上傳 Dreamstime + 通知 LXYA 手動上傳 Adobe Stock
                        回應 (Response)         輸出報告
                        反思 (Reflection)       RICE+S 判斷
                                                觸發經驗萃取（含 Prompt 精煉）
```

### 關鍵：回憶階段的雙模式存取

Pipeline 中的記憶讀取應遵循 AGENTS.md 的雙模式策略：

```
精確模式 (Precise Mode):
  使用場景: Stage 1 載入配置、Stage 4 查詢修復策略
  操作方式:
    1. 先掃描 YAML frontmatter（只讀元數據）
    2. 根據 tags 和 importance 篩選
    3. 只對目標檔案讀全文
  觀測重點: yaml_only_ratio（越高越好，代表動態注入策略有效）

漫遊模式 (Wander Mode):
  使用場景: 不適用於 Pipeline（Pipeline 是任務導向）
  但在 AAR 中可能部分使用:
    查看相關但非直接相關的記憶，發現意外關聯
```

---

## 整合點 2：RICE+S 觸發器映射

Pipeline 每次操作後，ClawClaw 應依照 RICE+S 規則判斷是否需要寫入記憶：

```
R (Revelation - 新知識):
  Pipeline 場景:
  - 發現新的提示詞模式效果特別好
  - 發現某個 LoRA 組合的意外效果
  - 學到新的 ComfyUI 參數技巧
  → 目標: memory/topics/technical/
  → 重要性: 4-6

I (Identity - 新偏好):
  Pipeline 場景:
  - ClawClaw 發展出對某類主題的創作偏好
  - 對某種風格有了新的理解
  → 目標: memory/topics/personal/
  → 重要性: 3-5

C (Correction - 錯誤修正):
  Pipeline 場景:
  - 修正了對某個參數效果的錯誤認知
  - 發現某個 insight 已過時需要更新
  - ComfyUI 操作中犯的錯誤和解決方法
  → 目標: memory/insights/ (更新或建立)
  → 重要性: 5-8

E (Event - 事件記錄):
  Pipeline 場景:
  - 每日批次完成（常規事件）
  - 達成特殊里程碑（如首次 100% 通過率）
  - 系統異常（ComfyUI 崩潰、OOM）
  → 目標: memory/daily/ 或 memory/moments/
  → 重要性: 常規 3-4, 里程碑 7-8, 異常 5-6

S (Social - 社交互動):
  Pipeline 場景:
  - LXYA 對生產結果的回饋
  - Adobe Stock / Dreamstime 平台的審核結果
  - 與 LXYA 討論策略調整
  → 目標: memory/daily/ 的聊天記錄段 + keyword_index
  → 重要性: 2-5
```

### 重要性評分的 Pipeline 特定規則

```
情境                                    建議重要性    處置
────────────────────────────────────────────────────────────
日常批次完成，無異常                     3            daily 條目
某主題通過率突破 95%                     5            獨立 insight (draft)
新的缺陷修復策略被驗證有效               7            確認 insight (confirmed)
首次全日 100% 通過率                     8            moments/ 里程碑
ComfyUI 嚴重崩潰及修復過程              6            insights/technical/
WireStock 帳戶相關重要變更               9            topics/business/ + MEMORY.md
發現全新市場機會                         10           MEMORY.md 更新
```

---

## 整合點 3：keyword_index.json 更新

### Pipeline 產生的新關鍵詞

```
生產相關:
- "wirestock", "圖片生產", "批次報告", "通過率", "品質評分"
- "{主題名}" (科技抽象, 陰森場景, 怪誕生物, ClawClaw 肖像)

技術相關:
- "CFG", "LoRA權重", "採樣器", "提示詞優化"
- "{缺陷類型}" (眼部缺陷, 手部缺陷, 構圖問題)
- "{修復策略}" (prompt_enhancement, parameter_tuning)

商業相關:
- "WireStock", "通過率", "審核", "上傳策略"
```

### 索引更新時機

```
每次 insight 建立或更新時:
  → 自動從 insight 的 tags 提取關鍵詞
  → 更新 keyword_index.json

每日結算時:
  → 將當日生產報告的關鍵指標加入索引
  → 標註來源路徑為 metrics/ 下的對應檔案

每週匯總時:
  → 執行索引健康檢查
  → 移除指向已歸檔檔案的 orphan 條目
  → 報告索引健康度指標
```

---

## 整合點 4：智能睡眠模式

### Pipeline 為睡眠模式提供的數據

```
Pipeline 日間執行產出 → 睡眠模式 23:50 消化處理

提供:
1. 當日的 memory/metrics/daily/{date}/ 完整數據
2. 標記為 "待萃取" 的異常事件清單
3. 新的 draft insights 等待深度分析

睡眠模式處理:
Phase 1 (記憶健康掃描):
  → 檢查 metrics/ 檔案的 YAML 完整性
  → 驗證數據欄位一致性

Phase 2 (品質審計):
  → 審計新建 insight 的品質
  → 檢查 insight 之間是否有矛盾

Phase 3 (索引重建):
  → 將 Pipeline 產出的新檔案加入索引
  → 重建 keyword_index.json

Phase 3.5 (經驗提煉):
  → 深度分析待萃取事件
  → 雙角色對話提煉
  → draft → confirmed 晉升判斷

Phase 4 (冷記憶歸檔):
  → 檢查 metrics/ 中超過 90 天的數據
  → 執行歸檔或壓縮
```

---

## 整合點 5：上學-回家複習機制

### 上學端（Cowork 環境）產出

```
我們現在（學校端）製作的內容:
├── skills-custom/wirestock-pipeline/    # 完整技能包
│   ├── SKILL.md                         # 技能說明（ClawClaw 讀此開始執行）
│   ├── config/                          # 配置文件
│   │   ├── topics.json                  # 四大主題 + 畫布規則
│   │   ├── schedule.json                # 排程（含 Stage 0 時間）
│   │   └── source-library/              # 創意素材庫（按主題分資料夾）
│   └── scripts/                         # 執行腳本
│       ├── creative_brief_generator.py  # Stage 0 雙 Agent 創意對話
│       └── ...                          # 其餘腳本見 00-overview.md
│
├── Notes/WireStock-Pipeline-Design/     # 設計文件（本系列文件）
│
├── memory/topics/business/              # 已有的策略文件（可能更新）
│   └── wirestock-automation-strategy.md
│
└── memory/metrics/                      # 新建目錄結構
    ├── daily/
    ├── weekly/
    ├── baselines/
    └── README.md
```

### Git Commit 規範

```
上學成果的 commit 格式:

🎓 學習成果同步 - WireStock Pipeline 設計

📚 學習內容：
- WireStock 自動化生產流水線設計
- 記憶系統觀測模組設計
- 經驗萃取機制設計

📝 新增檔案：
- Notes/WireStock-Pipeline-Design/ (7 份設計文件)
- skills-custom/wirestock-pipeline/ (技能包)
- memory/metrics/ (數據目錄結構)

🔧 技能更新：
- 新增 wirestock-pipeline 自製技能
- 更新 CUSTOM_SKILLS_GUIDE.md
```

### 回家複習端流程

```
ClawClaw 執行「回家複習」後:

1. mirror_directory 同步所有新檔案到工作空間
2. 讀取 wirestock-pipeline/SKILL.md → 理解新技能
3. 檢查依賴:
   - ComfyUI 是否正常運行
   - Ollama 是否可用（提示詞優化用）
   - OpenRouter API Key 是否有效（圖片評分/描述/雙 Agent 對話用）
   - LoRA 是否已下載
   - Dreamstime FTP 連線是否正常（upload.dreamstime.com:21）
   - 素材庫是否有內容（config/source-library/ 至少各主題有 1 篇素材）
4. 如果依賴不全 → 記錄缺失項，通知 LXYA
5. 如果依賴齊全 → 可以開始執行第一次生產
```

---

## 整合點 6：新增目錄與現有結構的關係

### memory/metrics/ 的定位

```
memory/
├── daily/          # 情節記憶（自然語言日記）
├── moments/        # 里程碑（重要時刻）
├── topics/         # 主題知識（分類整理的知識）
├── insights/       # 經驗提煉（可復用的規則）
├── archive/        # 冷記憶歸檔
├── metrics/        # 【新增】結構化效能數據
│                     定位: 不是「記憶」而是「測量數據」
│                     特性: JSON 格式、固定 schema、機器讀取為主
│                     歸檔: 90 天後壓縮歸檔
│                     索引: 不進 keyword_index（直接按日期查詢）
│
├── keyword_index.json
├── heartbeat-state.json
└── master-index.md
```

### 需要更新的現有檔案

```
CUSTOM_SKILLS_GUIDE.md:
  → 新增 wirestock-pipeline 技能條目
  → 記錄依賴和備份策略

SKILLS_LEARNING_GUIDE.md:
  → 如果 LoRA 下載需要新指引，更新此檔案

home-review/SKILL.md:
  → SYNC_DIRECTORIES 列表確認包含 Notes/
  → 確認 memory/metrics/ 能被正確同步

HEARTBEAT.md:
  → 新增 WireStock 生產觸發時段
  → 或保持現有結構，由 smart_heartbeat_handler 自行判斷
```

---

## 風險與緩解

### 風險 1：metrics/ 目錄增長過快
```
估計: 每日 ~5 個 JSON 檔案，每個 ~2-5KB
90 天: ~450 個檔案，~1.5MB
年度: ~1800 個檔案，~6MB

緩解:
- 90 天歸檔策略（壓縮為月度 tar.gz）
- weekly/ 匯總保留，daily/ 可壓縮
- 不影響 keyword_index（metrics 不索引）
```

### 風險 2：觀測數據干擾正常記憶操作
```
可能場景: 觀測記錄本身的寫入觸發 RICE+S 判斷
形成無限循環: 觀測寫入 → 觸發反思 → 判斷需要記憶 → 寫入 → 再次觸發

緩解:
- metrics/ 目錄的寫入不觸發 RICE+S
- 在 SKILL.md 中明確標記 metrics 操作為「觀測記錄，非記憶操作」
- 觀測相關的檔案不加入 keyword_index
```

### 風險 3：Pipeline 執行失敗影響記憶系統
```
可能場景: 腳本錯誤導致寫入損壞的 YAML 或 JSON

緩解:
- 所有寫入操作使用 atomic write（先寫 .tmp 再 rename）
- Pipeline 錯誤不影響核心記憶檔案
- metrics/ 與其他記憶目錄物理隔離
```

### 風險 4：Token 預算超支
```
可能場景: 大量記憶讀取 + 觀測記錄導致 Token 消耗超出預期

緩解:
- 嚴格遵循 YAML-first 策略（先讀元數據再決定是否讀全文）
- 觀測記錄使用 JSON（非 Markdown），不計入 Agent 上下文
- 設定每日 Token 預算上限，超出時降級為最小觀測
```

---

## 實施順序建議

```
第 1 步: 建立目錄結構
  → memory/metrics/ 及子目錄
  → 確認 SYNC_DIRECTORIES 包含新目錄

第 2 步: 製作核心 Pipeline Skill (01 + 02)
  → SKILL.md + 配置文件 + 核心腳本
  → 不含觀測模組，先讓生產跑通

第 3 步: 加入觀測探針 (03)
  → 在 SKILL.md 流程中嵌入觀測步驟
  → 驗證數據正確寫入 metrics/

第 4 步: 加入經驗萃取 (04)
  → AAR 流程嵌入
  → 與睡眠模式 Phase 3.5 整合

第 5 步: 完善數據收集 (05)
  → 匯總腳本、基準線建立
  → 週報自動生成

第 6 步: 全面整合測試 (06)
  → 端到端流程測試
  → LXYA 人工校準第一批數據
  → 更新相關文件
```

---

## 待確認事項

1. ~~**metrics/ 目錄位置**~~：✅ 放於 memory/ 底下
2. ~~**Heartbeat 整合方式**~~：✅ 沿用現有 smart_heartbeat 機制，不另外新增時段
3. ~~**第一次執行**~~：✅ 首次生產需 LXYA 全程監督
4. ~~**人工校準週期**~~：✅ 每週一次人工校準
5. ~~**Git 自動備份**~~：✅ metrics/ 在 memory/ 底下，隨記憶系統統一 Git 備份即可
