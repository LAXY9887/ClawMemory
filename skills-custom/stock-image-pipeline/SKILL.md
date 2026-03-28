---
name: stock-image-pipeline
description: Stock photo automated production pipeline. Daily workflow producing 2 high-quality AI-generated images for Adobe Stock and Dreamstime. Includes creative brief generation (dual-Agent dialogue), prompt optimization, ComfyUI image generation with dual refinement loop, OpenRouter quality scoring, defect detection, EXIF/IPTC metadata embedding, and Dreamstime FTP auto-upload. Use for daily scheduled production, manual image generation, quality review, or upload management.
---

# Stock Photo Production Pipeline

ClawClaw 的 AI 圖片自動化生產流水線，每日產出 2 張精煉高品質圖片上架 Adobe Stock 和 Dreamstime。

## Core Mission

透過自動化流程將創意素材轉化為商業級圖片：從創意討論、提示詞生成、圖片精煉、品質檢測到上傳，全程由 ClawClaw 自主執行。每張圖背後都有故事概念支撐，而非僅靠模板生成。

---

## When to Use

### Automatic Triggers
- **🆕 Daily production (10:00)**: Stage 0 創意素材討論會由 Heartbeat 觸發
- **🆕 Continuous execution**: Stage 0 完成後自動執行 Stage 1-5 (連續執行模式)
- **🆕 Weekly material crawl (週一 13:00)**: 自動爬取 4 個網站最新文章，更新素材庫
- **Batch completion**: 批次完成後自動觸發經驗萃取 (04-experience-distillation)
- **Weekly report**: 每週由 Heartbeat 觸發週報彙總

### Manual Triggers
- **LXYA 指令**: "開始今天的創意討論" → 啟動 Stage 0
- **LXYA 指令**: "開始今天的圖片生產" → 啟動 Stage 1-5
- **LXYA 指令**: "手動上傳通知" → 產出 Adobe Stock 上傳提醒
- **LXYA 指令**: "生產報告" → 產出最近的批次結算報告

---

## ⚠️ 核心原則

### 敏感資訊
- **OpenRouter API Key**: 從環境變數 `OPENROUTER_API_KEY` 讀取，絕不寫死在程式碼中
- **Dreamstime FTP 密碼**: 從環境變數 `DREAMSTIME_FTP_PASS` 讀取
- **Dreamstime FTP ID**: 從環境變數 `DREAMSTIME_FTP_ID` 讀取

### 所有門檻值從 config 讀取
- 品質分數門檻、重試次數、每日目標、畫布規則等全部定義在 `config/` 下的 JSON 檔案
- 禁止在腳本中硬編碼門檻值

### 記憶系統交互
- 所有新建檔案必須帶 YAML frontmatter
- 觀測數據寫入 `memory/metrics/`，不觸發 RICE+S
- 使用 `shutil.copy2()` 複製記憶檔案，保留 frontmatter

---

## Daily Workflow (Stage 0-5)

```
🆕 10:00  Stage 0：創意素材討論會
          ├── 確認今日主題（四主題輪替或 LXYA 指定）
          ├── 從素材庫抽取素材
          ├── 雙 Agent 對話（Creative Director + Visual Artist via OpenRouter）
          └── 產出 brief_{date}.json（2 張圖各自的視覺指導）
          
🆕 10:05  連續執行模式：Stage 0 完成後自動觸發 Stage 1-5
          ├── 延遲 30 秒讓 Stage 0 結果穩定
          └── 自動執行後續所有 Stage，無需額外排程

10:05  Stage 1：排程啟動 & 上下文載入
       ├── 讀取 Stage 0 簡報（或 fallback 模板模式）
       ├── 載入經驗 insights
       └── 計算今日生產計畫

       Stage 2：提示詞生成與優化
       ├── 從創意簡報提取視覺指導 → 轉化為 ComfyUI 提示詞
       ├── Ollama qwen3:8b 優化提示詞
       └── 去重檢查（近 7 天歷史）

       Stage 3：圖像生成精煉迴圈（每張圖獨立執行）
       ├── 3.1 初步候選生成（初步尺寸 × 5，不同 seed）
       ├── 3.2 OpenRouter 自評 → 選最佳 1 張（含 ControlNet 建議）
       ├── 3.3 精煉放大（精煉尺寸 × 5，不同 denoise + 可選 ControlNet）
       ├── 3.4 OpenRouter 再評 → 選最佳 1 張
       └── 3.5 ComfyUI 4x Upscale → 商業級解析度

       Stage 4：品質檢測與篩選
       ├── OpenRouter 多模態精檢（四維矩陣: 技術/美學/解剖/商業）
       ├── Ollama 推理修復策略（若需重試）
       └── 決策: PASS (≥8.5) / RETRY (7.0-8.4) / DISCARD (<7.0)

       Stage 5：上傳準備 & 批次結算
       ├── 5.1 OpenRouter 圖片描述提取 → EXIF/IPTC 嵌入
       ├── 5.2a Dreamstime FTP 自動上傳
       ├── 5.2b Adobe Stock 手動通知 LXYA
       └── 5.3 批次結算報告
```

