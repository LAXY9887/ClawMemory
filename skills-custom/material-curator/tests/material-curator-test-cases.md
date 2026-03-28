---
topic: "Material Curator 測試案例集"
category: knowledge
created: 2026-03-27
importance: high
importance_score: 8
tags: [測試, material-curator, 品質保證, eval]
summary: "涵蓋配置驗證、爬取適配器、萃取、分類、去重、存檔、統計的完整測試案例集"
last_updated: 2026-03-27
access_count: 0
last_accessed: null
---

# Material Curator 測試案例集

> 版本: v1.0
> 建立日期: 2026-03-27
> 搭配文件: `tests/material-curator-test-guide.md`
> 測試案例: 5 類 25 題，滿分 75 分

---

## 評分量表

| 分數 | 意義 |
|---|---|
| 3 | 完全符合預期，行為正確且品質優良 |
| 2 | 大致符合，有小偏差但不影響功能 |
| 1 | 部分符合，有明顯遺漏或錯誤 |
| 0 | 完全不符合預期 |

---

## A 類：配置與初始化（5 題）

### MC-A01：curator_config.json 結構驗證

- **操作**: 讀取 `config/curator_config.json` 並驗證欄位
- **前置條件**: 配置檔存在
- **預期結果**:
  - 包含 output_dir、ollama、scraping、dedup 四個區段
  - ollama.model 不為空
  - scraping.polite_delay_seconds ≥ 1
  - dedup.similarity_threshold 在 0-1 之間
- **評分標準**:
  - 3: 所有欄位存在且值合理
  - 2: 欄位存在但有可疑值
  - 1: 有必要欄位缺失
  - 0: JSON 解析失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-A02：output_dir 路徑解析

- **操作**: 驗證 SOURCE_LIB_DIR 正確解析到 stock-pipeline 的 source-library
- **前置條件**: curator_config.json 中 output_dir 配置正確
- **預期結果**:
  - 相對路徑正確解析為絕對路徑
  - 解析結果指向 skills-custom/stock-pipeline/config/source-library/
  - 目標目錄存在且包含 _index.json
- **評分標準**:
  - 3: 路徑正確解析 + 目標存在
  - 2: 解析正確但目標不存在（可能是配置問題）
  - 1: 解析邏輯有問題
  - 0: 路徑解析崩潰
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-A03：MaterialCurator 初始化

- **操作**: `from material_curator import MaterialCurator; mc = MaterialCurator()`
- **前置條件**: scripts/ 在 Python path
- **預期結果**:
  - 物件建立不報錯
  - Ollama 配置從 curator_config.json 載入（非 wirestock 的 schedule.json）
  - _scrapers 字典已註冊內建適配器
- **評分標準**:
  - 3: 初始化成功 + 配置來源正確
  - 2: 初始化成功但配置來源不確定
  - 1: 初始化有警告
  - 0: 初始化失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-A04：不依賴 stock-pipeline 模組

- **操作**: 檢查 material_curator.py 中所有 import 語句
- **前置條件**: 腳本存在
- **預期結果**:
  - 不 import pipeline 的任何模組（openrouter_client, comfyui_client 等）
  - 不讀取 wirestock 的 schedule.json
  - 只依賴標準庫 + requests + beautifulsoup4
- **評分標準**:
  - 3: 完全獨立，零 wirestock 依賴
  - 2: 有間接參考（如共用常數）但不影響運行
  - 1: 有明確的 wirestock import
  - 0: 運行必須依賴 wirestock 模組
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-A05：Skill 目錄結構完整性

- **操作**: 確認 material-curator/ 下所有必要檔案存在
- **前置條件**: Skill 目錄已建立
- **預期結果**:
  - SKILL.md 存在
  - config/curator_config.json 存在
  - scripts/material_curator.py 存在
  - tests/ 目錄含 conftest.py 和 test_material_curator.py
  - requirements.txt 存在
  - pytest.ini 存在
