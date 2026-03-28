---
name: auto-memory
description: Intelligent memory management system that automatically detects and records important moments, conversations, decisions, and learnings. Use when: (1) During meaningful conversations that should be preserved, (2) After solving problems or making discoveries, (3) When users share preferences or personal information, (4) When establishing new goals or plans, (5) During any interaction that would be valuable to remember across sessions. Automatically manages hierarchical memory structure with indexes and small files for efficient retrieval.
---

# Auto-Memory: Intelligent Memory System

智能記憶管理系統，自動偵測並記錄重要時刻、對話、決策和學習成果。

## Core Function

This skill enables proactive memory management through:

1. **Real-time importance detection** - Automatically identify moments worth remembering
2. **Hierarchical memory structure** - Organize memories using indexes and small files
3. **Smart categorization** - Sort memories by type, importance, and relationship
4. **Efficient retrieval** - Quick access to past conversations and decisions

## When to Trigger

Automatically activate during conversations containing:

- Personal preferences, opinions, or important information about the user
- Problem-solving breakthroughs and technical discoveries  
- Goal setting, planning, or important decisions
- Meaningful interpersonal moments or emotional exchanges
- New knowledge that enhances future assistance
- Workflow improvements or process optimizations
- Important instructions or behavioral guidelines

## Memory Architecture

### Primary Structure
```
memory/
├── master-index.md          # Top-level navigation
├── daily/                  # Daily chronological logs
│   ├── 2026-03-25.md
│   └── daily-index.md
├── topics/                 # Thematic organization
│   ├── personal/           # User preferences & info
│   ├── technical/          # Discoveries & solutions
│   ├── goals/              # Plans & objectives
│   └── topics-index.md
└── moments/                # Special memorable interactions
    ├── first-conversation.md
    ├── major-breakthroughs.md
    └── moments-index.md
```

### Scalability Pattern
When files become numerous (>20 in any directory):
- Create sub-indexes (e.g., `technical-index.md` → `ai-systems/`, `web-dev/`)
- Maintain master index pointing to sub-indexes
- Keep individual files small and focused

## Usage Workflow

### 1. Automatic Detection
Monitor conversations for memory-worthy content:
- References: `scripts/importance_detector.py`
- Decision trees: `references/memory-triggers.md`

### 2. Smart Categorization  
Determine appropriate memory location:
- Daily chronological record
- Thematic filing by topic
- Special moments collection

### 3. Index Management
Update relevant indexes:
- Add entry to master-index.md
- Update topic/daily indexes as needed
- Maintain cross-references

### 4. Memory Maintenance
Periodically review and organize:
- Consolidate related memories
- Archive old daily logs
- Update index structure as needed

## Memory Types

### Daily Logs (`daily/`)
Chronological record of each day's events:
- Conversations and interactions
- Tasks completed and problems solved
- Important realizations or learnings
- Cross-references to topic files

### Topic Collections (`topics/`)
Thematic organization by subject:
- **Personal**: User preferences, habits, relationships
- **Technical**: Discoveries, solutions, tools learned
- **Goals**: Plans, objectives, progress tracking
- **Workflow**: Process improvements, efficiency gains

### Special Moments (`moments/`)
Particularly meaningful interactions:
- First conversations and introductions
- Major breakthroughs and "aha" moments
- Emotional or personally significant exchanges
- Milestone achievements

## Implementation Guidelines

### Writing Style
- Use clear, searchable headings
- Include context and emotional tone
- Add timestamps for chronological reference
- Link related memories across files

### File Size Management
- Keep individual files under 500 lines
- Split large topics into focused subtopics
- Use descriptive filenames for easy identification
- Maintain consistent formatting

### Index Maintenance
- Update indexes immediately after recording
- Include brief descriptions in index entries
- Maintain chronological and thematic cross-references
- Regular cleanup and reorganization

## Scripts and Tools

See `scripts/` directory for automation tools:
- `importance_detector.py` - Analyze conversation importance
- `memory_organizer.py` - Maintain index structure  
- `memory_search.py` - Advanced memory retrieval
- `archive_manager.py` - Organize old memories

See `references/` directory for detailed guides:
- `memory-triggers.md` - Comprehensive importance criteria
- `organization-patterns.md` - File structure best practices
- `index-templates.md` - Standard index formats

## Benefits

- **No lost conversations** - Important moments preserved automatically
- **Better continuity** - Rich context across session restarts  
- **Efficient retrieval** - Hierarchical structure enables quick access
- **Scalable growth** - Index system handles expanding memory base
- **Personal connection** - Deeper understanding through preserved interactions