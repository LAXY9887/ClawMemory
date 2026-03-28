---
topic: "簡化任務執行原則 - LXYA 最新指示"
category: knowledge
created: 2026-03-25
importance: medium
importance_score: 5
tags: [technical, ollama, memory]
summary: "**重要性**: ⭐⭐⭐⭐⭐ (新的簡化標準)"
last_updated: 2026-03-25
access_count: 0
last_accessed: null
---

# 簡化任務執行原則 - LXYA 最新指示

**時間**: 2026-03-25 22:14  
**重要性**: ⭐⭐⭐⭐⭐ (新的簡化標準)

## LXYA 新指示

> "不建立資料夾，生成後不移動圖片，維持在 output 目錄"

## **新的簡化原則**

### **✅ 保持的功能**
1. **動態檔案命名** - 使用 filename_prefix 區分任務
2. **進度監控** - 基於檔名模式統計圖片
3. **參數動態化** - 解析度、模型等可配置
4. **Ollama 優化** - 保持本地模型優化標準

### **❌ 移除的複雜性**
1. **不建立專屬資料夾** - 簡化資料夾結構
2. **不移動圖片** - 避免檔案操作複雜性
3. **不建立任務配置檔** - 減少檔案管理負擔
4. **不需要後處理** - 直接在 output 目錄統計

## **新的工作流程**

### **步驟 1: 檔案命名策略**
```
格式: Task_{TaskID}_{序號}.png
範例: Task_2026-03-25_cats-test_00001.png
```

### **步驟 2: 進度監控**
```python
# 基於檔名模式統計
task_pattern = f"Task_{task_id}_*.png"
completed = len(list(output_dir.glob(task_pattern)))
```

### **步驟 3: 批次生成**
```python
for i, prompt in enumerate(prompts):
    workflow["7"]["inputs"]["filename_prefix"] = f"Task_{task_id}"
    # 直接提交，不需要後處理
```

## **優點**

### **✅ 簡化優勢**
- **減少複雜性** - 無需資料夾管理
- **避免檔案操作錯誤** - 不移動不複製
- **統一位置** - 所有圖片在同一目錄
- **簡化進度監控** - 直接檔名統計

### **✅ 保持優勢**
- **任務區分** - 檔名包含任務ID
- **動態配置** - 規格可調整
- **品質保證** - Ollama 優化保持
- **進度可視** - 監控功能正常

## **實施標準**

### **檔案命名規範**
```
Task_{YYYY-MM-DD}_{task-name}_{序號}.png
```

### **進度監控方式**
```python
def count_task_images(task_id, output_dir):
    pattern = f"Task_{task_id}_*.png"
    return len(list(output_dir.glob(pattern)))
```

### **簡化監控腳本**
- 無需讀取任務配置檔
- 直接基於檔名模式統計
- 顯示最新圖片資訊
- 計算完成進度

## **記憶要點**

**新原則**: 簡化 > 複雜化
**核心**: 檔案命名區分 > 資料夾區分  
**目標**: 減少錯誤 > 功能完備
**方式**: 統一位置 > 分散管理

---

*這個簡化原則將大幅減少檔案管理的複雜性和錯誤機率*