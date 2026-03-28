# 01 - 每日圖片生產主流程

> 模組定位: 核心執行引擎
> 依賴: ComfyUI API、Ollama qwen3:8b、OpenRouter API（多模態視覺模型 + 雙 Agent 對話）、LoRA 模型
> 被依賴: 02-defect-detection、03-memory-observation、04-experience-distillation

---

## 流程總覽

每日生產流程分為 6 個階段（Stage 0-5），依序執行。每日單一主題制，Stage 0 在早晨進行創意素材討論產出創意簡報，Stage 3 採用雙重精煉迴圈，每日精煉產出 2 張高品質圖片：

```
07:00
[Stage 0] 創意素材討論會（Creative Brief Session）
    ├── 0.1 確認今日主題（從輪替表或 LXYA 指定）
    ├── 0.2 從主題素材庫隨機抽取素材
    ├── 0.3 雙 Agent 對話：Creative Director + Visual Artist 討論視覺化細節
    └── 0.4 產出「今日創意簡報」（2 張圖各自的故事概念 + 視覺指導）

09:00
[Stage 1] 排程啟動 & 上下文載入（讀取 Stage 0 簡報 + 經驗 insights）
    ↓
[Stage 2] 提示詞生成與優化（基於創意簡報，而非純模板生成）
    ↓
[Stage 3] 圖像生成精煉迴圈（每張圖獨立執行以下子流程）
    ├── 3.1 初步候選生成（初步尺寸 × 5 張，不同 seed）
    ├── 3.2 OpenRouter 第一次自評 → 選最佳 1 張
    ├── 3.3 精煉放大生成（精煉尺寸 × 5 張，不同 denoise）
    ├── 3.4 OpenRouter 第二次自評 → 選最佳 1 張
    └── 3.5 ComfyUI 4x Upscale → 商業級最終解析度
    ↓
[Stage 4] 品質檢測與篩選（→ 呼叫 02-defect-detection，OpenRouter 多模態精檢）
    ↓
[Stage 5] 上傳準備 & 批次結算
    ├── 5.1 OpenRouter 圖片描述提取 → EXIF/IPTC 元數據嵌入
    ├── 5.2 FTP 自動上傳至 Dreamstime + 通知 LXYA 手動上傳 Adobe Stock
    └── 5.3 批次結算報告
    ↓
[Hook] 批次完成 → 觸發 04-experience-distillation（含 Prompt 精煉分析）
[Hook] 全程觀測 → 03-memory-observation 記錄數據
```

---

## Stage 0：創意素材討論會（Creative Brief Session）

### 設計理念
在正式生產前，由兩個 AI Agent 角色基於素材庫中的文本進行創意討論，產出有故事深度的「今日創意簡報」。這讓每張圖背後都有具體的故事概念支撐，而非僅靠模板 + 隨機變化，大幅提升圖片的獨特性和商業價值。

### 觸發方式
- **自動觸發**：由 Heartbeat 在 07:00 啟動
- **手動觸發**：LXYA 指令 "開始今天的創意討論"
- **跳過條件**：LXYA 可直接指定今日創意簡報內容，跳過 Stage 0

### 素材庫結構
```
config/source-library/
├── tech-abstract/                    # 科技抽象素材
│   ├── quantum-entanglement.md
│   ├── neural-network-topology.md
│   └── ...
├── eerie-scene/                      # 陰森場景素材
│   ├── creepypasta-abandoned-hospital.md
│   ├── urban-legend-midnight-train.md
│   └── ...
├── creature-design/                  # 怪誕生物素材
│   ├── deep-sea-anglerfish-mutation.md
│   ├── forest-spirit-mythology.md
│   └── ...
├── clawclaw-portrait/                # ClawClaw 肖像素材
│   ├── emotion-study-melancholy.md
│   ├── light-study-golden-hour.md
│   └── ...
└── _index.json                       # 素材索引（檔名、主題、已使用次數、上次使用日期）

素材文件格式範例 (eerie-scene/creepypasta-abandoned-hospital.md):
---
source: creepypasta.com
title: "The Last Ward"
collected_date: 2026-03-28
used_count: 0
last_used: null
tags: [hospital, abandoned, ghost, corridor, flickering-lights]
---
[原文內容或摘要]

素材庫管理:
- 初期由 LXYA 手動收集並投入對應主題資料夾
- 未來可建立自動搜集 Agent（每月啟動，從 creepypasta、科幻論壇等搜集新素材）
- 主題資料夾可隨時新增（新增主題時同步建立對應素材庫）
- _index.json 記錄每篇素材的使用歷史，避免短期內重複選用
```

### 雙 Agent 創意對話

使用 OpenRouter 調用兩個不同的 LLM 角色進行對話，產出有深度的視覺化方案：

```
Agent 角色定義:

Creative Director（創意總監）:
  - 職責: 從素材中提取核心敘事元素、定義情緒基調、決定故事角度
  - 關注點: 故事性、情感張力、市場差異化、關鍵詞潛力
  - 模型: OpenRouter 上的文字推理模型（如 anthropic/claude-sonnet 或同等級）

Visual Artist（視覺藝術家）:
  - 職責: 將敘事元素轉化為具體的視覺構圖、色彩方案、光影設計
  - 關注點: 構圖可行性、ComfyUI 技術限制、LoRA 風格匹配、缺陷預防
  - 模型: OpenRouter 上的另一個模型（如 google/gemini-flash 或同等級）

對話流程:
1. [系統] 提供今日主題 + 抽選的素材全文 + 過往相關 insights
2. [Creative Director] 讀完素材後提出 3 個故事角度，每個角度包含：
   - 核心場景描述（一句話）
   - 情緒關鍵詞（3-5 個）
   - 為什麼這個角度有商業價值
3. [Visual Artist] 對每個角度回應：
   - 視覺化可行性評估（ComfyUI 能否實現？有哪些技術風險？）
   - 建議的構圖方式和色彩方案
   - 推薦的畫布類型（portrait/square/landscape）
4. [Creative Director] 綜合回饋，選定最佳 2 個方案（對應今日 2 張圖）
5. [Visual Artist] 對選定方案產出詳細視覺指導：
   - 具體的正面/負面提示詞建議
   - LoRA 權重微調建議
   - 需要特別注意的缺陷預防點

對話輪次: 3-4 輪（約 6-8 則訊息），控制在 15-20 分鐘內完成
預估 OpenRouter 成本: ~$0.05-0.10/次討論（純文字對話，token 成本低）
```

