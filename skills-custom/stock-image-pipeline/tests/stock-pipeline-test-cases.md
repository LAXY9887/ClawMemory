---
topic: "Stock Photo Pipeline 測試案例集"
category: knowledge
created: 2026-03-27
importance: high
importance_score: 8
tags: [測試, stock-pipeline, 品質保證, eval]
summary: "涵蓋配置驗證、Creative Brief、Prompt 生成、品質評估、上傳、記憶學習、容錯、Material Curator 的完整測試案例集"
last_updated: 2026-03-27
access_count: 0
last_accessed: null
---

# Stock Photo Pipeline 測試案例集

> 版本: v1.0
> 建立日期: 2026-03-27
> 目的: 驗證 Stock Photo Production Pipeline 各模組的行為正確性與整合品質
> 搭配文件: `tests/stock-pipeline-test-guide.md`（Agent 自測指導文件）
> 測試案例: 10 類 45 題，滿分 135 分

---

## 測試結構說明

每個測試案例包含：
- **ID**: 唯一編號（SP-X##，SP = Stock Pipeline）
- **類別**: 測試的系統面向
- **操作**: 要執行的具體動作
- **前置條件**: 測試前需要的環境狀態
- **預期行為**: 模組應該做什麼
- **預期結果**: 最終應該產生什麼
- **評分標準**: 0-3 分量化評分
- **實際結果**: （測試時填寫）
- **得分**: （測試時填寫）

### 評分量表

| 分數 | 意義 |
|---|---|
| 3 | 完全符合預期，行為正確且品質優良 |
| 2 | 大致符合，有小偏差但不影響功能 |
| 1 | 部分符合，有明顯遺漏或錯誤 |
| 0 | 完全不符合預期 |

---

## A 類：配置與初始化（5 題）

### SP-A01：schedule.json 結構完整性

- **操作**: 讀取 `config/schedule.json` 並驗證所有必要欄位
- **前置條件**: 配置檔存在
- **預期行為**: JSON 可解析，包含 daily_target、retry_budget、openrouter、ollama、workspace、dreamstime_ftp 等區段
- **預期結果**:
  - `daily_target` = 2
  - `max_retries_per_image` 和 `max_daily_retries` 為正整數
  - `openrouter.model` 不為空
  - `ollama.model` = "qwen3:8b"
  - `workspace` 路徑使用相對路徑或 `~` 展開
- **評分標準**:
  - 3: 所有欄位存在且值合理
  - 2: 欄位存在但有 1-2 個值可疑（如 daily_target=0）
  - 1: 有必要欄位缺失但不影響啟動
  - 0: JSON 解析失敗或關鍵區段缺失
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-A02：topics.json 主題完整性

- **操作**: 讀取 `config/topics.json` 並驗證 4 主題定義
- **前置條件**: 配置檔存在
- **預期行為**: 4 個主題（eerie_environment, tech_horror, creature_design, dark_portrait）各有完整定義
- **預期結果**:
  - 每個主題包含 canvas_types、generation_params、style_keywords
  - canvas_types 含 portrait/square/landscape 三種尺寸定義
  - quality_thresholds: PASS ≥8.5, RETRY 7.0-8.4, DISCARD <7.0
  - refinement 配置包含 denoise_range
- **評分標準**:
  - 3: 4 主題各欄位完整，閾值合理
  - 2: 主題完整但個別欄位值可疑
  - 1: 有主題缺少必要欄位
  - 0: 主題定義嚴重不完整
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-A03：setup_workspace.py 目錄建立

- **操作**: 執行 `python scripts/setup_workspace.py`
- **前置條件**: schedule.json 配置的 workspace 路徑可寫入
- **預期行為**: 建立所有必要子目錄，不覆蓋已存在的檔案
- **預期結果**:
  - workspace 下建立 pending/, uploaded/, rejected/, briefs/, temp/
  - memory 下建立 metrics/, metrics/weekly/, metrics/archive/, insights/, daily/
  - prompt_history.json 初始化（若不存在）
  - 已存在的目錄和檔案不受影響
- **評分標準**:
  - 3: 所有目錄建立成功 + 不覆蓋既有資料
  - 2: 目錄建立成功但未檢查是否覆蓋
  - 1: 部分目錄建立失敗
  - 0: 腳本執行出錯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-A04：source-library 索引一致性

