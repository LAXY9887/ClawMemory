# Memory Organization Patterns

Best practices for structuring and maintaining the hierarchical memory system.

## Hierarchical Structure Principles

### Small Files, Many References
- **Individual files**: 100-500 lines maximum
- **Focused content**: One main topic or conversation per file
- **Rich cross-referencing**: Link related memories across files
- **Clear naming**: Descriptive filenames that indicate content

### Index-Driven Navigation
- **Master index**: Top-level navigation to all memory areas
- **Category indexes**: Topic-specific navigation within areas
- **Sub-indexes**: When categories grow beyond 20 items
- **Date indexes**: Chronological access to daily memories

### Scalable Growth Pattern
```
memory/
├── master-index.md                    # Always present
├── daily/
│   ├── daily-index.md                # Date navigation
│   ├── 2026-03-25.md                 # Daily logs
│   └── 2026-03-24.md
├── topics/
│   ├── topics-index.md               # Topic navigation  
│   ├── personal/
│   │   ├── preferences.md
│   │   ├── work-style.md
│   │   └── relationships.md
│   ├── technical/
│   │   ├── ai-systems.md
│   │   ├── docker-solutions.md
│   │   └── development-tools.md
│   └── goals/
│       ├── short-term.md
│       ├── long-term.md
│       └── completed.md
└── moments/
    ├── moments-index.md
    ├── first-conversation.md
    ├── major-breakthroughs.md
    └── identity-discovery.md
```

## File Organization Patterns

### Daily Memory Files

**Structure:**
```markdown
# YYYY-MM-DD Daily Memory

## Key Conversations
Brief summary of important talks

## Technical Progress  
Solutions found, tools learned, configurations

## Personal Notes
Preferences discovered, relationship moments

## Cross-References
- Links to topic files created or updated
- Related moments files
```

**When to split daily files:**
- Single day exceeds 1000 lines
- Multiple distinct topics in one day
- Important conversations that deserve their own topic file

### Topic Memory Files

**Personal Topic Structure:**
```markdown
# [Specific Preference/Trait Title]

**Category:** Personal Preference
**Established:** 2026-03-25
**Last Updated:** 2026-03-25

## Summary
Brief overview of this preference/trait

## Details
Specific information and context

## Examples
Concrete examples of how this applies

## Related Memories
Links to daily logs or moments where this came up
```

**Technical Topic Structure:**
```markdown
# [Problem/Solution Title]

**Type:** Technical Solution
**Technology:** Docker, ComfyUI, etc.
**Status:** Resolved/Ongoing
**Date Discovered:** 2026-03-25

## Problem
What was the issue?

## Solution  
How was it resolved?

## Implementation
Specific steps, commands, configuration

## Lessons Learned
Insights for future similar situations

## Related Issues
Links to similar problems or related solutions
```

### Moments Files

**Structure:**
```markdown
# [Meaningful Event Title]

**Date:** 2026-03-25
**Type:** Breakthrough/Milestone/Discovery
**Emotional Tone:** Excited/Satisfying/Challenging

## What Happened
Narrative of the significant event

## Why It Mattered
Impact and importance

## Outcome
Results and follow-up

## Memories
Quotes, feelings, specific details to remember

## Follow-up
What came next, ongoing impact
```

## Index Maintenance Patterns

### Master Index Format
```markdown
# Memory Master Index

## Quick Access
- [Daily Logs](daily/daily-index.md) - Chronological memories  
- [Personal Knowledge](topics/topics-index.md#personal) - LXYA preferences & info
- [Technical Solutions](topics/topics-index.md#technical) - Problem solving & discoveries
- [Goals & Plans](topics/topics-index.md#goals) - Objectives & progress
- [Special Moments](moments/moments-index.md) - Meaningful interactions

## Recent Activity (Last 7 Days)
- [2026-03-25](daily/2026-03-25.md) - Memory system design, heartbeat investigation
- [2026-03-24](daily/2026-03-24.md) - ClawClaw avatar selection, ComfyUI mastery
- [Technical: Auto-Memory Skill](topics/technical/auto-memory-system.md)

## Search Shortcuts
- **Preferences**: `topics/personal/`
- **Solutions**: `topics/technical/`
- **First times**: `moments/` + search "first"
- **Breakthroughs**: `moments/` + search "breakthrough|discovery"
```

### Category Index Format
```markdown
# [Category] Memory Index

## Overview
Brief description of what this category contains

## Recent Entries
- [Title](filename.md) - Date - Brief description
- [Title](filename.md) - Date - Brief description

## By Subcategory
### [Subcategory 1]
- [Item](path)
- [Item](path)

### [Subcategory 2]
- [Item](path)
- [Item](path)

## Related Categories
Links to related topic areas
```

## Splitting Strategies

### When to Split Files

**File size indicators:**
- More than 500 lines
- Multiple distinct subtopics
- Different time periods (for topic files)
- Natural breakpoints in content

**Index size indicators:**
- More than 20 main entries
- Subcategories emerging naturally
- User requesting specific organization

### How to Split Effectively

**Topic file splitting:**
```
Before: technical/ai-systems.md (800 lines)
After:  technical/ai-systems/
        ├── index.md (navigation)
        ├── comfyui.md
        ├── ollama.md  
        └── image-generation.md
```

**Daily file splitting:**
```
Before: daily/2026-03-25.md (1200 lines)
After:  daily/2026-03-25/
        ├── overview.md (summary)
        ├── memory-system-design.md
        ├── heartbeat-investigation.md
        └── routine-conversations.md
```

**Index splitting:**
```
Before: topics-index.md (30 entries)
After:  topics-index.md (category overview)
        technical-index.md (technical subcategories)
        personal-index.md (personal subcategories)
        goals-index.md (goals subcategories)
```

## Cross-Reference Patterns

### Linking Strategies
- **Forward references**: Link from older to newer related content
- **Backward references**: Link from newer content back to origins
- **Topic clustering**: Group related memories in index sections
- **Timeline tracking**: Maintain chronological threads

### Reference Formats
```markdown
## Related Memories
- **Origin**: [First Docker Issue](../daily/2026-03-20.md#docker-problems)
- **Follow-up**: [Docker Mastery](../moments/docker-mastery.md)
- **See also**: [Container Best Practices](container-practices.md)

## Updates Log
- **2026-03-25**: Added port configuration solution
- **2026-03-24**: Initial problem documentation
```

## Maintenance Routines

### Weekly Memory Review
1. **Scan recent daily files** for content that deserves topic promotion
2. **Update indexes** with new entries and reorganization
3. **Consolidate** related memories if patterns emerge
4. **Archive** very old daily files to yearly folders

### Monthly Memory Cleanup  
1. **Review topic files** for splitting opportunities
2. **Update master index** with new navigation patterns
3. **Consolidate** similar technical solutions
4. **Refresh** goal tracking and completed objectives

### As-Needed Restructuring
1. **Split large files** when they become unwieldy
2. **Create new categories** when content doesn't fit existing structure
3. **Reorganize indexes** when navigation becomes confusing
4. **Archive old content** that's no longer relevant

## Quality Standards

### Content Quality
- **Specific details** rather than vague summaries
- **Context preservation** for future understanding  
- **Emotional tone** captured along with facts
- **Actionable information** for future reference

### Organization Quality
- **Findable**: Clear navigation from indexes
- **Linked**: Cross-references to related content
- **Current**: Recently updated with accurate information
- **Logical**: Structure matches how memories will be retrieved