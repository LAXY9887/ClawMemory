#!/usr/bin/env python3
"""
validate_frontmatter.py - 驗證記憶檔案的 YAML Frontmatter 是否符合規範

功能：
  - 檢查所有記憶 MD 檔案是否有 YAML frontmatter
  - 驗證必填欄位是否存在
  - 驗證欄位值域是否正確
  - 輸出驗證報告

使用方式：
  python validate_frontmatter.py                          # 驗證全部
  python validate_frontmatter.py --file memory/daily/x.md # 驗證單一檔案
"""

import os
import re
import sys
import argparse
import yaml


# 規範定義
VALID_CATEGORIES = ['episode', 'milestone', 'knowledge', 'preference', 'insight', 'index', 'project_summary']
VALID_IMPORTANCE = ['critical', 'high', 'medium', 'low']
REQUIRED_FIELDS = ['topic', 'category', 'created']
RECOMMENDED_FIELDS = ['importance', 'tags', 'summary']


def parse_frontmatter(content):
    """解析 YAML frontmatter，回傳 (yaml_dict, error_msg)"""
    content = content.strip()
    if not content.startswith('---'):
        return None, "缺少 YAML frontmatter"

    # 找到第二個 ---
    second_sep = content.find('---', 3)
    if second_sep == -1:
        return None, "YAML frontmatter 未正確關閉（缺少結尾 ---）"

    yaml_str = content[3:second_sep].strip()
    try:
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            return None, "YAML 內容不是有效的字典格式"
        return data, None
    except yaml.YAMLError as e:
        return None, f"YAML 解析錯誤: {e}"


def validate_file(filepath, base_dir=None):
    """驗證單一檔案，回傳 (is_valid, errors, warnings)"""
    errors = []
    warnings = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"無法讀取檔案: {e}"], []

    data, parse_error = parse_frontmatter(content)
    if parse_error:
        return False, [parse_error], []

    # 驗證必填欄位
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"缺少必填欄位: {field}")

    # 驗證建議欄位
    for field in RECOMMENDED_FIELDS:
        if field not in data or data[field] is None or data[field] == '':
            warnings.append(f"建議填寫: {field}")

    # 驗證 category 值域
    if 'category' in data and data['category'] not in VALID_CATEGORIES:
        errors.append(f"category 值 '{data['category']}' 不在允許範圍: {VALID_CATEGORIES}")

    # 驗證 importance 值域
    if 'importance' in data and data['importance'] not in VALID_IMPORTANCE:
        errors.append(f"importance 值 '{data['importance']}' 不在允許範圍: {VALID_IMPORTANCE}")

    # 驗證 created 日期格式
    if 'created' in data:
        date_str = str(data['created'])
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            errors.append(f"created 日期格式錯誤: '{date_str}'（應為 YYYY-MM-DD）")

    # 驗證 tags 是列表
    if 'tags' in data and data['tags'] is not None:
        if not isinstance(data['tags'], list):
            errors.append(f"tags 應為列表格式，目前是: {type(data['tags']).__name__}")

    # 驗證 access_count 是數字
    if 'access_count' in data and data['access_count'] is not None:
        if not isinstance(data['access_count'], (int, float)):
            errors.append(f"access_count 應為數字，目前是: {type(data['access_count']).__name__}")

    # 驗證 deprecated 是布林
    if 'deprecated' in data and data['deprecated'] is not None:
        if not isinstance(data['deprecated'], bool):
            warnings.append(f"deprecated 應為布林值 (true/false)")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def find_memory_files(base_dir):
    """尋找所有記憶 MD 檔案"""
    memory_path = os.path.join(base_dir, 'memory')
    files = []
    for root, dirs, filenames in os.walk(memory_path):
        for fname in sorted(filenames):
            if fname.endswith('.md'):
                files.append(os.path.join(root, fname))
    return files


def main():
    parser = argparse.ArgumentParser(description='驗證記憶檔案的 YAML Frontmatter')
    parser.add_argument('--file', type=str, default=None, help='驗證特定檔案')
    parser.add_argument('--base', type=str, default=None, help='ClawMemory 根目錄路徑')
    parser.add_argument('--strict', action='store_true', help='嚴格模式（warnings 也視為錯誤）')
    args = parser.parse_args()

    # 自動偵測根目錄
    base_dir = args.base
    if not base_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))

    if args.file:
        filepath = os.path.join(base_dir, args.file) if not os.path.isabs(args.file) else args.file
        files = [filepath]
    else:
        files = find_memory_files(base_dir)

    if not files:
        print("⚠️ 找不到任何 .md 檔案")
        return

    print(f"🔍 驗證 {len(files)} 個記憶檔案...\n")

    total = len(files)
    passed = 0
    failed = 0
    warn_count = 0

    for filepath in files:
        rel_path = os.path.relpath(filepath, base_dir)
        is_valid, errors, warnings = validate_file(filepath, base_dir)

        if is_valid and not warnings:
            print(f"  ✅ {rel_path}")
            passed += 1
        elif is_valid and warnings:
            print(f"  ⚠️  {rel_path}")
            for w in warnings:
                print(f"      └─ {w}")
            if args.strict:
                failed += 1
            else:
                passed += 1
                warn_count += len(warnings)
        else:
            print(f"  ❌ {rel_path}")
            for e in errors:
                print(f"      └─ ❗ {e}")
            for w in warnings:
                print(f"      └─ ⚠️ {w}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"📊 驗證結果: {passed}/{total} 通過，{failed} 失敗")
    if warn_count > 0:
        print(f"   ⚠️ {warn_count} 個警告（建議修正）")

    if failed > 0:
        print(f"\n💡 使用 migrate_existing.py 來補上缺少的 YAML frontmatter")
        sys.exit(1)
    else:
        print(f"\n🎉 所有檔案驗證通過！")
        sys.exit(0)


if __name__ == '__main__':
    main()
