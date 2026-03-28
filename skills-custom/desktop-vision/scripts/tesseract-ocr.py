#!/usr/bin/env python3
"""
Tesseract OCR Text Recognition System
====================================

Local OCR text extraction using Tesseract engine with support for
Traditional Chinese and English text recognition.

Author: ClawClaw AI Services  
Version: 1.0
"""

import os
import re
import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️ Tesseract not available. Install pytesseract and tesseract-ocr.")

class TesseractOCR:
    def __init__(self, tesseract_path: Optional[str] = None):
        """Initialize Tesseract OCR system."""
        self.tesseract_available = TESSERACT_AVAILABLE
        
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif TESSERACT_AVAILABLE:
            # Try common Windows installation paths
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Tools\tesseract\tesseract.exe"
            ]
            
            for path in common_paths:
                if Path(path).exists():
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
        
        # OCR configuration for best Chinese + English results
        self.ocr_config = {
            'lang': 'chi_tra+eng',  # Traditional Chinese + English
            'config': '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        }
        
        # Confidence threshold for filtering results
        self.confidence_threshold = 30
        
        print(f"🔤 Tesseract OCR initialized")
        print(f"🌐 Languages: Traditional Chinese + English")
        print(f"🎯 Confidence threshold: {self.confidence_threshold}%")
    
    def extract_text_from_image(self, image_path: str, preprocess: bool = True) -> Dict:
        """Extract text from image file with preprocessing."""
        if not self.tesseract_available:
            return {"error": "Tesseract not available", "text": "", "confidence": 0}
        
        try:
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            print(f"🔍 Processing image: {image_path.name}")
            
            # Load image
            image = Image.open(image_path)
            
            # Preprocess if requested
            if preprocess:
                print("🔧 Applying image preprocessing...")
                image = self._preprocess_image(image)
            
            # Extract text with detailed data
            ocr_data = pytesseract.image_to_data(
                image, 
                lang=self.ocr_config['lang'],
                config=self.ocr_config['config'],
                output_type=pytesseract.Output.DICT
            )
            
            # Process results
            text_results = self._process_ocr_data(ocr_data)
            
            # Get simple text string
            full_text = pytesseract.image_to_string(
                image,
                lang=self.ocr_config['lang'], 
                config=self.ocr_config['config']
            )
            
            result = {
                "image_path": str(image_path),
                "full_text": full_text.strip(),
                "detailed_results": text_results,
                "total_characters": len(full_text.strip()),
                "confidence_avg": self._calculate_average_confidence(text_results),
                "languages_detected": self._detect_languages(full_text),
                "processing_time": time.time(),
                "preprocessed": preprocess
            }
            
            print(f"✅ OCR completed: {result['total_characters']} characters extracted")
            print(f"📊 Average confidence: {result['confidence_avg']:.1f}%")
            
            return result
            
        except Exception as e:
            print(f"❌ OCR extraction failed: {e}")
            return {"error": str(e), "text": "", "confidence": 0}
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Apply preprocessing to improve OCR accuracy."""
        try:
            # Convert PIL to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 1. Convert to grayscale
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            
            # 2. Noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # 3. Contrast enhancement
            enhanced = cv2.convertScaleAbs(denoised, alpha=1.2, beta=30)
            
            # 4. Morphological operations to improve text
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
            
            # 5. Adaptive threshold for better text separation
            adaptive = cv2.adaptiveThreshold(
                processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Convert back to PIL format
            final_image = Image.fromarray(adaptive)
            
            print("✨ Image preprocessing completed")
            return final_image
            
        except Exception as e:
            print(f"⚠️ Preprocessing failed, using original: {e}")
            return image
    
    def _process_ocr_data(self, ocr_data: Dict) -> List[Dict]:
        """Process raw OCR data into structured results."""
        results = []
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            confidence = int(ocr_data['conf'][i])
            
            # Filter by confidence threshold
            if confidence >= self.confidence_threshold and text:
                results.append({
                    'text': text,
                    'confidence': confidence,
                    'bbox': {
                        'left': ocr_data['left'][i],
                        'top': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i]
                    },
                    'word_num': ocr_data['word_num'][i],
                    'line_num': ocr_data['line_num'][i]
                })
        
        return results
    
    def _calculate_average_confidence(self, text_results: List[Dict]) -> float:
        """Calculate average confidence score."""
        if not text_results:
            return 0.0
        
        total_confidence = sum(item['confidence'] for item in text_results)
        return total_confidence / len(text_results)
    
    def _detect_languages(self, text: str) -> List[str]:
        """Detect languages present in the text."""
        languages = []
        
        # Simple language detection
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
        has_english = bool(re.search(r'[a-zA-Z]', text))
        has_numbers = bool(re.search(r'\d', text))
        
        if has_chinese:
            languages.append('Traditional_Chinese')
        if has_english:
            languages.append('English')
        if has_numbers:
            languages.append('Numbers')
        
        return languages if languages else ['Unknown']
    
    def extract_text_from_region(self, screenshot_path: str, region: Tuple[int, int, int, int]) -> Dict:
        """Extract text from specific region of screenshot."""
        try:
            # Load full image
            image = Image.open(screenshot_path)
            
            # Crop to specified region
            x, y, width, height = region
            cropped = image.crop((x, y, x + width, y + height))
            
            # Save cropped region temporarily
            temp_path = Path("temp_region.png")
            cropped.save(temp_path)
            
            # Extract text from cropped region
            result = self.extract_text_from_image(str(temp_path))
            
            # Clean up temporary file
            if temp_path.exists():
                temp_path.unlink()
            
            result['source_region'] = region
            return result
            
        except Exception as e:
            print(f"❌ Region OCR failed: {e}")
            return {"error": str(e), "text": "", "confidence": 0}
    
    def find_text_patterns(self, text: str, patterns: List[str]) -> Dict[str, List]:
        """Find specific text patterns in OCR results."""
        findings = {}
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                findings[pattern] = matches
                
                if matches:
                    print(f"🎯 Found pattern '{pattern}': {len(matches)} matches")
                
            except Exception as e:
                print(f"⚠️ Pattern search failed for '{pattern}': {e}")
                findings[pattern] = []
        
        return findings
    
    def analyze_comfyui_state(self, screenshot_path: str) -> Dict:
        """Specialized analysis for ComfyUI interface."""
        try:
            ocr_result = self.extract_text_from_image(screenshot_path)
            full_text = ocr_result.get('full_text', '')
            
            # ComfyUI specific patterns
            patterns = {
                'progress': r'(\d+)%',
                'queue': r'[Qq]ueue[:\s]*(\d+)',
                'status': r'[Ss]tatus[:\s]*(\w+)',
                'error': r'[Ee]rror[:\s]*(.+)',
                'completed': r'[Cc]omplete|[Ff]inished|[Dd]one'
            }
            
            analysis = {
                "screenshot_path": screenshot_path,
                "ocr_confidence": ocr_result.get('confidence_avg', 0),
                "full_text": full_text,
                "state_analysis": {}
            }
            
            # Analyze each pattern
            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                analysis["state_analysis"][pattern_name] = matches
            
            # Determine overall status
            if analysis["state_analysis"]["completed"]:
                analysis["overall_status"] = "completed"
            elif analysis["state_analysis"]["error"]:
                analysis["overall_status"] = "error"
            elif analysis["state_analysis"]["progress"]:
                progress_values = [int(m) for m in analysis["state_analysis"]["progress"]]
                max_progress = max(progress_values) if progress_values else 0
                analysis["overall_status"] = f"running ({max_progress}%)"
            else:
                analysis["overall_status"] = "unknown"
            
            print(f"🎨 ComfyUI State: {analysis['overall_status']}")
            return analysis
            
        except Exception as e:
            print(f"❌ ComfyUI analysis failed: {e}")
            return {"error": str(e)}

def main():
    """Example usage and testing."""
    import time
    
    ocr = TesseractOCR()
    
    if not ocr.tesseract_available:
        print("❌ Tesseract not available. Please install:")
        print("   1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   2. Install Python: pip install pytesseract opencv-python pillow")
        print("   3. Download language packs: chi_tra.traineddata")
        return
    
    try:
        print("🦞 ClawClaw Desktop Vision - OCR Testing")
        print("=" * 50)
        
        # Create test image with text (if we have screenshot)
        test_screenshots = list(Path("screenshots").glob("*.png")) if Path("screenshots").exists() else []
        
        if test_screenshots:
            # Test with existing screenshot
            test_image = test_screenshots[0]
            print(f"\\n🧪 Testing OCR with: {test_image}")
            
            result = ocr.extract_text_from_image(str(test_image))
            
            if result.get('full_text'):
                print(f"📝 Extracted text ({len(result['full_text'])} chars):")
                print(f"   {result['full_text'][:200]}...")
                print(f"📊 Average confidence: {result['confidence_avg']:.1f}%")
                print(f"🌐 Languages: {', '.join(result['languages_detected'])}")
            else:
                print("ℹ️ No text detected in the image")
                
        else:
            print("ℹ️ No test screenshots found. Run screenshot-manager.py first.")
        
        print("\\n✅ OCR testing completed!")
        
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()