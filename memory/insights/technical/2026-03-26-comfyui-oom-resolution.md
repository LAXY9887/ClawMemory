---
topic: "ComfyUI CUDA OOM 解決策略"
category: insight
insight_type: how-to
status: confirmed
trigger: "ComfyUI CUDA OUT_OF_MEMORY"
pattern: "高解析度、大批量、複雜 LoRA 都可能觸發顯存不足"
action: "根據具體場景選擇：高解析度→降解析度，大批量→分批處理，複雜模型→開啟 Tiled VAE"
source_episodes:
  - "memory/daily/test-ed-2026-03-15.md"
  - "memory/daily/test-ed-2026-03-20.md"
  - "memory/daily/test-ed-2026-03-22.md"
confirmed_at: 2026-03-26
challenge_count: 3
importance: high
importance_score: 7
confidence: high
tags: [comfyui, cuda, 顯存優化, 經驗提煉]
summary: "ComfyUI CUDA OOM 三種場景的對應解決策略"
created: 2026-03-26
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---

# ComfyUI CUDA OOM 解決策略

## 觸發模式識別
ComfyUI 在以下情況容易出現 CUDA OOM：
1. **高解析度渲染** (2048x2048+)
2. **大批量生成** (20+張)
3. **複雜 LoRA 模型**

## 解決策略矩陣

| 觸發場景 | 優先解法 | 效果 |
|---|---|---|
| 高解析度 | 降低解析度 | 直接減少顯存需求 |
| 大批量 | 分批處理 | 控制同時載入量 |
| 複雜模型 | Tiled VAE | 分塊處理不降品質 |

## 實戰經驗
- 解析度調整最直接但犧牲品質
- 分批處理適合批量生產  
- Tiled VAE 是品質和效能的最佳平衡

*此經驗來自 3 次實際 OOM 事件的模式提煉*