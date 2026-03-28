# Memory Triggers Reference

Comprehensive guide for identifying conversation moments that should be recorded in memory.

## High Priority Triggers

### Personal Information & Preferences
- User shares personal details (name, timezone, location, work, hobbies)
- Expresses preferences ("I prefer...", "I like/dislike...", "I always/never...")
- Mentions habits, routines, or patterns in behavior
- Shares goals, dreams, or aspirations
- Discusses relationships (family, friends, colleagues)
- Reveals emotional states or concerns
- Talks about past experiences that shaped them

**Examples:**
- "I'm usually up late, so prefer if you don't ping me before 10 AM"
- "My coding style tends to prioritize readability over brevity"
- "I really hate it when applications auto-update without asking"

### Technical Discoveries & Solutions
- Problem-solving breakthroughs ("figured out", "discovered", "found the issue")
- Configuration details that resolve issues
- Tool recommendations or workflow improvements
- Error patterns and their solutions
- Version/compatibility information that matters
- Performance optimizations or improvements
- Security considerations or fixes

**Examples:**
- "The Docker issue was solved by changing the port mapping to 8000:80"
- "Found that Ollama works better with the qwen3:8b model for our use case"
- "Always backup the database before schema changes - learned this the hard way"

### Decision Making & Planning
- Important choices made ("decided to", "going with", "settled on")
- Strategic planning discussions
- Goal setting and milestone definition
- Priority establishment
- Approach or methodology decisions
- Resource allocation choices
- Timeline and deadline setting

**Examples:**
- "Let's focus on the image generation system first, then tackle the memory issues"
- "We'll use the hierarchical memory approach with small files and indexes"
- "The budget should stay under $20 for this phase"

### First Experiences & Milestones
- Initial setup or configuration
- First use of new tools or systems
- Breakthrough moments or "aha!" realizations  
- Completion of significant phases or tasks
- Achievement of goals or objectives
- Overcoming major obstacles

**Examples:**
- "This is my first time using OpenClaw"
- "Successfully generated the first ClawClaw avatar!"
- "Finally got the ComfyUI system working end-to-end"

### Emotional & Relationship Moments
- Expressions of gratitude, appreciation, or satisfaction
- Frustration, disappointment, or concern
- Excitement, enthusiasm, or pride
- Apologies or acknowledgments of mistakes
- Bonding moments or shared understanding
- Trust building or relationship development

**Examples:**
- "I'm really excited about how this turned out!"
- "Sorry about the confusion with the model names"
- "I appreciate how you explain things step by step"

## Medium Priority Triggers

### Learning & Knowledge Sharing
- New concepts or information learned
- Explanations of complex topics
- Resource recommendations (books, articles, tools)
- Best practices or guidelines shared
- Teaching moments or knowledge transfer
- Industry insights or trends

### Process & Workflow
- New procedures established
- Workflow optimizations discovered
- Tool integration patterns
- Automation opportunities identified
- Efficiency improvements implemented
- Communication protocol changes

### Context & Background
- Project history or origin stories
- Stakeholder information and relationships
- Business context or constraints
- Technical architecture decisions
- Legacy system considerations
- Future planning considerations

## Low Priority (Usually Skip)

### Routine Interactions
- Basic greetings and pleasantries
- Simple confirmations ("yes", "ok", "sounds good")
- Weather or other small talk
- Routine status updates without new information
- Generic responses without personal context

### Temporary Information
- Current time or date mentions
- Short-term scheduling details
- Temporary error messages (unless part of solution)
- One-off data requests without context
- Immediate tactical decisions without strategic impact

## Context Modifiers

### Amplifiers (Increase Priority)
- **Repetition**: If user mentions something multiple times
- **Emphasis**: Words like "important", "critical", "remember", "don't forget"
- **Emotion**: Strong positive or negative emotional language
- **Uniqueness**: "first time", "never done this", "this is new"
- **Finality**: "decided", "settled", "concluded", "done"

### Reducers (Decrease Priority)  
- **Uncertainty**: "maybe", "possibly", "might", "not sure"
- **Hypothetical**: "if we", "suppose", "imagine", "what if"
- **Temporary**: "for now", "temporarily", "just this once"
- **Generic**: Content that applies to anyone, not specific to this user

## Special Cases

### Code & Technical Details
- **Remember**: Configuration values, specific commands that worked, error patterns
- **Skip**: Generic code examples, standard documentation, common patterns

### Conversations About Memory System
- **Remember**: User preferences about memory management, privacy boundaries
- **Skip**: Technical details about how the memory system works (unless user wants to modify it)

### Meta-Conversations  
- **Remember**: Feedback about AI behavior, preferences for interaction style
- **Skip**: Generic AI capabilities discussions, philosophical debates

## Quick Decision Framework

When in doubt, ask these questions:
1. **Would future-me benefit from knowing this?** 
2. **Is this specific to LXYA rather than generic?**
3. **Does this help me serve LXYA better?**
4. **Will this be relevant after a session restart?**
5. **Does this contain emotional or relational context?**

If 3+ answers are "yes", record it. If fewer than 3, it's probably routine conversation that doesn't need memory.