#!/usr/bin/env python3
"""
migrate_existing.py - 為現有記憶 MD 檔案補上 YAML Frontmatter

功能：
  - 掃描 memory/ 底下所有 .md 檔案
  - 根據路徑與內容自動推斷元數據
  - 在檔案頂部插入 YAML frontmatter
  - 支援 --dry-run 預覽模式

使用方式：
  python migrate_existing.py --dry-run          # 預覽，不修改
  python migrate_existing.py                     # 正式遷移
  python migrate_existing.py --path memory/daily # 只遷移特定資料夾
"""

import os
import re
import sys
import argparse
from datetime import datetime


def detect_category(filepath):
    """根據檔案路徑推斷記憶類別"""
    if filepath.endswith('-index.md') or filepath.endswith('master-index.md'):
        return 'index'
    if '/daily/' in filepath:
        if 'summary' in filepath.lower() or 'project' in filepath.lower():
            return 'project_summary'
        return 'episode'
    if '/moments/' in filepath:
        return 'milestone'
    if '/topics/technical/' in filepath:
        return 'knowledge'
    if '/topics/personal/' in filepath:
        return 'preference'
    if '/insights/' in filepath:
        return 'insight'
    return 'episode'


def detect_importance(category):
    """根據類別設定預設重要性"""
    importance_map = {
        'index': 'low',
        'episode': 'medium',
        'project_summary': 'medium',
        'milestone': 'high',
        'knowledge': 'medium',
        'preference': 'high',
        'insight': 'high',
    }
    return importance_map.get(category, 'medium')


def extract_date_from_file(filepath, content):
    """從檔名或內容提取日期"""
    # 嘗試從檔名提取 (YYYY-MM-DD)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(filepath))
    if date_match:
        return date_match.group(1)

    # 嘗試從內容提取 **時間**: YYYY-MM-DD
    time_match = re.search(r'\*\*時間\*\*:\s*(?:推測\s*)?(\d{4}-\d{2}-\d{2})', content)
    if time_match:
        return time_match.group(1)

    # 嘗試從內容提取任何 YYYY-MM-DD
    any_date = re.search(r'(\d{4}-\d{2}-\d{2})', content)
    if any_date:
        return any_date.group(1)

    # 最後回退到檔案修改時間
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')


def extract_topic(filepath, content):
    """從檔案標題或檔名提取主題"""
    # 嘗試從第一個 # 標題提取
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # 清理掉日期前綴
        title = re.sub(r'^\d{4}-\d{2}-\d{2}\s*[-—]\s*', '', title)
        # 截斷過長的標題
        if len(title) > 40:
            title = title[:40] + '...'
        return title

    # 回退到檔名
    name = os.path.splitext(os.path.basename(filepath))[0]
    return name.replace('-', ' ').replace('_', ' ')


def extract_tags(filepath, content, category):
    """從內容和路徑推斷標籤"""
    tags = []

    # 根據路徑加入基本標籤
    if '/technical/' in filepath:
        tags.append('technical')
    if '/personal/' in filepath:
        tags.append('personal')

    # 根據內容關鍵字加入標籤
    keyword_tags = {
        'ComfyUI': 'comfyui',
        'Ollama': 'ollama',
        'Git': 'git',
        'GitHub': 'github',
        'Telegram': 'telegram',
        'LoRA': 'lora',
        'OpenClaw': 'openclaw',
        '記憶': 'memory',
        '備份': 'backup',
        '技能': 'skill',
    }

    for keyword, tag in keyword_tags.items():
        if keyword.lower() in content.lower() and tag not in tags:
            tags.append(tag)

    return tags[:5]  # 最多 5 個標籤


def extract_summary(content):
    """從內容提取摘要（取第一個非標題、非空的段落）"""
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        # 跳過空行、標題、分隔線
        if not line or line.startswith('#') or line.startswith('---') or line.startswith('**時間'):
            continue
        # 跳過 emoji 開頭的裝飾行
        if line.startswith('>'):
            clean = line.lstrip('> ').strip()
            if len(clean) > 10:
                return clean[:80]
            continue
        # 取得有意義的第一行
        if len(line) > 10:
            return line[:80]

    return ""


def has_frontmatter(content):
    """檢查檔案是否已有 YAML frontmatter"""
    return content.strip().startswith('---')


