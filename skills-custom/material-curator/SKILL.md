# Material Curator — 創意素材搜集整理工具

> 版本: v1.0
> 建立日期: 2026-03-27
> 用途: 從網路爬取創意文本，萃取視覺意象，分類整理為結構化素材庫
> 頻率: 🆕 **每週一 13:00 自動爬取** + 手動執行
> 與 stock-image-pipeline 的關係: **獨立 Skill**，產出寫入 stock-image-pipeline 的 source-library 供 Stage 0 Creative Brief 使用

---

## 概述

Material Curator 是一個獨立於圖片生產流水線之外的素材搜集工具。它從指定網站爬取恐怖/奇幻文本，利用 Ollama qwen3:8b 本地 LLM 萃取視覺意象，自動分類至 4 大主題，並結構化為 JSON 素材檔供 stock-image-pipeline 的 Stage 0 Creative Brief Session 使用。

**設計原則：**
- 完全不依賴 stock-image-pipeline 的任何模組
- 只使用 Ollama（本地 LLM），不消耗 OpenRouter API 額度
- 禮貌爬取（polite delay），尊重網站 rate limit
- 所有配置集中在 `config/curator_config.json`

---

## 安裝

```bash
pip install requests beautifulsoup4 curl_cffi --break-system-packages
```

Ollama 需另外安裝並拉取模型：
```bash
ollama pull qwen3:8b
```

---

## 配置

### config/curator_config.json

```json
{
  "output_dir": "../../skills-custom/stock-image-pipeline/config/source-library",
  "ollama": {
    "model": "qwen3:8b",
    "host": "http://localhost:11434"
  },
  "scraping": {
    "polite_delay_seconds": 2,
    "max_articles_per_run": 20,
    "user_agent": "MaterialCurator/1.0 (research-bot)"
  },
  "dedup": {
    "similarity_threshold": 0.70
  }
}
```

- `output_dir`: 素材輸出路徑，指向 stock-image-pipeline 的 source-library（相對於 config/ 目錄解析）
- `ollama`: 本地 LLM 設定
- `scraping`: 爬取禮貌參數
- `dedup`: 去重閾值

---

## 檔案結構

```
material-curator/
├── SKILL.md                          ← 本文件
├── config/
│   └── curator_config.json           ← 集中配置（輸出路徑、Ollama、爬取參數）
├── scripts/
│   └── material_curator.py           ← 主程式（爬取→萃取→分類→存檔）
├── tests/
│   ├── test_material_curator.py      ← pytest 自動化測試
│   ├── conftest.py                   ← 測試 fixtures
│   ├── material-curator-test-cases.md← Agent 自測案例
│   ├── material-curator-test-guide.md← Agent 自測指導
│   └── reports/                      ← 測試報告輸出
├── requirements.txt
└── pytest.ini
```

---

## 使用方式

### CLI 指令

```bash
cd skills-custom/material-curator/scripts

# 爬取單一 URL
python material_curator.py scrape <url> [--theme <theme>] [--max <n>]

# 批次爬取（從檔案讀取 URL 列表）
python material_curator.py batch <file_with_urls> [--theme <theme>]

# 手動新增文字素材
python material_curator.py add-text <text_or_file> --theme <theme> [--title <title>]

# 列出素材
python material_curator.py list [--theme <theme>]

# 統計
python material_curator.py stats

# 匯出報告
python material_curator.py export-report

# 🆕 週一自動爬取（每週一 13:00 由 Heartbeat 觸發）
python material_curator.py auto-crawl-weekly
```

### 支援的網站

| 網站 | Adapter | 爬取方式 | 🆕 自動爬取 | 主題貢獻 |
|---|---|---|---|---|
| **hackernoon.com** | 專用 | HTML 解析（SSR） | ✅ 週一 13:00 | tech-abstract，每次 15 篇 |
| **creepypasta.fandom.com** | 專用 | HTML 解析 `.mw-parser-output` + curl_cffi | ✅ 週一 13:00 | eerie-scene，每次 10 篇 |
| **🆕 scp-wiki.wikidot.com** | 專用 | HTML 解析 `#page-content` | ✅ 週一 13:00 | creature-design，每次 15 篇 |
| 其他網站 | 通用 | `<article>` / `<main>` 提取 | ❌ 手動模式 | 品質可能較低 |

**已移除網站**（因反爬限制）：
- ~~medium.com~~ (403 禁止)
- ~~reddit.com~~ (API 變更)

### 自訂 Scraper 擴展

```python
from material_curator import MaterialCurator

curator = MaterialCurator()
curator.register_scraper("example.com", my_custom_scraper_fn)
```

---

## 素材 JSON 結構

每筆素材保存為一個 JSON 檔案：

