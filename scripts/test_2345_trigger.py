#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 23:45 觸發機制
模擬當時間到達 23:45 時的行為
"""

import datetime
import sys
from pathlib import Path

# 模擬 23:45 時間
class MockDateTime:
    def __init__(self, *args, **kwargs):
        self.original = original_datetime(*args, **kwargs)
        
    @classmethod
    def now(cls):
        # 返回 2026-03-26 23:45:30
        return original_datetime(2026, 3, 26, 23, 45, 30)
        
    def __getattr__(self, name):
        return getattr(self.original, name)

# 保存原始 datetime
original_datetime = datetime.datetime
# 替換 datetime 模組
datetime.datetime = MockDateTime

# 導入並執行智能 heartbeat 處理器
sys.path.append(str(Path.cwd() / 'scripts'))

try:
    from smart_heartbeat_handler import SmartHeartbeatHandler
    
    print("🧪 模擬測試：時間 = 23:45")
    print("=" * 50)
    
    handler = SmartHeartbeatHandler()
    result = handler.execute_heartbeat()
    
    print("📊 測試結果:")
    print(result)
    print("=" * 50)
    
    # 檢查是否生成了狀態檔案
    state_file = Path.cwd() / "memory" / "daily_summary_state.json"
    if state_file.exists():
        print("✅ 通知狀態檔案已創建")
        import json
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        print(f"📁 狀態內容: {state}")
    else:
        print("⚠️ 通知狀態檔案未創建")
    
except Exception as e:
    print(f"❌ 測試失敗: {e}")
    import traceback
    traceback.print_exc()

finally:
    # 恢復原始 datetime
    datetime.datetime = original_datetime