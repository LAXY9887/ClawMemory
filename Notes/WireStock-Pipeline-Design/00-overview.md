# WireStock Pipeline 設計總覽

> 建立日期: 2026-03-26
> 設計環境: Cowork (學校端)
> 目標執行環境: OpenClaw (ClawClaw 本地端)
> 傳遞機制: 上學-回家複習 (Git commit → push → pull → mirror sync)

---

## 專案雙重目標

### 目標 A：商業執行
讓 ClawClaw 能自主運行圖片生產流水線，從提示詞生成到品質把關，FTP 自動上傳至 Dreamstime + 通知 LXYA 手動上傳 Adobe Stock，實現每日穩定產出。

### 目標 B：記憶系統實驗（研究核心）
藉由 Stock Photo Pipeline 這個持續性、可量化的實戰任務，測試並收集 ClawClaw 記憶架構的表現數據。這些數據將用於驗證以下假設：

1. **YAML Frontmatter 元數據**是否真的能減少不必要的全文讀取？
2. **經驗萃取層（insights/）**產出的規則是否會被後續任務實際引用？
3. **冷熱記憶分離**在持續任務中是否有效控制 Token 消耗？
4. **keyword_index.json** 的語義匹配在實際生產場景中的命中率如何？
5. 記憶系統在長期運行後是否出現退化（記憶膨脹、索引失準、經驗過時）？

---

## 每日流程概要

```
07:00  Stage 0：創意素材討論會（雙 Agent 對話，產出今日創意簡報）
09:00  Stage 1：排程啟動 & 上下文載入（讀取 Stage 0 簡報 + 經驗 insights）
       Stage 2：提示詞生成與優化（基於創意簡報 / fallback 模板模式）
       Stage 3：圖像生成精煉迴圈（初步×5 → 自評 → 精煉×5 → 自評 → 4x Upscale）
       Stage 4：品質檢測與篩選（OpenRouter 多模態精檢）
       Stage 5：上傳準備 & 批次結算（Dreamstime FTP 自動 + Adobe Stock 手動通知）
每日目標：2 張精煉高品質圖片，單一主題制（四主題均等輪替）
```

---

## 文件結構

本資料夾下的每份文件對應一個獨立模組，方便針對性擴充：

```
Notes/WireStock-Pipeline-Design/
├── 00-overview.md                    ← 本文件，總覽與索引
├── 01-daily-production-pipeline.md   ← 每日圖片生產主流程（Stage 0-5 完整定義）
├── 02-defect-detection-repair.md     ← AI 缺陷檢測與迭代修復
├── 03-memory-observation-module.md   ← 記憶系統觀測探針
├── 04-experience-distillation.md     ← 任務後經驗萃取機制
├── 05-metrics-data-collection.md     ← 結構化數據收集規格
└── 06-memory-system-integration.md   ← 與現有記憶架構的整合點
```

---

## 技術前提

### ClawClaw 本地端已具備的能力
- **ComfyUI Desktop**：圖像生成引擎，rinIllusion 模型已安裝 ✅ API 已測試
- **Ollama qwen3:8b**：本地免費 LLM，用於提示詞優化和文字推理（不用於圖片分析）
- **OpenRouter API**：多模態視覺模型，用於圖片評分、缺陷檢測、描述提取（取代 Ollama 的圖片分析角色）
- **Enhanced-Browser**：反機器人偵測的網頁瀏覽
- **Desktop-Vision**：螢幕截圖 + OCR
- **Desktop-Input**：安全的滑鼠鍵盤控制
- **記憶系統 v2.0**：YAML frontmatter、insights/ 層、智能睡眠模式、keyword_index.json
- **LoRA 模型**：✅ 所有專業 LoRA 已下載完畢
- **GPU**：✅ RTX 4070 12GB 測試通過
- **排程系統**：✅ 排程測試通過