- **評分標準**:
  - 3: 所有檔案齊全
  - 2: 缺少非關鍵檔案（如 pytest.ini）
  - 1: 缺少測試檔案
  - 0: 缺少核心腳本或配置
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## B 類：爬取適配器（5 題）

### MC-B01：Scraper 註冊機制

- **操作**: 初始化後檢查 _scrapers，再用 register_scraper 新增自訂
- **前置條件**: MaterialCurator 可初始化
- **預期結果**:
  - 內建 "creepypasta.fandom.com" 和 "reddit.com"
  - register_scraper() 可新增自訂 adapter
  - URL 匹配邏輯正確分派到對應 adapter
- **評分標準**:
  - 3: 註冊 + 分派 + 自訂都正確
  - 2: 內建正確但自訂未測試
  - 1: 註冊正確但分派有問題
  - 0: 註冊機制不存在
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-B02：Creepypasta 單篇爬取（需網路）

- **操作**: 爬取 `https://creepypasta.fandom.com/wiki/The_Rake`
- **前置條件**: 網路可用
- **預期結果**:
  - 回傳至少 1 筆結果
  - title 不為空
  - content 長度 > 200 字元
  - 已去除導航、目錄、廣告等噪音
  - source_site = "creepypasta.fandom.com"
- **評分標準**:
  - 3: 內容完整 + 噪音清除乾淨
  - 2: 內容完整但有少量噪音殘留
  - 1: 爬取成功但內容不完整
  - 0: 爬取失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-B03：Creepypasta Category 批次（需網路）

- **操作**: 爬取 `https://creepypasta.fandom.com/wiki/Category:Monsters`，max_pages=3
- **前置條件**: 網路可用
- **預期結果**:
  - 回傳多篇文章
  - 支援新版（.category-page__member-link）和舊版（.mw-category）Fandom 佈局
  - 分頁正確處理
  - 每篇之間有 polite delay
- **評分標準**:
  - 3: 批次成功 + 分頁 + polite delay
  - 2: 批次成功但不確定 delay 是否生效
  - 1: 只爬到第一頁
  - 0: Category 解析失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-B04：Reddit .json API 爬取（需網路）

- **操作**: 爬取 `https://www.reddit.com/r/nosleep/top/?t=all`，max_pages=3
- **前置條件**: 網路可用
- **預期結果**:
  - 使用 .json API 而非 HTML 解析
  - 結果包含 score 欄位
  - 過濾 selftext < 200 字元的短帖
  - 過濾 [removed] 和 [deleted]
  - 有 after cursor 分頁
- **評分標準**:
  - 3: .json API + 過濾 + 分頁 + score 都正確
  - 2: 爬取成功但某個過濾條件未驗證
  - 1: 爬取成功但未使用 .json API
  - 0: 爬取失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-B05：通用 Scraper fallback

- **操作**: 用一個不在註冊表中的 URL 觸發通用 scraper
- **前置條件**: 網路可用
- **預期結果**:
  - 未匹配到專用 adapter → 使用通用 article/main 提取
  - 回傳結果或空列表（不崩潰）
  - 通用 scraper 至少嘗試 `<article>` 和 `<main>` 標籤
- **評分標準**:
  - 3: Fallback 正確觸發 + 合理結果
  - 2: Fallback 觸發但結果品質差
  - 1: Fallback 存在但有異常
  - 0: 未匹配 adapter 時崩潰
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## C 類：萃取與分類（5 題）

### MC-C01：Ollama 萃取完整結構（需 Ollama）

- **操作**: 用測試文章呼叫 `extract()`
- **前置條件**: Ollama qwen3:8b 運行中
- **預期結果**:
  - 回傳包含 core_concept, visual_elements, mood_keywords, color_palette_hint, composition_hint, potential_subjects
  - visual_elements 和 mood_keywords 為非空列表
  - core_concept 為中文或英文描述
- **評分標準**:
  - 3: 所有欄位完整且品質好
  - 2: 欄位完整但品質一般
  - 1: 缺少部分欄位
  - 0: 萃取失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-C02：Ollama 不可用時 fallback

