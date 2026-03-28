#!/usr/bin/env python3
"""
測試排程訊息 - 21:40 Hello 測試
"""

import schedule
import time
import datetime
import sys
import os

# 確保可以使用 message 功能
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def send_hello_message():
    """發送 Hello 測試訊息"""
    try:
        # 使用 OpenClaw message 功能
        os.system('openclaw message send --target telegram:7178763424 --message "🦞 Hello！這是 21:40 排程測試訊息！ClawClaw 的排程系統正常運作！✨"')
        
        print(f"✅ 21:40 Hello 訊息已發送 - {datetime.datetime.now()}")
        
        # 發送後停止排程
        return schedule.CancelJob
        
    except Exception as e:
        print(f"❌ 發送失敗: {e}")
        return schedule.CancelJob

def main():
    """主要執行函數"""
    current_time = datetime.datetime.now()
    target_time = current_time.replace(hour=21, minute=40, second=0, microsecond=0)
    
    # 如果已經過了 21:40，設定明天
    if current_time >= target_time:
        target_time += datetime.timedelta(days=1)
    
    print(f"🕘 設定 21:40 Hello 訊息排程")
    print(f"📅 目標時間: {target_time}")
    print(f"⏰ 當前時間: {current_time}")
    
    # 設定排程
    schedule.every().day.at("21:40").do(send_hello_message)
    
    print("🔄 排程已啟動，等待 21:40...")
    
    # 持續運行直到任務執行
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # 每30秒檢查一次
            
            # 顯示等待狀態
            now = datetime.datetime.now()
            if now.second % 30 == 0:  # 每30秒顯示一次
                remaining = target_time - now
                if remaining.total_seconds() > 0:
                    mins = int(remaining.total_seconds() // 60)
                    secs = int(remaining.total_seconds() % 60)
                    print(f"⏳ 等待中... 還有 {mins}:{secs:02d}")
                    
    except KeyboardInterrupt:
        print("\n🛑 排程測試已停止")

if __name__ == "__main__":
    main()