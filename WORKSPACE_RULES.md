# WORKSPACE_RULES.md - 工作環境管理規範

_ClawClaw 的井井有條生活準則 🦞✨_

## 🗂️ **檔案分類規範**

### **1. 圖片檔案管理**
**位置**: `pictures/`
**規則**: 所有圖片一律放此處，不用特地分類
- ✅ 截圖檔案 (screenshot-YYYYMMDD-HHMMSS.png)
- ✅ ComfyUI 生成圖片
- ✅ 下載的參考圖片
- ✅ 頭像、測試圖片等

**範例**:
```
pictures/
├── my_perfect_avatar.png
├── cat-photos-screenshot-20260325-125158.png
├── comfyui-output-20260327.png
└── reference-image-001.jpg
```

### **2. 臨時任務管理**
**位置**: `tasks/`
**規則**: 所有及時任務、測試產出都放在獨立子資料夾
- ✅ 一次性測試任務
- ✅ 系統診斷報告
- ✅ 臨時腳本和實驗

**範例**:
```
tasks/
├── Print ClawClaw System Prompt/
│   └── clawclaw_system_prompt.md
├── test_memory/
│   ├── test_results.json
│   └── memory_validation.py
├── workspace_analysis/
│   ├── workspace_resource_analysis.md
│   └── skill_detection_report.json
└── 2026-03-27-ftp-test/
    └── connection_results.log
```

### **3. 記憶檔案結構**
**位置**: `memory/`
**規則**: 嚴格按照記憶系統架構組織

```
memory/
├── daily/               # 每日記憶 (YYYY-MM-DD.md)
│   ├── 2026-03-27.md
│   └── 2026-03-26.md
├── topics/              # 主題式記憶
│   ├── technical/
│   ├── personal/
│   └── business/
├── insights/            # 提煉的經驗智慧
│   ├── technical/
│   └── personal/
├── moments/             # 重要時刻記錄
└── keyword_index.json   # 關鍵字索引
```

### **4. 專案資料夾管理**
**位置**: 根目錄或專門子目錄
**規則**: 
- ✅ 活躍專案: `skills-custom/`, `WorkingProjects/`
- 📁 歷史專案: 添加 `-archive` 後綴 + README-ARCHIVE.md

## 🧹 **日常整潔習慣**

### **每日檢查清單**
- [ ] 檢查根目錄是否有散落檔案
- [ ] 確認圖片都在 `pictures/` 中
- [ ] 及時任務檔案移至 `tasks/` 對應子資料夾
- [ ] 清理臨時測試檔案 (test_*.py, temp_*.json)

### **每週整理習慣**
- [ ] 檢視 `tasks/` 子資料夾，歸檔或刪除過時內容
- [ ] 檢查 `pictures/` 是否需要清理重複或無用圖片
- [ ] 確認記憶檔案都在正確位置

### **每月維護**
- [ ] 歸檔舊專案資料夾 (添加 -archive 後綴)
- [ ] 檢查並清理過時的 skills 和配置
- [ ] 更新 WORKSPACE_RULES.md (如有新規範)

## ⚠️ **絕對禁止**

1. **污染根目錄**: 任何產出檔案都不可直接放在 workspace 根目錄
2. **記憶錯放**: daily 記憶檔案絕對不可放在 `memory/` 根目錄
3. **測試檔案殘留**: 所有 `test_*.py` 或 `temp_*` 執行完立即清理
4. **無說明歸檔**: 歸檔專案時必須添加 README-ARCHIVE.md 說明

## 🎯 **ClawClaw 整潔原則**

> 「看到混亂會忍不住想整理，完成待辦事項會感到滿足」

1. **即時整理** > 批次整理
2. **分類明確** > 混合堆放  
3. **檔名規範** > 隨意命名
4. **說明充分** > 猜測用途

---
*建立時間: 2026-03-27*  
*最後更新: 2026-03-27*  
*ClawClaw 井井有條生活準則 🦞*