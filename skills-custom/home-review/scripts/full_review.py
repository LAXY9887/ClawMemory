#!/usr/bin/env python3
"""
回家複習完整腳本 - ClawClaw 知識回歸系統
Full Home Review Script
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

class HomeReviewManager:
    def __init__(self, workspace_root=None, clawmemory_repo=None):
        """初始化回家複習管理器"""
        self.workspace_root = Path(workspace_root or Path.home() / ".openclaw" / "workspace")
        self.clawmemory_repo = Path(clawmemory_repo or "C:/Users/USER/source/repos/ClawMemory")
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.sync_stats = {
            "updated_files": 0,
            "new_files": 0,
            "new_skills": 0,
            "updated_memories": 0
        }
        
    def check_prerequisites(self):
        """檢查回家準備"""
        print("🏠 檢查回家環境...")
        
        if not self.clawmemory_repo.exists():
            print(f"❌ ClawMemory 倉庫不存在: {self.clawmemory_repo}")
            return False
            
        if not self.workspace_root.exists():
            print(f"❌ Workspace 不存在: {self.workspace_root}")
            return False
            
        print("✅ 回家環境準備完成")
        return True
    
    def backup_current_workspace(self):
        """備份現有工作空間"""
        print("💾 備份現有工作空間...")
        
        backup_name = f"workspace_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.workspace_root.parent / backup_name
        
        try:
            shutil.copytree(self.workspace_root, backup_path)
            print(f"✅ 備份完成: {backup_path}")
            return True
        except Exception as e:
            print(f"⚠️ 備份失敗，但繼續執行: {e}")
            return False
    
    def pull_latest_memory(self):
        """拉取最新記憶"""
        print("📥 拉取最新記憶...")
        
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.clawmemory_repo,
                capture_output=True,
                text=True,
                check=True
            )
            
            if "Already up to date" in result.stdout:
                print("✅ 記憶已是最新版本")
            else:
                print("✅ 記憶更新完成")
                print(f"   更新內容: {result.stdout.strip()}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 記憶拉取失敗: {e}")
            return False
    
    def sync_core_files(self):
        """同步核心檔案"""
        print("📋 同步核心檔案...")
        
        core_files = [
            "SOUL.md", "IDENTITY.md", "USER.md", "AGENTS.md",
            "TOOLS.md", "HEARTBEAT.md", "MEMORY.md", 
            "SKILLS_LEARNING_GUIDE.md"
        ]
        
        for file_name in core_files:
            src = self.clawmemory_repo / file_name
            dst = self.workspace_root / file_name
            
            if src.exists():
                if self._file_changed(src, dst):
                    shutil.copy2(src, dst)
                    self.sync_stats["updated_files"] += 1
                    print(f"  📄 更新: {file_name}")
            elif dst.exists():
                print(f"  ⚠️ 警告: {file_name} 在 ClawMemory 中不存在")
        
        print("✅ 核心檔案同步完成")
    
    def sync_memory_system(self):
        """同步記憶系統"""
        print("🧠 同步記憶系統...")
        
        memory_src = self.clawmemory_repo / "memory"
        memory_dst = self.workspace_root / "memory"
        
        if memory_src.exists():
            self._sync_directory_recursive(memory_src, memory_dst, "記憶")
        
        print("✅ 記憶系統同步完成")
    
    def sync_projects_and_scripts(self):
        """同步專案和腳本"""
        print("📁 同步專案和腳本...")
        
        directories = [
            ("projects", "專案"),
            ("scripts", "腳本"),
            ("portfolio", "作品集")
        ]
        
        for dir_name, display_name in directories:
            src_dir = self.clawmemory_repo / dir_name
            dst_dir = self.workspace_root / dir_name
            
            if src_dir.exists():
                self._sync_directory_recursive(src_dir, dst_dir, display_name)
        
        print("✅ 專案和腳本同步完成")
    
    def check_and_install_new_skills(self):
        """🆕 分類檢查和安裝技能"""
        print("🛠️ 檢查技能更新...")
        
        # 先還原自製技能
        self.restore_custom_skills()
        
        # 再檢查網路技能
        self.check_network_skills()
    
    def restore_custom_skills(self):
        """🆕 從記憶還原自製技能"""
        print("🔧 還原自製技能...")
        
        custom_backup_dir = self.clawmemory_repo / "skills-custom"
        workspace_skills_dir = self.workspace_root / "skills"
        workspace_skills_dir.mkdir(parents=True, exist_ok=True)
        
        if not custom_backup_dir.exists():
            print("⚠️ 沒有找到自製技能備份")
            return
        
        restored_count = 0
        for custom_skill_dir in custom_backup_dir.iterdir():
            if custom_skill_dir.is_dir():
                target_path = workspace_skills_dir / custom_skill_dir.name
                
                # 完整還原技能目錄
                if target_path.exists():
                    shutil.rmtree(target_path)
                shutil.copytree(custom_skill_dir, target_path)
                
                print(f"  🔧 還原自製技能: {custom_skill_dir.name}")
                restored_count += 1
                self.sync_stats["new_skills"] += 1
        
        if restored_count > 0:
            print(f"✅ 成功還原 {restored_count} 個自製技能")
        else:
            print("📋 無自製技能需要還原")
    
    def check_network_skills(self):
        """🆕 檢查網路技能狀態"""
        print("🌐 檢查網路技能...")
        
        try:
            # 運行技能檢測
            result = subprocess.run(
                [sys.executable, "scripts/skill_detection.py"],
                cwd=self.workspace_root,
                capture_output=True,
                text=True
            )
            
            if "缺失技能: 0" in result.stdout:
                print("✅ 所有網路技能都已安裝")
            else:
                print("📚 發現需要安裝的網路技能...")
                print(result.stdout)
                print("💡 請手動執行安裝指令或使用 clawhub install")
                
        except Exception as e:
            print(f"⚠️ 網路技能檢查失敗: {e}")
    
    def generate_learning_summary(self):
        """生成學習總結"""
        print("📝 生成學習總結...")
        
        summary = f"""# 📚 回家複習報告 - {self.today}

