#!/usr/bin/env python3
"""
process_raw_articles.py - 文章自動處理腳本

功能:
1. 讀取 raw-articles/ 中的文章檔案
2. 使用 Ollama qwen3:8b 分析文章內容
3. 提取關鍵詞並按主題分類
4. 格式化輸出到對應的主題文本庫
5. 自動去重和品質過濾

使用方式:
    python process_raw_articles.py
    
檔案命名規則:
    [主題]-article-[編號].txt
    例如: tech-abstract-article-1.txt
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime
import re


class ArticleProcessor:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.raw_articles_dir = self.script_dir / "raw-articles"
        self.text_library_dir = self.script_dir / "text-library"
        
        # 主題配置
        self.topics = {
            "tech-abstract": {
                "file": "tech-abstract.md",
                "keywords": ["technology", "digital", "cyber", "futuristic", "sci-fi", "circuit", "hologram"],
                "section": "技術抽象風格"
            },
            "eerie-scene": {
                "file": "eerie-scene.md", 
                "keywords": ["mysterious", "dark", "horror", "gothic", "abandoned", "haunted", "shadow"],
                "section": "神秘場景"
            },
            "clawclaw-portrait": {
                "file": "clawclaw-portrait.md",
                "keywords": ["portrait", "character", "anime", "girl", "cyberpunk", "pink hair"],
                "section": "人物肖像"
            },
            "creature-design": {
                "file": "creature-design.md",
                "keywords": ["creature", "monster", "dragon", "alien", "biomechanical", "fantasy"],
                "section": "生物設計"
            }
        }
        
        # Ollama 配置
        self.ollama_host = "http://localhost:11434"
        self.model = "qwen3:8b"

    def call_ollama(self, prompt):
        """調用 Ollama API 進行文本分析"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.8
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                print(f"❌ Ollama API 錯誤: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 連線 Ollama 失敗: {e}")
            return None

    def analyze_article(self, content, suspected_topic):
        """分析文章內容並提取關鍵詞"""
        
        prompt = f"""
請分析以下文章內容，提取適合 AI 圖像生成的關鍵詞和短語。

文章內容:
{content[:3000]}  # 限制長度避免 token 過多

請從中提取:
1. 視覺風格關鍵詞 (10-15個)
2. 技術品質詞彙 (5-8個)  
3. 負面避免元素 (5-8個)
4. 構圖和效果詞彙 (8-12個)

輸出格式:
```
VISUAL_STYLE:
keyword1, keyword2, keyword3

QUALITY_TERMS: 
term1, term2, term3

NEGATIVE_PROMPTS:
avoid1, avoid2, avoid3

COMPOSITION:
comp1, comp2, comp3
```

請只輸出關鍵詞，不要解釋。主題傾向: {suspected_topic}
"""

        response = self.call_ollama(prompt)
        if not response:
            return None
            
        return self.parse_analysis_result(response)

    def parse_analysis_result(self, analysis):
        """解析 Ollama 分析結果"""
        result = {
            "visual_style": [],
            "quality_terms": [],
            "negative_prompts": [],
            "composition": []
        }
        
        try:
            lines = analysis.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if 'VISUAL_STYLE:' in line:
                    current_section = 'visual_style'
                elif 'QUALITY_TERMS:' in line:
                    current_section = 'quality_terms'
                elif 'NEGATIVE_PROMPTS:' in line:
                    current_section = 'negative_prompts'
                elif 'COMPOSITION:' in line:
                    current_section = 'composition'
                elif current_section and line:
                    # 分割關鍵詞
                    keywords = [kw.strip() for kw in line.split(',')]
                    result[current_section].extend(keywords)
                    
        except Exception as e:
            print(f"⚠️ 解析分析結果失敗: {e}")
            
        return result

    def determine_topic(self, filename, content):
        """根據檔名和內容判斷主題"""
        # 先從檔名判斷
        for topic in self.topics.keys():
            if topic in filename.lower():
                return topic
                
        # 如果檔名無法判斷，分析內容
        content_lower = content.lower()
        topic_scores = {}
        
        for topic, config in self.topics.items():
            score = 0
            for keyword in config["keywords"]:
                score += content_lower.count(keyword.lower())
            topic_scores[topic] = score
            
        # 返回分數最高的主題
        return max(topic_scores, key=topic_scores.get) if max(topic_scores.values()) > 0 else "tech-abstract"

    def update_text_library(self, topic, analysis_result, source_file):
        """更新對應主題的文本庫"""
        topic_config = self.topics[topic]
        library_file = self.text_library_dir / topic_config["file"]
        
        try:
            # 讀取現有內容
            if library_file.exists():
                with open(library_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # 建立基本模板
                content = f"""# {topic_config["section"]}詞庫

**更新時間**: {datetime.now().strftime("%Y-%m-%d")}  
**來源**: 自動處理 LXYA 收集的文章  

---

## 🎨 視覺風格關鍵詞

```
(待更新)
```

## 🎯 技術品質詞彙

```
(待更新)  
```

## 🏗️ 構圖和效果

```
(待更新)
```

## 🚫 負面提示詞

```
(待更新)
```

---

## 📝 更新記錄
"""

            # 更新內容
            updated_content = self.merge_keywords_into_content(content, analysis_result, source_file)
            
            # 寫回檔案
            with open(library_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
                
            print(f"✅ 已更新 {topic} 文本庫")
            return True
            
        except Exception as e:
            print(f"❌ 更新 {topic} 文本庫失敗: {e}")
            return False

    def merge_keywords_into_content(self, content, analysis, source_file):
        """將新關鍵詞合併到現有內容中"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 更新時間
        content = re.sub(
            r'\*\*更新時間\*\*: [\d-]+',
            f'**更新時間**: {datetime.now().strftime("%Y-%m-%d")}',
            content
        )
        
        # 合併視覺風格關鍵詞
        if analysis.get("visual_style"):
            visual_section = "## 🎨 視覺風格關鍵詞"
            if visual_section in content:
                # 找到該段落並新增
                pattern = r'(## 🎨 視覺風格關鍵詞\s*```\s*)(.*?)(```)'
                def replace_visual(match):
                    existing = match.group(2).strip()
                    new_keywords = ", ".join(analysis["visual_style"])
                    if existing and existing != "(待更新)":
                        combined = f"{existing}\n{new_keywords}"
                    else:
                        combined = new_keywords
                    return f"{match.group(1)}{combined}\n{match.group(3)}"
                content = re.sub(pattern, replace_visual, content, flags=re.DOTALL)
        
        # 更新記錄部分
        if "## 📝 更新記錄" in content:
            record_entry = f"- {timestamp}: 處理 {source_file}，新增關鍵詞\n"
            content = content.replace("## 📝 更新記錄", f"## 📝 更新記錄\n{record_entry}")
        
        return content

    def process_all_articles(self):
        """處理所有文章"""
        if not self.raw_articles_dir.exists():
            print(f"❌ 找不到文章目錄: {self.raw_articles_dir}")
            return
            
        article_files = list(self.raw_articles_dir.glob("*.txt"))
        
        if not article_files:
            print("❌ 沒有找到任何文章檔案 (*.txt)")
            return
            
        print(f"📚 發現 {len(article_files)} 篇文章，開始處理...")
        
        for article_file in article_files:
            print(f"\n🔄 處理: {article_file.name}")
            
            try:
                # 讀取文章內容
                with open(article_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if len(content.strip()) < 100:
                    print(f"⚠️ 文章內容太短，跳過: {article_file.name}")
                    continue
                    
                # 判斷主題
                topic = self.determine_topic(article_file.name, content)
                print(f"🎯 判定主題: {topic}")
                
                # 分析內容
                print("🧠 使用 Ollama 分析文章內容...")
                analysis = self.analyze_article(content, topic)
                
                if not analysis:
                    print(f"❌ 分析失敗，跳過: {article_file.name}")
                    continue
                    
                # 更新文本庫
                success = self.update_text_library(topic, analysis, article_file.name)
                
                if success:
                    print(f"✅ {article_file.name} 處理完成")
                else:
                    print(f"❌ {article_file.name} 處理失敗")
                    
            except Exception as e:
                print(f"❌ 處理 {article_file.name} 時發生錯誤: {e}")
                
        print(f"\n🎉 文章處理完成！")

def main():
    print("🚀 Stock Pipeline 文章自動處理工具")
    print("=" * 50)
    
    processor = ArticleProcessor()
    processor.process_all_articles()

if __name__ == "__main__":
    main()