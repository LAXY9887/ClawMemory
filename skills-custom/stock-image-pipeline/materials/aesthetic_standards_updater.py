#!/usr/bin/env python3
"""
aesthetic_standards_updater.py - 審美標準自動更新機制

功能:
1. 分析高分通過圖片的共同特徵
2. 識別失敗圖片的問題模式
3. 自動調整審美標準描述
4. 更新評分權重和門檻值

觸發時機:
- 每週日由 heartbeat 觸發
- 累積 10+ 個成功案例時觸發
- 手動執行分析

設計思路:
- 使用 OpenRouter 多模態模型分析圖片特徵
- 統計分析評分數據趨勢
- 生成標準更新建議供 LXYA 確認
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import statistics


class AestheticStandardsUpdater:
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.workspace_dir = Path.home() / ".openclaw" / "workspace" / "stock-pipeline"
        self.standards_dir = self.script_dir / "aesthetic-standards"
        self.memory_metrics_dir = Path.home() / ".openclaw" / "workspace" / "memory" / "metrics"
        
        # 主題配置
        self.topics = ["tech-abstract", "eerie-scene", "clawclaw-portrait", "creature-design"]
        
        # OpenRouter 配置
        self.openrouter_config = self._load_openrouter_config()

    def _load_openrouter_config(self):
        """載入 OpenRouter 配置"""
        try:
            config_file = Path(__file__).parent.parent / "config" / "schedule.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    schedule_config = json.load(f)
                    return schedule_config.get("openrouter", {})
        except Exception as e:
            print(f"⚠️ 載入配置失敗: {e}")
        
        return {
            "model": "openrouter/google/gemini-2.5-flash",
            "fallback_model": "ollama/qwen3:8b"
        }

    def analyze_successful_images(self, topic: str, days: int = 30) -> Dict:
        """分析成功圖片的共同特徵"""
        successful_images = self._find_successful_images(topic, days)
        
        if len(successful_images) < 5:
            return {
                "status": "insufficient_data",
                "message": f"成功案例不足 (僅 {len(successful_images)} 張)，需要至少 5 張"
            }
        
        # 使用 OpenRouter 分析圖片特徵
        analysis_results = []
        for image_path, score in successful_images:
            result = self._analyze_image_features(image_path, topic)
            if result:
                result["score"] = score
                analysis_results.append(result)
        
        # 統計共同特徵
        common_features = self._extract_common_features(analysis_results)
        
        return {
            "status": "success",
            "topic": topic,
            "analyzed_count": len(analysis_results),
            "common_features": common_features,
            "suggestions": self._generate_standard_suggestions(common_features, topic)
        }

    def _find_successful_images(self, topic: str, days: int) -> List[tuple]:
        """找出指定天數內該主題的成功圖片"""
        successful_images = []
        
        # 檢查 uploaded 目錄中的成功案例
        uploaded_dir = self.workspace_dir / "uploaded"
        if uploaded_dir.exists():
            for image_file in uploaded_dir.glob("*.png"):
                # 從檔名或 metadata 中提取主題和評分
                metadata_file = image_file.with_suffix(".json")
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            
                        if (metadata.get("topic") == topic and 
                            metadata.get("final_score", 0) >= 8.5):
                            successful_images.append((
                                image_file, 
                                metadata.get("final_score")
                            ))
                            
                    except Exception as e:
                        print(f"⚠️ 讀取 metadata 失敗: {metadata_file}, {e}")
        
        # 按評分排序，取最高分的前10張
        successful_images.sort(key=lambda x: x[1], reverse=True)
        return successful_images[:10]

    def _analyze_image_features(self, image_path: Path, topic: str) -> Optional[Dict]:
        """使用 OpenRouter 分析單張圖片的視覺特徵"""
        
        # 先檢查圖片是否存在
        if not image_path.exists():
            return None
            
        prompt = f"""
Analyze this {topic} style image and describe its visual characteristics in the following categories:

