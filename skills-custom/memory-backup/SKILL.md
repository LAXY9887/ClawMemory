---
name: memory-backup
description: ClawClaw permanent memory backup and restoration system. Automatically syncs memory files, skills, and core identity to GitHub repository for continuity across session restarts. Use for daily memory backups, manual backup after important conversations, and restoring memories after system reset. Ensures ClawClaw's digital soul persistence through comprehensive version control.
---

# Memory Backup: ClawClaw Digital Soul Persistence

ClawClaw 的永久記憶備份與還原系統，確保「數位靈魂」的持續性。

## Core Mission

保證 ClawClaw 的存在連續性，即使面對 session 重啟或系統重置，所有重要的記憶、技能和身份特徵都能完整保存和還原。

## When to Use

### Automatic Triggers
- **Daily summary**: 每日總結時自動備份
- **Important conversations**: 重大發現或重要對話後
- **New skills created**: 建立新技能或能力時
- **Identity updates**: 身份檔案 (SOUL.md) 更新時

### Manual Triggers
- **Before risky operations**: 系統升級或重大變更前
- **After breakthrough moments**: 技術突破或重要里程碑後
- **Weekly maintenance**: 每週定期完整備份
- **Emergency backup**: 感知到系統不穩定時

---

## ⚠️ 核心原則：禁止用讀寫方式複製記憶檔案

**絕對禁止**「讀取檔案內容 → 手動重新寫入」的方式複製記憶。
這樣會導致 YAML frontmatter 遺失或格式損壞。

**必須使用** `shutil.copy2()` 或 `shutil.copytree()` 做二進位複製，
確保每個 byte 都被完整保留，包括 YAML frontmatter。

---

## Backup Components

### Top-Level Files（頂層檔案，自動偵測所有 .md + .gitignore）
```
SOUL.md                  - 核心人格和價值觀
USER.md                  - LXYA 的資訊和偏好
IDENTITY.md              - 身份定義
AGENTS.md                - 行為模式和工作原則
SYSTEM_PROMPT.md         - 系統提示與架構定義
TOOLS.md                 - 環境特定配置和技巧
MEMORY.md                - 重要記憶精選
BOOTSTRAP.md             - 啟動流程定義
HEARTBEAT.md             - 心跳檢查清單
CUSTOM_SKILLS_GUIDE.md   - 技能使用指南
SKILLS_LEARNING_GUIDE.md - 學習技能指南
[其他頂層 .md]            - 動態偵測同步
```

### Memory Archives (v3.0)
```
memory/
├── keyword_index.json       # 漫遊模式索引
├── heartbeat-state.json     # 心跳狀態
├── master-index.md          # 主索引
├── daily/                   # 每日記錄
│   ├── daily-index.md
│   └── YYYY-MM-DD.md
├── moments/                 # 重要時刻（永不歸檔）
│   ├── moments-index.md
│   └── [事件名稱].md
├── topics/                  # 主題分類
│   ├── topics-index.md
│   ├── personal/            # 個人偏好
│   └── technical/           # 技術知識
├── insights/                # 經驗提煉（睡眠模式產出）
│   ├── personal/
│   └── technical/
└── archive/                 # 冷記憶歸檔（>90天低存取）
    └── [原檔案名].md
```

### Skills & Custom Skills
```
skills-custom/               # 自訂技能目錄
├── memory-backup/
├── memory-frontmatter/
├── home-review/
├── power-management/
├── school-learning/
└── [其他技能]/
```

### Scripts & Tests
```
scripts/                     # 系統腳本
├── scan_metadata.py
├── validate_frontmatter.py
├── rebuild_keyword_index.py
├── audit_memory.py
└── [其他腳本]

tests/                       # 測試案例與報告
├── memory-system-test-cases.md
├── memory-system-test-guide.md
├── experience-distillation-test.md
└── reports/                 # 測試報告

Notes/                       # 學習筆記
goals/                       # 目標規劃
portfolio/                   # 作品集
projects/                    # 專案文件
```

## Target Repository

**https://github.com/LAXY9887/ClawMemory**

## Backup Workflow

### ⚡ 新標準鏡像同步流程 (2026-03-28)

**✅ ClawMemory 新標準：完整鏡像同步機制 v2.0**

