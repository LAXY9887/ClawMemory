#!/usr/bin/env python3
"""
rebuild_keyword_index.py - 重建 keyword_index.json（睡眠模式 Phase 3 核心）

功能：
  - 掃描所有記憶檔案，提取關鍵詞並重建倒排索引
  - 從 daily 的 ## 閒聊紀錄 section 提取關鍵詞
  - 從 moments/、personal/、insights/ 提取關鍵詞
  - 冷啟動同義詞表（基於預設常見情緒/狀態詞彙）
  - 更新 metadata（last_rebuilt, total_entries, cumulative_importance）

使用方式：
  python rebuild_keyword_index.py                     # 完整重建
  python rebuild_keyword_index.py --dry-run            # 預覽模式，不寫入
  python rebuild_keyword_index.py --expand-synonyms    # 額外擴充同義詞表
  python rebuild_keyword_index.py --reset-cumulative   # 重置累積重要性分數

設計原則：
  - 「不準直接刪除，只能轉化」— 舊索引備份後再覆寫
  - 索引上限 200 條（超過時按 importance_score 淘汰最低分項目）
  - 同義詞表在冷啟動時自動填充常見中文情緒/狀態詞
"""

import os
import sys
import json
import re
import shutil
from datetime import datetime, timedelta

# ── 常數 ──────────────────────────────────────────────

INDEX_MAX_ENTRIES = 200  # 索引條目上限

# 冷啟動同義詞表：常見中文情緒/狀態/生活詞彙
DEFAULT_SYNONYMS = {
    "累": ["疲勞", "好累", "沒力", "加班", "爆肝", "疲倦", "累死"],
    "開心": ["高興", "快樂", "棒", "讚", "好耶", "開心", "爽"],
    "難過": ["傷心", "難受", "低落", "心情不好", "鬱悶", "沮喪"],
    "擔心": ["焦慮", "不安", "煩惱", "壓力", "煩", "緊張", "憂慮"],
    "生氣": ["氣", "火大", "不爽", "煩躁", "抓狂", "怒"],
    "無聊": ["沒事做", "發呆", "放空", "好閒", "閒到爆"],
    "忙": ["趕", "忙碌", "忙翻", "很多事", "事情很多", "沒空"],
    "生病": ["不舒服", "感冒", "頭痛", "肚子痛", "身體不好", "不太行"],
    "旅行": ["出去玩", "出門", "旅遊", "去哪玩", "放假去"],
    "吃": ["吃飯", "午餐", "晚餐", "早餐", "美食", "好吃", "聚餐"],
    "運動": ["健身", "跑步", "爬山", "游泳", "打球", "瑜伽"],
    "睡覺": ["睡", "睡不著", "失眠", "想睡", "熬夜", "晚睡", "補眠"],
    "工作": ["上班", "下班", "公司", "辦公", "專案", "project"],
    "學習": ["讀書", "看書", "課程", "教學", "研究", "study"],
    "天氣": ["下雨", "好熱", "好冷", "颱風", "晴天", "陰天"],
}

# 可索引的記憶路徑（漫遊模式 + 精準模式 insights/ 檢索）
INDEXABLE_PATHS = [
    "memory/moments/",
    "memory/topics/personal/",
    "memory/daily/",
    "memory/insights/",
]

# 不應索引的檔案名
SKIP_FILES = [
    "master-index.md",
    "daily-index.md",
    "moments-index.md",
    "topics-index.md",
]


# ── YAML 解析 ──────────────────────────────────────────

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


# ── 關鍵詞提取 ──────────────────────────────────────────

def extract_chat_section(filepath):
    """從 daily 檔案中提取 ## 閒聊紀錄 section 的內容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return ""

    # 找到 ## 閒聊紀錄 section
    pattern = r'## 閒聊紀錄\s*\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_full_content(filepath):
    """提取全文（去除 YAML frontmatter）"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return ""

    # 去除 frontmatter
    if content.strip().startswith('---'):
        second_sep = content.find('---', 3)
        if second_sep != -1:
            content = content[second_sep + 3:].strip()
    return content


