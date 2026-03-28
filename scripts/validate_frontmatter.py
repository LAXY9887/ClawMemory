#!/usr/bin/env python3
"""
validate_frontmatter.py - 驗證記憶檔案的 YAML frontmatter 完整性

功能：
  - 檢查所有記憶檔案是否具備 YAML frontmatter
  - 驗證必填欄位是否存在
  - 驗證欄位值是否符合規範（category, importance, confidence 等）
  - 對 insight 類別額外驗證 insight 專屬欄位
  - 報告缺失或不合規的欄位

使用方式：
  python scripts/validate_frontmatter.py                                # 驗證所有記憶
  python scripts/validate_frontmatter.py --file memory/daily/2026-03-26.md  # 驗證特定檔案
  python scripts/validate_frontmatter.py --fix                          # 自動補全缺失的選填欄位預設值
  python scripts/validate_frontmatter.py --format json                  # JSON 格式輸出
"""

import os
import sys
import json
import argparse
from datetime import date

# ── 重複使用 scan_metadata 的 YAML 解析器 ──────────────────

# 加入 scripts/ 到 path，讓 import 能找到 scan_metadata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_metadata import parse_yaml_frontmatter


# ── 規範定義 ──────────────────────────────────────────────

REQUIRED_FIELDS = ['topic', 'category', 'created']

RECOMMENDED_FIELDS = ['importance', 'importance_score', 'tags', 'summary']

SYSTEM_FIELDS = ['last_updated', 'access_count', 'last_accessed']

VALID_CATEGORIES = [
    'episode', 'milestone', 'knowledge', 'preference',
    'insight', 'index', 'project_summary'
]

VALID_IMPORTANCE = ['critical', 'high', 'medium', 'low']

VALID_CONFIDENCE = ['high', 'medium', 'low']

INSIGHT_REQUIRED_FIELDS = ['insight_type', 'status']

INSIGHT_RECOMMENDED_FIELDS = [
    'trigger', 'pattern', 'action', 'source_episodes',
    'confirmed_at', 'challenge_count'
]

VALID_INSIGHT_TYPES = ['how-to', 'pattern', 'preference', 'observation']

VALID_INSIGHT_STATUS = ['draft', 'confirmed']

SKIP_FILES = {
    'master-index.md', 'daily-index.md', 'moments-index.md',
    'topics-index.md', 'insights-index.md', '.gitkeep',
}

SKIP_DIRS = {'archive', '.git', '__pycache__'}


# ── 驗證邏輯 ──────────────────────────────────────────────


def validate_file(filepath, rel_path, meta, parse_error):
    """
    驗證單一檔案的 frontmatter，回傳驗證結果 dict。
    """
    result = {
        'path': rel_path,
        'errors': [],      # 嚴重問題（必填欄位缺失、值不合規）
        'warnings': [],    # 建議改善（推薦欄位缺失）
        'valid': True,
    }

    # 解析失敗
    if parse_error:
        result['errors'].append(f"YAML 解析失敗: {parse_error}")
        result['valid'] = False
        return result

    if meta is None:
        result['errors'].append("沒有 YAML frontmatter")
        result['valid'] = False
        return result

    # ── 必填欄位 ──
    for field in REQUIRED_FIELDS:
        if field not in meta or meta[field] is None:
            result['errors'].append(f"缺少必填欄位: {field}")
            result['valid'] = False

    # ── 值域檢查 ──
    category = meta.get('category')
    if category and category not in VALID_CATEGORIES:
        result['errors'].append(
            f"category 值不合規: '{category}'（允許: {', '.join(VALID_CATEGORIES)}）"
        )
        result['valid'] = False

    importance = meta.get('importance')
    if importance and importance not in VALID_IMPORTANCE:
        result['errors'].append(
            f"importance 值不合規: '{importance}'（允許: {', '.join(VALID_IMPORTANCE)}）"
        )
        result['valid'] = False

    confidence = meta.get('confidence')
    if confidence and confidence not in VALID_CONFIDENCE:
        result['warnings'].append(
            f"confidence 值不合規: '{confidence}'（允許: {', '.join(VALID_CONFIDENCE)}）"
        )

    # ── importance_score 範圍檢查 ──
    score = meta.get('importance_score')
    if score is not None:
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            result['warnings'].append(
                f"importance_score 應為 1-10 的數字，目前為: {score}"
            )

    # ── 推薦欄位 ──
    # index 類別不需要 importance_score
    skip_recommended = set()
    if category == 'index':
        skip_recommended.add('importance_score')

    for field in RECOMMENDED_FIELDS:
        if field in skip_recommended:
            continue
        if field not in meta or meta[field] is None:
            result['warnings'].append(f"建議填寫: {field}")

    # ── insight 類別專屬欄位 ──
    if category == 'insight':
        for field in INSIGHT_REQUIRED_FIELDS:
            if field not in meta or meta[field] is None:
                result['errors'].append(f"insight 缺少必要欄位: {field}")
                result['valid'] = False

        insight_type = meta.get('insight_type')
        if insight_type and insight_type not in VALID_INSIGHT_TYPES:
            result['errors'].append(
                f"insight_type 值不合規: '{insight_type}'（允許: {', '.join(VALID_INSIGHT_TYPES)}）"
            )
            result['valid'] = False

        status = meta.get('status')
        if status and status not in VALID_INSIGHT_STATUS:
            result['errors'].append(
                f"status 值不合規: '{status}'（允許: {', '.join(VALID_INSIGHT_STATUS)}）"
            )
            result['valid'] = False

        for field in INSIGHT_RECOMMENDED_FIELDS:
            if field not in meta:
                result['warnings'].append(f"insight 建議填寫: {field}")

    # ── created 格式 ──
    created = meta.get('created')
    if created:
        created_str = str(created).strip()
        valid_date = False
        for fmt in ('%Y-%m-%d', '%Y/%m/%d'):
            try:
                from datetime import datetime
                datetime.strptime(created_str, fmt)
                valid_date = True
                break
            except ValueError:
                continue
        if not valid_date:
            result['warnings'].append(
                f"created 日期格式不標準: '{created_str}'（建議 YYYY-MM-DD）"
            )

    return result


