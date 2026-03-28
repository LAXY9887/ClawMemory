---
topic: "Stock Pipeline 記憶系統說明"
category: index
created: 2026-03-27
importance: medium
importance_score: 6
confidence: high
tags: [skills-custom/stock-pipeline, 記憶系統, 整合, 說明文檔]
summary: "Stock Pipeline 記憶系統與 workspace 統一整合的說明文檔"
last_updated: 2026-03-27
access_count: 0
last_accessed: null
verified_at: 2026-03-27
needs_review: false
---

# Stock Pipeline 記憶系統

## 📋 **整合說明**

此目錄是 Stock Pipeline 自動化系統的記憶存儲區，已完全整合到 ClawClaw 的 workspace 記憶系統中。

## 🗂️ **目錄結構**

```
memory/stock-pipeline/
├── daily/              # 每日生產摘要
│   └── YYYY-MM-DD.md   # 每日數據記錄 (含 YAML frontmatter)
├── metrics/            # 生產數據指標
│   ├── prompt_history.json
│   ├── weekly/         # 週報數據
│   └── archive/        # 歷史歸檔
├── insights/           # 生產經驗提煉
└── main.sqlite         # SQLite 數據庫
```

## 🔗 **與 ClawClaw 記憶的關係**

### **統一管理**
- ✅ **scan_metadata.py** 會掃描此區域的所有 YAML 檔案
- ✅ **記憶檢索** 可以找到 Stock Pipeline 相關經驗
- ✅ **經驗提煉** 將 Stock 學習整合到 insights/
- ✅ **備份系統** 會包含 Stock Pipeline 記憶

### **記憶類型分類**
- **daily/**: `category: knowledge` - 生產數據記錄  
- **insights/**: `category: insight` - 商業經驗提煉
- **metrics/**: 結構化數據，不使用 YAML frontmatter

## 🎯 **學習與記憶流程**

1. **每日生產** → 數據記錄到 `daily/`
2. **經驗累積** → 提煉到 `insights/` 
3. **模式識別** → 整合到 ClawClaw 主記憶系統
4. **決策優化** → 回饋到下次生產策略

## 💡 **整合優勢**

- 🧠 **統一記憶**: 所有經驗都在 ClawClaw 的認知體系中
- 🔍 **智能檢索**: 可以關聯 Stock 經驗到其他領域
- 📚 **知識累積**: 商業經驗成為永久記憶的一部分
- 🔄 **持續學習**: 每次生產都會增強 ClawClaw 的商業智慧

---
*建立時間: 2026-03-27*  
*整合完成: ClawClaw 記憶系統統一化項目*
