#!/usr/bin/env python3
"""
scan_metadata.py - 掃描記憶檔案的 YAML 元數據，生成索引摘要

功能：
  - 只讀取 YAML frontmatter（不讀全文，節省 Token）
  - 支援按 category、importance、tags 篩選
  - 支援找出冷記憶（長期未存取）
  - 支援輸出為人類可讀格式或 JSON

使用方式：
  python scan_metadata.py                          # 掃描全部
  python scan_metadata.py --importance high         # 按重要性篩選
  python scan_metadata.py --category episode        # 按類別篩選
  python scan_metadata.py --tag comfyui             # 按標籤篩選
  python scan_metadata.py --cold --days 90          # 找冷記憶
  python scan_metadata.py --format json             # JSON 輸出
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

try:
    import yaml
except ImportError:
    # 若沒有 PyYAML，用簡易解析
    yaml = None


def simple_yaml_parse(yaml_str):
    """簡易 YAML 解析（不依賴 PyYAML）"""
    result = {}
    for line in yaml_str.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()

            # 處理列表
            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].strip()
                if items:
                    result[key] = [i.strip().strip('"').strip("'") for i in items.split(',')]
                else:
                    result[key] = []
            # 處理布林
            elif value.lower() in ('true', 'false'):
                result[key] = value.lower() == 'true'
            # 處理 null
            elif value.lower() == 'null' or value == '':
                result[key] = None
            # 處理數字
            elif value.isdigit():
                result[key] = int(value)
            # 處理字串（去除引號）
            else:
                result[key] = value.strip('"').strip("'")
    return result


def extract_frontmatter(filepath):
    """從檔案中只提取 YAML frontmatter"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # 只讀前 2000 字元（YAML 不會更長）
    except Exception:
        return None

    content = content.strip()
    if not content.startswith('---'):
        return None

    second_sep = content.find('---', 3)
    if second_sep == -1:
        return None

    yaml_str = content[3:second_sep].strip()

    if yaml:
        try:
            return yaml.safe_load(yaml_str)
        except Exception:
            return simple_yaml_parse(yaml_str)
    else:
        return simple_yaml_parse(yaml_str)


def find_memory_files(base_dir):
    """尋找所有記憶 MD 檔案"""
    memory_path = os.path.join(base_dir, 'memory')
    files = []
    for root, dirs, filenames in os.walk(memory_path):
        for fname in sorted(filenames):
            if fname.endswith('.md'):
                files.append(os.path.join(root, fname))
    return files


def is_cold(metadata, days_threshold):
    """判斷記憶是否為冷記憶"""
    last_accessed = metadata.get('last_accessed')
    if last_accessed is None or last_accessed == 'null':
        # 從未被存取，用 created 日期判斷
        created = str(metadata.get('created', ''))
        if created:
            try:
                created_date = datetime.strptime(created, '%Y-%m-%d')
                return (datetime.now() - created_date).days > days_threshold
            except ValueError:
                pass
        return True  # 無法判斷日期，視為冷記憶

    try:
        last_date = datetime.strptime(str(last_accessed), '%Y-%m-%d')
        return (datetime.now() - last_date).days > days_threshold
    except ValueError:
        return True


def format_human_readable(entries):
    """格式化為人類可讀的摘要"""
    if not entries:
        print("  （無符合條件的記憶）")
        return

    # 按 importance 排序
    importance_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    entries.sort(key=lambda e: importance_order.get(e.get('importance', 'medium'), 2))

    for entry in entries:
        imp = entry.get('importance', 'medium')
        imp_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}.get(imp, '⚪')
        cat = entry.get('category', '?')
        topic = entry.get('topic', '未命名')
        summary = entry.get('summary', '')
        path = entry.get('_path', '')
        access = entry.get('access_count', 0)
        created = entry.get('created', '?')

        print(f"  {imp_icon} [{cat}] {topic}")
        if summary:
            print(f"     📝 {summary}")
        print(f"     📁 {path} | 建立: {created} | 存取: {access}次")
        tags = entry.get('tags', [])
        if tags:
            print(f"     🏷️  {', '.join(tags)}")
        print()


def main():
    parser = argparse.ArgumentParser(description='掃描記憶檔案的 YAML 元數據')
    parser.add_argument('--category', type=str, default=None, help='按類別篩選')
    parser.add_argument('--importance', type=str, default=None, help='按重要性篩選')
    parser.add_argument('--tag', type=str, default=None, help='按標籤篩選')
    parser.add_argument('--cold', action='store_true', help='只顯示冷記憶')
    parser.add_argument('--days', type=int, default=90, help='冷記憶閾值（天數，預設 90）')
    parser.add_argument('--format', type=str, default='human', choices=['human', 'json'],
                        help='輸出格式')
    parser.add_argument('--base', type=str, default=None, help='ClawMemory 根目錄路徑')
    args = parser.parse_args()

    # 自動偵測根目錄
    base_dir = args.base
    if not base_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    files = find_memory_files(base_dir)
    entries = []

    for filepath in files:
        metadata = extract_frontmatter(filepath)
        if metadata is None:
            continue

        # 加入路徑資訊
        metadata['_path'] = os.path.relpath(filepath, base_dir)

        # 篩選條件
        if args.category and metadata.get('category') != args.category:
            continue
        if args.importance and metadata.get('importance') != args.importance:
            continue
        if args.tag:
            tags = metadata.get('tags', []) or []
            if args.tag not in tags:
                continue
        if args.cold and not is_cold(metadata, args.days):
            continue

        entries.append(metadata)

    # 輸出
    if args.format == 'json':
        print(json.dumps(entries, ensure_ascii=False, indent=2, default=str))
    else:
        filter_desc = []
        if args.category:
            filter_desc.append(f"category={args.category}")
        if args.importance:
            filter_desc.append(f"importance={args.importance}")
        if args.tag:
            filter_desc.append(f"tag={args.tag}")
        if args.cold:
            filter_desc.append(f"cold>{args.days}days")

        filter_str = f" (篩選: {', '.join(filter_desc)})" if filter_desc else ""
        print(f"🧠 記憶元數據掃描{filter_str} — 共 {len(entries)} 筆\n")
        format_human_readable(entries)

        # 統計摘要
        cats = {}
        imps = {}
        for e in entries:
            c = e.get('category', 'unknown')
            i = e.get('importance', 'unknown')
            cats[c] = cats.get(c, 0) + 1
            imps[i] = imps.get(i, 0) + 1

        if entries:
            print(f"📊 統計: ", end='')
            print(' | '.join(f"{k}:{v}" for k, v in sorted(cats.items())))
            print(f"   重要性: ", end='')
            print(' | '.join(f"{k}:{v}" for k, v in sorted(imps.items())))


if __name__ == '__main__':
    main()