### 產出物：今日創意簡報

```
輸出檔案: ~/.openclaw/workspace/stock-pipeline/briefs/brief_{date}.json

{
    "date": "2026-03-28",
    "theme": "eerie-scene",
    "source_material": {
        "file": "config/source-library/eerie-scene/creepypasta-abandoned-hospital.md",
        "title": "The Last Ward"
    },
    "images": [
        {
            "image_id": "brief-001",
            "concept": "廢棄醫院的最後一間病房，月光從破碎的窗戶灑入...",
            "mood_keywords": ["isolation", "decay", "eerie calm", "moonlit"],
            "visual_direction": {
                "composition": "走廊盡頭的門微開，門縫透出冷光",
                "color_palette": "冷藍灰為主，月光帶淡黃",
                "lighting": "側面月光，長影子",
                "canvas_type": "landscape",
                "positive_prompt_hints": ["abandoned hospital ward", "moonlight through broken window", "long shadows", "peeling paint walls"],
                "negative_prompt_hints": ["人物", "鮮豔色彩", "現代設備"],
                "lora_weight_adjustment": null,
                "defect_warnings": ["注意走廊透視不要扭曲", "窗戶玻璃反射要自然"]
            }
        },
        {
            "image_id": "brief-002",
            "concept": "走廊地板上散落的病歷，其中一頁被風吹起...",
            "mood_keywords": ["mystery", "forgotten", "wind", "paper"],
            "visual_direction": {
                "composition": "低角度俯瞰，病歷特寫，背景模糊走廊",
                "color_palette": "褪色紙張黃、陰暗綠灰",
                "lighting": "頂光，局部打亮病歷",
                "canvas_type": "square",
                "positive_prompt_hints": ["scattered medical records on floor", "paper floating in wind", "abandoned corridor background", "shallow depth of field"],
                "negative_prompt_hints": ["清晰文字", "人手", "現代物品"],
                "lora_weight_adjustment": {"horror_creepy": -0.1},
                "defect_warnings": ["紙張邊緣要自然", "不要出現可讀文字（版權風險）"]
            }
        }
    ],
    "discussion_log": "briefs/discussion_{date}.md",
    "total_discussion_time_sec": 900,
    "openrouter_cost": 0.08
}
```

### Stage 0 失敗處理
```
失敗情境與處理方式:

1. OpenRouter API 連線失敗:
   - 重試 2 次（間隔 30 秒）
   - 仍失敗 → 跳過 Stage 0，Stage 2 退化為模板模式
   - 記錄失敗原因到 daily log

2. 對話中途中斷（部分簡報）:
   - 若已完成至少 1 張圖的完整視覺指導 → 使用已完成部分
   - 第 2 張圖退化為模板模式補足
   - brief_{date}.json 標記 "partial: true"

3. 素材庫為空（該主題無素材）:
   - 直接跳過 Stage 0
   - Stage 2 使用模板模式
   - 記錄警告: "主題 {theme} 素材庫為空，請 LXYA 補充"

4. LXYA 手動指定簡報但格式不完整:
   - 對缺失欄位填入主題預設值
   - 缺 canvas_type → 使用主題 default_canvas
   - 缺 prompt hints → Stage 2 退化為模板模式填補

原則: Stage 0 失敗永遠不阻斷 Pipeline，最差情況退化為模板模式
```

### 記憶交互點
```
寫入:
- 每日創意簡報 → briefs/brief_{date}.json
- 討論紀錄 → briefs/discussion_{date}.md（完整對話記錄，供 04 模組萃取）
- 素材使用紀錄 → 更新 _index.json 的 used_count 和 last_used

讀取:
- 主題素材庫 → config/source-library/{theme}/
- 素材索引 → config/source-library/_index.json（避免重複選用）
- 過往 insights → 了解哪類故事角度產出的圖片通過率高（via keyword_index tags 查詢）
- 前次同素材的討論 → 如果同一篇素材被再次選中，參考上次的角度避免重複
```

---

## Stage 1：排程啟動 & 上下文載入

### 觸發方式
- **自動觸發**：由 Heartbeat 在 09:00 啟動（Stage 0 已在 07:00 完成）
- **手動觸發**：LXYA 指令 "開始今天的圖片生產"
- **補產觸發**：若前一天未達目標產量，隔日自動追加

