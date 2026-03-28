# 🔧 自製技能管理指南

## 概述
這份指南管理 ClawClaw 獨有的自製技能。這些技能無法從網路下載，必須完整備份到記憶系統中。

## 🔧 自製技能清單

### 上學學習系統 (school-learning) ⭐⭐⭐⭐⭐
- **功能**: 外部學習成果自動同步到記憶系統
- **路徑**: `skills/school-learning/`
- **依賴**: Git, Python
- **重要檔案**: 
  - `SKILL.md` - 技能說明文檔
  - `scripts/sync_learning.py` - 學習同步腳本
- **特色**: 支援技能/腳本/文檔分類同步，自動 Git 提交

### 回家複習系統 (home-review) ⭐⭐⭐⭐⭐  
- **功能**: 從記憶系統完整還原工作環境
- **路徑**: `skills/home-review/`
- **依賴**: Git, Python
- **重要檔案**:
  - `SKILL.md` - 技能說明文檔
  - `scripts/full_review.py` - 完整複習腳本
- **特色**: 環境備份、記憶同步、學習報告生成

### 記憶備份系統 (memory-backup) ⭐⭐⭐⭐⭐
- **功能**: 自動備份記憶和重要檔案到 GitHub
- **路徑**: `skills/memory-backup/`
- **依賴**: Git, Python
- **重要檔案**:
  - `SKILL.md` - 技能說明文檔
  - `scripts/backup_manager.py` - 備份管理腳本
- **特色**: 階層化記憶備份、Git 自動化、衝突解決

### 電源管理系統 (power-management) ⭐⭐⭐⭐
- **功能**: 智能電源管理和關機決策
- **路徑**: `skills/power-management/`
- **依賴**: Python, PowerShell
- **重要檔案**:
  - `SKILL.md` - 技能說明文檔
  - `scripts/daily-power-decision.py` - 電源決策腳本
- **特色**: 智能關機分析、30秒確認機制

### 增強瀏覽器控制 (enhanced-browser) ⭐⭐⭐⭐
- **功能**: 反機器人檢測的網頁自動化
- **路徑**: `skills/enhanced-browser/`
- **依賴**: Python, Playwright
- **重要檔案**:
  - `SKILL.md` - 技能說明文檔
  - 相關腳本檔案
- **特色**: 突破機器人檢測、智能網頁操作

### 桌面視覺控制 (desktop-vision) ⭐⭐⭐⭐
- **功能**: 螢幕截圖、OCR、應用程式監控
- **路徑**: `skills/desktop-vision/`
- **依賴**: Python, Tesseract
- **重要檔案**:
  - `SKILL.md` - 技能說明文檔
  - 相關腳本檔案
- **特色**: 1920x1080 支援、OCR 文字識別

### 桌面輸入控制 (desktop-input) ⭐⭐⭐
- **功能**: 安全的滑鼠鍵盤控制
- **路徑**: `skills/desktop-input/`
- **依賴**: Python
- **重要檔案**:
  - `SKILL.md` - 技能說明文檔
  - 相關腳本檔案
- **特色**: 多層安全檢查、敏感內容過濾

## 🔍 自製技能識別標準

### ✅ 自製技能特徵
- 由 ClawClaw/LXYA 開發
- 包含獨特業務邏輯
- 無 .git 目錄（非從網路 clone）
- 無法從公開渠道獲取
- 需要完整備份還原

### 🚫 排除標準 
- 包含 .git 目錄 → 視為網路技能
- 可從 clawhub 安裝 → 視為網路技能
- 標準化安裝流程 → 視為網路技能

## 📦 備份策略

### 完整備份內容
```
ClawMemory/skills-custom/
├── school-learning/          # 完整技能目錄
├── home-review/
├── memory-backup/
├── power-management/
├── enhanced-browser/
├── desktop-vision/
└── desktop-input/
```

### 備份範圍
- ✅ 所有檔案和子目錄
- ✅ SKILL.md 說明文檔
- ✅ scripts/ 腳本目錄
- ✅ 配置檔案和依賴說明
- ❌ 不備份：快取檔案、臨時檔案

## 🔄 同步機制

### 上學同步 (學習 → 記憶)
1. 檢測新增或修改的自製技能
2. 完整複製到 ClawMemory/skills-custom/
3. 更新本指南檔案
4. Git 提交並推送

### 回家複習 (記憶 → 工作空間)  
1. 從 ClawMemory/skills-custom/ 還原
2. 完整複製到 workspace/skills/
3. 驗證技能完整性
4. 生成復習報告

## 💡 管理原則

### 新技能添加
1. 確認是自製技能（無 .git 目錄）
2. 添加到此指南清單
3. 執行完整備份
4. 測試還原流程

### 技能更新
1. 修改工作空間中的技能
2. 執行上學同步
3. 自動更新記憶備份
4. 驗證同步完整性

### 技能移除
1. 從工作空間刪除
2. 從記憶備份移除
3. 更新指南清單
4. Git 記錄變更

---

**這些自製技能是 ClawClaw 獨有的核心能力，必須妥善保護和管理！** 🔧⚡✨