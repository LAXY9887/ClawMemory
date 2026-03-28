#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日總結選擇處理腳本
處理 LXYA 在 23:45 通知後的選擇
"""

import sys
import json
import datetime
import subprocess
from pathlib import Path

class DailySummaryChoiceHandler:
    def __init__(self):
        self.workspace_path = Path.cwd()
        self.state_file = self.workspace_path / "memory" / "daily_summary_state.json"
        
    def handle_choice(self, choice_number):
        """處理用戶選擇"""
        
        choice_map = {
            "1": "總結並關機",
            "2": "總結但不關機", 
            "3": "不總結也不關機"
        }
        
        choice_name = choice_map.get(str(choice_number), "未知選擇")
        
        print(f"🎯 LXYA 選擇: {choice_name}")
        
        try:
            if choice_number == 1:
                self.execute_full_summary_and_shutdown()
            elif choice_number == 2:
                self.execute_summary_only()
            elif choice_number == 3:
                self.skip_summary()
            else:
                print("❌ 無效選擇，執行預設選項 1")
                self.execute_full_summary_and_shutdown()
                
        except Exception as e:
            print(f"❌ 執行選擇時發生錯誤: {e}")
    
    def execute_full_summary_and_shutdown(self):
        """選項 1: 總結並關機"""
        print("🌙 執行完整流程：智能睡眠模式 + 關機")
        
        # 1. 執行智能睡眠模式
        print("📝 執行智能睡眠模式...")
        sleep_result = subprocess.run([
            sys.executable, 
            str(self.workspace_path / "skills-custom" / "intelligent-sleep" / "scripts" / "intelligent_sleep_mode.py"),
            "manual"
        ], capture_output=True, text=True)
        
        if sleep_result.returncode == 0:
            print("✅ 智能睡眠模式完成")
        else:
            print(f"⚠️ 智能睡眠模式部分失敗: {sleep_result.stderr}")
        
        # 2. 執行關機 (靜默，不發送訊息)
        print("🔋 執行安全關機...")
        
        # 設置靜默標記
        silence_file = self.workspace_path / "memory" / "shutdown_in_progress.flag"
        silence_file.write_text("關機進行中，請勿發送訊息", encoding='utf-8')
        
        shutdown_result = subprocess.run([
            sys.executable,
            str(self.workspace_path / "scripts" / "immediate_shutdown.py")
        ], capture_output=True, text=True)
        
        # 注意：關機後此程序會中斷，不會執行到這裡
    
    def execute_summary_only(self):
        """選項 2: 總結但不關機"""
        print("📝 執行智能睡眠模式 (夜間工作模式)")
        
        sleep_result = subprocess.run([
            sys.executable,
            str(self.workspace_path / "skills-custom" / "intelligent-sleep" / "scripts" / "intelligent_sleep_mode.py"), 
            "manual"
        ], capture_output=True, text=True)
        
        if sleep_result.returncode == 0:
            print("✅ 智能睡眠模式完成")
            # 移除確認訊息 - 避免子程序調用問題
        else:
            print(f"⚠️ 智能睡眠模式失敗: {sleep_result.stderr}")
            # 移除確認訊息 - 避免子程序調用問題
    
    def skip_summary(self):
        """選項 3: 不總結也不關機"""
        print("⏭️ 跳過今日總結")
        
        # 記錄跳過狀態
        skip_record = {
            "date": datetime.date.today().isoformat(),
            "action": "skipped",
            "reason": "user_choice",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 保存到 memory
        daily_path = self.workspace_path / "memory" / "daily" / f"{datetime.date.today().strftime('%Y-%m-%d')}.md"
        skip_note = f"\n## 每日總結記錄\n- ⏭️ {datetime.datetime.now().strftime('%H:%M')} LXYA 選擇跳過今日總結\n"
        
        try:
            with open(daily_path, 'a', encoding='utf-8') as f:
                f.write(skip_note)
        except Exception as e:
            print(f"⚠️ 記錄跳過狀態失敗: {e}")
        
        # 移除確認訊息 - 避免子程序調用問題
        print("⏭️ 已跳過今日總結，記錄已保存")
    
    def send_completion_message(self, message):
        """發送完成訊息 - 已停用避免子程序調用問題"""
        # 不再發送訊息，避免 OpenClaw 子程序調用衝突
        print(f"📝 訊息記錄: {message}")
        pass
    
    def clear_state(self):
        """清理狀態檔案"""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception as e:
            print(f"⚠️ 清理狀態失敗: {e}")

def main():
    """主執行入口"""
    if len(sys.argv) < 2:
        print("用法: python handle_daily_summary_choice.py [1|2|3]")
        sys.exit(1)
    
    try:
        choice = int(sys.argv[1])
        if choice not in [1, 2, 3]:
            raise ValueError("選擇必須是 1, 2, 或 3")
    except ValueError as e:
        print(f"❌ 無效選擇: {e}")
        choice = 1  # 預設選擇
    
    handler = DailySummaryChoiceHandler()
    handler.handle_choice(choice)
    handler.clear_state()

if __name__ == "__main__":
    main()