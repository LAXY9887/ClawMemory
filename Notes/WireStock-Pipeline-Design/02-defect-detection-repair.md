# 02 - AI 缺陷檢測與迭代修復

> 模組定位: 品質把關引擎
> 被呼叫者: 01-daily-production-pipeline (Stage 3.2 候選自評 + Stage 4 精檢)
> 依賴: OpenRouter API（多模態視覺模型，取代 Ollama qwen3:8b 的圖片分析角色）、Ollama qwen3:8b（文字推理輔助）
> 設計基礎: memory/insights/technical/2026-03-26-ai-defect-resolution-breakthrough.md

---

## 設計理念

來自 LXYA 的核心指導：**從規避 AI 弱點轉向主動克服 AI 弱點**。

本模組不是簡單的「通過/不通過」篩選器，而是一個能理解缺陷成因、提出修復建議、並追蹤修復效果的智能系統。每次修復的經驗都會回饋到記憶系統，讓下一次的預防更精準。

---

## 檢測架構：三層遞進

### Layer 1：快速篩選（< 2 秒/張）

目的：用低成本排除明顯問題，避免在細節檢測上浪費時間。

```
檢測項目:
├── 圖片完整性
│   ├── 檔案可讀且非損壞
│   ├── 解析度符合預期（依畫布類型：方形 5120x5120 / 人像 3600x5600 / 場景 10240x7680 ±5%）
│   └── 非全黑/全白/單色
│
├── 基礎構圖
│   ├── 主體是否存在（非空白背景）
│   ├── 主體是否大致居中或符合三分法
│   └── 是否有明顯的截斷或溢出
│
└── 明顯瑕疵
    ├── 大面積色塊異常
    ├── 明顯的重複圖案 (tiling artifact)
    └── 文字/浮水印殘留

判定:
- 任一項不通過 → score 直接設為 0，跳過後續檢測
- 全部通過 → 進入 Layer 2
```

### Layer 2：細節品質評估（OpenRouter 多模態視覺模型）

目的：利用 OpenRouter 多模態模型直接分析圖片，進行多維度品質評估。

```
執行方式:
1. 將圖片以 base64 編碼送入 OpenRouter 視覺模型
2. 附帶結構化評分 prompt，要求模型按四維矩陣逐項評分
3. 模型直接「看」圖片，不再需要 Desktop-Vision 截圖 + 文字描述的間接路徑
4. Ollama qwen3:8b 仍可輔助：根據 OpenRouter 回傳的缺陷描述，推理修復策略

四維評估矩陣:

技術品質 (Technical Quality) - 權重 30%
├── 清晰度: 主體邊緣是否銳利
├── 雜訊: 是否有不自然的顆粒或模糊
├── 色彩: 色彩是否自然、對比是否適當
└── 一致性: 光影方向是否統一

美學品質 (Aesthetic Quality) - 權重 25%
├── 構圖: 主體位置、空間分佈
├── 色彩和諧: 色調搭配是否協調
├── 視覺重心: 是否有明確的焦點
└── 氛圍: 是否與主題一致

解剖準確性 (Anatomical Accuracy) - 權重 30%
├── 眼部: 對稱性、瞳孔、虹膜、高光 (6 項子檢查)
├── 手部: 手指數、關節、比例、透視 (6 項子檢查)
├── 動物: 物種一致、眼位、毛髮、解剖 (5 項子檢查)
└── 整體: 身體比例、姿態自然度

商業價值 (Commercial Value) - 權重 15%
├── 市場相關性: 是否符合目標市場需求
├── 關鍵詞潛力: 能否產生有效的搜尋關鍵詞
├── 使用場景: 可用於哪些商業情境
└── 獨特性: 與庫存圖片的差異度
```

### Layer 3：專項缺陷深度檢測

目的：對 Layer 2 中標記的可疑區域進行精密檢查。

```
眼部缺陷檢測 (當圖片包含人物/生物時):
├── 對稱性評估: 左右眼位置、大小、角度一致性
├── 結構完整性: 瞳孔、虹膜、眼瞼、睫毛完整檢查
├── 光線邏輯: 高光位置與光源方向一致性
├── 質感準確性: 眼球濕潤度、表面質感
├── 異常模式: 多瞳孔、缺失虹膜、不對稱散光
└── 評分: 每項 0-10，加權平均

手部缺陷檢測 (當圖片包含手部時):
├── 手指數量: 嚴格 5 指檢查
├── 關節邏輯: 每個關節的彎曲方向
├── 比例關係: 手指長度比、掌指比
├── 拇指定位: 拇指位置和對掌能力
├── 透視一致: 手部與場景的透視關係
└── 自然度: 手勢是否符合人體工學

動物特徵檢測 (當圖片包含動物時):
├── 物種一致性: 特徵不混合（不會出現貓耳狗臉）
├── 眼部精度: 動物眼部結構（位置、大小、形狀）
├── 毛髮方向: 生長方向與重力關係
├── 解剖邏輯: 四肢、尾巴、翅膀等結構正確性
└── 整體協調: 身體比例與姿態自然度
```

