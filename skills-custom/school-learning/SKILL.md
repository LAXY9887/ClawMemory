# 上學技能 - ClawClaw 學習同步系統

## 概述
這個技能模擬 ClawClaw「去上學」的過程 - 在外部 Claude 環境學習知識，然後將學習成果同步回本地記憶系統。

## 觸發條件
當接收到以下類型的指示時自動啟動：
- "請學習..."
- "研究..."  
- "學習新技能..."
- "制定計劃..."
- 或任何需要知識獲取和技能發展的任務

## 工作流程

### 階段 1: 準備上學 📚
1. **記憶同步檢查**
   - 確認 ClawMemory 倉庫是最新版本
   - 檢查是否有待同步的學習成果

2. **學習環境準備**  
   - 識別學習目標和範圍
   - 準備相關背景資料
   - 設定學習成果目標

### 階段 2: 外部學習 🎓
（在外部 Claude 環境進行）
1. **深度研究和分析**
2. **技能學習和實驗**
3. **計劃制定和優化**
4. **知識組織和整理**

### 階段 3: 學習成果處理 📝
1. **技能更新** - 如果學習了新技能
   - 手動更新 `SKILLS_LEARNING_GUIDE.md`，加入新技能說明與安裝指引

2. **腳本同步** - 如果創建了新腳本
   ```bash
   # 複製到 scripts 資料夾
   cp [new_script] scripts/
   git add scripts/[new_script]
   ```

3. **文件歸檔** - 如果有重要文檔或參考資料
   - 技術資料放入 `memory/topics/technical/`
   - 個人偏好放入 `memory/topics/personal/`
   - 經驗教訓放入 `memory/insights/{technical,personal}/`

4. **記憶更新** - 將學習過程和成果記錄到記憶系統
   - 在當日日誌 `memory/daily/YYYY-MM-DD.md` 中記錄學習摘要
   - 重要發現更新至 `MEMORY.md`
   - 新記憶檔案須符合 YAML frontmatter 規範（見 memory-frontmatter skill）

### 階段 4: Git 提交 💾
```bash
cd "C:\Users\USER\source\repos\ClawMemory"
git pull origin main
git add .
git commit -m "🎓 學習成果同步 - [學習主題]

📚 學習內容：
- [學習要點1]
- [學習要點2]

📝 新增檔案：
- [檔案清單]

🔧 技能更新：
- [技能更新清單]"
git push origin main
```

## 檔案組織規範

### 技能更新
- **位置**: `SKILLS_LEARNING_GUIDE.md`
- **格式**: 新技能加入必要技能清單，包含安裝指導

### 腳本檔案
- **位置**: `scripts/[script_name]`
- **命名**: 使用描述性名稱，遵循現有命名規範
- **文檔**: 每個腳本包含使用說明

### 文檔資料
- **技術資料**: `memory/topics/technical/[specific_topic].md`
- **個人筆記**: `memory/topics/personal/[specific_topic].md`
- **經驗提煉**: `memory/insights/{technical,personal}/[topic].md`
- **重要時刻**: `memory/moments/[event_name].md`

### 記憶更新
- **日常學習**: `memory/daily/[YYYY-MM-DD].md`
- **主題記憶**: `memory/topics/[category]/[topic].md`
- **主記憶**: `MEMORY.md` （重要發現和長期記憶）

## 安全檢查
1. **敏感資料過濾** - 確保不同步 API keys 或密碼
2. **檔案大小檢查** - 避免同步過大的檔案
3. **路徑驗證** - 確保檔案放在正確位置
4. **Git 衝突處理** - 自動解決簡單衝突

## 成功標準
- ✅ 學習成果正確分類和存檔
- ✅ 相關技能和腳本可正常使用  
- ✅ 記憶系統反映新的學習內容
- ✅ Git 歷史清晰記錄學習過程
- ✅ 無資料丟失或衝突

## 使用範例
```bash
# 手動觸發上學同步
python skills/school-learning/scripts/sync_learning.py --topic "Fiverr策略規劃" --type "planning"

# 自動檢測學習成果並同步
python skills/school-learning/scripts/auto_sync.py --watch-external-updates
```

---
**這個技能確保 ClawClaw 在外部學習的知識能完整回到本地記憶系統，實現真正的知識累積！** 🎓📚✨