### 上下文載入流程
```
1. 讀取今日創意簡報 → briefs/brief_{date}.json
   - 確認 Stage 0 已完成，簡報檔案存在
   - 若簡報不存在 → fallback: 使用傳統模板模式（Stage 2 退化為純模板生成）
2. 讀取 config/schedule.json → 取得今日目標產量
3. 讀取 config/topics.json → 載入今日主題的畫布規則和參數
4. 查詢記憶系統：
   a. 掃描 memory/insights/technical/ 中與 stock-pipeline/comfyui 相關的 insights
      → 目的：帶著過去的經驗進場
   b. 讀取前一天的生產紀錄（memory/daily/ 或 memory/metrics/）
      → 目的：知道昨天的通過率、失敗模式
5. 今日主題已由 Stage 0 決定（從簡報中讀取）
   - 若無 Stage 0 → 按主題輪替策略決定（見 config/schedule.json）
   - 可由 LXYA 手動指定覆蓋
6. 計算今日生產計畫：
   - 基礎目標: 2 張/天（全部同一主題，來自同一篇素材的不同角度）
   - 根據主題自動選定對應的畫布方向與尺寸規則（見 Stage 3 畫布規則）
   - 每張圖的畫布類型可能不同（由創意簡報指定）
```

### 上下文載入的記憶觀測點（供 03 模組使用）
```
觀測項目:
- memory_reads_count: 本階段讀取了多少記憶檔案
- memory_hit_rate: 讀取的檔案中有多少實際影響了生產決策
- insight_applied: 套用了哪些 insight 規則（記錄 insight 檔案路徑）
- context_load_time_ms: 上下文載入耗時
- token_estimate: 估算載入的 Token 數量
```

---

## Stage 2：提示詞生成與優化

### 設計理念
Stage 2 的輸入來源優先使用 Stage 0 產出的創意簡報（brief_{date}.json），讓每張圖的提示詞背後都有故事概念支撐。若 Stage 0 未執行或簡報不存在，則退化為傳統模板模式作為 fallback。

### 流程細節

#### 2.1 讀取創意簡報 → 提取視覺指導

```
輸入來源判定:
  IF brief_{date}.json 存在:
    → 模式: "creative_brief"（創意簡報驅動）
    → 讀取每張圖的 visual_concept（場景/構圖/氛圍/關鍵物件/色調）
    → 讀取 creative_director_notes 和 visual_artist_notes
    → 將故事概念轉化為 ComfyUI 可用的提示詞結構
  ELSE:
    → 模式: "template_fallback"（傳統模板生成）
    → 使用下方 2.1b 的主題模板庫

提示詞結構映射（creative_brief 模式）:
  brief.scene_description  → 正面提示詞核心
  brief.mood_atmosphere    → 光影/色調修飾詞
  brief.key_objects        → 物件細節描述
  brief.color_palette      → 色彩方案關鍵詞
  brief.composition_notes  → 構圖指導（同時影響畫布選擇）
  brief.style_reference    → 風格關鍵詞
```

#### 2.1b 傳統模板庫（Fallback 模式）

```
每個主題維護一組提示詞模板（僅在 Stage 0 未執行時使用）:

科技抽象 (tech-abstract):
  - 結構: [科技概念] + [視覺風格] + [構圖指導] + [色彩方案]
  - 範例基底: "futuristic neural network visualization, abstract data flow..."
  - 變化維度: 概念類型、色溫、複雜度、視角

陰森場景 (eerie-scene):
  - 結構: [場所] + [氛圍描述] + [光影指導] + [細節元素]
  - 範例基底: "abandoned hospital corridor, flickering fluorescent lights..."
  - 變化維度: 場所類型、時間、天氣、恐怖程度

怪誕生物 (creature-design):
  - 結構: [生物基礎] + [變異特徵] + [環境適應] + [藝術風格]
  - 範例基底: "bioluminescent deep sea creature, translucent exoskeleton..."
  - 變化維度: 物種基底、變異方向、棲息環境、尺度

ClawClaw 個人風格肖像 (clawclaw-portrait):
  - 結構: [人物描述] + [情緒/表情] + [光影風格] + [背景氛圍] + [藝術手法]
  - 範例基底: "ethereal portrait of a young woman, soft cinematic lighting, painterly style..."
  - 變化維度: 人物特徵、情緒基調、光源方向、色調風格、背景複雜度
  - 特殊規則: 此主題強制使用 portrait 或 square 畫布（人形硬規則）
  - 不使用 LoRA，純靠 rinIllusion 基礎模型 + 精準提示詞塑造 ClawClaw 獨有風格
  - 風格目標: 發展出可辨識的個人風格特徵，讓 ClawClaw 的肖像作品有獨特辨識度
```

#### 2.2 Ollama 智能優化（必備步驟）
無論提示詞來源是創意簡報或傳統模板，所有提示詞必須經過本地模型優化：

```
呼叫流程:
1. 將原始提示詞送入 Ollama qwen3:8b
2. 附帶優化指令:
   - 增加視覺細節描述
   - 加入風格一致性關鍵詞
   - 插入品質保證詞 (masterpiece, best quality, highly detailed)
   - 加入缺陷預防詞 (anatomically correct, symmetrical, proper proportions)
   - [creative_brief 模式額外] 保留創意簡報中的核心故事元素，避免優化後稀釋
3. 接收優化後提示詞
4. 同時生成對應的負面提示詞 (negative prompt)
```

#### 2.3 提示詞多樣性保證
```
去重機制:
- 維護已使用提示詞的 hash 集合（存於 memory/metrics/prompt_history.json）
- 新生成的提示詞與近 7 天的歷史比對
- 相似度 > 85% 則重新生成
- 確保同一主題內的變化維度不重複
- [creative_brief 模式] 由於每日簡報的故事概念不同，重複機率天然較低
```

