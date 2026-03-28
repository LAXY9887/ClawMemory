#!/usr/bin/env python3
"""
立即安全關機腳本
修復電源管理問題的緊急腳本
"""
import os
import sys
import subprocess
import time
import psutil
from pathlib import Path

def safe_immediate_shutdown():
    """立即執行安全關機流程"""
    print("🔋 ClawClaw 立即安全關機")
    print("=" * 50)
    
    try:
        # 1. 停止重要服務
        print("🛑 停止重要服務...")
        stop_critical_services()
        
        # 2. 最後檢查
        print("💾 最後安全檢查...")
        time.sleep(2)
        
        # 3. 執行關機
        print("🌙 正在執行系統關機...")
        
        # 設置靜默標記 - 關機後不發送任何訊息
        silence_file = Path.cwd() / "memory" / "shutdown_in_progress.flag"
        silence_file.write_text("關機進行中，請勿發送訊息")
        
        # Windows 系統關機命令
        subprocess.run(["shutdown", "/s", "/t", "3", "/c", "ClawClaw 每日總結完成，系統關機中..."], 
                      check=False)
        
        return True
        
    except Exception as e:
        print(f"❌ 關機流程出現錯誤: {e}")
        print("請手動關機或聯繫技術支援")
        return False

def stop_critical_services():
    """停止關鍵服務"""
    services_to_stop = {
        'ComfyUI.exe': 'ComfyUI Desktop',
        'ollama.exe': 'Ollama 服務',
        'Docker Desktop.exe': 'Docker Desktop'
    }
    
    stopped_count = 0
    
    for process_name, display_name in services_to_stop.items():
        try:
            # 尋找並終止程序
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == process_name.lower():
                        print(f"   🔄 停止 {display_name} (PID: {proc.info['pid']})")
                        
                        # 優雅終止
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            # 強制終止
                            proc.kill()
                        
                        stopped_count += 1
                        break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            print(f"   ⚠️ 停止 {display_name} 失敗: {e}")
    
    if stopped_count > 0:
        print(f"   ✅ 成功停止 {stopped_count} 個服務")
    else:
        print("   ℹ️ 無需要停止的關鍵服務")

if __name__ == "__main__":
    print("⚡ 緊急關機流程啟動")
    success = safe_immediate_shutdown()
    
    if not success:
        print("\n手動關機指令:")
        print("shutdown /s /t 60")
        
    sys.exit(0 if success else 1)