def extract_keywords_from_metadata(tags, summary, synonyms_table):
    """
    從 YAML 元數據中提取高品質關鍵詞（不做暴力全文提取）。

    三個來源（品質從高到低）：
    1. YAML tags — 人工標註，直接採用
    2. YAML summary — 人工策展的一句話，提取有意義的詞
    3. 同義詞表反查 — 在 summary 中比對已知情緒/狀態詞

    注意：不做全文關鍵詞提取！
    Agent 在 S 觸發寫入時負責手動指定 keyword_index 的關鍵詞，
    本腳本只負責重建已有標註的索引。
    """
    keywords = set()

    # ── 層 1: YAML tags（最高品質）──
    if tags:
        for tag in tags:
            tag = str(tag).strip()
            if tag and len(tag) >= 1:
                keywords.add(tag)

    # ── 層 2: summary 提取 ──
    if summary:
        # 英文專有名詞（CamelCase 或全大寫）
        english_words = re.findall(r'\b[A-Z][a-zA-Z]{2,}(?:[A-Z][a-zA-Z]*)*\b', summary)
        english_words += re.findall(r'\b[A-Z]{2,}\b', summary)
        skip_english = {"LXYA", "YAML", "THE", "AND", "FOR", "JSON", "SOP"}
        for word in english_words:
            if len(word) >= 3 and word not in skip_english:
                keywords.add(word)

    # ── 層 3: 同義詞表反查 ──
    text_to_search = (summary or "") + " " + " ".join(str(t) for t in (tags or []))
    for root_word, syns in synonyms_table.items():
        if root_word in text_to_search:
            keywords.add(root_word)
        else:
            for syn in syns:
                if syn in text_to_search:
                    keywords.add(root_word)
                    break

    return keywords


def extract_keywords_from_chat_text(text, synonyms_table):
    """
    從閒聊紀錄內文中提取關鍵詞（僅用於 daily ## 閒聊紀錄 section）。

    比 metadata 提取多一層：在已知詞彙表中搜尋匹配。
    仍然不做暴力分詞。
    """
    keywords = set()

    # 同義詞表全量匹配
    for root_word, syns in synonyms_table.items():
        if root_word in text:
            keywords.add(root_word)
        else:
            for syn in syns:
                if syn in text:
                    keywords.add(root_word)
                    break

    # 英文專有名詞
    english_words = re.findall(r'\b[A-Z][a-zA-Z]{2,}(?:[A-Z][a-zA-Z]*)*\b', text)
    english_words += re.findall(r'\b[A-Z]{2,}\b', text)
    skip_english = {"LXYA", "YAML", "THE", "AND", "FOR"}
    for word in english_words:
        if len(word) >= 3 and word not in skip_english:
            keywords.add(word)

    return keywords


# ── 索引構建 ──────────────────────────────────────────

