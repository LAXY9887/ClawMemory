---
topic: "Material Curator 測試指導手冊"
category: knowledge
created: 2026-03-27
importance: high
importance_score: 8
tags: [測試, 自測, material-curator, eval, 指導]
summary: "Agent 自行執行 Material Curator 測試的完整操作手冊"
last_updated: 2026-03-27
access_count: 0
last_accessed: null
---

# Material Curator 測試指導手冊 — Agent 自測版

> 版本: v1.0
> 建立日期: 2026-03-27
> 搭配文件: `tests/material-curator-test-cases.md`

---

## 你是誰、你在做什麼

你是 ClawClaw，正在執行一次 **Material Curator 自我測試**。這是一個獨立於 stock-pipeline 的 Skill，負責從網路爬取創意文本並整理為結構化素材庫。測試目的是驗證爬取、萃取、分類、去重、存檔各環節是否正確運作。

---

## 外部服務依賴

| 服務 | 確認指令 | 不可用時的影響 |
|---|---|---|
| Ollama qwen3:8b | `curl -s http://localhost:11434/api/tags` | 萃取退化為規則基礎 |
| 網路連線 | `curl -s https://httpbin.org/ip` | 無法爬取 |

---

## 測試執行流程

### 階段 0: 環境準備

```
1. 讀取 material-curator/SKILL.md
2. 讀取 config/curator_config.json（確認 output_dir 指向正確路徑）
3. 確認 output_dir 目標目錄存在且可寫入
4. 執行 pytest tests/ -v -m "not network and not ollama" 確認基礎測試通過
5. 檢測 Ollama 和網路可用性
```

### 階段 1: 依序執行測試案例 A → B → C → D → E

### 階段 2: 產出報告

**報告路徑**: `tests/reports/YYYY-MM-DD-curator-test-report.md`

格式同 stock-pipeline 測試報告模板，包含：評分匯總表、各案例詳細結果、失敗分析、改善建議。

---

## 觸發指令

當 LXYA 說「測試素材搜集工具」或「跑一次 Curator 測試」時，讀取本文件並開始執行。

---

_讓每一次素材搜集都更加精準_ 🐾