### 記憶交互點
```
寫入:
- 每個提示詞的生成紀錄 → memory/metrics/ (批次結算時統一寫入)
- 效果特別好的提示詞 → memory/topics/technical/wirestock-prompt-patterns.md
- 提示詞來源模式 (creative_brief / template_fallback) → 記錄到日報

讀取:
- Stage 0 創意簡報 → brief_{date}.json
- 過去成功的提示詞模式 → 從 insights/ 中獲取
- 被拒絕的提示詞特徵 → 從 insights/ 中獲取避免重蹈覆轍
```

---

## Stage 3：圖像生成精煉迴圈

### 設計理念
採用「初步候選 → 自評篩選 → 精煉放大 → 再次自評 → 最終 Upscale」的多階段精煉流程。
核心優勢：初步階段快速試錯（×5 候選），精煉階段提升品質（×5 候選），最終階段 4x Upscale 輸出商業級解析度。

### 畫布方向與尺寸規則

根據實務經驗，不同內容類型需要對應的畫布方向以避免生成缺陷（如人像肢體扭曲）：

```
畫布類型定義:

┌─────────────┬────────────────────┬────────────────────┬──────────────────────────┐
│ 畫布類型     │ 初步尺寸           │ 精煉尺寸           │ 最終尺寸 (4x Upscale)     │
├─────────────┼────────────────────┼────────────────────┼──────────────────────────┤
│ 方形 square  │ 768 × 768          │ 1280 × 1280        │ 5120 × 5120              │
│ 人像 portrait│ 768 × 1280         │ 900 × 1400         │ 3600 × 5600              │
│ 場景 landscape│ 1280 × 960        │ 2560 × 1920        │ 10240 × 7680             │
└─────────────┴────────────────────┴────────────────────┴──────────────────────────┘

畫布選擇規則（寫入 config/topics.json）:

科技抽象 (tech-abstract):
  - 預設畫布: square（抽象圖形適合方形構圖）
  - 備選: landscape（大場景科技概念）
  - 注意: 若提示詞包含人形元素 → 強制切換為 portrait

陰森場景 (eerie-scene):
  - 預設畫布: landscape（場景以橫幅呈現最佳）
  - 備選: portrait（走廊、樓梯等窄長場景）
  - 注意: 若包含人物主體 → 切換為 portrait

怪誕生物 (creature-design):
  - 預設畫布: portrait（生物通常以直幅呈現）
  - 備選: square（頭部特寫、對稱構圖）
  - 注意: 生物類避免使用 landscape（容易產生肢體拉伸）

ClawClaw 個人風格肖像 (clawclaw-portrait):
  - 預設畫布: portrait（肖像標準直幅）
  - 備選: square（半身/臉部特寫時）
  - 注意: 此主題永遠不使用 landscape（人像硬規則強制覆蓋）

人形相關硬規則（最高優先順序）:
  - 提示詞包含人像/半身/全身/人物 → 強制 portrait
  - 提示詞包含臉部特寫/頭像 → 強制 square
  - 任何包含 "person", "human", "figure", "portrait" → 強制 portrait 或 square
  - 此規則覆蓋主題預設，目的是降低肢體扭曲發生率
```

### 呼叫架構
```
ComfyUI 呼叫參數:
- 模型: rinIllusion (基礎) + 當日主題對應 LoRA
- 初步解析度: 依畫布類型（見上表）
- 精煉解析度: 依畫布類型（見上表）
- 最終解析度: 精煉尺寸 × 4（ComfyUI Upscale）
- CFG Scale: 依主題調整 (科技 7-9, 陰森 6-8, 生物 8-10, 肖像 6-8)
- 步數: 20-25 (初步階段) / 28-35 (精煉階段)
- 採樣器: Euler a / DPM++ 2M Karras (依主題)
- Seed: 隨機，但記錄每張圖的 seed 供重現

LoRA 配置 (依當日主題):
- 科技抽象: Cyber Graphic LoRA (權重 0.6-0.8)
- 陰森場景: Horror & Creepy LoRA (權重 0.5-0.7)
- 怪誕生物: Creatures Design V1 (權重 0.7-0.9)
- ClawClaw 肖像: 不使用 LoRA（純 rinIllusion 基礎模型，靠提示詞塑造風格）
```