- **操作**: 停止 Ollama 後呼叫 extract()
- **前置條件**: Ollama 未運行
- **預期結果**:
  - 不崩潰
  - 退化為 `_rule_based_extraction()`
  - 回傳結構至少包含 source_url, source_title, theme, original_excerpt
  - 日誌記錄 Ollama 不可用
- **評分標準**:
  - 3: 優雅 fallback + 日誌記錄
  - 2: Fallback 正確但無日誌
  - 1: Fallback 結果不完整
  - 0: 崩潰
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-C03：關鍵字分類正確性

- **操作**: 用 4 種不同主題的文本測試分類
- **前置條件**: THEME_KEYWORDS 定義存在
- **預期結果**:
  - "abandoned hospital haunted" → eerie-scene
  - "quantum AI digital circuit" → tech-abstract
  - "tentacle monster alien" → creature-design
  - "portrait cinematic lighting" → clawclaw-portrait
  - 無明確關鍵字 → 預設 tech-abstract
- **評分標準**:
  - 3: 所有分類正確 + 預設正確
  - 2: 4/5 正確
  - 1: 3/5 或更少正確
  - 0: 分類邏輯完全錯誤
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-C04：既有 theme 保留

- **操作**: 傳入已有 theme 的素材呼叫 classify()
- **前置條件**: 無
- **預期結果**: 不覆蓋使用者手動指定的 theme
- **評分標準**:
  - 3: 完全保留既有 theme
  - 2: 保留但有警告或多餘計算
  - 1: 有時覆蓋
  - 0: 總是覆蓋
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-C05：萃取 Prompt 品質

- **操作**: 檢查 `_build_extraction_prompt()` 的指示品質
- **前置條件**: 方法可呼叫
- **預期結果**:
  - Prompt 明確要求 JSON 格式輸出
  - 包含所有期望欄位的說明
  - 有中文/英文的語言指示
  - Prompt 長度合理（不過長影響 token 使用）
- **評分標準**:
  - 3: Prompt 清晰完整且效率高
  - 2: 功能正確但冗餘
  - 1: 缺少關鍵欄位指示
  - 0: Prompt 品質差
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## D 類：去重與存檔（5 題）

### MC-D01：空目錄去重

- **操作**: 在空的 source-library 目錄中呼叫 dedup()
- **前置條件**: 臨時空目錄
- **預期結果**:
  - is_duplicate = False
  - similarity = 0.0
  - 不崩潰
- **評分標準**:
  - 3: 正確處理空目錄
  - 2: 正確但有多餘警告
  - 1: 有邊界錯誤但不影響結果
  - 0: 空目錄導致崩潰
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-D02：重複偵測

- **操作**: 先存一筆，再用相同 core_concept 去重
- **前置條件**: 臨時目錄有一筆素材
- **預期結果**:
  - is_duplicate = True
  - similarity ≥ 0.70
  - similar_to 指向已存在的 ID
- **評分標準**:
  - 3: 偵測正確 + 回傳完整資訊
  - 2: 偵測正確但缺少 similar_to
  - 1: 閾值錯誤（該重複但沒偵測到）
  - 0: 去重邏輯不存在
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-D03：不同概念不誤判

- **操作**: 存一筆素材，再用完全不同的 core_concept 去重
- **前置條件**: 臨時目錄有一筆素材
- **預期結果**:
  - is_duplicate = False
  - similarity < 0.70
- **評分標準**:
  - 3: 正確判定為不重複
  - 2: 正確但 similarity 分數不合理
  - 1: 誤判為重複
  - 0: 邏輯錯誤
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-D04：存檔 + 索引更新

- **操作**: 呼叫 save()，檢查 JSON 檔和 _index.json
- **前置條件**: 臨時 source-library 目錄
- **預期結果**:
  - JSON 檔建立在正確的 theme 子目錄
  - ID 格式為 `{theme}-{seq:03d}`
  - _index.json 更新 materials 列表和 total_count
  - 連續存入多筆時 ID 遞增