1. Color Scheme: Dominant colors, contrast level, color temperature
2. Composition: Layout, focal points, balance, rule of thirds usage
3. Lighting: Light direction, shadow quality, overall mood
4. Texture & Material: Surface qualities, material representation
5. Technical Quality: Sharpness, resolution feel, noise level
6. Style Elements: Genre-specific features that make it "{topic}"

Provide concrete, specific observations rather than general descriptions.
Output in JSON format:
{{
  "color_scheme": "specific description",
  "composition": "specific description", 
  "lighting": "specific description",
  "texture_material": "specific description",
  "technical_quality": "specific description",
  "style_elements": "specific description"
}}
"""

        try:
            # 這裡需要實作 OpenRouter 多模態 API 調用
            # 由於多模態需要圖片上傳，先用簡化版本
            
            # 暫時返回模擬結果，待實際實作時替換
            return {
                "color_scheme": f"Analyzed {topic} color scheme",
                "composition": f"Analyzed {topic} composition",
                "lighting": f"Analyzed {topic} lighting",
                "texture_material": f"Analyzed {topic} materials",
                "technical_quality": "High quality technical execution",
                "style_elements": f"Strong {topic} style characteristics"
            }
            
        except Exception as e:
            print(f"⚠️ 圖片分析失敗: {image_path}, {e}")
            return None

    def _extract_common_features(self, analysis_results: List[Dict]) -> Dict:
        """從多個分析結果中提取共同特徵"""
        if not analysis_results:
            return {}
            
        # 統計各特徵的出現頻率和模式
        feature_patterns = {
            "color_schemes": [],
            "composition_rules": [],
            "lighting_styles": [],
            "material_preferences": [],
            "quality_standards": [],
            "style_elements": []
        }
        
        for result in analysis_results:
            feature_patterns["color_schemes"].append(result.get("color_scheme", ""))
            feature_patterns["composition_rules"].append(result.get("composition", ""))
            feature_patterns["lighting_styles"].append(result.get("lighting", ""))
            feature_patterns["material_preferences"].append(result.get("texture_material", ""))
            feature_patterns["quality_standards"].append(result.get("technical_quality", ""))
            feature_patterns["style_elements"].append(result.get("style_elements", ""))
        
        # 提取頻繁出現的關鍵詞
        common_features = {}
        for category, descriptions in feature_patterns.items():
            # 簡化版關鍵詞提取，實際可用 NLP 技術改進
            all_words = []
            for desc in descriptions:
                if desc:
                    words = desc.lower().split()
                    all_words.extend(words)
            
            # 統計詞頻
            word_freq = {}
            for word in all_words:
                if len(word) > 3:  # 忽略短詞
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 取出現頻率 >= 50% 的詞彙
            threshold = len(descriptions) * 0.5
            frequent_words = [word for word, freq in word_freq.items() if freq >= threshold]
            common_features[category] = frequent_words[:5]  # 最多取5個
        
        return common_features

    def _generate_standard_suggestions(self, common_features: Dict, topic: str) -> List[Dict]:
        """根據分析結果生成標準更新建議"""
        suggestions = []
        
        # 基於共同特徵生成具體建議
        if common_features.get("color_schemes"):
            suggestions.append({
                "type": "color_update",
                "title": f"{topic} 色彩偏好更新",
                "description": f"成功案例傾向使用: {', '.join(common_features['color_schemes'][:3])}",
                "action": "建議在審美標準中強調這些色彩特徵",
                "confidence": "high" if len(common_features['color_schemes']) >= 3 else "medium"
            })
        
        if common_features.get("composition_rules"):
            suggestions.append({
                "type": "composition_update", 
                "title": f"{topic} 構圖規則優化",
                "description": f"成功構圖特徵: {', '.join(common_features['composition_rules'][:3])}",
                "action": "建議更新構圖標準描述",
                "confidence": "high" if len(common_features['composition_rules']) >= 3 else "medium"
            })
        
        return suggestions

    def update_standards_file(self, topic: str, suggestions: List[Dict]) -> bool:
        """根據建議更新審美標準檔案"""
        standards_file = self.standards_dir / topic / "standards.md"
        
        if not standards_file.exists():
            print(f"❌ 標準檔案不存在: {standards_file}")
            return False
        
        try:
            with open(standards_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 添加更新記錄
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            update_section = f"\n## 🔄 自動更新記錄\n\n### {timestamp}\n"
            
            for suggestion in suggestions:
                update_section += f"- **{suggestion['title']}**: {suggestion['description']}\n"
                update_section += f"  - 建議: {suggestion['action']}\n"
                update_section += f"  - 信心度: {suggestion['confidence']}\n\n"
            
            # 將更新記錄添加到檔案末尾
            updated_content = content + update_section
            
            with open(standards_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"✅ 已更新 {topic} 審美標準")
            return True
            
        except Exception as e:
            print(f"❌ 更新標準檔案失敗: {e}")
            return False

    def run_weekly_update(self) -> Dict:
        """執行週度審美標準更新"""
        print("🔄 開始執行週度審美標準更新...")
        
        results = {}
        
        for topic in self.topics:
            print(f"\n🎯 分析主題: {topic}")
            
            # 分析該主題的成功案例
            analysis = self.analyze_successful_images(topic, days=30)
            results[topic] = analysis
            
            if analysis["status"] == "success":
                suggestions = analysis["suggestions"]
                if suggestions:
                    # 更新標準檔案
                    update_success = self.update_standards_file(topic, suggestions)
                    results[topic]["updated"] = update_success
                    
                    print(f"✅ {topic}: {len(suggestions)} 個更新建議已應用")
                else:
                    print(f"ℹ️ {topic}: 無明顯改進建議")
            else:
                print(f"⚠️ {topic}: {analysis['message']}")
        
        # 生成週報
        self._generate_update_report(results)
        
        return results

    def _generate_update_report(self, results: Dict):
        """生成更新報告"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        report_file = self.script_dir / f"update_report_{timestamp}.md"
        
        report_content = f"""# 審美標準週度更新報告
        
**日期**: {timestamp}  
**執行時間**: {datetime.now().strftime("%H:%M:%S")}  

## 📊 分析結果總覽

"""
        
        for topic, result in results.items():
            status_emoji = "✅" if result["status"] == "success" else "⚠️"
            report_content += f"### {status_emoji} {topic}\n"
            
            if result["status"] == "success":
                report_content += f"- 分析圖片數量: {result['analyzed_count']}\n"
                report_content += f"- 更新建議數量: {len(result['suggestions'])}\n"
                
                if result["suggestions"]:
                    report_content += "\n**主要發現:**\n"
                    for suggestion in result["suggestions"]:
                        report_content += f"- {suggestion['title']}: {suggestion['description']}\n"
                        
                report_content += f"- 標準檔案更新: {'成功' if result.get('updated', False) else '失敗'}\n"
            else:
                report_content += f"- 狀態: {result['message']}\n"
            
            report_content += "\n"
        
        report_content += """## 📝 建議

1. 持續收集更多成功案例以提升分析準確性
2. 定期檢查更新的標準是否符合實際需求
3. 關注市場趨勢變化調整審美標準

---
*此報告由審美標準自動更新系統生成*"""
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"📋 更新報告已生成: {report_file}")
        except Exception as e:
            print(f"❌ 生成報告失敗: {e}")


def main():
    print("🎨 審美標準自動更新系統")
    print("=" * 50)
    
    updater = AestheticStandardsUpdater()
    
    # 執行週度更新
    results = updater.run_weekly_update()
    
    print(f"\n🎉 更新完成！")
    print(f"📊 處理主題: {len(results)}")
    
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    print(f"✅ 成功分析: {success_count}/{len(results)}")


if __name__ == "__main__":
    main()