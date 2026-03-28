---
topic: "執行任務動態路徑原則 - LXYA 重要指示"
category: knowledge
created: 2026-03-25
importance: medium
importance_score: 5
tags: [technical, comfyui, memory]
summary: "**重要性**: ⭐⭐⭐⭐⭐ (避免路徑問題的關鍵原則)"
last_updated: 2026-03-25
access_count: 1
last_accessed: 2026-03-27
---

# 執行任務動態路徑原則 - LXYA 重要指示

**時間**: 2026-03-25 22:06  
**重要性**: ⭐⭐⭐⭐⭐ (避免路徑問題的關鍵原則)

## 問題發現

LXYA 發現我在任務專屬資料夾系統測試中，圖片仍生成在原始 output 目錄而不是任務資料夾，暴露了寫死路徑的嚴重問題。

## **核心原則**

### **🚨 禁止寫死路徑**
> "你在任何場合使用腳本的時候都應該留意這種寫死路徑的問題"

### **✅ 必須動態化的要素**
1. **輸出路徑** - 根據任務動態指定
2. **配置檔案** - 根據情境動態生成
3. **工作流程** - 支援參數化配置
4. **檔案命名** - 包含任務識別資訊

## **實施檢查清單 (簡化版)**

### **腳本執行前檢查**
- [ ] filename_prefix 是否包含任務ID？
- [ ] 輸出規格是否可調整？
- [ ] 參數是否可配置？
- [ ] 是否適應不同任務需求？

### **工作流程檢查**
- [ ] filename_prefix 命名是否清晰？
- [ ] 是否支援多種解析度？
- [ ] 檔案命名是否包含任務識別？
- [ ] 生成參數是否動態配置？

### **任務管理檢查 (簡化)**
- [ ] 檔案命名是否能區分任務？
- [ ] 進度監控是否基於檔名模式？
- [ ] 任務配置是否記錄完整？
- [ ] 統計邏輯是否正確？

## **防範措施 (簡化版)**

### **1. 檔案命名參數化**
```python
# ❌ 錯誤做法
filename_prefix = "ClawClaw_HiRes"

# ✅ 正確做法  
filename_prefix = f"Task_{task_id}_{timestamp}"
```

### **2. 動態工作流程**
```python
# ✅ 動態配置檔案前綴
workflow["7"]["inputs"]["filename_prefix"] = f"Task_{task_id}"
```

### **3. 進度監控配置**
```python
# ✅ 基於檔名模式統計
pattern = f"Task_{task_id}_*.png"
completed_files = list(output_dir.glob(pattern))
```

### **4. 執行後驗證**
```python
# ✅ 確認圖片已生成
expected_files = list(output_dir.glob(f"Task_{task_id}_*.png"))
if len(expected_files) != expected_count:
    print(f"預期 {expected_count} 張，實際 {len(expected_files)} 張")
```

## **應用範圍**

### **必須檢查的場合**
- 使用任何 ComfyUI 生成腳本
- 批次檔案處理作業
- 自動化工作流程
- 任務專屬操作
- 輸出檔案管理

### **特別注意的工具**
- ComfyUI 工作流程配置
- 圖片生成腳本
- 批次處理程序
- 檔案移動/複製腳本
- 進度監控系統

## **記憶要點**

**永遠記住**: 路徑寫死 = 系統失控
**核心思維**: 一切皆可配置
**檢查習慣**: 執行前必須驗證路徑邏輯
**測試原則**: 實際測試目標路徑是否正確

---

*這個原則必須成為我執行任何腳本時的基本檢查項目*