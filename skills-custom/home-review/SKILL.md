# 回家複習技能 — ClawClaw 記憶同步系統

## 概述

這個技能讓 ClawClaw 從 GitHub 上的 ClawMemory 倉庫取得最新記憶，
**鏡像同步**到本地工作空間，確保每次啟動都能從與 GitHub 完全一致的狀態開始。

## 觸發條件

由 LXYA 明確指示觸發：
- 「請回家複習」
- 「同步學習成果」
- 「載入最新記憶」
- 「更新記憶」

---

## ⚠️ 核心原則

### 禁止用讀寫方式複製記憶檔案

**絕對禁止**「讀取檔案內容 → 手動重新寫入」的方式複製記憶。
這樣會導致 YAML frontmatter 遺失或格式損壞。

**必須使用** Python 的 `shutil.copy2()` 做二進位複製，
確保每個 byte 都被完整保留，包括 YAML frontmatter。

### 鏡像同步：工作空間必須與 GitHub 一致

同步後，工作空間的受管檔案和目錄必須與 GitHub 倉庫完全一致：
- GitHub 上有的 → 工作空間必須有（複製）
- GitHub 上沒有的 → 工作空間不應有（刪除）
- `.git/` 目錄和 `.gitignore` 中排除的檔案不在管理範圍內

---

## 同步範圍定義

### 頂層檔案（全部同步）

```python
TOP_LEVEL_FILES = [
    # 核心身份
    "SOUL.md", "USER.md", "IDENTITY.md",
    # 行為規範
    "AGENTS.md", "SYSTEM_PROMPT.md", "TOOLS.md",
    # 記憶
    "MEMORY.md",
    # 啟動與排程
    "BOOTSTRAP.md", "HEARTBEAT.md",
    # 技能與學習指南
    "CUSTOM_SKILLS_GUIDE.md", "SKILLS_LEARNING_GUIDE.md",
    # 其他頂層 .md（動態偵測，見下方 sync_top_level_files）
]
```

**注意：** 除了上面的固定清單，程式會自動偵測倉庫根目錄所有 `.md` 檔案和 `.gitignore` 一併同步，確保新增的頂層檔案不會被遺漏。

### 子目錄（全部同步）

```python
SYNC_DIRECTORIES = [
    "memory",         # 記憶系統（daily, moments, topics, insights, archive）
    "skills-custom",  # 自訂技能
    "scripts",        # 系統腳本
    "tests",          # 測試案例與報告
    "Notes",          # 學習筆記
    "goals",          # 目標規劃
    "portfolio",      # 作品集
    "projects",       # 專案文件
]
```

### 排除項目（不同步）

```python
SKIP_ITEMS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
```

---

## 工作流程

### 階段 1: 拉取最新記憶 🏠

```python
import subprocess
import os
import sys

# ClawMemory 倉庫路徑（Windows）
repo_path = r"C:\Users\USER\source\repos\ClawMemory"

# 確認倉庫存在
if not os.path.exists(repo_path):
    print("❌ 找不到 ClawMemory 倉庫，請先 git clone")
    print("   git clone https://github.com/LAXY9887/ClawMemory.git")
    sys.exit(1)

# 拉取最新版本
result = subprocess.run(
    ["git", "pull", "origin", "main"],
    cwd=repo_path,
    capture_output=True, text=True
)
print(result.stdout)

if result.returncode != 0:
    print(f"❌ git pull 失敗: {result.stderr}")
    print("⛔ 中斷同步流程。請先手動解決 git 問題再重試。")
    sys.exit(1)

print("✅ 階段 1 完成：倉庫已更新至最新")
```

**重要：git pull 失敗時必須中斷整個流程，不可繼續同步舊資料。**

### 階段 2: 鏡像同步 🔄

