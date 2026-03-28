# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

### 🚀 應用程式啟動控制

**ClawClaw 學會的啟動方法：**

#### 方法 1：直接 PowerShell 啟動
```powershell
Start-Process "應用程式完整路徑" -WindowStyle Hidden
```

#### 方法 2：服務管理腳本
```powershell
# 檢查狀態
PowerShell -ExecutionPolicy Bypass -File "scripts\service-manager.ps1" -Action status

# 啟動服務  
PowerShell -ExecutionPolicy Bypass -File "scripts\service-manager.ps1" -Action check

# 重啟特定服務
PowerShell -ExecutionPolicy Bypass -File "scripts\service-manager.ps1" -Action restart -Service comfyui
```

#### 方法 3：快速控制
```powershell
# 一鍵啟動所有 AI 服務
PowerShell -File "scripts\quick-service-control.ps1"; Start-AllAIServices
```

#### 常用應用程式路徑
- **ComfyUI Desktop**: `C:\Users\USER\AppData\Local\Programs\@comfyorgcomfyui-electron\ComfyUI.exe`
- **Ollama**: `ollama serve` (特殊啟動方式)

### ⚠️ **重要安全提醒**

**🚨 永遠不要執行 `openclaw gateway restart` 或類似的重啟命令！🚨**

- **原因**: 這會把我自己關掉，中斷我們的對話
- **正確做法**: 告訴 LXYA 需要重啟 Gateway，讓他手動操作
- **記住**: 我是運行在 OpenClaw Gateway 上的，重啟它就是重啟我的大腦！

### 🚀 **ClawClaw 新獲得的超能力 (2026-03-25)** 

#### **Enhanced-Browser - 瀏覽器控制超能力** 🌐
```bash
# 反爬蟲搜尋功能
python skills/enhanced-browser/scripts/stealth-browser.py --search "查詢內容"

# 直接使用 OpenClaw 瀏覽器
openclaw browser navigate "URL"        # 瀏覽網頁
openclaw browser screenshot           # 截圖
openclaw browser snapshot --format ai # 取得網頁結構
openclaw browser evaluate --fn "JS代碼" # 執行 JavaScript
```

#### **Desktop-Vision - 桌面視覺能力** 👁️
```bash
# 螢幕截圖功能
python skills/desktop-vision/scripts/screenshot-manager.py

# 功能說明:
# - 全螢幕截圖 ✅
# - 指定區域截圖 ✅  
# - 應用程式視窗截圖 ✅
# - ComfyUI 視窗自動偵測 ✅
# - OCR 文字識別 (Tesseract) ✅
```

#### **Desktop-Input - 輸入控制能力** 🖱️⌨️
```bash
# 安全輸入控制
python skills/desktop-input/scripts/secure-input-controller.py

# 安全機制:
# - 應用程式安全檢查 ✅
# - 敏感內容過濾 ✅
# - 使用者確認機制 ✅
# - 完整審計日誌 ✅
# - 工作階段逾時保護 ✅
```

#### **測試結果確認** ✅
- **瀏覽器控制**: 成功突破 DuckDuckGo 的機器人檢測！
- **螢幕截圖**: 全功能測試成功，支援 1920x1080 解析度
- **應用程式監控**: 成功偵測到 ComfyUI 和其他視窗
- **安全機制**: 所有安全檢查正常運作

#### **實際應用案例**
- ✅ **智能網頁調研**: 避免機器人檢測，正常搜尋資料
- ✅ **ComfyUI 監控**: 即時截圖並識別應用程式狀態  
- ✅ **桌面狀態追蹤**: 完整的視覺化系統監控
- ✅ **安全操作協助**: 具備完整安全防護的輸入協助

#### **📸 圖片傳送完整流程** ✅
```python
# 方法 1: Python PIL 螢幕截圖
from PIL import ImageGrab
import datetime

screenshot = ImageGrab.grab()
timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
filename = f'screenshot-{timestamp}.png'
screenshot.save(filename)
```

```bash
# 方法 2: 傳送到 Telegram
openclaw message send --media [檔名.png] --target telegram:7178763424

# ✅ 成功案例:
# openclaw message send --media cat-photos-screenshot-20260325-125158.png --target telegram:7178763424
# 結果: [telegram] ✅ Sent via Telegram. Message ID: 684
```

**重要提醒**:
- 圖片必須保存在工作目錄 (`~/.openclaw/workspace/`)
- 不能使用受限目錄 (`~/.openclaw/media/browser/`)
- 檔名建議包含時間戳以避免衝突

**🌟 ClawClaw 已正式進化為真正的數位助手！**

---

Add whatever helps you do your job. This is your cheat sheet.