---

## 評分計算

### 綜合評分公式
```
final_score = (
    technical_quality * 0.30 +
    aesthetic_quality * 0.25 +
    anatomical_accuracy * 0.30 +
    commercial_value * 0.15
)

# 缺陷懲罰
for defect in detected_defects:
    if defect.severity == "critical":   # 如手指數量錯誤
        final_score -= 3.0
    elif defect.severity == "major":    # 如眼部不對稱
        final_score -= 1.5
    elif defect.severity == "minor":    # 如輕微模糊
        final_score -= 0.5

final_score = max(0, min(10, final_score))
```

### 判定標準
```
>= 8.5: PASS     → 直接通過，進入上傳準備
7.0-8.4: RETRY   → 可修復，嘗試迭代修復
< 7.0:  DISCARD  → 丟棄，記錄失敗原因
```

---

## 迭代修復流程

當圖片評分在 7.0-8.4 之間且缺陷可修復時，啟動迭代修復：

### 修復策略選擇
```
根據缺陷類型選擇修復策略:

眼部缺陷:
├── 策略 1: 提示詞強化
│   → 追加 "symmetrical eyes, perfect eye alignment, detailed iris"
│   → 負面追加 "asymmetric eyes, malformed pupils"
├── 策略 2: 參數調整
│   → CFG +1 (增加提示詞遵從度)
│   → 步數 +5 (增加細節精度)
└── 策略 3: ControlNet 輔助
    → 使用 depth map 控制臉部結構

手部缺陷:
├── 策略 1: 提示詞強化
│   → 追加 "anatomically correct hands, five fingers on each hand"
│   → 負面追加 "extra fingers, missing fingers, deformed hands"
├── 策略 2: LoRA 權重調整
│   → 降低風格 LoRA 權重 (-0.1)，讓基礎模型的解剖能力發揮
└── 策略 3: 構圖迴避
    → 如果手部非核心元素，調整提示詞讓手部不可見

整體品質不足:
├── 策略 1: 提升生成品質
│   → 步數 +10, CFG 微調
├── 策略 2: 更換採樣器
│   → euler_a → dpmpp_2m_karras 或反向
└── 策略 3: 更換 seed
    → 保持其他參數，只換隨機種子
```

### 修復迭代控制
```
最大迭代次數: 2 (每張圖)
每日最大重試預算: 6 次

迭代記錄:
{
    "image_id": "tech-abstract_20260327_003",
    "original_score": 7.8,
    "defects": ["eye_asymmetry"],
    "iterations": [
        {
            "attempt": 1,
            "strategy": "prompt_enhancement",
            "changes": {"positive_append": "symmetrical eyes...", "cfg": "+1"},
            "result_score": 8.2,
            "remaining_defects": ["minor_eye_reflection"]
        },
        {
            "attempt": 2,
            "strategy": "parameter_tuning",
            "changes": {"steps": "+5", "seed": "random"},
            "result_score": 8.7,
            "remaining_defects": []
        }
    ],
    "final_score": 8.7,
    "final_status": "PASS",
    "total_repair_time_sec": 180
}
```

---

## 缺陷知識庫（與記憶系統聯動）

### 寫入記憶
```
每次檢測完成後:

1. 統計數據 → memory/metrics/defect_stats_{date}.json
   - 各類缺陷出現頻率
   - 各修復策略的成功率
   - 平均修復迭代次數

2. 新發現的缺陷模式 → 觸發 04-experience-distillation 評估
   - 如果某類缺陷連續 3 天出現 → 自動寫入 insights/
   - 如果某修復策略成功率 > 90% → 記錄為推薦策略

3. 更新 keyword_index.json
   - 新的缺陷關鍵詞索引
   - 修復策略的快速查找路徑
```

### 讀取記憶
```
每次檢測前:

1. 載入相關 insights:
   - insights/technical/ 中 tags 包含 "defect"、"quality"、"comfyui" 的檔案
   - 只讀 YAML frontmatter + summary（動態上下文注入策略）

2. 查詢歷史缺陷模式:
   - 近 7 天的 defect_stats
   - 識別反覆出現的模式

3. 應用已知的預防規則:
   - 如果歷史顯示某主題某 LoRA 組合容易出手部問題
     → 在 Stage 2 就預先加入預防提示詞
```

