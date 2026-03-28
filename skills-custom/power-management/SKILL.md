---
name: power-management
description: ClawClaw intelligent power management system for personal workstations. Provides safe shutdown control with flexibility for night work sessions. Use when: (1) Daily summary completion requires shutdown decision, (2) Manual shutdown with safety checks needed, (3) Emergency power management situations, (4) Configuring work vs personal schedule power policies. Includes smart analysis, file safety, and graceful service termination.
---

# Power Management: ClawClaw 智能電源管理系統

為個人工作站設計的智能電源管理，平衡自動化便利與工作彈性需求。

## Core Mission

提供安全、智能、靈活的電源管理解決方案，適合個人主機使用場景，同時保留夜間工作的彈性需求。

## When to Use

### Automatic Triggers
- **Daily summary completion**: 每日總結後的關機決策
- **Scheduled power management**: 預設時間的電源控制
- **Idle detection**: 長時間閒置的智能關機
- **Resource optimization**: 節能模式和待機控制

### Manual Triggers
- **Emergency shutdown**: 緊急情況下的安全關機
- **Maintenance mode**: 系統維護前的準備關機
- **Work session end**: 工作結束的手動關機
- **Power policy adjustment**: 臨時調整電源策略

## Core Features

### 1. Safe Shutdown System
- **Multi-stage validation**: 檔案安全、服務檢查、工作狀態
- **Graceful termination**: 優雅關閉所有服務和程序
- **Countdown mechanism**: 30秒取消窗口
- **Emergency abort**: 緊急中止功能

### 2. Intelligent Analysis
- **Work status detection**: 未完成工作和未儲存檔案
- **Service monitoring**: ComfyUI, Ollama, VS Code 等重要服務
- **Network activity**: 下載進度和網路連接
- **Schedule awareness**: 明日行程和工作需求

### 3. Flexible Decision System
- **Default behavior**: 每日總結後自動關機
- **Night work mode**: 保持待命狀態選項
- **Delayed shutdown**: 延後關機決策
- **Custom schedules**: 工作日/假日不同策略

### 4. Safety Mechanisms
- **File preservation**: 自動儲存和 Git commit
- **Service cleanup**: 優雅停止背景服務
- **State recovery**: 意外重啟後的工作恢復
- **Backup validation**: 確保重要資料已備份

## Usage Workflow

### Daily Summary Integration
```
23:50 Daily Summary Cron
         ↓
Memory organization, GitHub backup
         ↓
Power Management Decision
         ↓
┌─────────────────┬─────────────────┐
│  🌙 Shutdown    │ 💤 Stay Awake   │
│  (Default)      │ (Night Work)    │
│                 │                 │
├─ Safety checks  │ ├─ Set reminder │
├─ Service stop   │ ├─ Reduce power │
├─ 30s countdown  │ └─ Next check   │
└─ System halt    │                 │
```

### Smart Suggestion Engine
```python
def analyze_shutdown_readiness():
    analysis = {
        'file_safety': check_unsaved_files(),
        'service_status': check_critical_services(),
        'work_progress': check_ongoing_tasks(),
        'schedule_tomorrow': check_calendar(),
        'system_health': check_system_status()
    }
    
    recommendation = generate_smart_suggestion(analysis)
    return {
        'suggested_action': recommendation,
        'confidence': calculate_confidence(analysis),
        'reasoning': explain_decision(analysis)
    }
```

### User Interface Flow
```
🔋 ClawClaw 電源管理 - 每日總結完成

💡 智能分析結果：
✅ 所有重要檔案已儲存
✅ GitHub 備份完成
⚠️ ComfyUI 仍在運行 (無進行中任務)
✅ 明日行程輕鬆，適合休息

建議動作: 🌙 安全關機

請選擇動作：
1. 🌙 立即安全關機 (預設) - 30秒後執行
2. 💤 保持夜間待命 - 降功耗運行  
3. ⏰ 延後 1 小時 - 稍後再決定
4. ❌ 取消 - 維持正常運行

30秒後自動執行選項 1...
[████████████████▒▒▒▒] 25秒
```

## Technical Implementation