def build_yaml(filepath, content, category):
    """根據推斷的元數據建構 YAML frontmatter"""
    date = extract_date_from_file(filepath, content)
    topic = extract_topic(filepath, content)
    importance = detect_importance(category)
    tags = extract_tags(filepath, content, category)
    summary = extract_summary(content)

    # 建構 prev_event（僅 daily 類別）
    prev_event = 'null'
    if category == 'episode':
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(filepath))
        if date_match:
            try:
                current_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                from datetime import timedelta
                prev_date = current_date - timedelta(days=1)
                prev_path = f"memory/daily/{prev_date.strftime('%Y-%m-%d')}.md"
                # 檢查前一天檔案是否存在
                base_dir = filepath
                for _ in range(3):  # 往上走到 memory 的父目錄
                    base_dir = os.path.dirname(base_dir)
                full_prev = os.path.join(base_dir, prev_path)
                if os.path.exists(full_prev):
                    prev_event = prev_path
            except (ValueError, Exception):
                pass

    # 格式化 tags
    if tags:
        tags_str = '[' + ', '.join(tags) + ']'
    else:
        tags_str = '[]'

    # 索引檔案用精簡 YAML
    if category == 'index':
        yaml = f"""---
topic: "{topic}"
category: index
created: {date}
importance: low
last_updated: {date}
---"""
        return yaml

    # 完整 YAML
    yaml = f"""---
topic: "{topic}"
category: {category}
created: {date}
importance: {importance}
tags: {tags_str}
summary: "{summary}"
last_updated: {date}
access_count: 0
last_accessed: null"""

    if prev_event != 'null':
        yaml += f'\nprev_event: {prev_event}'

    yaml += '\n---'
    return yaml


def migrate_file(filepath, dry_run=False):
    """為單一檔案加入 YAML frontmatter"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if has_frontmatter(content):
        return None, "已有 YAML，跳過"

    category = detect_category(filepath)
    yaml = build_yaml(filepath, content, category)

    if dry_run:
        return yaml, f"[DRY RUN] 將加入 YAML (category={category})"

    # 寫入檔案
    new_content = yaml + '\n\n' + content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return yaml, f"✅ 已加入 YAML (category={category})"


def find_memory_files(base_path, target_path=None):
    """尋找所有需要遷移的 MD 檔案"""
    search_path = target_path or os.path.join(base_path, 'memory')
    files = []

    for root, dirs, filenames in os.walk(search_path):
        for fname in sorted(filenames):
            if fname.endswith('.md'):
                files.append(os.path.join(root, fname))

    return files


def main():
    parser = argparse.ArgumentParser(description='為現有記憶 MD 檔案補上 YAML Frontmatter')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不修改檔案')
    parser.add_argument('--path', type=str, default=None, help='只遷移特定資料夾路徑')
    parser.add_argument('--base', type=str, default=None, help='ClawMemory 根目錄路徑')
    args = parser.parse_args()

    # 自動偵測根目錄
    base_dir = args.base
    if not base_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 從 skills-custom/memory-frontmatter/scripts/ 往上走
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    target = os.path.join(base_dir, args.path) if args.path else None
    files = find_memory_files(base_dir, target)

    if not files:
        print("⚠️ 找不到任何 .md 檔案")
        return

    print(f"{'🔍 [DRY RUN] ' if args.dry_run else '🚀 '}開始遷移 {len(files)} 個檔案...\n")

    migrated = 0
    skipped = 0

    for filepath in files:
        rel_path = os.path.relpath(filepath, base_dir)
        yaml, message = migrate_file(filepath, dry_run=args.dry_run)

        if yaml is None:
            print(f"  ⏭️  {rel_path} — {message}")
            skipped += 1
        else:
            print(f"  {'📋' if args.dry_run else '✅'} {rel_path} — {message}")
            if args.dry_run:
                # 在 dry-run 時顯示前幾行 YAML
                preview = '\n'.join(yaml.split('\n')[:5])
                print(f"      {preview}")
                print(f"      ...")
            migrated += 1

    print(f"\n{'📊 預覽' if args.dry_run else '📊 結果'}：遷移 {migrated} 個，跳過 {skipped} 個")

    if args.dry_run:
        print("\n💡 確認無誤後，移除 --dry-run 執行正式遷移")


if __name__ == '__main__':
    main()