def build_index(base_dir):
    """
    掃描所有可索引的記憶檔案，構建 keyword_index。

    回傳：
    {
        "keyword_index": { "關鍵詞": [{ path, anchor, summary, importance_score, created }] },
        "stats": { "total_files_scanned": N, "total_entries": N, "new_keywords": N }
    }
    """
    keyword_index = {}
    stats = {"total_files_scanned": 0, "total_entries": 0, "new_keywords": 0}

    memory_path = os.path.join(base_dir, 'memory')

    for root, dirs, filenames in os.walk(memory_path):
        for fname in sorted(filenames):
            if not fname.endswith('.md'):
                continue
            if fname in SKIP_FILES:
                continue

            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, base_dir)

            # 檢查是否在可索引路徑內
            is_indexable = any(rel_path.replace('\\', '/').startswith(p) for p in INDEXABLE_PATHS)
            if not is_indexable:
                continue

            metadata = extract_frontmatter(filepath)
            if metadata is None:
                continue

            stats["total_files_scanned"] += 1

            # 根據檔案類型決定提取策略
            is_daily = "memory/daily/" in rel_path.replace('\\', '/')
            anchor = None

            if is_daily:
                # daily 檔案：只提取 ## 閒聊紀錄 section
                text = extract_chat_section(filepath)
                anchor = "閒聊紀錄"
                if not text:
                    continue  # 沒有閒聊紀錄 section，跳過
            else:
                # moments/ 和 personal/：提取全文
                text = extract_full_content(filepath)
                if not text:
                    continue

            # 取得 metadata 資訊
            summary = metadata.get('summary', '')
            importance_score = metadata.get('importance_score', 5)
            created = str(metadata.get('created', ''))
            tags = metadata.get('tags', []) or []

            # 關鍵詞提取（高品質來源優先）
            keywords = set()

            # 從 YAML metadata 提取（tags + summary + 同義詞反查）
            keywords.update(extract_keywords_from_metadata(tags, summary, DEFAULT_SYNONYMS))

            # 若是 daily 閒聊紀錄，額外從內文搜尋已知詞彙
            if is_daily and text:
                keywords.update(extract_keywords_from_chat_text(text, DEFAULT_SYNONYMS))

            # 將關鍵詞加入索引
            for kw in keywords:
                if kw not in keyword_index:
                    keyword_index[kw] = []
                    stats["new_keywords"] += 1

                # 避免重複（同一路徑+錨點不重複加入）
                existing = [e for e in keyword_index[kw]
                            if e["path"] == rel_path.replace('\\', '/') and e.get("anchor") == anchor]
                if not existing:
                    entry = {
                        "path": rel_path.replace('\\', '/'),
                        "anchor": anchor,
                        "summary": summary,
                        "importance_score": importance_score,
                        "created": created
                    }
                    keyword_index[kw].append(entry)
                    stats["total_entries"] += 1

    return keyword_index, stats


def prune_index(keyword_index, max_entries=INDEX_MAX_ENTRIES):
    """
    若索引條目超過上限，按 importance_score 淘汰最低分項目。
    回傳淘汰的關鍵詞數量。
    """
    total = sum(len(v) for v in keyword_index.values())
    if total <= max_entries:
        return 0

    # 把所有條目攤平，排序，取最低分的來刪
    all_entries = []
    for kw, entries in keyword_index.items():
        for entry in entries:
            all_entries.append((kw, entry, entry.get("importance_score", 0)))

    all_entries.sort(key=lambda x: x[2])

    to_remove = total - max_entries
    removed = 0

    for kw, entry, score in all_entries:
        if removed >= to_remove:
            break
        keyword_index[kw].remove(entry)
        if not keyword_index[kw]:
            del keyword_index[kw]
        removed += 1

    return removed


def merge_synonyms(existing_synonyms, default_synonyms):
    """合併同義詞表：保留既有的，補充缺少的"""
    merged = dict(existing_synonyms) if existing_synonyms else {}
    added = 0

    for root_word, syns in default_synonyms.items():
        if root_word not in merged:
            merged[root_word] = syns
            added += 1
        else:
            # 補充既有根詞缺少的同義詞
            existing_syns = set(merged[root_word])
            for syn in syns:
                if syn not in existing_syns:
                    merged[root_word].append(syn)

    return merged, added


