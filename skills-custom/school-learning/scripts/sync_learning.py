#!/usr/bin/env python3
"""
上學同步腳本 - ClawClaw 學習成果同步工具
School Learning Sync Script
"""

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

class SchoolLearningSync:
    def __init__(self, workspace_root=None, clawmemory_repo=None):
        """初始化同步管理器"""
        self.workspace_root = Path(workspace_root or Path.home() / ".openclaw" / "workspace")
        self.clawmemory_repo = Path(clawmemory_repo or "C:/Users/USER/source/repos/ClawMemory")
        self.today = datetime.now().strftime("%Y-%m-%d")
        
    def check_prerequisites(self):
        """檢查前置條件"""
        print("🔍 檢查學習環境...")
        
        # 檢查 ClawMemory 倉庫
        if not self.clawmemory_repo.exists():
            print(f"❌ ClawMemory 倉庫不存在: {self.clawmemory_repo}")
            return False
            
        # 檢查 workspace
        if not self.workspace_root.exists():
            print(f"❌ Workspace 不存在: {self.workspace_root}")
            return False
            
        print("✅ 學習環境準備完成")
        return True
    
    def pull_latest_memory(self):
        """拉取最新的記憶"""
        print("📥 拉取最新記憶...")
        try:
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.clawmemory_repo,
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ 記憶同步完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 記憶拉取失敗: {e}")
            return False
    
    def sync_new_skills(self, skills_data):
        """🆕 分類同步技能（自製 vs 網路）"""
        if not skills_data:
            return
            
        print("🛠️ 分類同步新技能...")
        
        custom_skills = []
        network_skills = []
        
        # 分類技能
        for skill in skills_data:
            skill_name = skill.get("name", "")
            skill_type = skill.get("type", "network")  # 默認為網路技能
            
            if skill_type == "custom":
                custom_skills.append(skill)
            else:
                network_skills.append(skill)
        
        # 同步自製技能
        if custom_skills:
            self.sync_custom_skills(custom_skills)
        
        # 同步網路技能
        if network_skills:
            self.sync_network_skills(network_skills)
    
    def sync_custom_skills(self, custom_skills_data):
        """🆕 同步自製技能到記憶"""
        print("🔧 同步自製技能...")
        
        custom_backup_dir = self.clawmemory_repo / "skills-custom"
        custom_backup_dir.mkdir(parents=True, exist_ok=True)
        
        for skill_info in custom_skills_data:
            skill_name = skill_info.get("name", "")
            skill_path = self.workspace_root / "skills" / skill_name
            backup_path = custom_backup_dir / skill_name
            
            if skill_path.exists() and skill_path.is_dir():
                # 檢查是否為自製技能（無 .git）
                if not (skill_path / ".git").exists():
                    # 完整複製技能目錄
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    shutil.copytree(skill_path, backup_path)
                    print(f"  🔧 備份自製技能: {skill_name}")
                else:
                    print(f"  ⚠️ 跳過網路技能: {skill_name} (包含 .git)")
        
        # 更新自製技能指南
        self._update_custom_skills_guide(custom_skills_data)
        
    def sync_network_skills(self, network_skills_data):
        """🆕 同步網路技能學習指導"""
        print("🌐 同步網路技能指導...")
        
        for skill_info in network_skills_data:
            skill_name = skill_info.get("name", "")
            print(f"  📦 更新網路技能指導: {skill_name}")
        
        # 更新網路技能學習指南
        self._update_network_skills_guide(network_skills_data)
    
    def _update_custom_skills_guide(self, skills_data):
        """🆕 更新自製技能指南"""
        guide_file = self.workspace_root / "CUSTOM_SKILLS_GUIDE.md"
        clawmemory_guide = self.clawmemory_repo / "CUSTOM_SKILLS_GUIDE.md"
        
        # 複製更新後的指南
        if guide_file.exists():
            shutil.copy2(guide_file, clawmemory_guide)
            print("✅ 自製技能指南已更新")
    
    def _update_network_skills_guide(self, skills_data):
        """🆕 更新網路技能學習指南"""
        guide_file = self.workspace_root / "SKILLS_LEARNING_GUIDE.md"
        clawmemory_guide = self.clawmemory_repo / "SKILLS_LEARNING_GUIDE.md"
        
        # 複製更新後的指南
        if guide_file.exists():
            shutil.copy2(guide_file, clawmemory_guide)
            print("✅ 網路技能指南已更新")
    
    def sync_new_scripts(self, scripts_data):
        """同步新腳本"""
        if not scripts_data:
            return
            
        print("📜 同步新腳本...")
        
        workspace_scripts = self.workspace_root / "scripts"
        clawmemory_scripts = self.clawmemory_repo / "scripts"
        
        for script_info in scripts_data:
            script_name = script_info.get("name", "")
            script_content = script_info.get("content", "")
            
            if script_name and script_content:
                script_file = clawmemory_scripts / script_name
                script_file.write_text(script_content, encoding='utf-8')
                print(f"  📜 新增腳本: {script_name}")
        
        print("✅ 腳本同步完成")
    
    def sync_new_documents(self, docs_data):
        """同步新文檔和資料"""
        if not docs_data:
            return
            
        print("📄 同步新文檔...")
        
        for doc_info in docs_data:
            doc_type = doc_info.get("type", "general")  # general, technical, personal, reference
            doc_name = doc_info.get("name", "")
            doc_content = doc_info.get("content", "")
            
            # 根據類型決定存放位置
            if doc_type == "technical":
                target_dir = self.clawmemory_repo / "memory" / "topics" / "technical"
            elif doc_type == "personal":
                target_dir = self.clawmemory_repo / "memory" / "topics" / "personal"
            elif doc_type == "reference":
                topic = doc_info.get("topic", "general")
                target_dir = self.clawmemory_repo / "memory" / "references" / topic
            else:
                target_dir = self.clawmemory_repo / "memory" / "topics"
            
            target_dir.mkdir(parents=True, exist_ok=True)
            doc_file = target_dir / doc_name
            doc_file.write_text(doc_content, encoding='utf-8')
            print(f"  📄 新增文檔: {doc_name} → {doc_type}")
        
        print("✅ 文檔同步完成")
    
    def update_daily_memory(self, learning_summary):
        """更新今日記憶"""
        print("📝 更新今日學習記憶...")
        
        daily_file = self.clawmemory_repo / "memory" / "daily" / f"{self.today}.md"
        
        # 準備學習記錄
        learning_entry = f"""
## {datetime.now().strftime("%H:%M")} 外部學習成果同步

### 📚 學習主題
{learning_summary.get('topic', '一般學習')}

### 🎯 學習目標
{learning_summary.get('objectives', '知識獲取和技能提升')}

### ✅ 學習成果
{learning_summary.get('achievements', '完成預定學習目標')}

### 🔄 同步內容
- 新技能: {len(learning_summary.get('skills', []))} 個
- 新腳本: {len(learning_summary.get('scripts', []))} 個  
- 新文檔: {len(learning_summary.get('documents', []))} 個

### 💡 重要發現
{learning_summary.get('insights', '持續累積知識和經驗')}
"""
        
        # 如果檔案存在，追加；否則創建
        if daily_file.exists():
            with open(daily_file, 'a', encoding='utf-8') as f:
                f.write(learning_entry)
        else:
            daily_content = f"# {self.today} 記憶記錄\n{learning_entry}"
            daily_file.write_text(daily_content, encoding='utf-8')
        
        print("✅ 今日記憶已更新")
    
    def commit_and_push(self, learning_topic):
        """提交並推送變更"""
        print("💾 提交學習成果...")
        
        try:
            # 添加所有變更
            subprocess.run(["git", "add", "."], cwd=self.clawmemory_repo, check=True)
            
            # 提交
            commit_message = f"""🎓 學習成果同步 - {learning_topic}

📚 外部學習完成，知識已同步回本地記憶
⏰ 同步時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}
🎯 學習主題: {learning_topic}

自動同步系統執行完成。"""
            
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.clawmemory_repo,
                check=True
            )
            
            # 推送
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=self.clawmemory_repo,
                check=True
            )
            
            print("✅ 學習成果已提交到 GitHub")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git 操作失敗: {e}")
            return False
    
    def sync_learning_results(self, learning_data):
        """完整同步學習成果"""
        print("🎓 開始學習成果同步...")
        print("=" * 50)
        
        # 檢查前置條件
        if not self.check_prerequisites():
            return False
        
        # 拉取最新記憶
        if not self.pull_latest_memory():
            return False
        
        # 解析學習資料
        topic = learning_data.get("topic", "一般學習")
        skills = learning_data.get("skills", [])
        scripts = learning_data.get("scripts", [])
        documents = learning_data.get("documents", [])
        summary = learning_data.get("summary", {})
        
        # 同步各類型內容
        self.sync_new_skills(skills)
        self.sync_new_scripts(scripts)
        self.sync_new_documents(documents)
        self.update_daily_memory(summary)
        
        # 提交變更
        if self.commit_and_push(topic):
            print("🎉 學習同步完成！")
            print("📚 所有學習成果已安全保存到 ClawMemory")
            return True
        else:
            return False

def main():
    """主函數"""
    # 示例學習資料結構
    sample_learning = {
        "topic": "Fiverr 策略規劃",
        "skills": [
            {
                "name": "fiverr-optimization",
                "description": "Fiverr 平台優化策略",
                "install_method": "manual"
            }
        ],
        "scripts": [
            {
                "name": "fiverr_analysis.py",
                "content": "# Fiverr 分析腳本\nprint('Hello Fiverr!')"
            }
        ],
        "documents": [
            {
                "type": "technical",
                "name": "fiverr-strategy.md",
                "content": "# Fiverr 策略文檔\n\n詳細的策略規劃..."
            }
        ],
        "summary": {
            "topic": "Fiverr 策略規劃",
            "objectives": "制定完整的 Fiverr 平台策略",
            "achievements": "完成市場分析和策略制定",
            "insights": "了解到平台競爭格局和最佳實踐"
        }
    }
    
    # 創建同步器並執行
    syncer = SchoolLearningSync()
    syncer.sync_learning_results(sample_learning)

if __name__ == "__main__":
    main()