def scan_and_validate(base_dir, target_file=None):
    """
    掃描並驗證所有記憶檔案（或指定檔案）。
    """
    results = []

    if target_file:
        # 驗證特定檔案
        filepath = os.path.join(base_dir, target_file)
        if not os.path.exists(filepath):
            return [{'path': target_file, 'errors': ['檔案不存在'], 'warnings': [], 'valid': False}]
        meta, error = parse_yaml_frontmatter(filepath)
        results.append(validate_file(filepath, target_file, meta, error))
        return results

    # 掃描 memory/ 下所有 .md
    memory_dir = os.path.join(base_dir, 'memory')
    if not os.path.isdir(memory_dir):
        print(f"⚠️ 找不到 memory/ 目錄: {memory_dir}", file=sys.stderr)
        return results

    for root, dirs, files in os.walk(memory_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for fname in sorted(files):
            if not fname.endswith('.md'):
                continue
            if fname in SKIP_FILES:
                continue

            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, base_dir).replace('\\', '/')
            meta, error = parse_yaml_frontmatter(filepath)
            results.append(validate_file(filepath, rel_path, meta, error))

    return results


# ── 輸出 ──────────────────────────────────────────────────


def render_human(results):
    """人類可讀輸出"""
    lines = []
    total = len(results)
    valid_count = sum(1 for r in results if r['valid'])
    error_count = total - valid_count
    warning_count = sum(1 for r in results if r['warnings'])

    lines.append(f"✅ ClawClaw Frontmatter 驗證報告 — {date.today().strftime('%Y-%m-%d')}")
    lines.append("━" * 56)
    lines.append(f"  檔案總數: {total}  |  通過: {valid_count}  |  "
                 f"錯誤: {error_count}  |  有警告: {warning_count}")
    lines.append("")

    # 錯誤清單
    error_files = [r for r in results if not r['valid']]
    if error_files:
        lines.append("❌ 驗證失敗:")
        for r in error_files:
            lines.append(f"  {r['path']}")
            for err in r['errors']:
                lines.append(f"    ✗ {err}")
            for warn in r['warnings']:
                lines.append(f"    ⚠ {warn}")
        lines.append("")

    # 警告清單（通過但有警告）
    warn_files = [r for r in results if r['valid'] and r['warnings']]
    if warn_files:
        lines.append("⚠️  有改善建議:")
        for r in warn_files:
            lines.append(f"  {r['path']}")
            for warn in r['warnings']:
                lines.append(f"    ⚠ {warn}")
        lines.append("")

    if error_count == 0:
        lines.append("🎉 所有檔案通過 frontmatter 驗證！")
    else:
        lines.append(f"💡 共 {error_count} 個檔案需要修正。")

    lines.append("━" * 56)
    return '\n'.join(lines)


def render_json_output(results):
    """JSON 格式輸出"""
    total = len(results)
    output = {
        'scan_date': date.today().strftime('%Y-%m-%d'),
        'total_files': total,
        'valid_count': sum(1 for r in results if r['valid']),
        'error_count': sum(1 for r in results if not r['valid']),
        'warning_count': sum(1 for r in results if r['warnings']),
        'files': results,
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


# ── 主程式 ──────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description='驗證 ClawMemory 記憶檔案的 YAML frontmatter 完整性'
    )
    parser.add_argument('--file', type=str, default=None,
                        help='只驗證特定檔案（相對於 ClawMemory 根目錄的路徑）')
    parser.add_argument('--format', choices=['human', 'json'], default='human',
                        help='輸出格式：human（預設）或 json')
    parser.add_argument('--base', type=str, default=None,
                        help='ClawMemory 根目錄路徑（預設自動偵測）')
    args = parser.parse_args()

    # 自動偵測根目錄
    base_dir = args.base
    if not base_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)

    # 驗證
    results = scan_and_validate(base_dir, target_file=args.file)

    # 輸出
    if args.format == 'json':
        print(render_json_output(results))
    else:
        print(render_human(results))

    # exit code: 有錯誤就回傳 1
    has_errors = any(not r['valid'] for r in results)
    return 1 if has_errors else 0


if __name__ == '__main__':
    sys.exit(main())
