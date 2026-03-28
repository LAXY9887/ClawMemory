#!/usr/bin/env python3
"""
ClawMemory 新標準鏡像同步系統 v2.0
完整鏡像同步：workspace → ClawMemory

執行標準 5 步驟流程：
1. 完整鏡像同步 (robocopy /MIR)
2. 正確排除目錄 (pictures/tasks/secure)
3. 真正同步對應 (刪除/新增/修改)
4. 單一 Git 倉庫 (ClawMemory only)
5. 統一提交推送 (所有 Git 操作在 ClawMemory)

Created: 2026-03-28
Author: ClawClaw
"""

import subprocess
import os
import shutil
from pathlib import Path
from datetime import datetime
import sys

# 路徑配置
WORKSPACE_PATH = r"C:\Users\USER\.openclaw\workspace"
CLAWMEMORY_PATH = r"C:\Users\USER\source\repos\ClawMemory"

class ClawMemorySync:
    def __init__(self):
        self.workspace_path = Path(WORKSPACE_PATH)
        self.clawmemory_path = Path(CLAWMEMORY_PATH)
        
    def log(self, message, level="INFO"):
        """輸出日誌"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "📋",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "📋")
        print(f"{prefix} {timestamp} {message}")
        
    def run_command(self, cmd, cwd=None, capture=True):
        """執行命令"""
        try:
            result = subprocess.run(
                cmd, 
                cwd=cwd or self.clawmemory_path,
                capture_output=capture,
                text=True,
                shell=True if isinstance(cmd, str) else False
            )
            return result
        except Exception as e:
            self.log(f"命令執行失敗: {e}", "ERROR")
            return None
    
    def step1_check_uncommitted_changes(self):
        """Step 1: 檢查並處理 ClawMemory 未提交變更"""
        self.log("Step 1: 檢查 ClawMemory 未提交變更")
        
        result = self.run_command(["git", "status", "--porcelain"])
        if not result:
            return False
            
        changes = result.stdout.strip()
        if changes:
            change_count = len(changes.splitlines())
            self.log(f"發現 {change_count} 個未提交變更，先提交...", "WARNING")
            
            # 提交變更
            self.run_command(["git", "add", "."])
            commit_result = self.run_command([
                "git", "commit", "-m", 
                "Pre-sync cleanup: commit pending changes before mirror sync"
            ])
            
            if commit_result and commit_result.returncode == 0:
                self.log("未提交變更已清理", "SUCCESS")
            else:
                self.log("提交變更失敗", "ERROR")
                return False
        else:
            self.log("沒有未提交變更", "SUCCESS")
            
        return True
    
    def step2_update_gitignore(self):
        """Step 2: 更新 .gitignore 排除目錄"""
        self.log("Step 2: 設定 .gitignore 排除目錄")
        
        gitignore_path = self.clawmemory_path / ".gitignore"
        exclude_dirs = ["pictures/", "tasks/", "secure/"]
        
        # 讀取現有內容
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text(encoding='utf-8')
        else:
            existing_content = ""
            
        # 添加排除目錄
        new_content = existing_content
        added_count = 0
        
        for dir_name in exclude_dirs:
            if dir_name not in existing_content:
                new_content += f"\n{dir_name}"
                added_count += 1
                self.log(f"添加排除目錄: {dir_name}")
            else:
                self.log(f"排除目錄已存在: {dir_name}")
        
        # 寫入更新的內容
        gitignore_path.write_text(new_content.strip(), encoding='utf-8')
        
        if added_count > 0:
            self.log(f"已更新 .gitignore，新增 {added_count} 個排除目錄", "SUCCESS")
        else:
            self.log(".gitignore 已是最新狀態", "SUCCESS")
            
        return True
    
    def step3_mirror_sync(self):
        """Step 3: 執行完整鏡像同步"""
        self.log("Step 3: 執行完整鏡像同步")
        
        # robocopy 參數
        robocopy_args = [
            "robocopy",
            str(self.workspace_path),
            str(self.clawmemory_path),
            "/MIR",  # 鏡像同步
            "/XD", "pictures", "tasks", "secure", ".git",  # 排除目錄
            "/R:1",  # 重試 1 次
            "/W:1",  # 等待 1 秒
            "/NP",   # 不顯示進度
            "/NS", "/NC", "/NFL"  # 簡化輸出
        ]
        
        self.log(f"執行: {' '.join(robocopy_args)}")
        result = self.run_command(robocopy_args)
        
        if not result:
            self.log("robocopy 執行失敗", "ERROR")
            return False
            
        # robocopy 退出碼 0-7 表示成功
        if result.returncode <= 7:
            self.log(f"鏡像同步成功 (退出碼: {result.returncode})", "SUCCESS")
            
            # 顯示同步統計
            output_lines = result.stdout.splitlines()
            for line in output_lines[-10:]:  # 顯示最後10行
                if "Files :" in line or "Bytes :" in line or "Times :" in line:
                    self.log(f"統計: {line.strip()}")
                    
            return True
        else:
            self.log(f"鏡像同步失敗 (退出碼: {result.returncode})", "ERROR")
            self.log(f"錯誤: {result.stderr}", "ERROR")
            return False
    
    def step4_cleanup_excluded_dirs(self):
        """Step 4: 清理意外同步的排除目錄"""
        self.log("Step 4: 清理意外同步的排除目錄")
        
        exclude_dirs = ["tasks", "secure"]  # pictures 通常不會意外同步
        cleaned_count = 0
        
        for dir_name in exclude_dirs:
            dir_path = self.clawmemory_path / dir_name
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    self.log(f"已清理意外同步的目錄: {dir_name}", "WARNING")
                    cleaned_count += 1
                except Exception as e:
                    self.log(f"清理目錄 {dir_name} 失敗: {e}", "ERROR")
            else:
                self.log(f"{dir_name} 目錄正確排除")
                
        if cleaned_count == 0:
            self.log("排除目錄狀態正確", "SUCCESS")
            
        return True
    
    def step5_git_commit_push(self):
        """Step 5: Git 提交與推送"""
        self.log("Step 5: 執行 Git 提交與推送")
        
        # 檢查變更
        self.run_command(["git", "add", "."])
        
        status_result = self.run_command(["git", "status", "--porcelain"])
        if not status_result:
            self.log("Git status 檢查失敗", "ERROR")
            return False
            
        changes = status_result.stdout.strip()
        change_count = len(changes.splitlines()) if changes else 0
        
        if change_count == 0:
            self.log("沒有變更需要提交", "SUCCESS")
            return True
            
        self.log(f"發現 {change_count} 個變更，準備提交")
        
        # 統計同步信息
        try:
            total_files = len([f for f in self.clawmemory_path.rglob("*") if f.is_file() and ".git" not in str(f)])
        except:
            total_files = "Unknown"
        
        # 生成提交訊息
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"""🔄 ClawMemory 鏡像同步：完整 workspace 同步 ({timestamp})

