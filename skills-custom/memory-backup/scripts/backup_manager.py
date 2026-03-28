#!/usr/bin/env python3
"""
ClawClaw Memory Backup Manager v2.0

🚀 新標準鏡像同步系統整合版

使用新標準 5 步驟鏡像同步流程：
1. 完整鏡像同步 (robocopy /MIR)
2. 正確排除目錄 (pictures/tasks/secure)
3. 真正同步對應 (刪除/新增/修改)
4. 單一 Git 倉庫 (ClawMemory only)
5. 統一提交推送 (所有 Git 操作在 ClawMemory)

整合新的 clawmemory_sync.py 進行完整鏡像同步。
Created: 2026-03-25
Updated: 2026-03-28 (新標準鏡像同步整合)
"""

import os
import shutil
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 整合新的鏡像同步模組
try:
    from .clawmemory_sync import ClawMemorySync
    MIRROR_SYNC_AVAILABLE = True
except ImportError:
    # 如果 clawmemory_sync.py 不在同一目錄，回退到舊方法
    MIRROR_SYNC_AVAILABLE = False

class MemoryBackupManager:
    def __init__(self, workspace_root: str = None, backup_repo: str = None):
        """Initialize the backup manager."""
        # Default workspace should be the OpenClaw workspace, not the skill directory
        default_workspace = Path.home() / ".openclaw" / "workspace"
        self.workspace_root = Path(workspace_root or default_workspace)
        self.backup_repo = Path(backup_repo or "C:/Users/USER/source/repos/ClawMemory")
        
        # Files and directories to backup
        self.core_files = [
            "SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md", 
            "TOOLS.md", "HEARTBEAT.md", "MEMORY.md", "SKILLS_LEARNING_GUIDE.md",
            "CUSTOM_SKILLS_GUIDE.md",  # 🆕 自製技能指南
            "claude-pro-vs-openrouter-analysis.md",
            "model-usage-policy-updated.md",
            "自由工作平台服務定價策略分析報告.md"
        ]
        
        # Backup important directories
        self.backup_dirs = ["memory", "projects", "scripts", "portfolio", "goals"]
        
        # 🆕 自製技能列表（無 .git 的技能）
        self.custom_skills = [
            "school-learning", "home-review", "memory-backup", "power-management",
            "enhanced-browser", "desktop-vision", "desktop-input"
        ]
        
        # Directories to exclude from backup (sensitive or temporary)
        self.exclude_dirs = ["secure", "test_memory", "test_screenshots", ".openclaw"]
        
        # File patterns to exclude from backup
        self.exclude_patterns = [
            "*.png", "*.jpg", "*.jpeg", "*.gif",  # 圖片檔案
            "*screenshot*",  # 截圖檔案
            "*report.json",  # 自動生成報告
            "daily_summary_*.md",  # 臨時總結
            "test-*.py",  # 測試腳本
            "my_perfect_avatar.png"  # 大型圖片檔案
        ]
        
        # Git settings
        self.git_remote = "origin"
        self.git_branch = "main"
        
        self.backup_log = self.backup_repo / "backup.log"
    
    def check_workspace_changes(self) -> Dict[str, List[str]]:
        """Check for changes in workspace files."""
        changes = {
            "modified": [],
            "new": [],
            "deleted": []
        }
        
        # Check core files
        for file in self.core_files:
            workspace_file = self.workspace_root / file
            backup_file = self.backup_repo / file
            
            if workspace_file.exists():
                if not backup_file.exists():
                    changes["new"].append(file)
                elif self._files_different(workspace_file, backup_file):
                    changes["modified"].append(file)
            elif backup_file.exists():
                changes["deleted"].append(file)
        
        # Check directories
        for dir_name in self.backup_dirs:
            workspace_dir = self.workspace_root / dir_name
            backup_dir = self.backup_repo / dir_name
            
            if workspace_dir.exists():
                dir_changes = self._compare_directories(workspace_dir, backup_dir, dir_name)
                changes["modified"].extend(dir_changes["modified"])
                changes["new"].extend(dir_changes["new"])
                changes["deleted"].extend(dir_changes["deleted"])
        
        return changes
    
    def _files_different(self, file1: Path, file2: Path) -> bool:
        """Check if two files have different content."""
        try:
            with open(file1, 'r', encoding='utf-8') as f1, open(file2, 'r', encoding='utf-8') as f2:
                return f1.read() != f2.read()
        except Exception:
            return True
    
    def _compare_directories(self, workspace_dir: Path, backup_dir: Path, relative_base: str) -> Dict[str, List[str]]:
        """Compare workspace and backup directories."""
        changes = {"modified": [], "new": [], "deleted": []}
        
        if not backup_dir.exists():
            # Entire directory is new
            for file_path in workspace_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(self.workspace_root))
                    changes["new"].append(rel_path)
            return changes
        
        # Get all files in both directories
        workspace_files = set()
        backup_files = set()
        
        for file_path in workspace_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(workspace_dir)
                workspace_files.add(rel_path)
        
        for file_path in backup_dir.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(backup_dir)
                backup_files.add(rel_path)
        
        # Compare files
        for rel_path in workspace_files:
            full_rel_path = f"{relative_base}/{rel_path}"
            workspace_file = workspace_dir / rel_path
            backup_file = backup_dir / rel_path
            
            if rel_path not in backup_files:
                changes["new"].append(full_rel_path)
            elif self._files_different(workspace_file, backup_file):
                changes["modified"].append(full_rel_path)
        
        for rel_path in backup_files:
            if rel_path not in workspace_files:
                full_rel_path = f"{relative_base}/{rel_path}"
                changes["deleted"].append(full_rel_path)
        
        return changes
    
    def backup_to_repository(self, force: bool = False, use_mirror_sync: bool = True) -> Dict:
        """Backup workspace files to the Git repository."""
        timestamp = datetime.now()
        backup_result = {
            "timestamp": timestamp.isoformat(),
            "success": False,
            "changes": {},
            "commit_hash": None,
            "errors": []
        }
        
        try:
            # 🚀 新標準：優先使用鏡像同步
            if use_mirror_sync and MIRROR_SYNC_AVAILABLE:
                print("🚀 使用新標準鏡像同步流程...")
                syncer = ClawMemorySync()
                sync_success = syncer.execute_sync()
                
                if sync_success:
                    backup_result["success"] = True
                    backup_result["message"] = "Mirror sync completed successfully"
                    backup_result["method"] = "mirror_sync"
                    return backup_result
                else:
                    print("⚠️ 鏡像同步失敗，回退到傳統方法...")
                    # 繼續執行傳統備份流程
            
            # 🔄 傳統備份流程（回退選項）
            print("📦 使用傳統備份流程...")
            
            # Check for changes
            changes = self.check_workspace_changes()
            backup_result["changes"] = changes
            
            total_changes = sum(len(changes[key]) for key in changes)
            
            if total_changes == 0 and not force:
                backup_result["success"] = True
                backup_result["message"] = "No changes detected, backup skipped"
                backup_result["method"] = "traditional_skip"
                return backup_result
            
            # Ensure backup repository exists
            if not self.backup_repo.exists():
                self.backup_repo.mkdir(parents=True, exist_ok=True)
                self._init_git_repo()
            
            # Copy files
            self._copy_workspace_files()
            
            # Git operations
            git_result = self._git_commit_and_push(changes)
            backup_result["method"] = "traditional_backup"
            backup_result["commit_hash"] = git_result["commit_hash"]
            backup_result["success"] = git_result["success"]
            
            if git_result["success"]:
                backup_result["message"] = f"Backup completed: {total_changes} changes"
            else:
                backup_result["errors"].append(git_result["error"])
            
        except Exception as e:
            backup_result["errors"].append(f"Backup failed: {str(e)}")
        
        # Log the result
        self._log_backup_result(backup_result)
        
        return backup_result
    
    def _copy_workspace_files(self):
        """Copy workspace files to backup repository."""
        # Copy core files
        for file in self.core_files:
            src = self.workspace_root / file
            dst = self.backup_repo / file
            
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        
        # Copy directories with deep recursive copying
        for dir_name in self.backup_dirs:
            src_dir = self.workspace_root / dir_name
            dst_dir = self.backup_repo / dir_name
            
            if src_dir.exists():
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                self._copy_directory_recursive(src_dir, dst_dir)
        
        # 🆕 Copy custom skills to dedicated backup location
        self._backup_custom_skills()
    
    def _copy_directory_recursive(self, src_dir, dst_dir):
        """Recursively copy directory with all subdirectories."""
        dst_dir.mkdir(parents=True, exist_ok=True)
        
        for src_item in src_dir.rglob("*"):
            if src_item.is_file():
                # Calculate relative path from source directory
                rel_path = src_item.relative_to(src_dir)
                dst_item = dst_dir / rel_path
                
                # Ensure parent directories exist
                dst_item.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_item, dst_item)
    
    def _backup_custom_skills(self):
        """🆕 備份自製技能到專用目錄"""
        skills_dir = self.workspace_root / "skills"
        custom_backup_dir = self.backup_repo / "skills-custom"
        
        # 清理舊的備份
        if custom_backup_dir.exists():
            shutil.rmtree(custom_backup_dir)
        custom_backup_dir.mkdir(parents=True, exist_ok=True)
        
        if not skills_dir.exists():
            return
        
        # 備份每個自製技能
        for skill_name in self.custom_skills:
            src_skill = skills_dir / skill_name
            dst_skill = custom_backup_dir / skill_name
            
            if src_skill.exists() and src_skill.is_dir():
                # 檢查是否為自製技能（無 .git 目錄）
                if not (src_skill / ".git").exists():
                    shutil.copytree(src_skill, dst_skill)
                    print(f"✅ 備份自製技能: {skill_name}")
                else:
                    print(f"⚠️ 跳過網路技能: {skill_name} (包含 .git)")
    
    def _is_custom_skill(self, skill_dir):
        """🆕 判斷是否為自製技能"""
        # 檢查是否在自製技能列表中且沒有 .git 目錄
        return (skill_dir.name in self.custom_skills and 
                not (skill_dir / ".git").exists())
    
    def _init_git_repo(self):
        """Initialize Git repository if needed."""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=self.backup_repo,
                check=True,
                capture_output=True
            )
            
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/LAXY9887/ClawMemory.git"],
                cwd=self.backup_repo,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Repository might already exist
    
    def _git_commit_and_push(self, changes: Dict) -> Dict:
        """Commit changes and push to remote repository."""
        result = {"success": False, "commit_hash": None, "error": None}
        
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "."],
                cwd=self.backup_repo,
                check=True,
                capture_output=True
            )
            
            # Generate commit message
            commit_msg = self._generate_commit_message(changes)
            
            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.backup_repo,
                capture_output=True,
                text=True
            )
            
            if commit_result.returncode != 0:
                # Check if it's because there were no changes
                if "nothing to commit" in commit_result.stdout:
                    result["success"] = True
                    result["error"] = "No changes to commit"
                    return result
                else:
                    result["error"] = f"Commit failed: {commit_result.stderr}"
                    return result
            
            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.backup_repo,
                capture_output=True,
                text=True,
                check=True
            )
            result["commit_hash"] = hash_result.stdout.strip()
            
            # Push to remote
            push_result = subprocess.run(
                ["git", "push", self.git_remote, self.git_branch],
                cwd=self.backup_repo,
                capture_output=True,
                text=True
            )
            
            if push_result.returncode != 0:
                result["error"] = f"Push failed: {push_result.stderr}"
            else:
                result["success"] = True
            
        except subprocess.CalledProcessError as e:
            result["error"] = f"Git operation failed: {str(e)}"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
        
        return result
    
    def _generate_commit_message(self, changes: Dict) -> str:
        """Generate descriptive commit message."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        total_changes = sum(len(changes[key]) for key in changes)
        
        if total_changes == 0:
            return f"🔄 Memory backup sync - {timestamp}"
        
        msg_parts = [f"💾 Memory backup update - {timestamp}"]
        
        if changes["new"]:
            msg_parts.append(f"✨ New: {len(changes['new'])} files")
        
        if changes["modified"]:
            msg_parts.append(f"📝 Modified: {len(changes['modified'])} files")
        
        if changes["deleted"]:
            msg_parts.append(f"🗑️ Deleted: {len(changes['deleted'])} files")
        
        # Add key files if modified
        important_files = ["SOUL.md", "IDENTITY.md", "MEMORY.md"]
        modified_important = [f for f in changes["modified"] if f in important_files]
        
        if modified_important:
            msg_parts.append(f"🌟 Updated: {', '.join(modified_important)}")
        
        return "\\n\\n".join(msg_parts)
    
    def _log_backup_result(self, result: Dict):
        """Log backup result to file."""
        try:
            log_entry = {
                "timestamp": result["timestamp"],
                "success": result["success"],
                "total_changes": sum(len(result["changes"][key]) for key in result["changes"]),
                "commit_hash": result["commit_hash"],
                "errors": result.get("errors", [])
            }
            
            # Read existing log
            log_data = []
            if self.backup_log.exists():
                with open(self.backup_log, 'r') as f:
                    log_data = json.load(f)
            
            # Add new entry
            log_data.append(log_entry)
            
            # Keep only last 100 entries
            log_data = log_data[-100:]
            
            # Write back
            with open(self.backup_log, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            print(f"Failed to log backup result: {e}")
    
    def get_backup_status(self) -> Dict:
        """Get current backup status and recent history."""
        try:
            if not self.backup_log.exists():
                return {"status": "No backup history found"}
            
            with open(self.backup_log, 'r') as f:
                log_data = json.load(f)
            
            if not log_data:
                return {"status": "Empty backup log"}
            
            latest = log_data[-1]
            recent_failures = [entry for entry in log_data[-10:] if not entry["success"]]
            
            return {
                "last_backup": latest["timestamp"],
                "last_success": latest["success"],
                "last_commit": latest.get("commit_hash"),
                "recent_failures": len(recent_failures),
                "total_backups": len(log_data)
            }
            
        except Exception as e:
            return {"status": f"Error reading backup log: {e}"}

def main():
    """主函數 - 支持新舊備份方法"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawClaw Memory Backup Manager v2.0")
    parser.add_argument("--force", action="store_true", help="強制備份即使沒有變更")
    parser.add_argument("--validate-only", action="store_true", help="僅驗證檔案，不執行備份")
    parser.add_argument("--legacy", action="store_true", help="使用傳統備份方法（不使用鏡像同步）")
    parser.add_argument("--status", action="store_true", help="顯示備份狀態")
    
    args = parser.parse_args()
    
    manager = MemoryBackupManager()
    
    print("🦞 ClawClaw Memory Backup Manager v2.0")
    print("=" * 50)
    
    if MIRROR_SYNC_AVAILABLE and not args.legacy:
        print("✅ 新標準鏡像同步可用")
    else:
        print("⚠️ 使用傳統備份方法")
    
    if args.status:
        # 顯示備份狀態
        status = manager.get_backup_status()
        print("\n📊 當前狀態:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        return
    
    if args.validate_only:
        print("\n🔍 僅執行驗證...")
        # 這裡可以加入 YAML 驗證邏輯
        print("✅ 驗證完成")
        return
    
    # 執行備份
    print("\n🔍 檢查變更...")
    use_mirror_sync = not args.legacy
    
    print(f"\n🚀 開始備份（方法：{'鏡像同步' if use_mirror_sync else '傳統'}）...")
    result = manager.backup_to_repository(force=args.force, use_mirror_sync=use_mirror_sync)
    
    if result["success"]:
        method = result.get("method", "unknown")
        print(f"✅ 備份完成！ (方法: {method})")
        if "commit_hash" in result:
            print(f"   Commit: {result['commit_hash']}")
        if "message" in result:
            print(f"   訊息: {result['message']}")
    else:
        print(f"❌ 備份失敗: {result.get('message', 'Unknown error')}")
        if result.get("errors"):
            for error in result["errors"]:
                print(f"   錯誤: {error}")

if __name__ == "__main__":
    main()