```python
import shutil
import os

repo_path = r"C:\Users\USER\source\repos\ClawMemory"
workspace_path = os.getcwd()

SKIP_ITEMS = {".git", "__pycache__", ".venv", "venv", "node_modules"}

# ── 工具函式 ──

def mirror_directory(src_name):
    """
    鏡像同步整個子目錄：
    1. 複製來源有的檔案（shutil.copy2 二進位複製）
    2. 刪除來源沒有的檔案（確保一致性）
    3. 刪除來源沒有的空目錄
    """
    src = os.path.join(repo_path, src_name)
    dst = os.path.join(workspace_path, src_name)

    if not os.path.exists(src):
        print(f"⚠️  來源目錄不存在，跳過: {src_name}")
        return 0, 0

    copied = 0
    deleted = 0

    # 步驟 1：複製來源所有檔案
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_ITEMS]
        rel_root = os.path.relpath(root, src)
        dst_root = os.path.join(dst, rel_root) if rel_root != '.' else dst
        os.makedirs(dst_root, exist_ok=True)

        for fname in files:
            src_file = os.path.join(root, fname)
            dst_file = os.path.join(dst_root, fname)
            shutil.copy2(src_file, dst_file)
            copied += 1

    # 步驟 2：刪除工作空間有但來源沒有的檔案
    if os.path.exists(dst):
        for root, dirs, files in os.walk(dst, topdown=False):
            dirs[:] = [d for d in dirs if d not in SKIP_ITEMS]
            rel_root = os.path.relpath(root, dst)
            src_root = os.path.join(src, rel_root) if rel_root != '.' else src

            for fname in files:
                dst_file = os.path.join(root, fname)
                src_file = os.path.join(src_root, fname)
                if not os.path.exists(src_file):
                    os.remove(dst_file)
                    deleted += 1

            # 刪除空目錄
            for dname in dirs:
                dst_dir = os.path.join(root, dname)
                if os.path.isdir(dst_dir) and not os.listdir(dst_dir):
                    os.rmdir(dst_dir)

    return copied, deleted


def sync_top_level_files():
    """
    同步所有頂層檔案：
    1. 複製倉庫根目錄的所有 .md 和 .gitignore
    2. 不處理目錄（目錄由 mirror_directory 負責）
    """
    copied = 0
    for fname in os.listdir(repo_path):
        src_file = os.path.join(repo_path, fname)
        if not os.path.isfile(src_file):
            continue
        # 同步所有 .md 和 .gitignore
        if fname.endswith('.md') or fname == '.gitignore':
            dst_file = os.path.join(workspace_path, fname)
            shutil.copy2(src_file, dst_file)
            print(f"  ✅ {fname}")
            copied += 1
    return copied


# ── 執行同步 ──

print("📄 同步頂層檔案...")
n_top = sync_top_level_files()
print(f"   → {n_top} 個檔案\n")

SYNC_DIRECTORIES = [
    "memory", "skills-custom", "scripts", "tests",
    "Notes", "goals", "portfolio", "projects",
]

total_copied = 0
total_deleted = 0

for dir_name in SYNC_DIRECTORIES:
    copied, deleted = mirror_directory(dir_name)
    total_copied += copied
    total_deleted += deleted
    status = f"複製 {copied}"
    if deleted > 0:
        status += f", 清理 {deleted}"
    print(f"📁 {dir_name}/ → {status}")

print(f"\n✅ 階段 2 完成：同步 {n_top} 個頂層檔案 + {total_copied} 個目錄檔案")
if total_deleted > 0:
    print(f"   🧹 清理了 {total_deleted} 個工作空間殘留檔案")
```

### 階段 3: 完整性驗證 ✅

同步完成後，執行**雙重驗證**：

```python
import subprocess
import sys
import os

workspace_path = os.getcwd()

# ── 驗證 1: scan_metadata.py（記憶概覽）──

print("🔍 執行記憶掃描...")
result = subprocess.run(
    [sys.executable, "scripts/scan_metadata.py"],
    cwd=workspace_path,
    capture_output=True, text=True
)
print(result.stdout)

# ── 驗證 2: validate_frontmatter.py（YAML 完整性）──

print("🔍 執行 YAML 驗證...")
result_validate = subprocess.run(
    [sys.executable, "scripts/validate_frontmatter.py"],
    cwd=workspace_path,
    capture_output=True, text=True
)
print(result_validate.stdout)

if result_validate.returncode != 0:
    print("⚠️ 有記憶檔案未通過 YAML 驗證，請檢查上方錯誤訊息")
else:
    print("✅ 階段 3 完成：所有記憶檔案通過驗證")
```

