#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能睡眠模式快速觸發器
用於手動觸發智能睡眠模式，適合 LXYA 直接調用
"""

import sys
import subprocess
from pathlib import Path

def trigger_intelligent_sleep_mode():
    """觸發智能睡眠模式"""
    
    workspace_path = Path.cwd()
    sleep_script = workspace_path / 'skills-custom' / 'intelligent-sleep' / 'scripts' / 'intelligent_sleep_mode.py'
    
    if not sleep_script.exists():
        print("❌ 智能睡眠模式腳本不存在")
        print(f"期望路徑: {sleep_script}")
        return False
    
    try:
        print("🌙 啟動智能睡眠模式...")
        print("-" * 50)
        
        # 執行智能睡眠模式
        result = subprocess.run([
            sys.executable, str(sleep_script), 'manual'
        ], cwd=workspace_path)
        
        if result.returncode == 0:
            print("-" * 50)
            print("✅ 智能睡眠模式執行完成")
            return True
        else:
            print("-" * 50)
            print("❌ 智能睡眠模式執行失敗")
            return False
            
    except Exception as e:
        print(f"❌ 執行異常: {e}")
        return False

if __name__ == "__main__":
    success = trigger_intelligent_sleep_mode()
    sys.exit(0 if success else 1)