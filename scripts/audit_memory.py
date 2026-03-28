#!/usr/bin/env python3
"""
audit_memory.py - 記憶正確性審計腳本（睡眠模式 Phase 2 整合）

功能：
  - 掃描所有記憶的 YAML frontmatter
  - 對路徑類記憶執行環境落地驗證（os.path.exists）
  - 標記過時記憶（>90天未更新 + confidence=low → needs_review）
  - 偵測潛在衝突（同 topic 多檔案）
  - 輸出審計報告

使用方式：
  python audit_memory.py                    # 完整審計
  python audit_memory.py --dry-run          # 預覽模式，不修改檔案
  python audit_memory.py --grounding-only   # 只跑環境落地驗證
  python audit_memory.py --conflicts-only   # 只跑衝突偵測

設計原則：
  - 可擴充：新增驗證類型只需加一個 verify_* 函式 + tag 匹配規則
  - 不自行修改記憶內容 — 只修改 YAML 中的 confidence / verified_at / needs_review
  - 驗證失敗不刪除 — 標記後等 LXYA 確認
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime, timedelta

# ── 常數 ──────────────────────────────────────────

# 路徑類驗證的 tag 關鍵詞（匹配這些 tag 的記憶會被環境落地驗證）
PATH_TAGS = {"path", "路徑", "資料夾", "目錄", "folder", "directory", "安裝路徑"}

# 過時閾值
STALE_DAYS = 90


# ── YAML 解析（與 scan_metadata.py 共用邏輯）──────────

def simple_yaml_parse(yaml_str):
    """簡易 YAML 解析"""
    result = {}
    for line in yaml_str.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].strip()
                result[key] = [i.strip().strip('"').strip("'") for i in items.split(',')] if items else []
            elif value.lower() in ('true', 'false'):
                result[key] = value.lower() == 'true'
            elif value.lower() == 'null' or value == '':
                result[key] = None
            elif value.replace('.', '', 1).isdigit():
                result[key] = int(value) if '.' not in value else float(value)
            else:
                result[key] = value.strip('"').strip("'")
    return result


def extract_frontmatter(filepath):
    """提取 YAML frontmatter"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(2000)
    except Exception:
        return None

    content = content.strip()
    if not content.startswith('---'):
        return None
    second_sep = content.find('---', 3)
    if second_sep == -1:
        return None

    yaml_str = content[3:second_sep].strip()
    try:
        import yaml as pyyaml
        return pyyaml.safe_load(yaml_str)
    except (ImportError, Exception):
        return simple_yaml_parse(yaml_str)


