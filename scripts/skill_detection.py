#!/usr/bin/env python3
"""
自動技能檢測和學習引導腳本
Auto Skill Detection and Learning Guide
"""

import os
import json
from pathlib import Path

class SkillDetector:
    def __init__(self, workspace_dir=None):
        if workspace_dir is None:
            workspace_dir = Path.home() / ".openclaw" / "workspace"
        self.workspace_dir = Path(workspace_dir)
        self.skills_dir = self.workspace_dir / "skills"
        
        # 🆕 分類技能定義
        self.custom_skills = {
            "school-learning": {
                "description": "上學學習系統",
                "key_files": ["SKILL.md", "scripts/sync_learning.py"],
                "type": "custom",
                "priority": "critical"
            },
            "home-review": {
                "description": "回家複習系統", 
                "key_files": ["SKILL.md", "scripts/full_review.py"],
                "type": "custom",
                "priority": "critical"
            },
            "memory-backup": {
                "description": "Memory 備份系統",
                "key_files": ["SKILL.md", "scripts/backup_manager.py"],
                "type": "custom",
                "priority": "critical"
            },
            "power-management": {
                "description": "電源管理系統",
                "key_files": ["SKILL.md", "scripts/daily-power-decision.py"],
                "type": "custom",
                "priority": "high"
            },
            "enhanced-browser": {
                "description": "Enhanced Browser 控制",
                "key_files": ["SKILL.md"],
                "type": "custom",
                "priority": "high"
            },
            "desktop-vision": {
                "description": "Desktop Vision 能力",
                "key_files": ["SKILL.md"],
                "type": "custom", 
                "priority": "high"
            },
            "desktop-input": {
                "description": "Desktop Input 控制",
                "key_files": ["SKILL.md"],
                "type": "custom",
                "priority": "medium"
            }
        }
        
        self.network_skills = {
            "comfyui-skill-openclaw": {
                "description": "ComfyUI 圖像生成系統",
                "key_files": ["SKILL.md", "config.json"],
                "type": "network",
                "install_method": "git_clone",
                "priority": "critical"
            },
            "github": {
                "description": "GitHub 操作",
                "key_files": ["SKILL.md"],
                "type": "network",
                "install_method": "builtin",
                "priority": "medium"
            },
            "weather": {
                "description": "天氣查詢",
                "key_files": ["SKILL.md"],
                "type": "network", 
                "install_method": "builtin",
                "priority": "low"
            }
        }
        
        # 合併所有技能
        self.required_skills = {**self.custom_skills, **self.network_skills}
    
    def scan_installed_skills(self):
        """掃描已安裝的技能"""
        if not self.skills_dir.exists():
            return {}
            
        installed = {}
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and skill_dir.name in self.required_skills:
                skill_info = self.check_skill_health(skill_dir)
                installed[skill_dir.name] = skill_info
                
        return installed
    
    def check_skill_health(self, skill_dir):
        """檢查技能完整性"""
        skill_name = skill_dir.name
        required_info = self.required_skills.get(skill_name, {})
        
        health_status = {
            "name": skill_name,
            "path": str(skill_dir),
            "exists": True,
            "key_files_status": {},
            "overall_health": "unknown"
        }
        
        key_files = required_info.get("key_files", [])
        missing_files = []
        
        for file_path in key_files:
            file_full_path = skill_dir / file_path
            exists = file_full_path.exists()
            health_status["key_files_status"][file_path] = exists
            if not exists:
                missing_files.append(file_path)
        
        # 判斷整體健康狀況
        if len(missing_files) == 0:
            health_status["overall_health"] = "healthy"
        elif len(missing_files) < len(key_files) / 2:
            health_status["overall_health"] = "degraded"
        else:
            health_status["overall_health"] = "broken"
            
        health_status["missing_files"] = missing_files
        return health_status
    
    def identify_missing_skills(self, installed_skills):
        """識別缺失的技能"""
        missing = {}
        for skill_name, skill_info in self.required_skills.items():
            if skill_name not in installed_skills:
                missing[skill_name] = skill_info
        return missing
    
    def generate_learning_guidance(self):
        """生成學習引導報告"""
        installed = self.scan_installed_skills()
        missing = self.identify_missing_skills(installed)
        
        report = {
            "timestamp": "2026-03-26T00:13:00",
            "workspace_dir": str(self.workspace_dir),
            "installed_skills": installed,
            "missing_skills": missing,
            "recommendations": []
        }
        
        # 生成建議
        for skill_name, skill_info in missing.items():
            priority = skill_info.get("priority", "low")
            install_method = skill_info.get("install_method", "clawhub_install")
            
            if priority == "critical":
                urgency = "🚨 立即安裝"
            elif priority == "high":
                urgency = "⚠️ 建議安裝"  
            else:
                urgency = "💡 可選安裝"
                
            recommendation = {
                "skill": skill_name,
                "description": skill_info.get("description", ""),
                "urgency": urgency,
                "install_command": f"clawhub install {skill_name}" if install_method == "clawhub_install" else "手動安裝"
            }
            report["recommendations"].append(recommendation)
        
        return report
    
    def print_report(self, report):
        """🆕 輸出分類技能檢測報告"""
        print("🎓 ClawClaw 分類技能檢測報告")
        print("=" * 50)
        
        installed = report["installed_skills"]
        missing = report["missing_skills"]
        
        # 分類顯示已安裝技能
        custom_installed = {k: v for k, v in installed.items() if self.required_skills[k].get("type") == "custom"}
        network_installed = {k: v for k, v in installed.items() if self.required_skills[k].get("type") == "network"}
        
        print(f"🔧 自製技能: {len(custom_installed)}")
        for skill_name, skill_info in custom_installed.items():
            health = skill_info["overall_health"]
            status_emoji = {"healthy": "🟢", "degraded": "🟡", "broken": "🔴"}.get(health, "⚪")
            print(f"   {status_emoji} {skill_name} - {health}")
            
            if skill_info.get("missing_files"):
                print(f"      缺失檔案: {', '.join(skill_info['missing_files'])}")
        
        print(f"\n🌐 網路技能: {len(network_installed)}")
        for skill_name, skill_info in network_installed.items():
            health = skill_info["overall_health"] 
            status_emoji = {"healthy": "🟢", "degraded": "🟡", "broken": "🔴"}.get(health, "⚪")
            has_git = (Path(skill_info["path"]) / ".git").exists() if skill_info["path"] else False
            git_indicator = "📦" if has_git else "⚠️"
            print(f"   {status_emoji} {git_indicator} {skill_name} - {health}")
            
            if skill_info.get("missing_files"):
                print(f"      缺失檔案: {', '.join(skill_info['missing_files'])}")
        
        # 分類顯示缺失技能
        custom_missing = [r for r in report["recommendations"] if self.required_skills[r["skill"]].get("type") == "custom"]
        network_missing = [r for r in report["recommendations"] if self.required_skills[r["skill"]].get("type") == "network"]
        
        if custom_missing:
            print(f"\n❌ 缺失自製技能: {len(custom_missing)}")
            for recommendation in custom_missing:
                print(f"   {recommendation['urgency']} {recommendation['skill']}")
                print(f"      {recommendation['description']}")
                print(f"      還原: 從 ClawMemory/skills-custom/ 還原")
                print()
        
        if network_missing:
            print(f"\n❌ 缺失網路技能: {len(network_missing)}")
            for recommendation in network_missing:
                print(f"   {recommendation['urgency']} {recommendation['skill']}")
                print(f"      {recommendation['description']}")
                print(f"      安裝: {recommendation['install_command']}")
                print()
        
        if not missing:
            print("🎉 所有必要技能都已安裝！")

def main():
    """主函數 - 執行技能檢測"""
    detector = SkillDetector()
    report = detector.generate_learning_guidance()
    detector.print_report(report)
    
    # 保存報告
    report_file = detector.workspace_dir / "skill_detection_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"📄 詳細報告已保存: {report_file}")

if __name__ == "__main__":
    main()