```json
{
  "id": "eerie-scene-012",
  "source_url": "https://creepypasta.fandom.com/wiki/The_Backrooms",
  "source_title": "The Backrooms",
  "captured_date": "2026-03-27",
  "theme": "eerie-scene",
  "core_concept": "無盡的辦公空間迷宮，發霉的地毯和嗡嗡作響的日光燈",
  "visual_elements": ["fluorescent lights", "yellow wallpaper", "wet carpet", "endless hallways"],
  "mood_keywords": ["liminal", "unsettling", "isolation", "monotony"],
  "color_palette_hint": ["sickly yellow", "beige", "fluorescent white"],
  "composition_hint": "one-point perspective down a corridor",
  "potential_subjects": ["empty hallway", "flickering light", "stained ceiling"],
  "original_excerpt": "（原文摘錄前 500 字）",
  "quality_score": null,
  "used_count": 0,
  "last_used": null
}
```

---

## 4 大主題分類

| 主題 key | 中文 | 關鍵字範例 |
|---|---|---|
| tech-abstract | 科技抽象 | technology, AI, digital, circuit, quantum, neon |
| eerie-scene | 詭異場景 | abandoned, haunted, fog, ghost, SCP, asylum |
| creature-design | 生物設計 | creature, monster, alien, tentacle, biomechanical |
| clawclaw-portrait | 爪爪肖像 | portrait, expression, cinematic, dramatic, painterly |

---

## 工作流程

```
1. scrape()     — 爬取指定 URL 文章原文
2. extract()    — Ollama qwen3:8b 萃取視覺意象 → JSON
3. classify()   — 規則 + 關鍵字自動分類至 4 主題
4. dedup()      — SequenceMatcher 比對 core_concept 去重
5. save()       — 寫入 source-library/{theme}/ + 更新 _index.json
```

---

## Agent 自主執行指引

當 Agent（ClawClaw）被指示執行此 Skill 時，請遵循以下決策流程：

### 1. 前置檢查

```bash
# 確認 Ollama 正在運行（萃取品質的關鍵）
curl -s http://localhost:11434/api/tags | head -1
# 若無回應 → 警告使用者 Ollama 未啟動，素材將缺少視覺意象分析
```

### 2. 主題 → 來源對應表

| 主題 | 預設來源 URL | 備註 |
|---|---|---|
| tech-abstract | `https://hackernoon.com/c` | 科技文章，SSR 可直接爬 |
| eerie-scene | `https://creepypasta.fandom.com/wiki/Category:Suggested_Reading` | 需 curl_cffi |
| eerie-scene | `https://www.reddit.com/r/nosleep/top/?t=week` | .json API |
| creature-design | `https://creepypasta.fandom.com/wiki/Category:Monsters` | 需 curl_cffi |
| creature-design | `https://www.reddit.com/r/SCP/top/?t=week` | .json API |
| clawclaw-portrait | **不使用** — 此主題素材由其他方式產生 | 不要爬取 |

### 3. 標準執行流程

```bash
cd skills-custom/material-curator/scripts

# Step 1: 先看庫存
python material_curator.py stats

# Step 2: 對庫存不足的主題補貨（每主題 5-10 篇）
python material_curator.py scrape "https://hackernoon.com/c" --theme tech-abstract --max 5
python material_curator.py scrape "https://creepypasta.fandom.com/wiki/Category:Suggested_Reading" --theme eerie-scene --max 5
python material_curator.py scrape "https://www.reddit.com/r/nosleep/top/?t=week" --theme eerie-scene --max 5

# Step 3: 確認結果
python material_curator.py stats
```

### 4. 判斷是否需要補貨

- 執行 `stats` 後，如果某主題的 `unused` 數量 < 5，優先補該主題
- 如果所有主題 `unused` >= 10，本週可以跳過
- **不要爬取 clawclaw-portrait 主題**

### 5. Ollama 離線時的處理

如果 Ollama 未啟動，腳本會靜默降級（visual_elements 等欄位為空）。Agent 應：
- 在爬取前檢查 Ollama 狀態
- 若離線，告知使用者「Ollama 未啟動，素材將只有原文摘錄，缺少視覺意象分析」
- 讓使用者決定是否繼續

---

## 建議更新頻率

- **每週一次**：週末或週一使用 `batch` 模式批次更新
- **每次約 10-20 篇**新文章
- **手動審核**：爬取後可用 `list` + `stats` 檢視品質，低質素材手動刪除

---

## 與 stock-image-pipeline 的接口

Material Curator 的唯一輸出接口是 `output_dir` 指向的 source-library 目錄。stock-image-pipeline 的 Stage 0 Creative Brief Generator 從該目錄讀取素材作為靈感來源。

兩者之間**沒有程式碼依賴**，僅透過檔案系統共享資料。


