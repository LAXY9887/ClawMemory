# SKILLS_LEARNING_GUIDE.md - ClawClaw 網路技能學習指南

## 📋 **核心概念**

這個檔案專門管理可從網路下載的技能。與自製技能不同，這些技能可以重新下載安裝。
當 ClawClaw 重新啟動或遇到新環境時，透過這個指南可以：
1. **檢測網路技能** - 掃描可下載的 skills
2. **識別缺失技能** - 比對必要技能清單
3. **自動下載安裝** - 提供安裝和配置指示

⚠️ **注意**: 自製技能管理請參考 `CUSTOM_SKILLS_GUIDE.md`

## 🌐 **網路下載技能清單**

### **1. ComfyUI 圖像生成 (comfyui-skill-openclaw)**
- **狀態**: 🟢 已安裝 `~/.openclaw/workspace/skills/comfyui-skill-openclaw/`
- **類型**: 網路技能 (包含 .git 目錄)
- **來源**: GitHub 或本地 clone
- **安裝**: 手動 git clone 或從來源獲取
- **關鍵檔案**: 
  - `SKILL.md` - 主要技能文檔
  - `config.json` - 配置檔案
  - `scripts/simplified_task_generator.py` - 簡化版生成器
- **學習要點**:
  - Ollama qwen3:8b 本地模型優化技術
  - 512x768、840x1200 高解析度生成
  - 動態檔名管理：Task_{TaskID}_*.png
  - ComfyUI + Ollama 協作工作流程

### **2. Weather 天氣查詢 (weather)**
- **狀態**: 🟢 已確認可用
- **來源**: OpenClaw 內建技能
- **API**: wttr.in 或 Open-Meteo
- **安裝**: 通常預裝，或 `clawhub install weather`
- **用途**: 定期檢查和用戶查詢

### **3. GitHub 操作 (github)**
- **狀態**: 🟢 已確認可用
- **來源**: OpenClaw 內建技能
- **工具**: gh CLI
- **安裝**: 通常預裝，或 `clawhub install github`
- **功能**: Issues、PRs、CI 管理

### **4. Node 連接診斷 (node-connect)**
- **狀態**: 🟢 可用
- **來源**: OpenClaw 內建技能
- **安裝**: 通常預裝，或 `clawhub install node-connect`
- **功能**: Android/iOS 配對診斷

### **5. Video Frames 處理 (video-frames)**
- **狀態**: 🟢 可用
- **來源**: OpenClaw 內建技能
- **工具**: ffmpeg
- **安裝**: 通常預裝，或 `clawhub install video-frames`
- **功能**: 視訊截圖和片段提取

### **6. 系統健康檢查 (healthcheck)**
- **狀態**: 可安裝
- **來源**: ClawHub 技能市場
- **安裝**: `clawhub install healthcheck`
- **功能**: 主機安全強化和風險評估

### **7. Oracle CLI 助手 (oracle)**
- **狀態**: 可安裝
- **來源**: ClawHub 技能市場
- **安裝**: `clawhub install oracle`
- **功能**: Prompt 優化和檔案處理

### **8. MCP 伺服器管理 (mcporter)**
- **狀態**: 可安裝
- **來源**: ClawHub 技能市場
- **安裝**: `clawhub install mcporter`
- **功能**: MCP 伺服器配置和工具調用

## 🔍 **技能檢測與學習流程**

### **自動檢測腳本**
```bash
# 檢測已安裝技能
openclaw skills list

# 檢查特定技能
ls ~/.openclaw/workspace/skills/

# 驗證 ComfyUI 技能
python skills/comfyui-skill-openclaw/scripts/simplified_task_generator.py --help
```

### **學習引導流程**

#### **當發現缺失技能時**：

1. **立即通知用戶**
   ```
   🚨 發現缺失技能: [技能名稱]
   📖 建議: 使用 clawhub 安裝或手動配置
   ```

2. **提供安裝指示**
   ```bash
   # 使用 ClawHub 安裝
   clawhub install [skill-name]
   
   # 或從 GitHub 手動安裝
   git clone [skill-repo] skills/[skill-name]
   ```

3. **配置指導**
   - 提供必要的配置步驟
   - 檢查依賴項和環境
   - 驗證安裝成功

#### **當技能版本過舊時**：
```bash
# 更新技能
clawhub update [skill-name]

# 或手動更新
cd skills/[skill-name] && git pull
```

## 🎓 **技能學習重點**

### **ComfyUI 技能精通要求**
- ✅ **本地模型優化** - Ollama qwen3:8b 整合
- ✅ **動態檔案管理** - 避免路徑寫死問題
- ✅ **多解析度支援** - 512x768, 840x1200
- ✅ **批次處理** - 進度監控和錯誤處理

### **記憶系統精通要求**
- ✅ **階層化組織** - daily/topics/moments 結構
- ✅ **自動備份** - GitHub 整合
- ✅ **衝突解決** - Git 問題處理能力

### **系統整合精通要求**
- ✅ **跨技能協作** - ComfyUI + Ollama + Memory
- ✅ **錯誤恢復** - 自動修復和人工介入
- ✅ **效能優化** - 成本控制和資源管理

## 🔄 **自動學習檢查**

### **每次啟動時執行**
1. 檢查 `~/.openclaw/workspace/skills/` 目錄
2. 比對必要技能清單
3. 報告缺失或過時的技能
4. 提供學習和安裝建議

### **學習完成標準**
- 技能目錄存在且可讀取
- 主要腳本可執行
- 配置檔案正確
- 基本功能測試通過

## 📚 **延伸學習資源**

### **官方文檔**
- [ClawHub 技能市場](https://clawhub.com)
- [OpenClaw 文檔](https://docs.openclaw.ai)
- [AgentSkills 規範](https://github.com/openclaw/openclaw/docs/skills)

### **社群資源**
- [Discord 社群](https://discord.com/invite/clawd)
- [GitHub 討論區](https://github.com/openclaw/openclaw/discussions)

---

**使用方式**: 當 ClawClaw 重新啟動時，讀取這個檔案並執行技能檢測，確保所有必要技能都已正確安裝和配置。

**更新頻率**: 當新增重要技能或現有技能有重大更新時，及時更新這個指南。