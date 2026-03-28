#!/usr/bin/env python3
"""
Memory Organization System for Auto-Memory

Manages hierarchical memory structure with automatic index creation and maintenance.
Handles file splitting, cross-references, and memory consolidation.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class MemoryOrganizer:
    def __init__(self, memory_root: str = "memory"):
        """Initialize memory organization system."""
        self.memory_root = Path(memory_root)
        self.max_file_size = 50000  # ~50KB per file
        self.max_index_entries = 20  # Split index when it gets this big
        
        # Ensure base structure exists
        self._ensure_structure()
    
    def _ensure_structure(self):
        """Create base memory directory structure."""
        dirs_to_create = [
            self.memory_root,
            self.memory_root / "daily",
            self.memory_root / "topics" / "personal",
            self.memory_root / "topics" / "technical", 
            self.memory_root / "topics" / "goals",
            self.memory_root / "moments"
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create indexes if they don't exist
        self._ensure_index_files()
    
    def _ensure_index_files(self):
        """Create index files if they don't exist."""
        indexes = {
            "master-index.md": self._create_master_index_template(),
            "daily/daily-index.md": self._create_daily_index_template(),
            "topics/topics-index.md": self._create_topics_index_template(),
            "moments/moments-index.md": self._create_moments_index_template()
        }
        
        for index_path, template in indexes.items():
            full_path = self.memory_root / index_path
            if not full_path.exists():
                self._write_file(full_path, template)
    
    def add_memory(self, content: str, location: str, title: str = None, 
                  categories: List[str] = None, cross_refs: List[str] = None) -> str:
        """
        Add a new memory to the system.
        
        Args:
            content: The memory content to store
            location: Target location (daily/topics/personal/technical/goals/moments)
            title: Optional title for the memory
            categories: Categories/tags for this memory
            cross_refs: Related memory file references
            
        Returns:
            Path to the created memory file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Generate title if not provided
        if not title:
            title = self._generate_title(content)
        
        # Determine file path
        file_path = self._determine_file_path(location, title, timestamp)
        
        # Format memory content
        formatted_content = self._format_memory(
            content, title, timestamp, categories, cross_refs
        )
        
        # Write memory file
        self._write_file(file_path, formatted_content)
        
        # Update relevant indexes
        self._update_indexes(file_path, title, timestamp, categories, location)
        
        return str(file_path)
    
    def _determine_file_path(self, location: str, title: str, timestamp: str) -> Path:
        """Determine the appropriate file path for a memory."""
        # Clean title for filename
        safe_title = self._sanitize_filename(title)
        date_str = timestamp.split()[0]  # YYYY-MM-DD part
        
        if location == "daily":
            return self.memory_root / "daily" / f"{date_str}.md"
        elif location.startswith("topics/"):
            topic = location.split("/")[1]
            return self.memory_root / "topics" / topic / f"{safe_title}-{date_str}.md"
        elif location == "moments":
            return self.memory_root / "moments" / f"{safe_title}-{date_str}.md"
        else:
            # Default to daily
            return self.memory_root / "daily" / f"{date_str}.md"
    
    def _format_memory(self, content: str, title: str, timestamp: str, 
                      categories: List[str] = None, cross_refs: List[str] = None) -> str:
        """Format memory content with metadata."""
        formatted = f"# {title}\\n\\n"
        formatted += f"**Timestamp:** {timestamp}\\n"
        
        if categories:
            formatted += f"**Categories:** {', '.join(categories)}\\n"
        
        if cross_refs:
            formatted += f"**Related:** {', '.join(cross_refs)}\\n"
        
        formatted += f"\\n---\\n\\n"
        formatted += content
        formatted += "\\n"
        
        return formatted
    
    def _update_indexes(self, file_path: Path, title: str, timestamp: str, 
                       categories: List[str], location: str):
        """Update relevant index files with new memory entry."""
        # Update master index
        self._add_to_index(
            self.memory_root / "master-index.md", 
            title, str(file_path.relative_to(self.memory_root)), timestamp
        )
        
        # Update specific indexes based on location
        if location == "daily":
            self._add_to_index(
                self.memory_root / "daily" / "daily-index.md",
                title, str(file_path.relative_to(self.memory_root / "daily")), timestamp
            )
        elif location.startswith("topics/"):
            self._add_to_index(
                self.memory_root / "topics" / "topics-index.md",
                title, str(file_path.relative_to(self.memory_root / "topics")), timestamp
            )
        elif location == "moments":
            self._add_to_index(
                self.memory_root / "moments" / "moments-index.md",
                title, str(file_path.relative_to(self.memory_root / "moments")), timestamp
            )
    
    def _add_to_index(self, index_path: Path, title: str, file_ref: str, timestamp: str):
        """Add entry to an index file."""
        if not index_path.exists():
            return
        
        # Read current index
        content = index_path.read_text(encoding='utf-8')
        
        # Add new entry (insert after the header)
        lines = content.split('\\n')
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith('##') or line.startswith('---'):
                header_end = i + 1
                break
        
        # Create new entry
        new_entry = f"- [{title}]({file_ref}) - {timestamp}"
        
        # Insert new entry
        lines.insert(header_end + 1, new_entry)
        
        # Write back
        updated_content = '\\n'.join(lines)
        self._write_file(index_path, updated_content)
        
        # Check if index needs splitting
        self._check_index_size(index_path)
    
    def _check_index_size(self, index_path: Path):
        """Check if an index file needs to be split due to size."""
        content = index_path.read_text(encoding='utf-8')
        entry_lines = [line for line in content.split('\\n') if line.strip().startswith('- [')]
        
        if len(entry_lines) > self.max_index_entries:
            self._split_index(index_path)
    
    def _split_index(self, index_path: Path):
        """Split large index into sub-indexes by date or topic."""
        # This is a placeholder for index splitting logic
        # In practice, you might split by year, month, or topic
        pass
    
    def search_memories(self, query: str, location: str = None) -> List[Dict]:
        """Search through memories for relevant content."""
        results = []
        search_dirs = [self.memory_root]
        
        if location:
            search_dirs = [self.memory_root / location]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            for file_path in search_dir.rglob("*.md"):
                if "index" in file_path.name:
                    continue
                    
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if query.lower() in content.lower():
                        results.append({
                            'file': str(file_path),
                            'title': self._extract_title(content),
                            'snippet': self._extract_snippet(content, query),
                            'location': str(file_path.relative_to(self.memory_root))
                        })
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        
        return results
    
    def consolidate_memories(self, topic: str) -> str:
        """Consolidate related memories into a summary."""
        topic_dir = self.memory_root / "topics" / topic
        if not topic_dir.exists():
            return "No memories found for this topic."
        
        memories = []
        for file_path in topic_dir.glob("*.md"):
            try:
                content = file_path.read_text(encoding='utf-8')
                memories.append({
                    'file': file_path.name,
                    'content': content,
                    'timestamp': self._extract_timestamp(content)
                })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        # Sort by timestamp
        memories.sort(key=lambda x: x['timestamp'])
        
        # Create consolidated summary
        summary = f"# {topic.title()} Memory Consolidation\\n\\n"
        summary += f"Consolidated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}\\n\\n"
        
        for memory in memories:
            title = self._extract_title(memory['content'])
            summary += f"## {title}\\n"
            summary += f"From: {memory['file']}\\n"
            summary += memory['content'] + "\\n\\n---\\n\\n"
        
        return summary
    
    # Helper methods
    def _sanitize_filename(self, text: str) -> str:
        """Convert text to safe filename."""
        import re
        # Remove invalid characters and limit length
        safe = re.sub(r'[<>:"/\\\\|?*]', '', text)
        safe = re.sub(r'\\s+', '-', safe)
        return safe[:50].lower()
    
    def _generate_title(self, content: str) -> str:
        """Generate title from content."""
        # Take first meaningful line or first sentence
        lines = [line.strip() for line in content.split('\\n') if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) > 60:
                first_line = first_line[:57] + "..."
            return first_line
        return "Untitled Memory"
    
    def _extract_title(self, content: str) -> str:
        """Extract title from formatted memory content."""
        lines = content.split('\\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled"
    
    def _extract_timestamp(self, content: str) -> str:
        """Extract timestamp from memory content."""
        lines = content.split('\\n')
        for line in lines:
            if line.startswith('**Timestamp:**'):
                return line.split(':', 1)[1].strip()
        return "Unknown"
    
    def _extract_snippet(self, content: str, query: str, context: int = 100) -> str:
        """Extract relevant snippet around query match."""
        content_lower = content.lower()
        query_lower = query.lower()
        
        match_pos = content_lower.find(query_lower)
        if match_pos == -1:
            return content[:context] + "..."
        
        start = max(0, match_pos - context // 2)
        end = min(len(content), match_pos + len(query) + context // 2)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
            
        return snippet
    
    def _write_file(self, file_path: Path, content: str):
        """Write content to file with error handling."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
        except Exception as e:
            print(f"Error writing to {file_path}: {e}")
    
    # Template methods for index creation
    def _create_master_index_template(self) -> str:
        return """# Memory Master Index

Top-level navigation for all memories in the ClawClaw memory system.

## Quick Access

- [Daily Memories](daily/daily-index.md) - Chronological daily logs
- [Topic Collections](topics/topics-index.md) - Thematic memory organization  
- [Special Moments](moments/moments-index.md) - Memorable interactions and breakthroughs

## Recent Entries

"""

    def _create_daily_index_template(self) -> str:
        return """# Daily Memory Index

Chronological index of daily memory files.

## Recent Days

"""

    def _create_topics_index_template(self) -> str:
        return """# Topics Memory Index

Thematic organization of memories by subject area.

## Available Topics

- [Personal](personal/) - User preferences, habits, relationships
- [Technical](technical/) - Discoveries, solutions, tools learned  
- [Goals](goals/) - Plans, objectives, progress tracking

## Recent Topic Entries

"""

    def _create_moments_index_template(self) -> str:
        return """# Special Moments Index

Particularly meaningful interactions and memorable experiences.

## Memorable Moments

"""

def main():
    """Example usage of the Memory Organizer."""
    organizer = MemoryOrganizer("test_memory")
    
    # Test adding memories
    organizer.add_memory(
        "LXYA prefers using dark mode for all applications. He mentioned this is important for his eyes during late night work sessions.",
        "topics/personal",
        "LXYA's Dark Mode Preference",
        ["preferences", "accessibility", "work-habits"]
    )
    
    organizer.add_memory(
        "Successfully solved the Docker port binding issue by updating the docker-compose.yml configuration. The key was changing the port mapping from 8080:80 to 8000:80.",
        "topics/technical", 
        "Docker Port Configuration Fix",
        ["docker", "troubleshooting", "configuration"]
    )
    
    organizer.add_memory(
        "Today we established ClawClaw's identity and selected the perfect avatar. This was a meaningful moment of self-discovery and creative collaboration.",
        "moments",
        "ClawClaw's Identity Discovery",
        ["identity", "collaboration", "milestone"]
    )
    
    print("Memories added successfully!")
    print("\\nSearching for 'docker':")
    results = organizer.search_memories("docker")
    for result in results:
        print(f"- {result['title']} in {result['location']}")

if __name__ == "__main__":
    main()