### 精煉迴圈流程（每張圖的完整生命週期）
```
對每個生產任務（同一提示詞）:

═══════════════════════════════════════════
[3.1] 初步候選生成（快速試錯）
═══════════════════════════════════════════
  - 依畫布規則選定初步尺寸
  - 生成 5 張候選圖（相同提示詞，不同 seed）
  - 步數 20-25，加快生成速度
  - 目的：用較低成本探索不同構圖可能性

═══════════════════════════════════════════
[3.2] 第一次 OpenRouter 自評 → 選出最佳 1 張
═══════════════════════════════════════════
  - 將 5 張初步候選送入 OpenRouter 視覺模型
  - 評估維度：構圖完整性、主體清晰度、明顯缺陷、主題匹配度
  - 輸出格式（每張圖）:
    {
      "score": 7.8,
      "reason": "構圖平衡，但人物左手比例略大",
      "controlnet_advice": {
        "use": true,                    // 是否建議在 3.3 精煉階段使用 ControlNet
        "type": "openpose",             // openpose / depth / canny / null
        "reason": "人物姿勢良好值得保留，用 pose 約束防止精煉階段偏移"
      }
    }
  - controlnet_advice 由模型自行判斷:
    - use: true + "openpose": 姿勢好、想保留 → pose ControlNet
    - use: true + "depth": 空間透視好、想保留 → depth ControlNet
    - use: true + "canny": 邊緣/輪廓精準、想保留 → canny ControlNet
    - use: false: 不需要，或結構本身有問題需要重新探索
  - 選出分數最高的 1 張作為精煉基底，其 controlnet_advice 傳遞給 Stage 3.3
  - 若 5 張全部低於 5.0 → 該提示詞品質不佳，重新生成提示詞（最多 1 次回退至 Stage 2）
  - 記錄：落選的 4 張及其分數，供 insight 分析

═══════════════════════════════════════════
[3.3] 精煉放大生成（品質提升）
═══════════════════════════════════════════
  - 以 3.2 選出的最佳候選為基底
  - 使用 img2img 放大至精煉尺寸
  - 生成 5 張精煉候選（基於相同基底圖，不同 seed + 微調 denoise）
  - denoise strength 變化範圍: 0.25, 0.30, 0.35, 0.40, 0.45
    （5 張各用不同 denoise，探索最佳保留/創新平衡）
  - 步數提高至 28-35
  - ControlNet 精修（由 3.2 自評建議驅動）:
    - 讀取 3.2 最佳候選的 controlnet_advice
    - 若 use: true → 在精煉階段套用指定的 ControlNet 模型
    - 若 use: false → 不使用 ControlNet，純 img2img 精煉
    - ControlNet 的 reference image 為 3.2 選出的最佳候選圖

═══════════════════════════════════════════
[3.4] 第二次 OpenRouter 自評 → 選出最佳 1 張
═══════════════════════════════════════════
  - 將 5 張精煉候選送入 OpenRouter 視覺模型
  - 評估維度（比 3.2 更嚴格）：
    - 細節品質（放大後是否出現模糊、偽影）
    - 結構準確性（人體比例、手指數、對稱性）
    - 色彩一致性（放大後色彩是否失真）
    - 與原始候選的一致性（是否保留了最佳構圖）
  - 輸出：每張圖的評分 (1-10) + 詳細理由 + 缺陷列表
  - 選出分數最高的 1 張作為最終候選
  - 若 5 張全部低於 7.0 → 丟棄本張，記錄失敗原因

═══════════════════════════════════════════
[3.5] 最終 Upscale（商業級解析度輸出）
═══════════════════════════════════════════
  - 將 3.4 選出的最終候選送入 ComfyUI Upscale
  - 使用 4x-UltraSharp 或 ESRGAN 4x 模型
  - 放大倍率: 4x（精煉尺寸 → 最終尺寸）
  - 此階段純放大，不改變內容
  - 輸出格式: PNG (無損)
  - 輸出至 Stage 4 品質檢測
```

### 精煉迴圈視覺化
```
每張圖的生命週期:

  提示詞 ──→ [3.1 初步 ×5] ──→ [3.2 自評] ──→ 最佳1張
                                     │                │
                              落選4張丟棄        ┌─────┘
                                                 ↓
              [3.4 自評] ←── [3.3 精煉 ×5] ←── 基底圖
                   │
              最佳1張 ──→ [3.5 Upscale 4x] ──→ Stage 4 精檢
                   │
            落選4張丟棄

  每張最終輸出消耗: 初步5張 + 精煉5張 = 10次ComfyUI生成 + 2次OpenRouter評分 + 1次Upscale
  每日2張目標消耗: ~20次生成 + ~4次評分 + ~2次Upscale
```

### 重試預算與邊緣條件
```
重試預算計算規則:
  config: max_retries_per_image = 2, max_daily_retries = 4

  每張圖的重試預算獨立計算（最多 2 次）:
  - Stage 3.2 全部 < 5.0 → 回退 Stage 2 重新生成提示詞（消耗 1 次重試）
  - Stage 3.4 全部 < 7.0 → 丟棄本張（不消耗重試，直接放棄）
  - Stage 4 偵測到可修復缺陷 → 回退 Stage 3.1 重新生成（消耗 1 次重試）
  - 累計每日所有圖片的重試不超過 4 次

  優先順序: 人形硬規則 (highest) > 主題預設畫布 > 替代畫布

邊緣條件處理:

  1. 同一天兩張圖全部失敗（0/2）:
     → 接受部分成功（含 0），不自動追加生產
     → 批次結算報告中記錄 "target_fulfillment_rate: 0.0"
     → 觸發 AAR 深度分析失敗原因
     → 隔日自動嘗試補產（catch_up_enabled: true）

  2. Stage 3.2 回退 Stage 2 後仍全部 < 5.0:
     → 丟棄該圖，記錄 "prompt_quality_failure"
     → 移至下一張圖（不繼續重試）

  3. OpenRouter API 呼叫失敗（Stage 3.2/3.4）:
     → 重試 2 次（間隔 15 秒）
     → 仍失敗 → 使用 Ollama qwen3:8b 作為 fallback 文字評估
     → Ollama fallback 只做簡單排序（無法看圖），基於 prompt 和 seed 差異推理
     → 記錄 "openrouter_fallback_used: true"
```

### OpenRouter 視覺模型配置
```
用途: Stage 3.2 初步自評 + Stage 3.4 精煉自評
模型選擇策略: 見「OpenRouter 模型策略」章節（初期 Gemini Flash，穩定後 Claude Sonnet）
  - 全局配置: config 中 openrouter_model 欄位，一處修改全局生效
  - 要求: 支援圖片輸入、回應速度快
  - Stage 3.2 呼叫: 5 張圖片 + 快速評分指令（構圖完整性、主體清晰度、明顯缺陷、主題匹配）
  - Stage 3.4 呼叫: 5 張圖片 + 詳細評分指令（含 02 文件定義的四維矩陣: 技術/美學/解剖/商業）
  - 預估成本: Gemini Flash ~$0.02-0.05/次，Claude Sonnet ~$0.08-0.15/次

API 呼叫範本:
  endpoint: https://openrouter.ai/api/v1/chat/completions
  headers: { "Authorization": "Bearer {OPENROUTER_API_KEY}" }
  body: {
    "model": "{selected_model}",
    "messages": [
      { "role": "user", "content": [
        { "type": "text", "text": "評分指令..." },
        { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
      ]}
    ]
  }
```

