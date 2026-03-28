#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版每日總結通知
直接輸出訊息，讓 ClawClaw 在 heartbeat 中發送
"""

import datetime

def generate_notification_message():
    """生成每日總結選擇通知訊息"""
    
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

請回覆數字 1/2/3 選擇，或等待稍後的確認 ☺️""".format(
        date=datetime.date.today().strftime("%Y-%m-%d")
    )
    
    return message

def main():
    """主執行入口"""
    message = generate_notification_message()
    print("SEND_NOTIFICATION")  # 特殊標記讓 heartbeat 知道要發送通知
    print(message)

if __name__ == "__main__":
    main()