---

## Dependencies

### 必要環境
- **ComfyUI Desktop**: API 模式啟動，rinIllusion 模型
- **Ollama qwen3:8b**: 本地 LLM，提示詞優化 + 修復策略推理
- **OpenRouter API**: 多模態視覺模型（初期 Gemini Flash → 穩定後 Claude Sonnet）
- **Python packages**: 見 `requirements.txt`

### 安裝步驟
```bash
# 1. 安裝 Python 依賴
pip install -r requirements.txt

# 2. 初始化 workspace 目錄
python scripts/setup_workspace.py

# 3. 設定環境變數（見下方）

# 4. 驗證安裝
python -m pytest tests/ -v
```

### LoRA 模型
- `cyber_graphic`: 科技抽象主題
- `horror_creepy`: 陰森場景主題
- `creatures_design_v1`: 怪誕生物主題
- ClawClaw 肖像: 不使用 LoRA（純 rinIllusion 基礎模型）

### ControlNet 模型
- `openpose`: 人物姿勢保留
- `depth`: 空間透視保留
- `canny`: 邊緣輪廓保留

### 環境變數
```bash
OPENROUTER_API_KEY=sk-or-...
DREAMSTIME_FTP_ID=123456        # 數字 ID，非 email
DREAMSTIME_FTP_PASS=...
```

---

## Configuration Files

### config/schedule.json
排程參數、重試預算、主題輪替策略。

### config/topics.json
四大主題配置（畫布規則、LoRA、採樣器參數）、品質門檻、精煉參數。

### config/source-library/
創意素材庫，按主題分資料夾，`_index.json` 記錄使用歷史。

---

## OpenRouter Model Strategy

```
Phase 1 - 初期測試（全部 Gemini Flash）:
  驗證 Pipeline 端到端運作，收集基準成本

Phase 2 - 穩定運行（全部 Claude Sonnet）:
  提升評分精度和創意品質

切換方式: config/schedule.json 中 openrouter_model 欄位
```

---

## Retry Budget

```
max_retries_per_image: 2（每張圖獨立）
max_daily_retries: 4（全日累計）

Stage 3.2 全部 <5.0 → 回退 Stage 2（消耗 1 次）
Stage 3.4 全部 <7.0 → 直接丟棄（不消耗重試）
Stage 4 可修復缺陷 → 回退 Stage 3.1（消耗 1 次）
```

---

## File Structure

```
skills-custom/stock-image-pipeline/
├── SKILL.md                          ← 本文件
├── config/
│   ├── schedule.json                 # 排程 + 重試 + 模型選擇
│   ├── topics.json                   # 主題 + 畫布 + 品質門檻
│   └── source-library/               # 創意素材庫
│       ├── tech-abstract/
│       ├── eerie-scene/
│       ├── creature-design/
│       ├── clawclaw-portrait/
│       └── _index.json
├── scripts/
│   ├── pipeline_main.py              # 主流程編排 (Stage 0-5)
│   ├── creative_brief_generator.py   # Stage 0 雙 Agent 創意對話
│   ├── prompt_generator.py           # Stage 1-2 提示詞生成
│   ├── comfyui_client.py             # ComfyUI API 封裝
│   ├── openrouter_client.py          # OpenRouter API 封裝
│   ├── image_refiner.py              # Stage 3 圖像生成精煉迴圈 (3.1-3.5)
│   ├── defect_detector.py            # Stage 4 品質精檢
│   ├── image_describer.py            # Stage 5.1 描述提取
│   ├── metadata_embedder.py          # EXIF/IPTC 嵌入
│   ├── ftp_uploader.py               # Dreamstime FTP 上傳
│   ├── upload_preparer.py            # 上傳流程編排
│   ├── memory_observer.py            # 觀測記錄
│   ├── experience_distiller.py       # 經驗萃取 (AAR)
│   └── metrics_collector.py          # 結算報告 + 週報
```

---

## Workspace Directories

```
~/.openclaw/workspace/stock-pipeline/
├── pending/                          # 待上傳圖片
├── uploaded/                         # 已上傳圖片
├── rejected/                         # 被拒絕圖片
├── briefs/                           # 創意簡報 + 討論記錄
│   ├── brief_{date}.json
│   └── discussion_{date}.md
└── temp/                             # 生成過程暫存（候選圖、中間產物）
```

---

## Integration with Memory System

- **寫入 memory/metrics/daily/**: 每日批次結算報告 (JSON)
- **寫入 memory/metrics/weekly/**: 週報彙總
- **寫入 memory/insights/**: 經驗萃取產出（帶 `source: realtime_aar` 標記）
- **寫入 memory/daily/**: 當日生產摘要（自然語言）
- **讀取 memory/insights/**: 帶著經驗進場（via keyword_index tags 查詢）
- **觸發 04-experience-distillation**: 批次完成後 Hook

---

## Design Documentation

詳細設計請參考：`Notes/stock-image-pipeline-Design/` (7 份文件 00-06)