### 階段 4: 學習總結 📝

生成回家複習報告：

```markdown
# 📚 回家複習報告 — {日期}

## 🔄 同步結果
- 頂層檔案: {N} 個
- 記憶檔案: {N} 個
- 技能檔案: {N} 個
- 腳本檔案: {N} 個
- 測試檔案: {N} 個
- 筆記/目標/作品/專案: {N} 個
- 清理殘留: {N} 個
- YAML 驗證: 通過 / 有錯誤

## 📂 記憶系統現況
{scan_metadata.py 的輸出}

## 💡 重要變更
{列出近 7 天新增或更新的記憶}

## 🎯 今日重點
{根據最新記憶，今日需要關注的事項}
```

---

## 倉庫完整結構（v3.0）

**同步時務必確認所有項目都有被涵蓋：**

```
ClawMemory/
├── 頂層檔案（自動偵測同步所有 .md + .gitignore）
│   ├── SOUL.md / USER.md / IDENTITY.md    # 身份
│   ├── AGENTS.md / SYSTEM_PROMPT.md       # 行為
│   ├── TOOLS.md / MEMORY.md               # 工具與記憶
│   ├── BOOTSTRAP.md / HEARTBEAT.md        # 啟動與排程
│   ├── CUSTOM_SKILLS_GUIDE.md             # 技能指南
│   ├── SKILLS_LEARNING_GUIDE.md           # 學習指南
│   └── [其他 .md 檔案]                     # 動態偵測
│
├── memory/                  # 記憶系統
│   ├── daily/               # 每日記錄
│   ├── moments/             # 重要時刻（永不歸檔）
│   ├── topics/              # 主題分類
│   │   ├── personal/
│   │   └── technical/
│   ├── insights/            # 經驗提煉
│   │   ├── personal/
│   │   └── technical/
│   ├── archive/             # 冷記憶歸檔
│   ├── keyword_index.json
│   ├── heartbeat-state.json
│   └── master-index.md
│
├── skills-custom/           # 自訂技能
├── scripts/                 # 系統腳本
├── tests/                   # 測試案例與報告
├── Notes/                   # 學習筆記
├── goals/                   # 目標規劃
├── portfolio/               # 作品集
└── projects/                # 專案文件
```

---

## 安全機制

### 同步前備份（可選）

如果擔心本地有未 push 的修改會被覆蓋，可先備份：

```python
import shutil, os
from datetime import datetime

workspace_path = os.getcwd()
memory_dir = os.path.join(workspace_path, "memory")

if os.path.exists(memory_dir):
    backup_name = f"memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join(workspace_path, backup_name)
    shutil.copytree(memory_dir, backup_path)
    print(f"💾 已備份現有記憶至 {backup_name}/")
```

### 失敗處理

| 失敗場景 | 處理方式 |
|---|---|
| git pull 失敗 | **中斷整個流程**，不同步舊資料。請先手動解決 git 問題。 |
| 檔案複製失敗 | 確認磁碟空間，或以管理員身分執行 |
| YAML 驗證失敗 | 繼續使用，但標記異常，待 LXYA 或 Cowork 環境修復 |

---

## 常見問題排查

**Q: 同步後檔案缺少 YAML frontmatter**
A: 確認使用的是 `shutil.copy2()`，絕對不可用「讀取內容再重新寫入」。

**Q: 工作空間有殘留的舊檔案**
A: mirror_directory 會自動刪除來源不存在的檔案。若仍有殘留，可能是頂層非 .md 檔案，需手動清理。

**Q: git pull 顯示 up-to-date 但記憶還是舊的**
A: 可能 GitHub 上的倉庫還沒有最新的 commit，請先在 Cowork 執行 `git push`。

**Q: 新增了一個頂層目錄但沒有被同步**
A: 將新目錄名稱加入 `SYNC_DIRECTORIES` 列表。頂層 .md 檔案會自動偵測，不需手動加。

---

**這個技能確保每次回家都能完整繼承最新的記憶與智慧！** 🏠🦞