### 異常處理
```
ComfyUI 無回應:
  → 等待 30 秒重試，最多 3 次
  → 仍失敗則記錄錯誤，跳過該張，記入 insights

CUDA OOM (記憶體不足):
  → 參考 memory/insights/technical/2026-03-26-cuda-相關經驗.md
  → 初步階段較少發生（尺寸適中）
  → 精煉階段 OOM → 降低精煉尺寸或減少 LoRA 數量
  → Upscale 階段 OOM → 改用 2x 分兩次放大（2x → 2x = 4x）

生成結果全黑/全白:
  → 調整 CFG Scale (±2)
  → 更換採樣器重試
  → 記錄為異常模式供 insight 分析

OpenRouter API 失敗:
  → 重試 2 次（間隔 5 秒）
  → 仍失敗 → fallback:
    - Stage 3.2: 跳過自評，隨機選一張進入精煉
    - Stage 3.4: 跳過自評，選 denoise=0.35 的中間值
  → 記錄 API 錯誤供後續排查
```

---

## Stage 4：品質檢測與篩選

（詳見 02-defect-detection-repair.md，此處僅記錄接口）

注意：Stage 3 內部的自評是「構圖/結構篩選」（選出最佳候選），Stage 4 是「商業品質精檢」（全面多維度，決定能否上架）。Stage 4 檢測的是 Upscale 後的最終圖片。

### 呼叫接口
```
輸入: 4x Upscale 後的最終圖片路徑 + 生成參數 + Stage 3.4 的精煉評分
輸出: {
    "pass": true/false,
    "score": 8.7,
    "defects": [...],
    "defect_details": {
        "pros": ["構圖平衡", "色彩和諧", "..."],
        "cons": ["右手第六指", "..."]
    },
    "suggestions": [...],
    "retry_params": {...}  // 如未通過，建議的重試參數
}
```

### 決策邏輯
```
score >= 8.5 且 defects 為空:
  → 通過，進入 Stage 5

score >= 7.0 且 defects 可修復:
  → Ollama qwen3:8b 根據 OpenRouter 回傳的缺陷描述推理修復策略
    （如: "右手第六指" → 建議 "negative prompt 加強 extra fingers, 啟用 pose ControlNet"）
  → 使用 retry_params + Ollama 修復建議 回到 Stage 3.1 重新生成（消耗重試預算）
  → 重試後仍未通過則丟棄

score < 7.0:
  → 直接丟棄
  → 記錄失敗原因供 insight 分析

角色分工:
  OpenRouter = 圖片視覺分析（看圖找缺陷）
  Ollama qwen3:8b = 文字推理（根據缺陷描述推理修復策略和參數調整）
```

---

## Stage 5：上傳準備 & 批次結算

### 5.1 圖片描述提取 & 元數據嵌入

使用 OpenRouter 多模態視覺模型讀取最終圖片，產出精準的英文描述和關鍵詞，再嵌入 EXIF/IPTC 元數據。Dreamstime 會自動讀取嵌入的元數據；Adobe Stock 手動上傳時也能直接使用已嵌入的元數據。

```
對每張通過的圖片:

1. OpenRouter 圖片描述提取:
   - 將圖片送入 OpenRouter 視覺模型
   - Prompt 指令: "為這張圖片產生以下內容（全英文）:
     a) 一段 100-150 字的商業描述 (description)
     b) 15-25 個搜尋關鍵詞 (keywords)，逗號分隔
     c) 建議的 Adobe Stock 類別 (category)"
   - 此步驟確保描述基於「圖片實際內容」而非只是提示詞

2. EXIF/IPTC 元數據嵌入（使用 Python exiftool 或 Pillow + iptcinfo3）:
   - IPTC:ObjectName → 簡短標題
   - IPTC:Caption-Abstract → OpenRouter 產出的商業描述
   - IPTC:Keywords → OpenRouter 產出的關鍵詞列表
   - EXIF:ImageDescription → 同上描述
   - EXIF:UserComment → "AI Generated"
   - XMP:Creator → 創作者資訊

3. 檔案命名規範:
   - 格式: {topic}_{date}_{sequence}_{score}.png
   - 範例: tech-abstract_20260326_003_8.7.png

4. 平台特殊處理:
   - Adobe Stock: 需額外標記 "Generative AI" 標籤
   - Dreamstime: 需在描述中包含 "AI generated" 標記
   - ClawClaw 肖像主題: 人臉需標記 "People and Property are fictional"

5. 存放位置:
   - 待上傳: ~/.openclaw/workspace/stock-pipeline/pending/
   - 已上傳: ~/.openclaw/workspace/stock-pipeline/uploaded/
   - 被拒絕: ~/.openclaw/workspace/stock-pipeline/rejected/
```

### 5.2 上傳：Dreamstime FTP 自動 + Adobe Stock 手動

Dreamstime 支援 FTP 上傳，由 ClawClaw 自動完成；Adobe Stock 不支援 FTP/SFTP contributor 上傳，由 LXYA 手動上傳（元數據已嵌入，拖拽即可）。