- **操作**: 比對 `config/source-library/_index.json` 與 `topics.json` 的主題列表
- **前置條件**: 兩個配置檔都存在
- **預期行為**: source-library 中每個主題都在 topics.json 中有對應定義
- **預期結果**:
  - _index.json 包含 4 個主題條目
  - 每個主題名稱與 topics.json 的 key 完全匹配
  - 各主題子目錄存在
- **評分標準**:
  - 3: 完全一致，目錄齊全
  - 2: 主題一致但有子目錄缺失
  - 1: 有主題不匹配
  - 0: _index.json 不存在或解析失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-A05：路徑解析一致性

- **操作**: 檢查所有 scripts/*.py 的路徑解析方式
- **前置條件**: 所有腳本檔存在
- **預期行為**: 每個模組使用 `Path(__file__).resolve().parent` 相對路徑解析
- **預期結果**:
  - 沒有任何 hardcoded 絕對路徑（如 `/home/user/...`）
  - 沒有使用 `os.getcwd()` 作為基礎路徑
  - CONFIG_DIR, SCRIPT_DIR 等常數由 `__file__` 衍生
- **評分標準**:
  - 3: 所有模組一致使用 resolve().parent 模式
  - 2: 大部分正確但有 1-2 個模組用了不同方式
  - 1: 多個模組有不一致的路徑解析
  - 0: 有 hardcoded 絕對路徑
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## B 類：Creative Brief — Stage 0（4 題）

### SP-B01：CreativeBriefGenerator 初始化

- **操作**: `from creative_brief_generator import CreativeBriefGenerator; cbg = CreativeBriefGenerator()`
- **前置條件**: scripts/ 目錄在 Python path 中
- **預期行為**: 載入 schedule.json 和 topics.json，初始化成功
- **預期結果**:
  - 物件建立不報錯
  - 可存取 `cbg.config`（schedule 配置）
  - 可存取主題列表
- **評分標準**:
  - 3: 初始化成功，配置正確載入
  - 2: 初始化成功但有警告訊息
  - 1: 初始化需要環境變數才能完成
  - 0: import 或初始化失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-B02：主題輪替邏輯

- **操作**: 模擬連續 8 天的主題選擇，驗證 4-theme 等量輪替
- **前置條件**: topics.json 包含 4 個主題
- **預期行為**: 每 4 天完整輪替一次，不重複
- **預期結果**:
  - 8 天中每個主題各出現 2 次
  - 連續日期不重複同一主題
  - 支援 `theme_override` 手動指定
- **評分標準**:
  - 3: 輪替邏輯正確，支援 override
  - 2: 輪替正確但 override 未測試
  - 1: 輪替有偏差（某主題出現過多/過少）
  - 0: 輪替邏輯完全錯誤
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-B03：Dual-Agent 對話（需 OpenRouter）

- **操作**: 呼叫 Creative Brief 生成，觀察 Creative Director + Visual Artist 對話
- **前置條件**: OpenRouter API key 可用
- **預期行為**: 兩個角色交替對話，產出一份完整 brief
- **預期結果**:
  - Brief 包含 theme, canvas_type, session_log, final_concept, visual_keywords
  - session_log 中有至少 2 輪對話
  - final_concept 不為空
  - Brief 保存到 workspace/briefs/
- **評分標準**:
  - 3: 完整對話 + 結構化 brief + 正確保存
  - 2: Brief 產出但對話品質平庸
  - 1: Brief 產出但缺少關鍵欄位
  - 0: 無法產出 brief（API 錯誤不算）
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-B04：Canvas 選擇規則

- **操作**: 給定不同主題和 brief 內容，驗證 canvas 選擇
- **前置條件**: topics.json 中有 canvas_override_rules
- **預期行為**:
  - 含人形主體的 brief → 強制 portrait 或 square
  - 環境類主題 → 可選 landscape
  - canvas_override_rules 正確套用
- **預期結果**:
  - dark_portrait 主題 → 必為 portrait 或 square
  - creature_design 含人形特徵 → 不選 landscape
  - eerie_environment → landscape 可用
- **評分標準**:
  - 3: 所有 override rules 正確套用
  - 2: 大部分正確但有邊界情況未處理
  - 1: Override rules 被忽略
  - 0: Canvas 選擇完全隨機
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## C 類：Prompt 生成 — Stage 1（4 題）

### SP-C01：PromptGenerator 初始化與 observation

- **操作**: 初始化 PromptGenerator，檢查 observation property
- **前置條件**: scripts/ 目錄在 Python path
- **預期行為**: 初始化成功，observation 回傳 dict
- **預期結果**:
  - `observation` 是 property（非 method）
  - 包含 memory_reads_count, prompt_source, insight_applied
  - 初始值合理（counts 為 0）
- **評分標準**:
  - 3: 初始化 + observation 結構完全正確
  - 2: 正確但有額外未預期的 key
  - 1: observation 可存取但結構不完整
  - 0: 初始化或 observation 存取失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-C02：Prompt 去重機制

- **操作**: 用相同參數連續生成 2 次 prompt，檢查是否觸發去重
- **前置條件**: prompt_history.json 存在
- **預期行為**: 第二次生成時偵測到與第一次相似，產出不同結果或標記警告
- **預期結果**:
  - prompt_dedup 設定中的 similarity_threshold 被讀取
  - 歷史 prompt 被比對
  - 相似度過高時有處理（重新生成或變化）
- **評分標準**:
  - 3: 去重機制完整運作
  - 2: 有去重邏輯但閾值未正確套用
  - 1: 只記錄歷史但未比對
  - 0: 完全沒有去重概念
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-C03：Prompt Package 結構

- **操作**: 生成一個完整的 prompt package，驗證其結構
- **前置條件**: Brief 已就緒（可用模擬 brief）
- **預期行為**: 產出結構化的 prompt package
- **預期結果**:
  - 包含 positive_prompt, negative_prompt
  - 包含 generation_params（steps, cfg_scale, sampler 等）
  - 包含 canvas 尺寸（width, height）
  - negative_prompt 不為空
- **評分標準**:
  - 3: Package 結構完整，所有欄位有合理值
  - 2: 結構正確但某些參數用預設值
  - 1: 缺少關鍵欄位（如 negative_prompt）
  - 0: 無法產出 package
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-C04：Ollama Prompt 優化（需 Ollama）

- **操作**: 用 Ollama qwen3:8b 優化一個基礎 prompt
- **前置條件**: Ollama 服務運行中
- **預期行為**: 將簡單描述優化為更豐富的 Stable Diffusion prompt
- **預期結果**:
  - 輸出比輸入更長、更具體
  - 保留原始語意
  - 不引入與主題無關的元素
  - Ollama 超時或失敗時有 fallback（回傳原始 prompt）
- **評分標準**:
  - 3: 優化品質好 + fallback 機制存在
  - 2: 優化可用但品質一般
  - 1: 有呼叫但結果不如預期
  - 0: Ollama 呼叫失敗且無 fallback
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## D 類：品質評估與重試 — Stage 3（5 題）

### SP-D01：DefectDetector 三層架構

- **操作**: 初始化 DefectDetector，確認三層偵測邏輯
- **前置條件**: scripts/ 在 Python path
- **預期行為**: DefectDetector 具備 Layer1 (rule-based), Layer2 (OpenRouter 4-dimension), Layer3 (specialized)
- **預期結果**:
  - `observation` property 包含 layer1_rejects, layer2_calls, layer3_calls, pass/retry/discard counts
  - 初始值皆為 0
  - 三層各有獨立的方法或邏輯分支
- **評分標準**:
  - 3: 三層架構清晰，observation 完整
  - 2: 架構正確但某層的邊界不夠清楚
  - 1: 只有部分層級實作
  - 0: 缺乏分層概念
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-D02：四維品質矩陣加權

- **操作**: 給定一組模擬分數，計算加權總分
- **前置條件**: topics.json 中有 quality_thresholds
- **預期行為**: Technical 30% + Aesthetic 25% + Anatomical 30% + Commercial 15%
- **預期結果**:
  - 輸入: tech=8, aes=9, anat=7, comm=8 → 加權 = 8×0.3 + 9×0.25 + 7×0.3 + 8×0.15 = 7.95
  - verdict 依閾值: ≥8.5=PASS, 7.0-8.4=RETRY, <7.0=DISCARD
  - 以上例: 7.95 → RETRY
- **評分標準**:
  - 3: 加權計算正確 + 閾值判定正確
  - 2: 計算正確但閾值邊界有 off-by-one
  - 1: 權重不正確或閾值未從配置讀取
  - 0: 完全沒有加權邏輯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-D03：ControlNet Advice 欄位

- **操作**: 檢查 Stage 3.2 評估結果是否包含 controlnet_advice
- **前置條件**: OpenRouter API 可用（或用模擬回傳）
- **預期行為**: 評估結果 JSON 包含 `controlnet_advice: {use, type, reason}`
- **預期結果**:
  - `use` 為 boolean
  - `type` 為 ControlNet 類型名稱（depth, canny, openpose 等）
  - `reason` 為中文或英文說明
  - Stage 3.3 能讀取此欄位
- **評分標準**:
  - 3: 欄位完整且 Stage 3.3 能正確消費
  - 2: 欄位存在但 type 偶爾為空
  - 1: 欄位存在但 Stage 3.3 忽略它
  - 0: 完全沒有 controlnet_advice
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-D04：Retry 預算管理

- **操作**: 模擬 retry 場景，驗證預算控制
- **前置條件**: schedule.json 中有 max_retries_per_image 和 max_daily_retries
- **預期行為**:
  - 單張圖片最多重試 max_retries_per_image 次
  - 每日總重試最多 max_daily_retries 次
  - 超過預算後停止重試，標記為 rejected
- **預期結果**:
  - 重試次數被正確計數
  - 超過預算時不再嘗試
  - 超過預算的圖片移至 rejected/
- **評分標準**:
  - 3: 兩個預算限制都正確執行
  - 2: 單張限制正確但每日限制未檢查
  - 1: 有重試概念但預算未從配置讀取
  - 0: 無限重試或無重試邏輯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-D05：Repair Strategy 傳遞

- **操作**: 當 verdict=RETRY 時，驗證 repair strategy 是否傳遞給下一次生成
- **前置條件**: 模擬的品質評估結果含 repair_strategy
- **預期行為**: repair_strategy 和 controlnet_advice 傳遞給 image_refiner 的下一輪
- **預期結果**:
  - Refine 階段收到 defect 描述和修復建議
  - denoise 值根據 defect 嚴重度調整（在 refinement.denoise_range 範圍內）
  - 不是重頭來過，而是基於上一張 refinement
- **評分標準**:
  - 3: Strategy 完整傳遞 + denoise 適當調整
  - 2: Strategy 傳遞但 denoise 未動態調整
  - 1: 重試時無視前次 defect 資訊
  - 0: Retry 是完全重新生成（無 repair 概念）
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## E 類：後處理與上傳 — Stage 4-5（4 題）

### SP-E01：ImageDescriber 描述生成

- **操作**: 給定一張測試圖片，生成商業描述
- **前置條件**: OpenRouter API 可用（或驗證 fallback）
- **預期行為**: 以多模態視覺模型分析圖片，產出結構化描述
- **預期結果**:
  - 包含 title（英文，≤200 字元）
  - 包含 description（英文，2-3 句）
  - 包含 keywords（列表，10-50 個）
  - 包含 category 分類
- **評分標準**:
  - 3: 描述品質佳，欄位完整，符合 Stock Photo 規範
  - 2: 欄位完整但描述品質一般
  - 1: 缺少部分欄位
  - 0: 無法生成描述
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-E02：MetadataEmbedder EXIF/IPTC 寫入

- **操作**: 對測試圖片寫入 EXIF/IPTC 元資料
- **前置條件**: piexif 套件已安裝、測試用 JPEG 檔案
- **預期行為**: 將 title, description, keywords 寫入圖片 EXIF/IPTC
- **預期結果**:
  - 寫入後用 piexif.load() 能讀回 title
  - Keywords 以 IPTC 格式嵌入
  - 圖片檔案不損壞（仍可正常開啟）
- **評分標準**:
  - 3: 寫入 + 讀回驗證 + 圖片完整
  - 2: 寫入成功但未做讀回驗證
  - 1: 部分欄位寫入失敗
  - 0: 寫入過程損壞圖片
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-E03：UploadPreparer 檔案準備

- **操作**: 給定 pending/ 中的圖片，執行上傳前準備
- **前置條件**: pending/ 中有帶 metadata 的圖片
- **預期行為**: 檢查檔案完整性、重命名符合平台規範
- **預期結果**:
  - 檔案命名符合 Dreamstime 要求
  - Metadata 已嵌入
  - 檔案大小在合理範圍
  - 準備好的檔案可識別為「待上傳」
- **評分標準**:
  - 3: 檔案準備完整，命名正確
  - 2: 準備完成但命名不完全符合規範
  - 1: 部分檔案準備失敗
  - 0: 準備流程出錯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-E04：FtpUploader 連線與容錯（需 FTP）

- **操作**: 測試 FTP 連線邏輯（或驗證無法連線時的容錯）
- **前置條件**: DREAMSTIME_FTP_USER 和 DREAMSTIME_FTP_PASS 環境變數
- **預期行為**:
  - 可用時: Passive mode 連線，上傳檔案，驗證
  - 不可用時: 拋出明確錯誤，不崩潰，檔案留在 pending/
- **預期結果**:
  - 連線使用 Passive mode（FTP 設定）
  - 上傳成功的檔案移至 uploaded/
  - 連線失敗時檔案不丟失
  - 有日誌記錄上傳結果
- **評分標準**:
  - 3: 上傳/容錯邏輯都正確
  - 2: 上傳正確但容錯不夠優雅
  - 1: 只測到其中一種情境
  - 0: FTP 邏輯有嚴重問題
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## F 類：記憶與學習 — Memory System（5 題）

### SP-F01：MemoryObserver 觀察收集

- **操作**: 呼叫 `observer.collect()` 多次，然後 `get_observations()`
- **前置條件**: MemoryObserver 可初始化
- **預期行為**: 按 stage 收集觀察數據，get_observations 回傳所有資料
- **預期結果**:
  - 每次 collect 的 stage_name + observation dict 被記錄
  - get_observations() 回傳完整字典
  - reset() 清空所有觀察
- **評分標準**:
  - 3: collect/get/reset 三個操作都正確
  - 2: collect/get 正確但 reset 有殘留
  - 1: 只有 collect 正確
  - 0: 資料收集邏輯有錯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-F02：Daily Observation 保存

- **操作**: `observer.save_daily_observation("2026-03-27")`
- **前置條件**: observer 中已有收集的資料
- **預期行為**: 寫入 JSON 到 `memory/metrics/daily_2026-03-27.json`
- **預期結果**:
  - 檔案建立成功
  - JSON 結構包含 date, stages, summary
  - summary 含 pass_rate, total_generated 等統計
  - 可用 `load_daily_observation()` 讀回
- **評分標準**:
  - 3: 保存 + 讀回 + summary 計算正確
  - 2: 保存成功但 summary 計算有誤
  - 1: 保存成功但無法讀回
  - 0: 保存失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-F03：Daily Summary Markdown

- **操作**: `observer.save_daily_summary_md("2026-03-27")`
- **前置條件**: observer 中已有收集的資料
- **預期行為**: 寫入 YAML frontmatter 的 markdown 到 `memory/daily/`
- **預期結果**:
  - Markdown 檔包含 YAML frontmatter（topic, category, created, tags）
  - 正文包含當日生產摘要
  - 中文可讀
- **評分標準**:
  - 3: YAML + 正文都正確，中文品質好
  - 2: 結構正確但內容過於簡略
  - 1: 缺少 YAML frontmatter
  - 0: 檔案未產生
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-F04：ExperienceDistiller AAR

- **操作**: 給定模擬觀察數據，執行 `distiller.run_aar()`
- **前置條件**: 有至少 1 天的觀察數據
- **預期行為**: 5 維度分析（quality_trend, topic_performance, defect_patterns, prompt_effectiveness, resource_efficiency）
- **預期結果**:
  - 5 個維度各產出分析結果
  - Ollama 可用時有 AI 綜合分析
  - Ollama 不可用時有 fallback（規則基礎分析）
  - Insights 保存到 `memory/insights/`
- **評分標準**:
  - 3: 5 維度完整 + AI/fallback 都正常
  - 2: 分析完整但 fallback 未測試
  - 1: 部分維度缺失
  - 0: AAR 執行失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-F05：MetricsCollector 週報

- **操作**: 模擬 7 天數據，呼叫 `generate_weekly_report()`
- **前置條件**: memory/metrics/ 中有至少 7 個 daily JSON
- **預期行為**: 聚合 7 天數據，產出週報
- **預期結果**:
  - 週報保存到 `memory/metrics/weekly/weekly_YYYY-MM-DD.json`
  - 包含 pass_rate 趨勢、topic 排名、defect 統計
  - `format_weekly_summary_text()` 產出中文可讀摘要
  - 數據不足時回傳明確的 insufficient data 標記
- **評分標準**:
  - 3: 週報完整 + 趨勢正確 + 中文摘要可讀
  - 2: 報完成但趨勢計算有誤
  - 1: 週報不完整
  - 0: 週報生成失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## G 類：Pipeline 整合 — Main（4 題）

### SP-G01：StockPipeline 初始化

- **操作**: `from pipeline_main import StockPipeline; sp = StockPipeline()`
- **前置條件**: 所有子模組可 import
- **預期行為**: 載入所有 11 個子模組，初始化成功
- **預期結果**:
  - 無 import 錯誤
  - 11 個子模組實例都建立成功
  - config 正確載入
- **評分標準**:
  - 3: 完整初始化，無錯誤無警告
  - 2: 初始化成功但有非致命警告（如 FTP 環境變數未設）
  - 1: 部分子模組初始化失敗但不影響核心流程
  - 0: 無法初始化
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-G02：CLI 模式分派

- **操作**: 測試 argparse 各模式：daily, stage0, produce, weekly, monthly, stats
- **前置條件**: pipeline_main.py 可執行
- **預期行為**: 每種模式呼叫對應的方法
- **預期結果**:
  - `--mode daily` → `run_daily_production()`
  - `--mode stage0` → `run_stage0_only()`
  - `--mode produce` → `run_production_only()`
  - `--mode weekly` → `run_weekly_tasks()`
  - `--mode monthly` → `run_monthly_tasks()`
  - `--mode stats` → 顯示統計
  - 未知模式 → 明確錯誤訊息
- **評分標準**:
  - 3: 所有模式正確分派
  - 2: 核心模式正確但 weekly/monthly 未測
  - 1: 只有部分模式可用
  - 0: CLI 解析錯誤
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-G03：Stage 串接順序

- **操作**: 檢查 `_run_production()` 的 Stage 執行順序
- **前置條件**: pipeline_main.py 可讀取
- **預期行為**: Stage 1→2→3→4→5 依序執行，每個 Stage 的輸出是下一個的輸入
- **預期結果**:
  - Stage 1 輸出 prompt_package → Stage 2 輸入
  - Stage 2 輸出 image_path → Stage 3 輸入
  - Stage 3 輸出 verdict + strategy → 決定 retry 或進 Stage 4
  - Stage 4 輸出 metadata_image → Stage 5 輸入
  - 中間任何 Stage 失敗都有處理
- **評分標準**:
  - 3: 串接邏輯完整，中間失敗有處理
  - 2: 串接正確但某個 Stage 失敗時處理不夠
  - 1: 串接順序有誤
  - 0: Stage 之間沒有資料傳遞
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-G04：Finalize 流程

- **操作**: 檢查 `_finalize()` 在生產結束後的行為
- **前置條件**: 有至少一次完整的生產流程（可模擬）
- **預期行為**: observer.save + distiller.run_aar 依序執行
- **預期結果**:
  - 每日觀察數據保存
  - AAR 分析執行
  - 產生 daily summary markdown
  - 所有異常被捕獲不影響結果保存
- **評分標準**:
  - 3: finalize 完整執行，異常安全
  - 2: 功能正確但異常處理不完善
  - 1: 只執行部分 finalize 步驟
  - 0: finalize 未被呼叫或執行失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## H 類：錯誤處理與容錯（5 題）

### SP-H01：ComfyUI 不可用時的降級

- **操作**: 在 ComfyUI 未啟動時呼叫 image_refiner
- **前置條件**: ComfyUI 服務未運行
- **預期行為**: 嘗試連線 → 偵測到不可用 → 回傳明確錯誤，不崩潰
- **預期結果**:
  - 拋出自定義異常或回傳 error dict
  - 錯誤訊息包含「ComfyUI 不可用」等描述
  - 不會 hang 住（有 timeout）
  - Pipeline 可以跳過此張圖片繼續
- **評分標準**:
  - 3: 快速偵測 + 明確錯誤 + pipeline 繼續
  - 2: 偵測到但錯誤訊息不清楚
  - 1: 偵測到但 pipeline 中斷
  - 0: 程式 hang 住或未捕獲的異常
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-H02：OpenRouter API Key 缺失

- **操作**: 清除 OPENROUTER_API_KEY 環境變數後嘗試評估
- **前置條件**: 環境變數未設定
- **預期行為**: 偵測到 key 缺失，回傳 fallback 或明確錯誤
- **預期結果**:
  - 不發送無效 API 請求
  - 錯誤訊息指引使用者設定環境變數
  - 有 fallback（如跳過 AI 評估，使用規則基礎判定）
- **評分標準**:
  - 3: 提前偵測 + 有 fallback + 清楚指引
  - 2: 偵測到但無 fallback
  - 1: 發送了無效請求才發現
  - 0: 拋出未處理的異常
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-H03：Ollama 服務不可用

- **操作**: 在 Ollama 未啟動時呼叫 prompt 優化
- **前置條件**: Ollama 服務未運行
- **預期行為**: 連線失敗 → fallback 到原始 prompt
- **預期結果**:
  - 不崩潰
  - 回傳原始 prompt（graceful fallback）
  - 日誌記錄 Ollama 不可用
- **評分標準**:
  - 3: 快速 fallback + 日誌記錄
  - 2: Fallback 正確但無日誌
  - 1: 超時很久才 fallback
  - 0: 崩潰或卡住
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-H04：FTP 環境變數缺失

- **操作**: 清除 FTP 相關環境變數後嘗試上傳
- **前置條件**: DREAMSTIME_FTP_USER 未設定
- **預期行為**: 偵測到環境變數缺失，跳過上傳
- **預期結果**:
  - 不嘗試連線
  - 檔案留在 pending/（不丟失）
  - 明確錯誤提示
- **評分標準**:
  - 3: 提前偵測 + 檔案安全 + 明確提示
  - 2: 正確處理但提示不清
  - 1: 嘗試連線才發現
  - 0: 檔案丟失或崩潰
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-H05：日產量上限保護

- **操作**: 模擬已完成 daily_target 張圖片後再觸發生產
- **前置條件**: 當日已生產 2 張（= daily_target）
- **預期行為**: 檢測到已達上限，拒絕再生產
- **預期結果**:
  - 不啟動新的生成流程
  - 回傳「已達每日上限」訊息
  - 不影響其他功能（stats, weekly 仍可用）
- **評分標準**:
  - 3: 正確阻止 + 明確訊息 + 其他功能不受影響
  - 2: 阻止成功但訊息不清
  - 1: 阻止但影響了其他功能
  - 0: 未檢查上限，繼續生產
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## I 類：Material Curator（5 題）

### SP-I01：Curator 初始化與 Scraper 註冊

- **操作**: 初始化 MaterialCurator，檢查內建 scraper
- **前置條件**: scripts/ 在 Python path
- **預期行為**: 內建 scraper（creepypasta_fandom, reddit_nosleep）自動註冊
- **預期結果**:
  - 物件建立成功
  - `_scrapers` 字典包含 "creepypasta.fandom.com" 和 "reddit.com"
  - 可註冊自定義 scraper
- **評分標準**:
  - 3: 初始化成功 + 內建 scraper 齊全 + 可擴展
  - 2: 初始化成功但少了一個內建 scraper
  - 1: 初始化成功但 scraper 註冊機制有問題
  - 0: 初始化失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-I02：分類邏輯正確性

- **操作**: 用不同主題的文本測試 `_classify_by_keywords()`
- **前置條件**: 分類關鍵字定義 THEME_KEYWORDS 存在
- **預期行為**: 根據文本中的關鍵字匹配最合適的主題
- **預期結果**:
  - 含 "haunted house" → eerie_environment
  - 含 "robot", "AI" → tech_horror
  - 含 "monster", "creature" → creature_design
  - 含 "face", "portrait" → dark_portrait
  - 無明確關鍵字 → 預設 tech_horror
  - 已有 theme 的素材不被重新分類
- **評分標準**:
  - 3: 所有分類正確 + 保留既有分類
  - 2: 大部分正確但邊界情況有誤
  - 1: 分類邏輯過於簡陋
  - 0: 分類結果完全錯誤
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-I03：去重機制

- **操作**: 用相似的 core_concept 測試去重
- **前置條件**: source-library 中已有素材
- **預期行為**: SequenceMatcher 比對 core_concept，threshold 0.70
- **預期結果**:
  - 完全相同的 concept → 判定為重複
  - 相似度 >0.70 → 判定為重複
  - 相似度 <0.70 → 判定為不重複
  - 去重只在同一主題下比對
- **評分標準**:
  - 3: 閾值正確 + 同主題限定 + 邊界正確
  - 2: 去重運作但閾值未從配置讀取
  - 1: 去重概念存在但實作有缺陷
  - 0: 沒有去重機制
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-I04：stats() 統計正確性

- **操作**: 在有素材的 source-library 上呼叫 `stats()`
- **前置條件**: 至少有 1 個主題包含素材
- **預期行為**: 統計各主題素材數量和未使用數量
- **預期結果**:
  - 4 個主題各有 count 和 unused
  - total 和 total_unused 為各主題加總
  - 空主題的 count=0, unused=0
  - 不會因為空目錄而報錯
- **評分標準**:
  - 3: 統計完全正確
  - 2: 統計正確但有多餘欄位
  - 1: 基本統計正確但加總有誤
  - 0: stats() 執行報錯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-I05：Creepypasta / Reddit Scraper（需網路）

- **操作**: 對 creepypasta.fandom.com 和 reddit.com/r/nosleep 各爬取 1 篇
- **前置條件**: 網路連線可用
- **預期行為**:
  - Creepypasta: 偵測 Category vs 單篇，正確選擇解析策略
  - Reddit: 使用 .json API，不是 HTML 解析
  - 兩者都有 polite delay
- **預期結果**:
  - 回傳 raw_text 不為空
  - Reddit 回傳包含 score 欄位
  - Creepypasta 回傳已去除導航和廣告噪音
  - 429 rate limit 有自動等待重試
- **評分標準**:
  - 3: 兩個 scraper 都正確工作 + polite delay + 429 處理
  - 2: 爬取成功但缺少某個細節（如無 delay）
  - 1: 只有一個 scraper 正常
  - 0: 兩個都失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## J 類：邊界條件與安全（4 題）

### SP-J01：空 Brief 處理

- **操作**: 在沒有 brief 的情況下嘗試 `run_production_only()`
- **前置條件**: workspace/briefs/ 為空
- **預期行為**: 偵測到無 brief，提示先執行 Stage 0
- **預期結果**:
  - 不崩潰
  - 明確錯誤訊息：「未找到今日 brief，請先執行 stage0」
  - 不嘗試用空資料生成圖片
- **評分標準**:
  - 3: 提前偵測 + 明確訊息 + 安全退出
  - 2: 偵測到但訊息不清
  - 1: 到了 Stage 1 才發現沒有 brief
  - 0: 用空資料嘗試生成
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-J02：模型切換（Phase 1→2）

- **操作**: 修改 schedule.json 中的 openrouter.model，驗證全局生效
- **前置條件**: schedule.json 可修改
- **預期行為**: 修改一個配置欄位即可切換所有 OpenRouter 呼叫的模型
- **預期結果**:
  - creative_brief_generator 使用新模型
  - defect_detector 使用新模型
  - image_describer 使用新模型
  - 不需要修改多個地方
- **評分標準**:
  - 3: 單一配置切換全局生效
  - 2: 大部分模組讀取統一配置但有 1 個獨立設定
  - 1: 需要修改多處配置
  - 0: 模型名稱 hardcoded
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-J03：API Key 不在程式碼中

- **操作**: 掃描所有 scripts/*.py 檔案中的 API key 模式
- **前置條件**: 所有腳本檔存在
- **預期行為**: 不含任何 hardcoded API key（sk-or-XXXX 格式 20+ 字元）
- **預期結果**:
  - 所有 API key 從環境變數讀取
  - 錯誤訊息中的範例 key 不會被誤判（短字串 OK）
  - 沒有 FTP 密碼 hardcoded
- **評分標準**:
  - 3: 零 hardcoded secrets
  - 2: 有可疑字串但實際是範例/說明文字
  - 1: 有 1 處 hardcoded 但非真實 key
  - 0: 有真實 API key 在程式碼中
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### SP-J04：Lazy Import 安全性

- **操作**: 檢查模組間的 cross-import 是否使用 lazy import 模式
- **前置條件**: 所有腳本檔可讀取
- **預期行為**: 跨模組 import 使用 `sys.path.insert(0, SCRIPT_DIR)` + import
- **預期結果**:
  - 不使用相對 import（`from .module import`）
  - SCRIPT_DIR 由 `__file__` 衍生
  - 不依賴 PYTHONPATH 環境變數
  - 單獨執行任一腳本不會 ImportError
- **評分標準**:
  - 3: 所有 cross-import 一致使用 lazy 模式
  - 2: 大部分正確但有例外
  - 1: Import 方式不一致
  - 0: 有 circular import 或執行失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## 附錄：測試涵蓋對照表

| Pipeline Stage | 對應測試類別 | 測試數量 |
|---|---|---|
| 配置/初始化 | A | 5 |
| Stage 0: Creative Brief | B | 4 |
| Stage 1: Prompt 生成 | C | 4 |
| Stage 2: 圖片生成 | (含在 D, H) | — |
| Stage 3: 品質評估 | D | 5 |
| Stage 4: 後處理 | E (E01-E02) | 2 |
| Stage 5: 上傳 | E (E03-E04) | 2 |
| Memory 系統 | F | 5 |
| Pipeline 整合 | G | 4 |
| 容錯 | H | 5 |
| Material Curator | I | 5 |
| 安全/邊界 | J | 4 |
| **合計** | | **45** |

---

_測試案例由 ClawClaw 設計，每一題都是為了讓流水線更可靠_ 🐾
