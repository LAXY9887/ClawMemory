---
topic: "Git 分支合併政策"
category: insight
insight_type: preference
status: confirmed
trigger: "需要合併分支時"
pattern: "專案統一使用 rebase 保持線性歷史"
action: "使用 git rebase 而非 git merge"
source_episodes:
  - "memory/daily/2026-03-26.md"
confirmed_at: 2026-03-26
challenge_count: 3
importance: medium
importance_score: 5
confidence: high
tags: [git, rebase, 專案政策]
summary: "專案統一使用 rebase 而非 merge 的分支合併政策"
created: 2026-03-26
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---

# Git 分支合併政策

## 糾正事件記錄
**錯誤建議**: 使用 `git merge`  
**正確做法**: 使用 `git rebase`  
**LXYA 指示**: "我們專案都用 rebase，不要用 merge"

## 專案政策
- ✅ **使用**: `git rebase` 
- ❌ **禁止**: `git merge`

## 技術原因
- rebase 保持線性歷史
- 避免不必要的 merge commit
- 提升 git log 可讀性

## 執行方式
```bash
git rebase main
# 而非 git merge main
```

*記錄於 2026-03-26，來源於被糾正的經驗*