### Shutdown Safety Script
```powershell
# Safe-Shutdown.ps1
function Invoke-SafeShutdown {
    param(
        [int]$DelaySeconds = 30,
        [bool]$Force = $false
    )
    
    Write-Host "🔋 ClawClaw 安全關機流程開始..." -ForegroundColor Cyan
    
    # 1. 保存所有工作
    Write-Host "💾 保存工作狀態..."
    Save-OpenClawWorkspace
    Invoke-GitAutoCommit
    
    # 2. 檢查重要服務
    Write-Host "🔍 檢查系統狀態..."
    $services = @("ComfyUI", "Ollama", "Docker")
    foreach ($service in $services) {
        Stop-ServiceGracefully -Name $service
    }
    
    # 3. 最後確認
    if (-not $Force) {
        Write-Host "⏰ ${DelaySeconds}秒後關機，按任意鍵取消..." -ForegroundColor Yellow
        $timeout = New-TimeSpan -Seconds $DelaySeconds
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        
        while ($sw.Elapsed -lt $timeout) {
            if ([Console]::KeyAvailable) {
                [Console]::ReadKey($true)
                Write-Host "❌ 關機已取消" -ForegroundColor Green
                return $false
            }
            $remaining = $DelaySeconds - [int]$sw.Elapsed.TotalSeconds
            Write-Host "`r⏱️  ${remaining}秒後關機... (按任意鍵取消)" -NoNewline -ForegroundColor Yellow
            Start-Sleep -Milliseconds 100
        }
        Write-Host ""
    }
    
    # 4. 執行關機
    Write-Host "🌙 正在安全關機..." -ForegroundColor Magenta
    shutdown /s /t 5 /c "ClawClaw 每日總結完成，系統關機中..."
    return $true
}
```

### Service Management
```python
# service_manager.py
import subprocess
import psutil
import time

class ServiceManager:
    def __init__(self):
        self.critical_services = {
            'ComfyUI': {'port': 8000, 'process': 'ComfyUI.exe'},
            'Ollama': {'port': 11434, 'process': 'ollama.exe'},
            'Docker': {'process': 'Docker Desktop.exe'}
        }
    
    def stop_all_services(self, graceful=True):
        """Gracefully stop all critical services."""
        stopped_services = []
        
        for service_name, config in self.critical_services.items():
            try:
                if self.is_service_running(service_name):
                    print(f"🔄 Stopping {service_name}...")
                    
                    if graceful:
                        self.stop_service_gracefully(service_name, config)
                    else:
                        self.force_stop_service(config['process'])
                    
                    stopped_services.append(service_name)
                    time.sleep(2)  # Allow time for graceful shutdown
                    
            except Exception as e:
                print(f"⚠️ Error stopping {service_name}: {e}")
        
        return stopped_services
    
    def stop_service_gracefully(self, name, config):
        """Attempt graceful service termination."""
        if 'port' in config:
            # Try HTTP shutdown endpoint first
            try:
                import requests
                requests.post(f"http://localhost:{config['port']}/shutdown", 
                            timeout=5)
                time.sleep(3)
            except:
                pass
        
        # Fallback to process termination
        self.terminate_process_by_name(config['process'])
    
    def check_unsaved_work(self):
        """Check for unsaved files and ongoing work."""
        warnings = []
        
        # Check for modified files in workspace
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, cwd='.')
        if result.stdout.strip():
            warnings.append("Uncommitted changes in workspace")
        
        # Check ComfyUI for running workflows
        if self.is_service_running('ComfyUI'):
            # Implementation would check ComfyUI API for active workflows
            pass
        
        return warnings
```

### Smart Decision Engine
```python
# decision_engine.py
from datetime import datetime, timedelta
import json

