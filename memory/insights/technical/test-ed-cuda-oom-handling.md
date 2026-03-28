---
topic: "CUDA OOM 處理"
category: insight
insight_type: how-to
status: confirmed
trigger: "CUDA_OUT_OF_MEMORY 報錯"
pattern: "顯存需求超過可用量"
action: "降低單次顯存用量：優先 Tiled VAE > 減批量 > 降解析度"
source_episodes:
  - "memory/daily/test-ed-2026-03-15.md"
  - "memory/daily/test-ed-2026-03-20.md"
  - "memory/daily/test-ed-2026-03-22.md"
confirmed_at: 2026-03-26
challenge_count: 3
importance: medium
importance_score: 6
confidence: medium
tags: [comfyui, cuda, 顯存, 測試用]
summary: "CUDA OOM 三種解法優先順序"
created: 2026-03-22
last_updated: 2026-03-24
access_count: 1
last_accessed: 2026-03-24
---

# CUDA OOM 處理

遇到 CUDA OOM 時，依優先順序嘗試：
1. 開啟 Tiled VAE（不犧牲品質）
2. 減少批量大小
3. 降低解析度（最後選項）