# ── 主程式 ──────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description='重建 keyword_index.json（睡眠模式 Phase 3）')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不寫入檔案')
    parser.add_argument('--expand-synonyms', action='store_true', help='擴充同義詞表')
    parser.add_argument('--reset-cumulative', action='store_true', help='重置累積重要性分數')
    parser.add_argument('--base', type=str, default=None, help='ClawMemory 根目錄路徑')
    args = parser.parse_args()

    # 自動偵測根目錄
    base_dir = args.base
    if not base_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)  # scripts/ 的上一層

    index_path = os.path.join(base_dir, 'memory', 'keyword_index.json')

    # ── 讀取現有索引 ──
    existing_data = {}
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = {}

    existing_synonyms = existing_data.get("synonyms", {})
    existing_metadata = existing_data.get("metadata", {})
    old_cumulative = existing_metadata.get("cumulative_importance", 0)

    print("🌙 睡眠模式 Phase 3 — 記憶整合開始\n")
    print(f"📂 根目錄: {base_dir}")
    print(f"📇 索引路徑: {index_path}")
    print(f"📊 現有累積重要性: {old_cumulative}")
    print()

    # ── Phase 3a: 重建索引 ──
    print("━━ 3a. 重建關鍵詞索引 ━━")
    keyword_index, stats = build_index(base_dir)
    print(f"  掃描檔案: {stats['total_files_scanned']}")
    print(f"  提取關鍵詞: {stats['new_keywords']}")
    print(f"  索引條目: {stats['total_entries']}")

    # 裁剪超過上限的條目
    pruned = prune_index(keyword_index)
    if pruned > 0:
        print(f"  ⚠️ 裁剪 {pruned} 個低分條目（上限 {INDEX_MAX_ENTRIES}）")
    print()

    # ── Phase 3b: 同義詞維護 ──
    print("━━ 3b. 同義詞表維護 ━━")
    merged_synonyms, added_roots = merge_synonyms(existing_synonyms, DEFAULT_SYNONYMS)
    print(f"  同義詞根詞總數: {len(merged_synonyms)}")
    print(f"  本次新增根詞: {added_roots}")

    if args.expand_synonyms:
        print("  📝 同義詞擴充模式已啟用（冷啟動完成後可由 Agent 手動擴充）")
    print()

    # ── Phase 3c: 更新 metadata ──
    new_cumulative = 0 if args.reset_cumulative else old_cumulative
    final_total = sum(len(v) for v in keyword_index.values())

    new_metadata = {
        "last_rebuilt": datetime.now().strftime('%Y-%m-%d'),
        "total_entries": final_total,
        "cumulative_importance": new_cumulative
    }

    if args.reset_cumulative:
        print("━━ 3c. 累積重要性已重置 ━━")
        print(f"  {old_cumulative} → 0")
        print()

    # ── 組裝最終 JSON ──
    final_data = {
        "keyword_index": keyword_index,
        "synonyms": merged_synonyms,
        "metadata": new_metadata
    }

    # ── 輸出結果 ──
    if args.dry_run:
        print("🔍 預覽模式 — 以下是重建後的索引：")
        print()
        for kw in sorted(keyword_index.keys()):
            entries = keyword_index[kw]
            print(f"  「{kw}」→ {len(entries)} 筆")
            for e in entries:
                print(f"    📁 {e['path']}" + (f" #{e['anchor']}" if e['anchor'] else ""))
        print()
        print(f"📊 同義詞根詞: {list(merged_synonyms.keys())}")
        print("\n⚠️ 預覽模式，未寫入檔案")
    else:
        # 備份舊索引
        if os.path.exists(index_path):
            backup_path = index_path + ".bak"
            shutil.copy2(index_path, backup_path)
            print(f"💾 已備份舊索引 → {os.path.basename(backup_path)}")

        # 寫入新索引
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        print(f"✅ keyword_index.json 已重建")

    # ── 最終統計 ──
    print()
    print("━━ 重建完成 ━━")
    print(f"  📇 關鍵詞數: {len(keyword_index)}")
    print(f"  📝 索引條目: {final_total}")
    print(f"  🔤 同義詞根詞: {len(merged_synonyms)}")
    print(f"  📅 重建日期: {new_metadata['last_rebuilt']}")


if __name__ == '__main__':
    main()