class PowerDecisionEngine:
    def __init__(self):
        self.config_file = "power-management-config.json"
        self.load_config()
    
    def analyze_shutdown_readiness(self):
        """Comprehensive shutdown readiness analysis."""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'recommendation': {},
            'confidence': 0
        }
        
        # File safety check
        analysis['checks']['file_safety'] = self.check_file_safety()
        
        # Service status check
        analysis['checks']['services'] = self.check_service_status()
        
        # Work progress check
        analysis['checks']['work_progress'] = self.check_work_progress()
        
        # Schedule analysis
        analysis['checks']['tomorrow_schedule'] = self.check_tomorrow_schedule()
        
        # Generate recommendation
        analysis['recommendation'] = self.generate_recommendation(analysis['checks'])
        analysis['confidence'] = self.calculate_confidence(analysis['checks'])
        
        return analysis
    
    def generate_recommendation(self, checks):
        """Generate smart power management recommendation."""
        score = 0
        reasons = []
        
        # File safety (critical)
        if checks['file_safety']['safe']:
            score += 30
            reasons.append("✅ 所有檔案已安全儲存")
        else:
            score -= 50
            reasons.append("⚠️ 有未儲存的檔案")
        
        # Service status
        if not checks['services']['critical_running']:
            score += 20
            reasons.append("✅ 無重要服務運行")
        else:
            score -= 10
            reasons.append("⚠️ 重要服務仍在運行")
        
        # Work progress
        if not checks['work_progress']['ongoing_tasks']:
            score += 25
            reasons.append("✅ 無進行中的工作")
        
        # Schedule
        if checks['tomorrow_schedule']['light_day']:
            score += 15
            reasons.append("✅ 明日行程輕鬆")
        else:
            score -= 5
            reasons.append("⚠️ 明日行程較滿")
        
        # Determine recommendation
        if score >= 70:
            action = "shutdown"
            message = "建議立即安全關機"
        elif score >= 30:
            action = "ask_user"
            message = "建議詢問使用者偏好"
        else:
            action = "stay_awake"
            message = "建議保持運行"
        
        return {
            'action': action,
            'message': message,
            'score': score,
            'reasons': reasons
        }
```

## Integration with Daily Summary

### Modified Cron Job
```bash
# Update daily-summary cron to include power management
openclaw cron edit daily-summary --system-event " 
After completing daily summary tasks, execute power management decision via 
python skills/power-management/scripts/daily-power-decision.py
"
```

### HEARTBEAT.md Integration
```markdown
### 🌙 **每日總結 (23:50)**
- 📚 整理今日重要記憶到 memory/daily/YYYY-MM-DD.md
- 🔄 觸發 Memory-Backup 自動備份到 GitHub
- 📊 生成今日活動摘要和成就回顧
- 🎯 準備明日目標和重點
- 💾 確保所有重要對話和發現都已記錄
- 🔋 **執行智能電源管理決策**

*電源管理將自動分析系統狀態並提供關機建議，預設30秒後執行安全關機流程*
```

## Configuration

### Default Settings
```json
{
  "powerManagement": {
    "defaultAction": "shutdown",
    "confirmationTimeout": 30,
    "enableSmartSuggestions": true,
    "schedules": {
      "weekday": {
        "shutdownTime": "23:55",
        "forceShutdown": false
      },
      "weekend": {
        "shutdownTime": "00:30", 
        "forceShutdown": false
      }
    },
    "safetyChecks": {
      "checkUnsavedFiles": true,
      "checkRunningServices": true,
      "forceGitCommit": true,
      "validateBackups": true
    },
    "emergencySettings": {
      "maxDelayHours": 4,
      "forceShutdownAfterDelay": false
    }
  }
}
```

## Benefits

### Cost Optimization
- **Eliminate night heartbeats**: 省下夜間每2小時的檢查費用
- **Automatic power saving**: 個人主機不再24/7運行
- **Smart scheduling**: 只在需要時保持開機

### Work-Life Balance  
- **Flexible control**: 夜間工作時可選擇保持開機
- **Automatic routine**: 日常使用時無需手動關機
- **Emergency override**: 緊急情況下的靈活控制

### System Health
- **Graceful shutdowns**: 避免強制關機損壞
- **Service management**: 正確停止所有服務
- **Data protection**: 確保工作不遺失

## Usage Examples

### Tonight's Automatic Flow
```
23:50 → Daily Summary Cron 觸發
       ↓
All tasks completed successfully
       ↓
Power Management Analysis:
✅ Files saved ✅ Backup complete ✅ No urgent work
       ↓
Recommendation: 🌙 Safe Shutdown
       ↓
30-second countdown → System shutdown
```

### Manual Override Example
```python
# Manual power management
from skills.power_management.scripts.power_controller import PowerController

controller = PowerController()

# Force stay awake for night work
controller.set_night_work_mode(duration_hours=8)

# Manual safe shutdown
controller.safe_shutdown(delay_seconds=60, force=False)

# Emergency immediate shutdown
controller.emergency_shutdown()
```

---

**ClawClaw 的智能電源管理 - 讓休息和工作都自動化！** 🔋🌙🦞✨