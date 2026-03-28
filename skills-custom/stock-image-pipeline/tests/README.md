# Stock Pipeline 測試指南

## 環境準備

### 1. 安裝 Python 依賴

```bash
cd skills-custom/wirestock-pipeline
pip install -r requirements.txt
pip install pytest
```

### 2. 依賴清單

| 套件 | 用途 | 必要性 |
|---|---|---|
| `requests` | OpenRouter / ComfyUI / Ollama API 通訊 | **必要** |
| `Pillow` | 圖片處理、EXIF 嵌入、Layer1 品質檢測 | **必要** |
| `piexif` | JPEG EXIF 進階嵌入 | 選用（Pillow 有 fallback） |
| `beautifulsoup4` | material_curator 網頁爬取 | 選用（僅素材搜集需要） |
| `pytest` | 測試框架 | 開發時需要 |

### 3. 外部服務

| 服務 | 用途 | 測試是否需要 |
|---|---|---|
| ComfyUI Desktop | 圖片生成 | ❌ 離線測試不需要 |
| OpenRouter API | 多模態評分 | ❌ 離線測試不需要 |
| Ollama qwen3:8b | 本地 LLM | ⚠️ 僅 `@pytest.mark.ollama` 測試需要 |
| 網路連線 | 爬取外部網站 | ⚠️ 僅 `@pytest.mark.network` 測試需要 |

---

## 執行測試

### 全部離線測試（推薦，不需任何外部服務）

```bash
python -m pytest tests/ -v
```

### 排除網路和 Ollama 測試

```bash
python -m pytest tests/ -v -m "not network and not ollama"
```

### 僅跑 config 驗證

```bash
python -m pytest tests/test_config.py -v
```

### 僅跑模組 import 驗證

```bash
python -m pytest tests/test_modules_import.py -v
```

### 僅跑 material_curator 離線測試

```bash
python -m pytest tests/test_material_curator.py -v -m "not network and not ollama"
```

### 跑包含 Ollama 的測試（需先啟動 Ollama）

```bash
ollama serve &
ollama pull qwen3:8b
python -m pytest tests/ -v -m "not network"
```

### 跑包含網路的測試（完整測試）

```bash
python -m pytest tests/ -v
```

---

## 測試檔案說明

| 檔案 | 內容 | 外部依賴 |
|---|---|---|
| `conftest.py` | 共用 fixtures（config 載入、sample data、tmp 目錄） | 無 |
| `test_config.py` | Config 檔案結構驗證（欄位、一致性） | 無 |
| `test_modules_import.py` | 語法驗證 + import 驗證 + 無硬編碼密鑰 | 需 `requests`, `Pillow` |
| `test_material_curator.py` | 素材工具（分類/去重/存檔/爬取） | 離線可跑，爬取需網路 |
| `test_pipeline_integration.py` | 模組間介面一致性、observation 格式 | 無 |

---

## 測試標記 (markers)

```
@pytest.mark.ollama   — 需要本地 Ollama 服務
@pytest.mark.network  — 需要網路連線
```

無標記的測試全部可以在沒有外部服務的情況下執行。

---

## 初次部署驗證 Checklist

```bash
# 1. 安裝依賴
pip install -r requirements.txt
pip install pytest

# 2. 初始化 workspace
python scripts/setup_workspace.py

# 3. 跑離線測試
python -m pytest tests/ -v -m "not network and not ollama"

# 4. 設定環境變數
export OPENROUTER_API_KEY=sk-or-...
export DREAMSTIME_FTP_ID=123456
export DREAMSTIME_FTP_PASS=...

# 5. 啟動 Ollama + 跑 Ollama 測試
ollama serve &
ollama pull qwen3:8b
python -m pytest tests/ -v -m "not network"

# 6. 跑完整測試（含網路爬取）
python -m pytest tests/ -v

# 7. 試跑 material_curator
python scripts/material_curator.py stats

# 8. 試跑 pipeline (dry run)
python scripts/pipeline_main.py stats
```
