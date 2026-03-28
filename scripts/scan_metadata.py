#!/usr/bin/env python3
"""
scan_metadata.py - ClawClaw 記憶系統 YAML 前置資料掃描器

用途:
  - 掃描 memory/ 目錄下所有 .md 檔案的 YAML frontmatter
  - 提供全局記憶概覽，不讀取完整檔案內容
  - 支援分類篩選、標籤搜尋、新鮮度分析
  - Token 優化：只讀取 YAML 部分，避免全文載入

使用方式:
  python scripts/scan_metadata.py                    # 全量掃描
  python scripts/scan_metadata.py --category insight # 篩選類別
  python scripts/scan_metadata.py --tags comfyui     # 篩選標籤
  python scripts/scan_metadata.py --recent 7         # 近 7 天
  python scripts/scan_metadata.py --cold --days 90   # 90 天未存取
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import Counter

# 確保可以載入其他模組
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parent
MEMORY_DIR = WORKSPACE / "memory"

def extract_yaml_frontmatter(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    提取 YAML frontmatter，不讀取完整檔案。
    
    Args:
        file_path: .md 檔案路徑
        
    Returns:
        YAML frontmatter 字典，如果解析失敗返回 None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 檢查是否以 --- 開始
        if not content.startswith('---'):
            return None
            
        # 找到第二個 --- 的位置
        parts = content.split('---', 2)
        if len(parts) < 3:
            return None
            
        yaml_content = parts[1].strip()
        
        # 解析 YAML，處理路徑中的反斜線
        yaml_content = yaml_content.replace('\\', '/')
        metadata = yaml.safe_load(yaml_content)
        
        # 添加檔案資訊
        metadata['_file_path'] = str(file_path.relative_to(WORKSPACE))
        metadata['_file_size'] = file_path.stat().st_size
        metadata['_modified'] = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d')
        
        return metadata
        
    except Exception as e:
        print(f"⚠️ 解析錯誤 {file_path.name}: {e}", file=sys.stderr)
        return None

def scan_memory_files(
    category_filter: Optional[str] = None,
    tags_filter: Optional[List[str]] = None,
    recent_days: Optional[int] = None,
    show_cold: bool = False,
    cold_days: int = 90
) -> List[Dict[str, Any]]:
    """
    掃描記憶檔案的 YAML frontmatter。
    
    Args:
        category_filter: 篩選特定類別 (episode, milestone, etc.)
        tags_filter: 篩選包含指定標籤的檔案
        recent_days: 只顯示近 N 天的檔案
        show_cold: 顯示冷記憶 (超過 cold_days 未存取)
        cold_days: 冷記憶天數閾值
        
    Returns:
        記憶檔案 metadata 列表
    """
    if not MEMORY_DIR.exists():
        print(f"❌ 記憶目錄不存在: {MEMORY_DIR}")
        return []
    
    memories = []
    parse_errors = 0
    
    # 遞迴掃描所有 .md 檔案
    for md_file in MEMORY_DIR.rglob("*.md"):
        metadata = extract_yaml_frontmatter(md_file)
        
        if metadata is None:
            parse_errors += 1
            continue
            
        # 套用篩選條件
        if category_filter and metadata.get('category') != category_filter:
            continue
            
        if tags_filter:
            file_tags = metadata.get('tags', [])
            if not any(tag in file_tags for tag in tags_filter):
                continue
                
        if recent_days:
            created = metadata.get('created')
            if created:
                try:
                    created_date = datetime.strptime(str(created), '%Y-%m-%d')
                    cutoff = datetime.now() - timedelta(days=recent_days)
                    if created_date < cutoff:
                        continue
                except:
                    pass
                    
        if show_cold:
            last_accessed = metadata.get('last_accessed')
            if last_accessed:
                try:
                    access_date = datetime.strptime(str(last_accessed), '%Y-%m-%d')
                    cutoff = datetime.now() - timedelta(days=cold_days)
                    if access_date >= cutoff:
                        continue
                except:
                    pass
            else:
                # 沒有存取記錄的也算冷記憶
                created = metadata.get('created')
                if created:
                    try:
                        created_date = datetime.strptime(str(created), '%Y-%m-%d')
                        cutoff = datetime.now() - timedelta(days=cold_days)
                        if created_date >= cutoff:
                            continue
                    except:
                        pass
        
        memories.append(metadata)
    
    return memories

def generate_overview_report(memories: List[Dict[str, Any]]) -> str:
    """
    生成記憶系統概覽報告。
    
    Args:
        memories: 記憶檔案 metadata 列表
        
    Returns:
        格式化的概覽報告
    """
    if not memories:
        return "📊 ClawClaw 記憶系統概覽 — 無記憶檔案"
    
    # 基本統計
    total_count = len(memories)
    
    # 類別分佈
    categories = Counter(m.get('category', 'unknown') for m in memories)
    
    # 重要性分佈
    importance_levels = Counter(m.get('importance', 'unknown') for m in memories)
    
    # 需要審核的檔案
    needs_review = sum(1 for m in memories if m.get('needs_review', False))
    
    # 近期新增 (7天內)
    cutoff_date = datetime.now() - timedelta(days=7)
    recent_memories = []
    
    for m in memories:
        created = m.get('created')
        if created:
            try:
                created_date = datetime.strptime(str(created), '%Y-%m-%d')
                if created_date >= cutoff_date:
                    recent_memories.append(m)
            except:
                pass
    
    # 冷記憶 (90天未存取)
    cold_cutoff = datetime.now() - timedelta(days=90)
    cold_memories = 0
    
    for m in memories:
        last_accessed = m.get('last_accessed')
        if last_accessed:
            try:
                access_date = datetime.strptime(str(last_accessed), '%Y-%m-%d')
                if access_date < cold_cutoff:
                    cold_memories += 1
            except:
                pass
        else:
            # 沒有存取記錄，檢查建立日期
            created = m.get('created')
            if created:
                try:
                    created_date = datetime.strptime(str(created), '%Y-%m-%d')
                    if created_date < cold_cutoff:
                        cold_memories += 1
                except:
                    pass
    
    # 生成報告
    today = datetime.now().strftime('%Y-%m-%d')
    
    report = f"""📊 ClawClaw 記憶系統概覽 — {today}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  總記憶數: {total_count}  |  解析錯誤: 0  |  需要審核: {needs_review}  |  冷記憶: {cold_memories}

