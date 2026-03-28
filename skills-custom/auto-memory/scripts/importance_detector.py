#!/usr/bin/env python3
"""
Importance Detection for Auto-Memory System

Analyzes conversation content to determine if it contains memory-worthy information.
Provides scoring and categorization for intelligent memory management.
"""

import re
import json
from datetime import datetime
from pathlib import Path

class ImportanceDetector:
    def __init__(self):
        """Initialize importance detection system."""
        self.high_value_keywords = {
            'personal': [
                'prefer', 'like', 'dislike', 'hate', 'love', 'favorite', 'always', 'never',
                'name', 'timezone', 'location', 'hobby', 'interest', 'goal', 'dream',
                'important to me', 'care about', 'value', 'believe', 'think'
            ],
            'technical': [
                'solution', 'fix', 'breakthrough', 'discovered', 'learned', 'figured out',
                'works', "doesn't work", 'error', 'bug', 'issue', 'problem solved',
                'configuration', 'setup', 'install', 'upgrade', 'version'
            ],
            'decision': [
                'decided', 'choose', 'selected', 'picked', 'going with', 'settled on',
                'plan to', 'will', 'strategy', 'approach', 'method', 'way forward',
                'next step', 'priority', 'focus on'
            ],
            'emotional': [
                'excited', 'happy', 'sad', 'frustrated', 'proud', 'worried', 'concerned',
                'amazing', 'terrible', 'wonderful', 'disappointing', 'surprising',
                'grateful', 'thankful', 'sorry', 'apologize'
            ],
            'goal': [
                'want to', 'need to', 'should', 'must', 'goal', 'objective', 'target',
                'plan', 'intend', 'hope', 'wish', 'dream', 'vision', 'future',
                'by', 'deadline', 'timeline', 'schedule'
            ]
        }
        
        self.memory_triggers = [
            r'\b(remember|don\'t forget|important|note|keep in mind)\b',
            r'\b(first time|never done|new to)\b',
            r'\b(always|never|usually|typically|generally)\b',
            r'\b(breakthrough|discovery|realization|insight)\b',
            r'\b(problem solved|figured out|got it working)\b',
            r'\b(my name is|call me|I\'m)\b',
            r'\b(I prefer|I like|I hate|I love)\b',
            r'\b(let\'s|we should|we need to|we will)\b',
            r'\b(goal|plan|strategy|next step)\b',
            r'\b(question|doubt|concern|worry)\b'
        ]
    
    def analyze_importance(self, text: str, context: dict = None) -> dict:
        """
        Analyze text for memory-worthy content.
        
        Args:
            text: The conversation text to analyze
            context: Additional context (speaker, timestamp, etc.)
            
        Returns:
            Dictionary with importance score and categorization
        """
        if not text or len(text.strip()) < 10:
            return {'score': 0, 'reason': 'Text too short'}
        
        text_lower = text.lower()
        results = {
            'score': 0,
            'categories': [],
            'reasons': [],
            'suggested_location': 'daily',
            'urgency': 'normal'
        }
        
        # Check for high-value keywords
        for category, keywords in self.high_value_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                results['score'] += matches * 10
                results['categories'].append(category)
                results['reasons'].append(f"Contains {matches} {category} keywords")
        
        # Check for memory trigger patterns
        trigger_matches = 0
        for pattern in self.memory_triggers:
            if re.search(pattern, text_lower):
                trigger_matches += 1
                results['score'] += 15
        
        if trigger_matches > 0:
            results['reasons'].append(f"Contains {trigger_matches} memory trigger patterns")
        
        # Special scoring adjustments
        if any(word in text_lower for word in ['first', 'initial', 'beginning']):
            results['score'] += 20
            results['reasons'].append("First-time/initial experience")
            
        if any(word in text_lower for word in ['problem', 'solution', 'fix', 'work']):
            results['score'] += 15
            results['reasons'].append("Problem-solving content")
            
        if any(word in text_lower for word in ['important', 'critical', 'urgent', 'priority']):
            results['score'] += 25
            results['urgency'] = 'high'
            results['reasons'].append("Explicitly marked as important")
        
        # Text length bonus for substantial content
        if len(text) > 200:
            results['score'] += 5
        if len(text) > 500:
            results['score'] += 10
        
        # Determine suggested memory location
        results['suggested_location'] = self._suggest_location(results['categories'], results['score'])
        
        # Determine if worth remembering (threshold: 30)
        results['should_remember'] = results['score'] >= 30
        
        return results
    
    def _suggest_location(self, categories: list, score: int) -> str:
        """Suggest the best memory location based on content analysis."""
        if score >= 70:
            return 'moments'  # Special memorable moment
        elif 'personal' in categories and score >= 50:
            return 'topics/personal'
        elif 'technical' in categories and score >= 40:
            return 'topics/technical'
        elif 'goal' in categories or 'decision' in categories:
            return 'topics/goals'
        else:
            return 'daily'
    
    def batch_analyze(self, conversations: list) -> list:
        """Analyze multiple conversation segments for importance."""
        results = []
        for i, conv in enumerate(conversations):
            if isinstance(conv, str):
                analysis = self.analyze_importance(conv)
            else:
                analysis = self.analyze_importance(conv.get('text', ''), conv.get('context', {}))
            
            analysis['index'] = i
            results.append(analysis)
        
        return results
    
    def generate_summary(self, analysis_results: list) -> dict:
        """Generate summary of importance analysis for multiple texts."""
        total_items = len(analysis_results)
        memorable_items = sum(1 for r in analysis_results if r['should_remember'])
        high_urgency = sum(1 for r in analysis_results if r.get('urgency') == 'high')
        
        avg_score = sum(r['score'] for r in analysis_results) / max(total_items, 1)
        
        categories_found = set()
        for result in analysis_results:
            categories_found.update(result.get('categories', []))
        
        return {
            'total_analyzed': total_items,
            'memorable_count': memorable_items,
            'high_urgency_count': high_urgency,
            'average_score': round(avg_score, 1),
            'categories_found': list(categories_found),
            'recommendation': 'high' if memorable_items > total_items * 0.3 else 'normal'
        }

def main():
    """Example usage and testing."""
    detector = ImportanceDetector()
    
    # Test examples
    test_conversations = [
        "I prefer using dark mode for all my applications",
        "The weather is nice today",
        "We solved the Docker connection problem by updating the port configuration",
        "My goal is to learn AI image generation by the end of March",
        "This is my first time using OpenClaw",
        "Hello, how are you?",
        "I discovered that the issue was caused by a missing API key",
        "Remember to always backup the database before making schema changes"
    ]
    
    print("Importance Detection Analysis")
    print("=" * 50)
    
    for i, text in enumerate(test_conversations):
        result = detector.analyze_importance(text)
        print(f"\nText {i+1}: '{text}'")
        print(f"Score: {result['score']}")
        print(f"Should Remember: {result['should_remember']}")
        print(f"Categories: {', '.join(result['categories']) if result['categories'] else 'None'}")
        print(f"Location: {result['suggested_location']}")
        print(f"Reasons: {'; '.join(result['reasons'])}")
    
    # Batch analysis example
    batch_results = detector.batch_analyze(test_conversations)
    summary = detector.generate_summary(batch_results)
    
    print(f"\n\nBatch Analysis Summary")
    print("=" * 30)
    print(f"Total analyzed: {summary['total_analyzed']}")
    print(f"Worth remembering: {summary['memorable_count']}")
    print(f"Average score: {summary['average_score']}")
    print(f"Categories found: {', '.join(summary['categories_found'])}")
    print(f"Recommendation: {summary['recommendation']}")

if __name__ == "__main__":
    main()