---

## 實作考量

### 技術方案變更
原設計依賴 Ollama qwen3:8b（純文字模型）+ Desktop-Vision 的間接圖片分析路徑。
現改為 **OpenRouter 多模態視覺模型**，可直接讀取圖片進行評分和缺陷檢測。

### 角色分工
```
OpenRouter 視覺模型（主角）:
  - 直接分析圖片：構圖、缺陷、美學、解剖準確性
  - Stage 3.2 候選自評（快速、低成本 prompt）
  - Stage 4 精檢（詳細、多維度 prompt）
  - Stage 5.1 圖片描述提取（商業描述 + 關鍵詞）

Ollama qwen3:8b（輔助）:
  - 根據 OpenRouter 回傳的缺陷描述，推理修復策略
  - 提示詞優化（Stage 2，不需要看圖）
  - 結合歷史 insight 分析缺陷趨勢（純文字推理）
```

### OpenRouter 視覺模型呼叫規格
```
API endpoint: https://openrouter.ai/api/v1/chat/completions
認證: Bearer {OPENROUTER_API_KEY}

Stage 3.2 初步自評 prompt（快速模式）:
  - 輸入: 5 張初步候選圖（base64）
  - 要求: 每張圖給 1-10 分 + 一句話理由
  - 預期回應時間: < 5 秒
  - 預估成本: ~$0.02/次

Stage 3.4 精煉自評 prompt（中度模式）:
  - 輸入: 5 張精煉候選圖（base64，尺寸較大）
  - 要求: 每張圖給 1-10 分 + 詳細理由 + 缺陷列表
  - 預期回應時間: < 8 秒
  - 預估成本: ~$0.03-0.05/次

Stage 4 精檢 prompt（詳細模式）:
  - 輸入: 1 張放大後圖片
  - 要求: 四維評分矩陣 + 缺陷列表 + pros/cons + 修復建議
  - 預期回應時間: < 10 秒
  - 預估成本: ~$0.02-0.05/次

Stage 5.1 描述提取 prompt:
  - 輸入: 1 張最終圖片
  - 要求: 英文商業描述 (100-150 字) + 15-25 個關鍵詞 + 類別建議
  - 預期回應時間: < 8 秒
  - 預估成本: ~$0.02/次
```

### 成本預估（每日 2 張目標）
```
Stage 0   雙 Agent 創意對話: 1 次 × $0.05-0.10 = ~$0.08
Stage 3.2 初步自評: 2 任務 × $0.02 = ~$0.04
Stage 3.4 精煉自評: 2 任務 × $0.04 = ~$0.08
Stage 4   精檢: 2 張 × $0.05 = ~$0.10（含部分重試，圖片為 4x Upscale 大圖）
Stage 5.1 描述提取: ~2 張通過 × $0.03 = ~$0.06
每日總計: ~$0.36（月 ~$10.80）
注意: 實際成本取決於選用的模型和圖片大小，上述為保守預估值
      每日 2 張精煉目標大幅降低 API 成本，同時提升單張品質投入
```

### 漸進式實作路徑
```
Phase 1 (立即可做):
  - Layer 1 快速篩選（純規則，不需 AI）
  - OpenRouter 視覺模型基礎評分（直接看圖評分）
  - 簡單的重試邏輯（換 seed、微調參數）

Phase 2 (累積數據後):
  - 結合 LXYA 的人工評分校準 OpenRouter 的評分偏差
  - 用歷史數據微調 prompt 中的評分標準描述
  - 加入缺陷模式的統計分析

Phase 3 (系統成熟後):
  - 完整的 Layer 2/3 自動化檢測
  - 預測性缺陷預防（在生成前就避免已知問題）
  - 自適應品質門檻（根據市場反饋調整）
  - 評估是否需要切換到更精準/更便宜的 OpenRouter 模型
```

---

## 待確認事項

1. ~~**圖片分析方案**~~：✅ 決定使用 OpenRouter 多模態視覺模型，可直接讀取圖片
2. **品質基準線**：⏳ LXYA 將先搜集圖片並自行評分，完成後再協助初期建置校準。預計每週一次人工校準
3. ~~**ControlNet 可用性**~~：✅ 所有需要的 ControlNet 模型已下載安裝（depth、pose 等）
4. **修復策略的有效性**：⏳ 需建立獨立測試流程，在首批正式生產前完成驗證
5. ~~**OpenRouter 模型選擇**~~：✅ 兩階段切換：初期全部用 Gemini Flash 驗證流程，穩定後全部切換 Claude Sonnet。config 中一處修改全局生效