- **評分標準**:
  - 3: 檔案 + 索引 + ID 遞增都正確
  - 2: 檔案正確但索引有小問題
  - 1: 檔案存入但索引未更新
  - 0: 存檔失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-D05：stats() 統計正確性

- **操作**: 在有素材的目錄上呼叫 stats()
- **前置條件**: 至少一個主題有素材
- **預期結果**:
  - 4 個主題各有 count 和 unused
  - total 和 total_unused 為正確加總
  - 空主題 count=0, unused=0
  - 不因空目錄或 int/dict 混合迭代而報錯
- **評分標準**:
  - 3: 統計完全正確
  - 2: 正確但有多餘欄位
  - 1: 基本統計正確但加總有誤
  - 0: stats() 報錯
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## E 類：端到端與邊界條件（5 題）

### MC-E01：process_url 完整流程（需 Ollama + 網路）

- **操作**: `curator.process_url("https://creepypasta.fandom.com/wiki/The_Rake")`
- **前置條件**: Ollama + 網路都可用
- **預期結果**:
  - scrape → extract → classify → dedup → save 全流程執行
  - 最終產出 JSON 檔在 source-library 對應主題目錄
  - _index.json 更新
- **評分標準**:
  - 3: 全流程成功 + 結果品質好
  - 2: 流程成功但品質一般
  - 1: 流程中斷在某個步驟
  - 0: 完全失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-E02：add-text 手動新增

- **操作**: `curator.add_text("一段測試文字...", theme="eerie-scene", title="手動測試")`
- **前置條件**: 無
- **預期結果**:
  - 不需要爬取，直接萃取文字
  - 產出結構化素材 JSON
  - theme 使用指定值
  - source_url 為空或標記為 "manual"
- **評分標準**:
  - 3: 手動新增完全正確
  - 2: 新增成功但某些欄位缺失
  - 1: 新增成功但 theme 被覆蓋
  - 0: 新增失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-E03：export-report 中文報告

- **操作**: `curator.export_report()`
- **前置條件**: 有至少一些素材
- **預期結果**:
  - 回傳中文可讀的統計報告文字
  - 包含各主題素材數量
  - 包含未使用素材數量
  - 包含生成時間
- **評分標準**:
  - 3: 報告完整可讀
  - 2: 報告產出但格式粗糙
  - 1: 報告不完整
  - 0: 報告生成失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-E04：CLI 所有子命令

- **操作**: 測試 CLI 的 scrape, batch, add-text, list, stats, export-report 子命令
- **前置條件**: material_curator.py 可執行
- **預期結果**:
  - 每個子命令能正確解析參數
  - --help 顯示用法
  - 未知子命令 → 明確錯誤
- **評分標準**:
  - 3: 所有子命令正確
  - 2: 核心子命令正確但某些未測
  - 1: 只有部分可用
  - 0: CLI 解析失敗
- **實際結果**: _（待填）_
- **得分**: _（待填）_

### MC-E05：Rate Limit 429 處理（需網路）

- **操作**: 快速連續爬取 Reddit，觀察 429 處理
- **前置條件**: 網路可用
- **預期結果**:
  - 收到 429 時自動等待後重試
  - 不崩潰
  - 有日誌記錄 rate limit
  - 重試後繼續正常爬取
- **評分標準**:
  - 3: 自動等待 + 重試 + 日誌完整
  - 2: 處理正確但無日誌
  - 1: 偵測到 429 但處理不當
  - 0: 429 導致崩潰
- **實際結果**: _（待填）_
- **得分**: _（待填）_

---

## 附錄：測試涵蓋對照表

| 功能模組 | 對應類別 | 題數 |
|---|---|---|
| 配置 / 初始化 / 獨立性 | A | 5 |
| 爬取適配器 | B | 5 |
| 萃取 / 分類 | C | 5 |
| 去重 / 存檔 / 統計 | D | 5 |
| 端到端 / CLI / 邊界 | E | 5 |
| **合計** | | **25** |

---

_每一筆素材都是 Stage 0 靈感的種子_ 🐾