📂 類別分佈:"""
    
    # 類別分佈圖表
    max_count = max(categories.values()) if categories else 0
    for category, count in sorted(categories.items()):
        bar_length = int((count / max_count) * 15) if max_count > 0 else 0
        bar = "█" * bar_length
        report += f"\n  {category:<15}: {bar} {count}"
    
    # 重要性分佈
    if importance_levels:
        report += "\n\n⭐ 重要性分佈:"
        for level in ['critical', 'high', 'medium', 'low']:
            count = importance_levels.get(level, 0)
            if count > 0:
                report += f"\n  {level:<8}  : {count}"
    
    # 近期新增
    if recent_memories:
        report += f"\n\n🆕 近 7 天新增:"
        # 按日期分組
        by_date = {}
        for m in recent_memories:
            created = str(m.get('created', ''))
            if created not in by_date:
                by_date[created] = []
            by_date[created].append(m)
        
        # 按日期排序顯示
        for date in sorted(by_date.keys(), reverse=True):
            for m in by_date[date]:
                file_path = m.get('_file_path', '')
                topic = m.get('topic', '未命名記憶')
                report += f"\n  {date}  {file_path}"
                report += f"\n             └─ {topic}"
    
    report += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return report

def main():
    """主要執行函數"""
    parser = argparse.ArgumentParser(description='ClawClaw 記憶系統 YAML frontmatter 掃描器')
    
    parser.add_argument('--category', type=str, 
                       help='篩選類別 (episode, milestone, knowledge, preference, insight, etc.)')
    parser.add_argument('--tags', type=str, nargs='+',
                       help='篩選標籤 (可多個)')
    parser.add_argument('--recent', type=int,
                       help='只顯示近 N 天新增的記憶')
    parser.add_argument('--cold', action='store_true',
                       help='顯示冷記憶 (長時間未存取)')
    parser.add_argument('--days', type=int, default=90,
                       help='冷記憶天數閾值 (預設 90 天)')
    parser.add_argument('--json', action='store_true',
                       help='輸出 JSON 格式 (供程式使用)')
    
    args = parser.parse_args()
    
    # 掃描記憶檔案
    memories = scan_memory_files(
        category_filter=args.category,
        tags_filter=args.tags,
        recent_days=args.recent,
        show_cold=args.cold,
        cold_days=args.days
    )
    
    if args.json:
        # JSON 輸出 (供程式使用)
        import json
        print(json.dumps(memories, ensure_ascii=False, indent=2, default=str))
    else:
        # 人類可讀的概覽報告
        report = generate_overview_report(memories)
        print(report)

if __name__ == "__main__":
    main()