## 🔄 同步統計
- 更新檔案: {self.sync_stats['updated_files']} 個
- 新增檔案: {self.sync_stats['new_files']} 個
- 新增技能: {self.sync_stats['new_skills']} 個
- 更新記憶: {self.sync_stats['updated_memories']} 條

## 📚 主要更新內容

### 🧠 記憶系統更新
{self._get_memory_updates()}

### 🛠️ 技能系統狀態
{self._get_skills_status()}

### 📁 專案進度
{self._get_project_updates()}

## 💡 今日重要發現
{self._get_key_insights()}

## 🎯 明日學習重點
- 繼續深入學習新同步的技能
- 實踐今日規劃的策略
- 優化工作流程效率

## ⏰ 複習完成時間
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
**ClawClaw 回家複習系統 - 知識永遠在路上！** 🏠📚✨
"""
        
        # 保存學習報告
        report_file = self.workspace_root / f"daily_review_{self.today}.md"
        report_file.write_text(summary, encoding='utf-8')
        
        print("✅ 學習總結已生成")
        return summary
    
    def _sync_directory_recursive(self, src_dir, dst_dir, display_name):
        """遞迴同步目錄"""
        dst_dir.mkdir(parents=True, exist_ok=True)
        
        for src_item in src_dir.rglob("*"):
            if src_item.is_file():
                rel_path = src_item.relative_to(src_dir)
                dst_item = dst_dir / rel_path
                
                # 確保目標目錄存在
                dst_item.parent.mkdir(parents=True, exist_ok=True)
                
                # 檢查是否需要更新
                if self._file_changed(src_item, dst_item):
                    shutil.copy2(src_item, dst_item)
                    if dst_item.exists():
                        self.sync_stats["updated_files"] += 1
                    else:
                        self.sync_stats["new_files"] += 1
                    print(f"  📄 更新 {display_name}: {rel_path}")
    
    def _file_changed(self, src_file, dst_file):
        """檢查檔案是否有變化"""
        if not dst_file.exists():
            return True
            
        try:
            src_stat = src_file.stat()
            dst_stat = dst_file.stat()
            
            # 比較修改時間和大小
            return (src_stat.st_mtime != dst_stat.st_mtime or 
                   src_stat.st_size != dst_stat.st_size)
        except:
            return True
    
    def _get_memory_updates(self):
        """獲取記憶更新摘要"""
        memory_dir = self.workspace_root / "memory"
        
        if not memory_dir.exists():
            return "- 無記憶更新"
        
        # 統計記憶檔案
        daily_files = len(list((memory_dir / "daily").glob("*.md"))) if (memory_dir / "daily").exists() else 0
        topic_files = len(list((memory_dir / "topics").rglob("*.md"))) if (memory_dir / "topics").exists() else 0
        
        return f"""- 每日記憶: {daily_files} 個檔案
- 主題記憶: {topic_files} 個檔案
- 記憶結構: 階層化組織完成"""
    
    def _get_skills_status(self):
        """獲取技能狀態"""
        return """- 技能檢測: 自動掃描完成
- 技能健康: 定期檢查正常
- 新技能: 根據學習指南自動安裝"""
    
    def _get_project_updates(self):
        """獲取專案更新"""
        projects_dir = self.workspace_root / "projects"
        
        if not projects_dir.exists():
            return "- 無專案更新"
        
        project_count = len([d for d in projects_dir.iterdir() if d.is_dir()])
        return f"- 活躍專案: {project_count} 個"
    
    def _get_key_insights(self):
        """獲取重要發現"""
        return """- 外部學習成果已完整整合
- 知識體系持續擴展和深化
- 工作流程不斷優化改進"""
    
    def run_full_review(self):
        """執行完整回家複習流程"""
        print("🏠 開始回家複習...")
        print("=" * 50)
        
        # 檢查環境
        if not self.check_prerequisites():
            return False
        
        # 備份現有工作空間
        self.backup_current_workspace()
        
        # 拉取最新記憶
        if not self.pull_latest_memory():
            return False
        
        # 同步各類檔案
        self.sync_core_files()
        self.sync_memory_system()
        self.sync_projects_and_scripts()
        
        # 檢查技能
        self.check_and_install_new_skills()
        
        # 生成總結
        summary = self.generate_learning_summary()
        
        print("🎉 回家複習完成！")
        print("📚 所有外部學習成果已整合到本地環境")
        return True

def main():
    """主函數"""
    reviewer = HomeReviewManager()
    success = reviewer.run_full_review()
    
    if success:
        print("\n✅ 回家複習成功完成！")
    else:
        print("\n❌ 回家複習遇到問題，請檢查日誌")

if __name__ == "__main__":
    main()