def update_yaml_field(filepath, field, value):
    """更新 YAML frontmatter 中的單一欄位（不動其他內容）"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False

    if not content.strip().startswith('---'):
        return False

    second_sep = content.find('---', 3)
    if second_sep == -1:
        return False

    yaml_section = content[3:second_sep]
    rest = content[second_sep:]

    # 將值轉為 YAML 格式字串
    if isinstance(value, bool):
        val_str = 'true' if value else 'false'
    elif value is None:
        val_str = 'null'
    elif isinstance(value, str):
        val_str = f'"{value}"' if ' ' in value or not value else value
    else:
        val_str = str(value)

    # 嘗試替換已有欄位
    pattern = rf'^({field}:\s*)(.*)$'
    new_yaml, count = re.subn(pattern, rf'\g<1>{val_str}', yaml_section, flags=re.MULTILINE)

    if count == 0:
        # 欄位不存在，加在最後
        new_yaml = yaml_section.rstrip('\n') + f'\n{field}: {val_str}\n'

    new_content = '---' + new_yaml + rest

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception:
        return False


# ── 驗證函式 ──────────────────────────────────────────

def verify_path(memory_content):
    """
    從記憶內容中提取路徑，執行環境落地驗證。

    回傳: list of (path_found, exists_bool)
    """
    results = []

    # 提取常見路徑格式
    # Windows: C:\..., D:\..., E:\...
    win_paths = re.findall(r'[A-Z]:\\[^\s\n\r\t"\'`\]\)]+', memory_content)
    # Unix: /home/..., /usr/..., ~/...
    unix_paths = re.findall(r'(?:/[a-zA-Z0-9._-]+){2,}', memory_content)

    all_paths = set(win_paths + unix_paths)

    for p in all_paths:
        # 清理尾部標點
        p = p.rstrip('.,;:!?')
        if len(p) > 3:  # 避免太短的誤判
            exists = os.path.exists(p)
            results.append((p, exists))

    return results


def check_staleness(metadata):
    """檢查記憶是否過時"""
    last_updated = str(metadata.get('last_updated', '') or '')
    confidence = metadata.get('confidence', 'medium')

    if not last_updated:
        return True  # 無日期，視為過時

    try:
        updated_date = datetime.strptime(last_updated, '%Y-%m-%d')
        days_since = (datetime.now() - updated_date).days
        return days_since > STALE_DAYS and confidence != 'high'
    except ValueError:
        return True


def find_topic_conflicts(all_metadata):
    """偵測同一 topic 的多檔案衝突"""
    topic_map = {}
    conflicts = []

    for meta in all_metadata:
        topic = meta.get('topic', '')
        if not topic or meta.get('deprecated', False):
            continue

        if topic in topic_map:
            topic_map[topic].append(meta)
        else:
            topic_map[topic] = [meta]

    for topic, metas in topic_map.items():
        if len(metas) > 1:
            # 多個非 deprecated 的檔案共享同一 topic
            paths = [m.get('_path', '?') for m in metas]
            conflicts.append({
                "topic": topic,
                "files": paths,
                "count": len(metas)
            })

    return conflicts


# ── 主程式 ──────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='記憶正確性審計（睡眠模式 Phase 2）')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不修改檔案')
    parser.add_argument('--grounding-only', action='store_true', help='只跑環境落地驗證')
    parser.add_argument('--conflicts-only', action='store_true', help='只跑衝突偵測')
    parser.add_argument('--base', type=str, default=None, help='ClawMemory 根目錄路徑')
    args = parser.parse_args()

    # 自動偵測根目錄
    base_dir = args.base
    if not base_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)

    memory_path = os.path.join(base_dir, 'memory')

    print("🔒 記憶正確性審計開始\n")
    print(f"📂 根目錄: {base_dir}")
    if args.dry_run:
        print("⚠️  預覽模式 — 不修改任何檔案")
    print()

    # ── 收集所有記憶 ──
    all_metadata = []
    skip_files = {"master-index.md", "daily-index.md", "moments-index.md", "topics-index.md"}

    for root, dirs, filenames in os.walk(memory_path):
        # 跳過 archive 目錄
        if 'archive' in root:
            continue
        for fname in sorted(filenames):
            if not fname.endswith('.md') or fname in skip_files:
                continue
            filepath = os.path.join(root, fname)
            metadata = extract_frontmatter(filepath)
            if metadata:
                metadata['_path'] = os.path.relpath(filepath, base_dir)
                metadata['_filepath'] = filepath
                all_metadata.append(metadata)

    print(f"📊 掃描到 {len(all_metadata)} 個記憶檔案\n")

    # 統計
    stats = {
        "total": len(all_metadata),
        "grounding_passed": 0,
        "grounding_failed": 0,
        "grounding_skipped": 0,
        "stale_marked": 0,
        "conflicts_found": 0,
    }

    # ── 1. 環境落地驗證 ──
    if not args.conflicts_only:
        print("━━ 1. 環境落地驗證（路徑類）━━")
        today = datetime.now().strftime('%Y-%m-%d')

        for meta in all_metadata:
            tags = meta.get('tags', []) or []
            tags_lower = {str(t).lower() for t in tags}

            # 檢查是否有路徑類 tag
            has_path_tag = bool(tags_lower & PATH_TAGS)
            if not has_path_tag:
                stats["grounding_skipped"] += 1
                continue

            # 讀取檔案內容進行路徑提取
            filepath = meta['_filepath']
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                continue

            path_results = verify_path(content)
            if not path_results:
                stats["grounding_skipped"] += 1
                continue

            all_exist = all(exists for _, exists in path_results)
            any_failed = any(not exists for _, exists in path_results)

            if all_exist:
                stats["grounding_passed"] += 1
                print(f"  ✅ {meta['_path']}")
                for p, _ in path_results:
                    print(f"     📁 {p} — 存在")

                if not args.dry_run:
                    update_yaml_field(filepath, 'confidence', 'high')
                    update_yaml_field(filepath, 'verified_at', today)
                    update_yaml_field(filepath, 'needs_review', False)

            elif any_failed:
                stats["grounding_failed"] += 1
                print(f"  ❌ {meta['_path']}")
                for p, exists in path_results:
                    status = "存在" if exists else "不存在"
                    icon = "✅" if exists else "❌"
                    print(f"     {icon} {p} — {status}")

                if not args.dry_run:
                    update_yaml_field(filepath, 'needs_review', True)
                    update_yaml_field(filepath, 'verified_at', today)

        print()
        print(f"  通過: {stats['grounding_passed']} | 失敗: {stats['grounding_failed']} | 跳過: {stats['grounding_skipped']}")
        print()

    # ── 2. 過時標記 ──
    if not args.conflicts_only and not args.grounding_only:
        print("━━ 2. 過時記憶掃描 ━━")
        for meta in all_metadata:
            if check_staleness(meta):
                needs_review = meta.get('needs_review', False)
                if not needs_review:
                    stats["stale_marked"] += 1
                    print(f"  ⏰ {meta['_path']} — 超過 {STALE_DAYS} 天未更新")

                    if not args.dry_run:
                        update_yaml_field(meta['_filepath'], 'needs_review', True)

        if stats["stale_marked"] == 0:
            print("  （無過時記憶）")
        print()

    # ── 3. 衝突偵測 ──
    if not args.grounding_only:
        print("━━ 3. 衝突偵測 ━━")
        conflicts = find_topic_conflicts(all_metadata)
        stats["conflicts_found"] = len(conflicts)

        if conflicts:
            for c in conflicts:
                print(f"  ⚠️  Topic「{c['topic']}」有 {c['count']} 個檔案:")
                for f in c['files']:
                    print(f"     📁 {f}")
        else:
            print("  （無衝突）")
        print()

    # ── 審計摘要 ──
    print("━━ 審計完成 ━━")
    print(f"  📊 掃描: {stats['total']} 個記憶")
    if not args.conflicts_only:
        print(f"  ✅ 路徑驗證通過: {stats['grounding_passed']}")
        print(f"  ❌ 路徑驗證失敗: {stats['grounding_failed']}")
    if not args.conflicts_only and not args.grounding_only:
        print(f"  ⏰ 新標記過時: {stats['stale_marked']}")
    if not args.grounding_only:
        print(f"  ⚠️  潛在衝突: {stats['conflicts_found']}")

    # 回傳 JSON 供其他腳本使用
    if '--json' in sys.argv:
        print(json.dumps(stats, ensure_ascii=False))


if __name__ == '__main__':
    main()
