---
topic: "LoRA 模型配置技術指南"
category: knowledge
created: 2026-03-26
importance: high
importance_score: 8
tags: [lora, 配置, 技術指南, comfyui]
summary: "5個LoRA模型的詳細技術配置，包含適用Base Model、CLIP Skip、權重設定和觸發關鍵字"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---

# LoRA 模型配置技術指南

## 🎯 **配置對照表**

| LoRA 名稱 | 檔案名 | 適用 Base Model | CLIP Skip | 權重範圍 | 主要觸發詞 |
|---|---|---|---|---|---|
| Horror & Creepy | Horror.safetensors | SD1.5 | 1-2 | 0.6-0.8 | horror, creepy, dark atmosphere |
| Creatures Design V1 | CreaturesDesignV1.safetensors | SD1.5 | 2-3 | 0.8-0.9 | A fantz creature |
| Cyberpunk Style | C7b3rp0nkStyle.safetensors | 通用 | 1-2 | 0.7-1.0 | C7b3rp0nk style |
| Abandoned Office DX | Abandoned_Office_DX_-_CyberRealistic_PONY.safetensors | Pony V6 XL | 2 | 0.7-0.9 | abandoned office building |
| Eldritch Creatures | eldritch_abomination.safetensors | Illustrious | 1 | 0.4-0.6 | monster, eldritch abomination |

## 🔧 **Base Model 匹配策略**

### Illustrious-XL v2.0 組合
```yaml
最佳 LoRA:
  - Eldritch Creatures (0.4-0.6) ⭐⭐⭐⭐⭐
  - Horror & Creepy (0.6-0.8) ⭐⭐⭐⭐ 
  - Cyberpunk Style (0.7-0.9) ⭐⭐⭐⭐

CLIP Skip: 1 (Illustrious 標準)
解析度: 1024x1024, 832x1216
```

### SD1.5 組合  
```yaml
最佳 LoRA:
  - Creatures Design V1 (0.8-0.9) ⭐⭐⭐⭐⭐
  - Horror & Creepy (0.6-0.8) ⭐⭐⭐⭐⭐
  - Cyberpunk Style (0.7-1.0) ⭐⭐⭐⭐

CLIP Skip: 2-3 (Creatures 需要 3)
解析度: 512x512 → 升頻
```

### Pony V6 XL 組合
```yaml
專用 LoRA:
  - Abandoned Office DX (0.7-0.9) ⭐⭐⭐⭐⭐

CLIP Skip: 2 (Pony 必須)
前置提示: score_9, score_8_up...
解析度: 1024x1024+
```

## 💡 **關鍵技術發現**

### CLIP Skip 重要性
- **Illustrious 系列**: CLIP Skip 1 (標準)
- **SD1.5 + Creatures**: CLIP Skip 2-3 (性能關鍵)  
- **Pony 系列**: CLIP Skip 2 (必須設定)

### LoRA 權重平衡
- **強效 LoRA**: Eldritch (0.4-0.6)，避免過度影響
- **標準 LoRA**: Horror、Cyberpunk (0.6-0.8)
- **需要強化**: Creatures Design (0.8-0.9)，效果需要足夠

### 觸發詞策略
- **必要前綴**: "A fantz creature" (Creatures Design)
- **虛構觸發**: "C7b3rp0nk style" (純粹訓練效果)
- **可選觸發**: "eldritch abomination" (增強但非必須)

---

**技術狀態**: LoRA 配置研究 100% 完成，準備整合到 ComfyUI 工作流！