### 尚待準備的資源
- **平台帳號**：✅ Adobe Stock + Dreamstime 帳號已辦好
- **Dreamstime FTP 憑證**：需取得 FTP ID 並測試連線 upload.dreamstime.com（Adobe Stock 不支援 FTP，由 LXYA 手動上傳）
- **OpenRouter API Key**：需設定並測試視覺模型（建議先測 google/gemini-flash-1.5）
- **品質評估基準線**：第一批圖片的人工評分，作為 OpenRouter 評分的校準依據
- **ControlNet 模型**：確認已安裝的 ControlNet 模型（depth、pose 等）

---

## 設計原則

### 1. 觀測不干預
記憶觀測模組只記錄數據，不主動修改記憶系統的行為邏輯。確保收集到的數據反映系統的自然表現。

### 2. 最小侵入
所有觀測探針以 hook/callback 方式嵌入，不改變主流程的執行路徑。即使觀測模組故障，生產流程仍可獨立運行。

### 3. 漸進式部署
先讓核心生產流程跑通（01-02），再疊加觀測與萃取（03-04-05），最後完成整合（06）。

### 4. 數據可追溯
每筆觀測數據都帶有時間戳、session_id、觸發來源，確保後續分析時能還原完整上下文。

---

## 預期的 Skill 結構（最終形態，現階段僅供參考）

```
skills-custom/wirestock-pipeline/
├── SKILL.md                        # 技能總說明
├── config/
│   ├── topics.json                 # 四大主題配置與配比（含畫布規則、品質門檻）
│   ├── schedule.json               # 每日排程參數（含 Stage 0 時間）
│   └── source-library/             # 創意素材庫（按主題分資料夾）
│       ├── tech-abstract/
│       ├── eerie-scene/
│       ├── creature-design/
│       ├── clawclaw-portrait/
│       └── _index.json             # 素材索引（檔名、使用次數、上次使用日期）
├── scripts/
│   ├── pipeline_main.py            # 主流程編排
│   ├── creative_brief_generator.py # Stage 0 雙 Agent 創意對話（調用 openrouter_client）
│   ├── prompt_generator.py         # 提示詞生成（讀取簡報 + Ollama 優化）
│   ├── comfyui_client.py           # ComfyUI API 呼叫
│   ├── openrouter_client.py        # OpenRouter 視覺模型呼叫（評分/描述/缺陷/對話）
│   ├── defect_detector.py          # 缺陷檢測引擎（調用 openrouter_client）
│   ├── quality_scorer.py           # 品質評分（調用 openrouter_client）
│   ├── image_describer.py          # 圖片描述提取（調用 openrouter_client）
│   ├── metadata_embedder.py        # EXIF/IPTC 元數據嵌入
│   ├── ftp_uploader.py             # FTP 自動上傳至 Dreamstime（Adobe Stock 由 LXYA 手動上傳）
│   ├── upload_preparer.py          # 上傳前處理（編排 metadata + upload）
│   ├── memory_observer.py          # 記憶觀測探針
│   ├── experience_distiller.py     # 經驗萃取引擎
│   └── metrics_collector.py        # 數據收集器
│
│   注: 不設獨立 templates/ 目錄
│   - 提示詞 fallback 模板直接定義在 01 文件 Stage 2.1b 區塊
│   - 報告格式直接定義在 01 文件「批次結算」區塊
```

---

## 模組間依賴關係

```
01-daily-production-pipeline (主流程，Stage 0-5)
    ├── Stage 0 使用 → OpenRouter 雙 Agent 對話 + 素材庫
    ├── Stage 2 使用 → Stage 0 產出的創意簡報（或 fallback 模板）
    ├── Stage 3-4 使用 → 02-defect-detection-repair (品質把關)
    ├── 被觀測 → 03-memory-observation-module (數據探針)
    ├── 觸發 → 04-experience-distillation (批次完成後)
    └── 產出 → 05-metrics-data-collection (結構化數據)

06-memory-system-integration
    └── 定義上述所有模組如何與 ClawClaw 現有記憶系統交互
```

---

## 下一步

逐份完善 01-06 的細節設計，每份文件確認後再進入 Skill 實作階段。