✅ 同步統計:
- 變更檔案: {change_count} 個
- 總檔案數: {total_files}

📁 架構更新:
- ✅ 完整鏡像同步 (robocopy /MIR)
- ✅ 排除目錄正確設定 (pictures/tasks/secure)
- ✅ 真正同步對應 (刪除/新增/修改)

🎯 同步完整性:
- 鏡像模式: 完整刪除、新增、修改同步
- 單一 Git 倉庫策略執行

🦞 ClawMemory 狀態: 與 workspace 完全同步"""

        # 提交變更
        commit_result = self.run_command(["git", "commit", "-m", commit_msg])
        if not commit_result or commit_result.returncode != 0:
            self.log("Git commit 失敗", "ERROR")
            return False
            
        self.log("Git commit 成功", "SUCCESS")
        
        # 推送變更
        self.log("推送變更到 GitHub...")
        push_result = self.run_command(["git", "push", "origin", "main"])
        
        if push_result and push_result.returncode == 0:
            self.log("推送成功！", "SUCCESS")
            return True
        elif push_result and "fetch first" in push_result.stderr:
            self.log("遠端有變更，執行 rebase...", "WARNING")
            
            # 執行 rebase
            rebase_result = self.run_command(["git", "pull", "--rebase", "origin", "main"])
            if rebase_result and rebase_result.returncode == 0:
                self.log("Rebase 成功", "SUCCESS")
                
                # 重新推送
                final_push = self.run_command(["git", "push", "origin", "main"])
                if final_push and final_push.returncode == 0:
                    self.log("重新推送成功！", "SUCCESS")
                    return True
                else:
                    self.log("重新推送失敗", "ERROR")
                    return False
            else:
                self.log("Rebase 失敗，需要手動處理", "ERROR")
                return False
        else:
            self.log(f"推送失敗: {push_result.stderr if push_result else 'Unknown error'}", "ERROR")
            return False
    
    def execute_sync(self):
        """執行完整同步流程"""
        self.log("🚀 開始執行 ClawMemory 新標準鏡像同步流程 v2.0", "SUCCESS")
        
        # 檢查路徑存在性
        if not self.workspace_path.exists():
            self.log(f"Workspace 路徑不存在: {self.workspace_path}", "ERROR")
            return False
            
        if not self.clawmemory_path.exists():
            self.log(f"ClawMemory 路徑不存在: {self.clawmemory_path}", "ERROR")
            return False
        
        # 執行 5 步驟流程
        steps = [
            ("檢查未提交變更", self.step1_check_uncommitted_changes),
            ("更新 .gitignore", self.step2_update_gitignore),
            ("完整鏡像同步", self.step3_mirror_sync),
            ("清理排除目錄", self.step4_cleanup_excluded_dirs),
            ("Git 提交推送", self.step5_git_commit_push)
        ]
        
        for step_name, step_func in steps:
            self.log(f"執行: {step_name}")
            success = step_func()
            if not success:
                self.log(f"{step_name} 執行失敗，中止同步", "ERROR")
                return False
        
        self.log("🎉 ClawMemory 鏡像同步流程執行完成！", "SUCCESS")
        return True

def main():
    """主函數"""
    print("=" * 60)
    print("🦞 ClawMemory 新標準鏡像同步系統 v2.0")
    print("=" * 60)
    
    syncer = ClawMemorySync()
    success = syncer.execute_sync()
    
    if success:
        print("\n✅ 同步成功完成！")
        return 0
    else:
        print("\n❌ 同步執行失敗！")
        return 1

if __name__ == "__main__":
    sys.exit(main())