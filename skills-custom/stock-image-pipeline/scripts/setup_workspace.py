"""
setup_workspace.py — 初始化 workspace 和 memory 目錄結構

使用方式:
  python scripts/setup_workspace.py

建立目錄:
  ~/.openclaw/workspace/skills-custom/stock-image-pipeline/pending/
  ~/.openclaw/workspace/skills-custom/stock-image-pipeline/uploaded/
  ~/.openclaw/workspace/skills-custom/stock-image-pipeline/rejected/
  ~/.openclaw/workspace/skills-custom/stock-image-pipeline/briefs/
  ~/.openclaw/workspace/skills-custom/stock-image-pipeline/temp/
  ~/.openclaw/memory/metrics/
  ~/.openclaw/memory/metrics/weekly/
  ~/.openclaw/memory/metrics/archive/
  ~/.openclaw/memory/insights/
  ~/.openclaw/memory/daily/
"""

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

def main():
    # 讀取 schedule.json
    try:
        with open(CONFIG_DIR / "schedule.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ 無法讀取 schedule.json: {e}")
        return

    ws_config = config.get("workspace", {})
    base = Path(ws_config.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")).expanduser()

    # Workspace 子目錄
    ws_dirs = [
        ws_config.get("pending_dir", "pending"),
        ws_config.get("uploaded_dir", "uploaded"),
        ws_config.get("rejected_dir", "rejected"),
        ws_config.get("briefs_dir", "briefs"),
        ws_config.get("temp_dir", "temp"),
    ]
    for d in ws_dirs:
        path = base / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {path}")

    # Stock Pipeline Memory 目錄 (整合到 workspace)
    memory_base = base / ".." / ".." / "memory" / "stock-pipeline"
    mem_dirs = [
        "daily",
        "metrics", 
        "metrics/weekly",
        "metrics/archive",
        "insights",
    ]
    for d in mem_dirs:
        path = memory_base / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {path}")

    # prompt_history.json (空初始化)
    history_path = memory_base / "metrics" / "prompt_history.json"
    if not history_path.exists():
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        print(f"  ✅ {history_path} (空初始化)")

    print("\n🎉 Workspace 初始化完成！")


if __name__ == "__main__":
    main()