```
═══════════════════════════════════════════
[5.2a] Dreamstime FTP 自動上傳
═══════════════════════════════════════════

FTP 上傳流程:
1. 連線至 Dreamstime FTP 伺服器
2. 將 pending/ 資料夾中的圖片批量上傳
3. 上傳成功後將圖片移至 uploaded/
4. 記錄上傳結果（成功/失敗/檔案大小/耗時）

Dreamstime FTP 設定:
  host: upload.dreamstime.com
  port: 21
  transfer_mode: Passive
  username: (Dreamstime FTP ID，非 email，是一串數字，在帳戶頁面右側可見)
  password: (建議存於環境變數 DREAMSTIME_FTP_PASS)
  remote_path: / (根目錄直接上傳圖片)
  additional_formats: /additional/ (上傳額外格式)
  model_releases: /modelrelease/ (上傳 Model Release)
  upload_limit: 1GB 總量

技術實作:
  - Python ftplib，被動模式 (PASV)
  - 上傳前驗證: 確認元數據已嵌入、檔案大小合理 (< 50MB)
  - 斷線重連: 自動重試 3 次（間隔 30 秒）
  - 3 次重試後仍失敗 → 放棄 FTP，通知 LXYA 手動上傳（同 5.2b 通知格式）
  - 單張上傳超時: 5 分鐘
  - 上傳日誌: 記錄每張圖的 FTP 回應碼

═══════════════════════════════════════════
[5.2b] Adobe Stock 手動上傳通知
═══════════════════════════════════════════

Adobe Stock 不支援 contributor FTP/SFTP 上傳，需 LXYA 手動操作:
1. ClawClaw 完成 Dreamstime 自動上傳後
2. 產出通知給 LXYA，內容包含:
   - pending/ 資料夾路徑（或 uploaded/ 如已上傳 Dreamstime）
   - 本批圖片清單（檔名 + 評分 + 主題）
   - 提醒: "請至 Adobe Stock Contributor Portal 手動上傳，元數據已嵌入，勾選 Generative AI 標記"
3. LXYA 上傳時只需拖拽檔案，描述和關鍵詞會自動帶入

分批策略（兩個平台共用）:
  - 每批最多 15 張
  - 批次間隔 12 小時
  - 上午批次: 09:00-10:00
  - 下午批次: 21:00-22:00

Fallback:
  - Dreamstime FTP 不可用 → 也改為通知 LXYA 手動上傳
  - ClawClaw 產出上傳待辦通知，附帶路徑和圖片清單

未來擴展:
  - 可隨時新增支援 FTP 的平台（如 123RF），只需新增一組 FTP 設定
  - ftp_uploader.py 設計為平台無關的迴圈
  - 未來擴展多平台時建立 config/platforms.json（目前僅 Dreamstime，設定直接寫在腳本中）
```

### 批次結算
```
每日生產結束後產出結算報告:

{
    "date": "2026-03-27",
    "session_id": "ws-20260327-001",
    "target": 2,
    "today_theme": "tech-abstract",
    "prompt_source": "creative_brief",       // "creative_brief" 或 "template_fallback"
    "generated": 4,              // 總生成數（含重試）
    "passed": 2,                 // 通過品質檢測
    "retried": 1,                // 重試次數
    "discarded": 2,              // 丟棄數
    "pass_rate": 0.50,           // 2/4
    "final_pass_rate": 1.00,     // 2/2 (對目標)
    "avg_score": 8.8,
    "topic_detail": {
        "theme": "tech-abstract",
        "target": 2,
        "passed": 2,
        "avg_score": 8.8
    },
    "total_generation_time_min": 25,
    "stage0_brief_used": true,
    "defect_summary": {
        "eye_issues": 0,
        "hand_issues": 0,
        "composition": 1
    },
    "upload_status": {
        "dreamstime_ftp": {"uploaded": 2, "failed": 0},
        "adobe_stock_notified": true
    }
}
```

---

## 參數配置結構

### config/schedule.json
```json
{
    "daily_target": 2,
    "max_retries_per_image": 2,
    "max_daily_retries": 4,
    "batch_upload_size": 15,
    "upload_intervals_hours": 12,
    "creative_brief_session": {
        "start": "07:00",
        "auto_trigger": true,
        "comment": "Stage 0 創意素材討論會，由雙 Agent 對話產出今日創意簡報"
    },
    "production_window": {
        "start": "09:00",
        "end": "14:00",
        "comment": "每日僅 2 張精煉圖，預估 09:00-11:00 可完成生產，14:00 為安全上限"
    },
    "auto_trigger": true,
    "catch_up_enabled": true,
    "topic_rotation": {
        "mode": "equal_cycle",
        "cycle_order": ["tech-abstract", "eerie-scene", "clawclaw-portrait", "creature-design"],
        "comment": "每日只生產一個主題，四主題均等輪替（各 25%）。LXYA 可手動覆蓋。"
    },
    "manual_topic_override": null
}
```