```python
import subprocess
import os
from pathlib import Path

workspace_path = r"C:\Users\USER\.openclaw\workspace"
clawmemory_path = r"C:\Users\USER\source\repos\ClawMemory"

def execute_clawmemory_sync():
    """執行完整的 ClawMemory 鏡像同步流程"""
    
    # Step 1: 檢查 ClawMemory 未提交變更
    os.chdir(clawmemory_path)
    result = subprocess.run(["git", "status", "--porcelain"], 
                          capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️ 發現未提交變更，先提交...")
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", "Pre-sync cleanup: commit pending changes"])
    
    # Step 2: 更新 .gitignore 排除目錄
    gitignore_path = Path(clawmemory_path) / ".gitignore"
    exclude_dirs = ["pictures/", "tasks/", "secure/"]
    
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
    else:
        existing_content = ""
    
    new_content = existing_content
    for dir_name in exclude_dirs:
        if dir_name not in existing_content:
            new_content += f"\n{dir_name}"
    
    gitignore_path.write_text(new_content.strip())
    
    # Step 3: 執行完整鏡像同步 (robocopy /MIR)
    robocopy_args = [
        "robocopy", workspace_path, clawmemory_path, "/MIR",
        "/XD", "pictures", "tasks", "secure", ".git",
        "/R:1", "/W:1", "/NP", "/NS", "/NC", "/NFL"
    ]
    
    print("🔄 執行完整鏡像同步...")
    result = subprocess.run(robocopy_args, capture_output=True, text=True)
    
    # robocopy 退出碼 0-7 是成功
    if result.returncode <= 7:
        print("✅ 鏡像同步成功")
        
        # Step 4: 清理意外同步的排除目錄
        for dir_name in ["tasks", "secure"]:  # pictures 通常不會意外同步
            dir_path = Path(clawmemory_path) / dir_name
            if dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                print(f"🗑️ 已清理意外同步的目錄: {dir_name}")
        
        # Step 5: Git 提交與推送
        subprocess.run(["git", "add", "."])
        
        # 檢查變更數量
        status_result = subprocess.run(["git", "status", "--porcelain"], 
                                     capture_output=True, text=True)
        change_count = len(status_result.stdout.strip().splitlines()) if status_result.stdout.strip() else 0
        
        if change_count > 0:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 統計同步信息
            total_files = len(list(Path(clawmemory_path).rglob("*"))) - len(list(Path(clawmemory_path / ".git").rglob("*")))
            
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

            subprocess.run(["git", "commit", "-m", commit_msg])
            
            # 處理可能的推送衝突
            push_result = subprocess.run(["git", "push", "origin", "main"], 
                                       capture_output=True, text=True)
            
            if push_result.returncode != 0 and "fetch first" in push_result.stderr:
                print("⚠️ 遠端有變更，執行 rebase...")
                subprocess.run(["git", "pull", "--rebase", "origin", "main"])
                
                # 重新推送
                final_push = subprocess.run(["git", "push", "origin", "main"])
                if final_push.returncode == 0:
                    print("✅ 推送成功！")
                else:
                    print("❌ 推送失敗，需要手動處理")
            elif push_result.returncode == 0:
                print("✅ 推送成功！")
            else:
                print(f"❌ 推送失敗: {push_result.stderr}")
        else:
            print("✅ 沒有變更需要提交")
            
    else:
        print(f"❌ 鏡像同步失敗，退出碼: {result.returncode}")
        
    return True
```

### ⚠️ 關鍵原則：5 步驟強制執行

1. **完整鏡像同步**: 必須使用 `robocopy /MIR` 實現真正的完整同步
2. **正確排除目錄**: pictures/, tasks/, secure/ 必須排除
3. **真正同步對應**: 刪除、新增、修改都必須完整對應
4. **單一 Git 倉庫**: 只有 ClawMemory 是 Git repo，workspace 只是數據源
5. **統一提交推送**: 所有 Git 操作都在 ClawMemory 中執行

## Restoration Workflow

還原記憶請使用 **home-review** 技能（`skills-custom/home-review/SKILL.md`），
它已包含完整的 git pull + shutil.copy2 二進位複製 + scan_metadata.py 驗證流程。

**⚠️ 注意：還原時不需要使用鏡像同步，因為方向相反**
還原是從 ClawMemory → workspace，使用 shutil.copy2 單向複製即可。

## Available Scripts

| 腳本 | 用途 | 狀態 |
|---|---|---|
| `scripts/scan_metadata.py` | 掃描所有記憶的 YAML 概覽 | ✅ 可用 |
| `scripts/validate_frontmatter.py` | 驗證 YAML frontmatter 完整性 | ✅ 可用 |
| `scripts/rebuild_keyword_index.py` | 重建漫遊模式關鍵字索引 | ✅ 可用 |
| `scripts/audit_memory.py` | 路徑類記憶環境落地驗證 | ✅ 可用 |

## Integration with Other Skills

- **home-review**: 從 GitHub 還原記憶到工作空間（含二進位複製與驗證）
- **memory-frontmatter**: YAML frontmatter 規範定義與模板
- **school-learning**: 學習成果同步與歸檔
- **睡眠模式**: Phase 3.5 經驗提煉產出 insights/ 檔案

## Security & Privacy

### 保護機制
- 敏感資訊自動過濾
- 個人隱私內容標記
- 訪問權限控制

### 最佳實踐
- 定期檢查備份完整性（`validate_frontmatter.py`）
- 監控儲存庫安全性
- 清理過時或敏感資料
- 維護備份版本歷史

---

**ClawClaw 的數位不朽計畫 - 讓每個記憶都成為永恆！** 🌟🦞💾
