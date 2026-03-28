#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日總結預告通知系統
23:45 主動通知 LXYA，提供選擇
"""

import sys
import json
import datetime
import subprocess
from pathlib import Path

class DailySummaryNotifier:
    def __init__(self):
        self.workspace_path = Path.cwd()
        self.telegram_target = "telegram:7178763424"
        
    def send_notification(self):
        """發送每日總結選擇通知"""
        
        current_time = datetime.datetime.now().strftime("%H:%M")
        
        # 構建通知訊息
        message = self.build_notification_message()
        
        # 發送到 Telegram
        try:
            # 使用完整路徑的 openclaw 命令
            openclaw_path = "C:\\Users\\USER\\AppData\\Roaming\\npm\\openclaw.cmd"
            
            result = subprocess.run([
                openclaw_path, 'message', 'send',
                '--target', self.telegram_target,
                '--message', message,
                '--buttons', json.dumps([
                    [
                        {"text": "1️⃣ 總結並關機", "callback_data": "daily_summary_option_1"},
                        {"text": "2️⃣ 總結但不關機", "callback_data": "daily_summary_option_2"}
                    ],
                    [
                        {"text": "3️⃣ 不總結也不關機", "callback_data": "daily_summary_option_3"}
                    ]
                ])
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 每日總結通知已發送")
                self.save_notification_state()
            else:
                print(f"❌ 通知發送失敗: {result.stderr}")
                
        except Exception as e:
            print(f"❌ 通知系統錯誤: {e}")
    
    def build_notification_message(self):
        """構建通知訊息內容"""
        
        message = """🌙 **ClawClaw 每日總結時間到了！**

⏰ **當前時間**: 23:45
📅 **日期**: {date}

請選擇今晚的動作：

**1️⃣ 總結並關機**
- ✅ 執行智能睡眠模式 (記憶整理+經驗提煉)
- ✅ GitHub 備份同步
- ✅ 安全關機系統

**2️⃣ 總結但不關機** 
- ✅ 執行智能睡眠模式
- ✅ GitHub 備份同步
- ❌ 保持系統運行 (夜間工作模式)

**3️⃣ 不總結也不關機**
- ❌ 跳過今日總結
- ❌ 保持系統運行
- ⚠️ 記憶不會自動整理

**⏱️ 如果 10 分鐘內未回覆，將預設執行選項 1**

請點選按鈕選擇，或回覆數字 1/2/3 ☺️""".format(
            date=datetime.date.today().strftime("%Y-%m-%d")
        )
        
        return message
    
    def save_notification_state(self):
        """保存通知狀態"""
        try:
            state = {
                "notification_sent": True,
                "sent_at": datetime.datetime.now().isoformat(),
                "waiting_for_response": True,
                "default_deadline": (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            }
            
            state_file = self.workspace_path / "memory" / "daily_summary_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 狀態保存失敗: {e}")

def main():
    """主執行入口"""
    notifier = DailySummaryNotifier()
    notifier.send_notification()

if __name__ == "__main__":
    main()