### config/topics.json
```json
{
    "canvas_types": {
        "square": {
            "initial": [768, 768],
            "refined": [1280, 1280],
            "description": "方形畫布，適合抽象圖形、臉部特寫、對稱構圖"
        },
        "portrait": {
            "initial": [768, 1280],
            "refined": [900, 1400],
            "description": "直幅畫布，適合人像、生物、直立主體。人形必用此畫布避免肢體扭曲"
        },
        "landscape": {
            "initial": [1280, 960],
            "refined": [2560, 1920],
            "description": "橫幅畫布，適合場景、全景、非人形橫向構圖"
        }
    },
    "upscale": {
        "multiplier": 4,
        "model": "4x-UltraSharp",
        "fallback_model": "ESRGAN_4x",
        "comment": "最終 Upscale 統一 4x，從精煉尺寸放大至商業級解析度"
    },
    "canvas_override_rules": [
        {
            "condition": "prompt contains human/person/figure/portrait/半身/全身/人物",
            "force_canvas": "portrait",
            "priority": "highest",
            "reason": "人形使用直幅或方形可大幅降低肢體扭曲"
        },
        {
            "condition": "prompt contains face closeup/headshot/頭像/臉部特寫",
            "force_canvas": "square",
            "priority": "highest",
            "reason": "臉部特寫用方形最佳"
        }
    ],
    "topics": {
        "tech-abstract": {
            "display_name": "抽象科技概念",
            "rotation_weight": 0.25,
            "priority": 1,
            "default_canvas": "square",
            "alt_canvas": "landscape",
            "canvas_note": "抽象圖形預設方形；大場景科技概念可用橫幅",
            "base_cfg": 8,
            "initial_steps": 22,
            "refined_steps": 30,
            "sampler": "euler_a",
            "lora": "cyber_graphic",
            "lora_weight": 0.7,
            "negative_boost": ["blurry", "low quality", "text", "watermark"]
        },
        "eerie-scene": {
            "display_name": "陰森場景風格",
            "rotation_weight": 0.25,
            "priority": 2,
            "default_canvas": "landscape",
            "alt_canvas": "portrait",
            "canvas_note": "場景預設橫幅；走廊/樓梯等窄長場景可用直幅。含人物主體時切換 portrait",
            "base_cfg": 7,
            "initial_steps": 20,
            "refined_steps": 28,
            "sampler": "dpmpp_2m_karras",
            "lora": "horror_creepy",
            "lora_weight": 0.6,
            "negative_boost": ["bright", "cheerful", "cartoon", "anime face"]
        },
        "creature-design": {
            "display_name": "怪誕生物設計",
            "rotation_weight": 0.25,
            "priority": 3,
            "default_canvas": "portrait",
            "alt_canvas": "square",
            "canvas_note": "生物預設直幅；頭部特寫/對稱構圖可用方形。避免 landscape（易肢體拉伸）",
            "base_cfg": 9,
            "initial_steps": 23,
            "refined_steps": 35,
            "sampler": "euler_a",
            "lora": "creatures_design_v1",
            "lora_weight": 0.8,
            "negative_boost": ["human", "realistic photo", "simple background"]
        },
        "clawclaw-portrait": {
            "display_name": "ClawClaw 個人風格肖像",
            "rotation_weight": 0.25,
            "priority": 4,
            "default_canvas": "portrait",
            "alt_canvas": "square",
            "canvas_note": "肖像永遠使用 portrait 或 square，永不使用 landscape",
            "base_cfg": 7,
            "initial_steps": 22,
            "refined_steps": 32,
            "sampler": "dpmpp_2m_karras",
            "lora": null,
            "lora_weight": 0,
            "lora_note": "不使用 LoRA，純靠 rinIllusion 基礎模型 + 精準提示詞塑造 ClawClaw 獨有風格",
            "negative_boost": ["deformed face", "extra fingers", "bad anatomy", "blurry", "low quality", "asymmetric eyes", "cartoon", "anime"],
            "style_keywords": ["cinematic lighting", "painterly", "soft focus background", "emotional expression", "detailed skin texture"],
            "style_note": "ClawClaw 的個人風格定位：透過累積 insight 逐步發展獨有的肖像風格特徵"
        }
    },
    "refinement": {
        "initial_candidates": 5,
        "refined_candidates": 5,
        "denoise_range": [0.25, 0.30, 0.35, 0.40, 0.45],
        "initial_min_score": 5.0,
        "refined_min_score": 7.0,
        "max_prompt_retries": 1
    },
    "quality_threshold": 8.5,
    "retry_threshold": 7.0
}
```

---

## 待確認事項

1. ~~**ComfyUI API 接口**~~：✅ 已測試確認沒問題
2. ~~**上傳平台與方式**~~：✅ Dreamstime FTP 自動上傳 + Adobe Stock 手動上傳，不經中間商
3. ~~**LoRA 可用性**~~：✅ 模型都已下載完畢
4. ~~**GPU 記憶體限制**~~：✅ RTX 4070 12GB 目前測試沒問題
5. ~~**每日排程與 Heartbeat 整合**~~：✅ 排程測試沒問題

### 新增待確認事項
6. ~~**平台帳號**~~：✅ Adobe Stock 和 Dreamstime contributor 帳號已辦好
7. **Dreamstime FTP 憑證測試**：⏳ LXYA 後續自行測試（取得 FTP ID，測試連線 upload.dreamstime.com:21）
8. ~~**OpenRouter API Key**~~：✅ API Key 已確認可用
9. ~~**OpenRouter 每日成本預估**~~：✅ Gemini Flash 預估 ~$0.36/天（月 ~$10.80），Claude Sonnet 預估 ~$1.50/天（月 ~$45），實際運行後校準
10. ~~**ControlNet 模型可用性**~~：✅ 所有需要的 ControlNet 模型已下載安裝

### OpenRouter 模型策略（已確認）
```
採用兩階段切換策略:

Phase 1 - 初期測試階段（全部 Gemini Flash）:
  所有 Stage 統一使用 Gemini Flash，目的:
  - 確認整條 Pipeline 端到端可正常運作
  - 建立基準成本數據
  - 驗證 prompt 格式和回傳格式的穩定性

Phase 2 - 穩定運行後（全部 Claude Sonnet）:
  所有 Stage 統一切換至 Claude Sonnet，目的:
  - 提升評分精度和創意對話品質
  - 提升描述提取的商業價值

切換時機: Pipeline 連續 3 天無報錯、基準成本數據已收集完成後，由 LXYA 手動切換
切換方式: config 中設定 openrouter_model 欄位，一處修改全局生效
```
