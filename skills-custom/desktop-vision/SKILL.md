---
name: desktop-vision
description: Desktop visual monitoring and OCR text recognition using local Tesseract engine. Captures screenshots, extracts text content, and monitors application states without cloud dependencies. Use when: (1) Need to monitor ComfyUI or other GUI applications, (2) Extract text from images or screenshots, (3) Analyze desktop application states, (4) Automate tasks requiring visual feedback, (5) Track progress of visual applications.
---

# Desktop Vision: Visual Monitoring and OCR Recognition

桌面視覺監控與文字識別系統，使用本地 Tesseract 引擎提供螢幕截圖和文字提取功能。

## Core Function

This skill provides comprehensive desktop visual capabilities:

1. **Screenshot capture** - Full screen, regions, and application windows
2. **OCR text recognition** - Tesseract-based local text extraction  
3. **Application monitoring** - Visual state tracking for GUI apps
4. **Change detection** - Monitor visual changes over time
5. **Text analysis** - Extract and analyze text content from images

## When to Use

### Automatic Triggers
- ComfyUI progress monitoring needs
- Application crash or error detection
- Visual confirmation of automated tasks
- Text extraction from images or PDFs

### Manual Usage
- `/desktop-vision screenshot` - Capture current desktop
- `/desktop-vision ocr "image.png"` - Extract text from image
- `/desktop-vision monitor "ComfyUI"` - Monitor application state
- `/desktop-vision analyze "region"` - Analyze specific screen area

## Technical Architecture

### Screenshot System

#### Windows API Integration
```python
import ctypes
from ctypes import wintypes
import win32gui
import win32ui
from PIL import Image

class DesktopCapture:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
    
    def capture_screen(self, region=None):
        """Capture full screen or specified region"""
        if region is None:
            width = self.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            height = self.user32.GetSystemMetrics(1) # SM_CYSCREEN
            region = (0, 0, width, height)
        
        return self._capture_region(*region)
```

#### Application Window Detection
```python
def find_application_window(app_name):
    """Find application window by name or process"""
    windows = []
    
    def enum_handler(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if app_name.lower() in window_text.lower():
                windows.append({
                    'hwnd': hwnd,
                    'title': window_text,
                    'rect': win32gui.GetWindowRect(hwnd)
                })
    
    win32gui.EnumWindows(enum_handler, windows)
    return windows
```

### OCR Text Recognition

#### Tesseract Configuration
```python
import pytesseract
import cv2
import numpy as np
from PIL import Image

class OCRProcessor:
    def __init__(self):
        # Configure Tesseract for Traditional Chinese + English
        self.config = {
            'lang': 'chi_tra+eng',
            'config': '--oem 3 --psm 6'  # LSTM engine, uniform text block
        }
        
        # Image preprocessing pipeline
        self.preprocessing_steps = [
            self.grayscale_conversion,
            self.noise_reduction,
            self.contrast_enhancement,
            self.text_deskew
        ]
    
    def extract_text(self, image_path, preprocess=True):
        """Extract text from image using Tesseract OCR"""
        try:
            image = Image.open(image_path)
            
            if preprocess:
                image = self.preprocess_image(image)
            
            # OCR with confidence scores
            data = pytesseract.image_to_data(image, **self.config, output_type=pytesseract.Output.DICT)
            
            # Filter results by confidence
            text_results = []
            for i, confidence in enumerate(data['conf']):
                if int(confidence) > 30:  # Confidence threshold
                    text_results.append({
                        'text': data['text'][i],
                        'confidence': confidence,
                        'bbox': (data['left'][i], data['top'][i], 
                               data['width'][i], data['height'][i])
                    })
            
            return text_results
            
        except Exception as e:
            print(f"❌ OCR failed: {e}")
            return []
```

#### Image Preprocessing
```python
def preprocess_image(self, image):
    """Enhance image for better OCR accuracy"""
    # Convert PIL to OpenCV format
    opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    # Apply preprocessing pipeline
    for step in self.preprocessing_steps:
        opencv_image = step(opencv_image)
    
    # Convert back to PIL
    return Image.fromarray(cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB))

def grayscale_conversion(self, image):
    """Convert to grayscale for better text recognition"""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def noise_reduction(self, image):
    """Remove noise to improve text clarity"""
    return cv2.medianBlur(image, 3)

def contrast_enhancement(self, image):
    """Enhance contrast for better character definition"""
    return cv2.convertScaleAbs(image, alpha=1.5, beta=30)

def text_deskew(self, image):
    """Correct text skew for better recognition"""
    coords = np.column_stack(np.where(image > 0))
    if len(coords) > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        if abs(angle) > 0.5:  # Only correct significant skew
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return image
```

### Application Monitoring

#### ComfyUI Specific Monitoring
```python
class ComfyUIMonitor:
    def __init__(self, vision_system):
        self.vision = vision_system
        self.comfyui_patterns = {
            'progress': r'(\d+)%',
            'queue': r'Queue: (\d+)',
            'status': r'Status: (\w+)',
            'error': r'Error: (.+)',
            'completion': r'Finished|Complete|Done'
        }
    
    def get_generation_progress(self):
        """Monitor ComfyUI generation progress"""
        try:
            # Find ComfyUI window
            windows = self.vision.find_application_window("ComfyUI")
            
            if not windows:
                return {"status": "not_found", "message": "ComfyUI not detected"}
            
            # Capture ComfyUI window
            comfyui_window = windows[0]
            screenshot = self.vision.capture_window(comfyui_window['hwnd'])
            
            # Extract text from screenshot
            ocr_results = self.vision.ocr.extract_text(screenshot)
            
            # Analyze for progress indicators
            analysis = self._analyze_comfyui_state(ocr_results)
            
            return {
                "status": "active",
                "progress": analysis.get("progress", "unknown"),
                "queue_size": analysis.get("queue", 0),
                "current_status": analysis.get("status", "running"),
                "errors": analysis.get("errors", []),
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _analyze_comfyui_state(self, ocr_results):
        """Analyze OCR results for ComfyUI state information"""
        import re
        
        analysis = {}
        full_text = " ".join([r['text'] for r in ocr_results if r['confidence'] > 50])
        
        # Extract progress percentage
        progress_match = re.search(self.comfyui_patterns['progress'], full_text)
        if progress_match:
            analysis['progress'] = int(progress_match.group(1))
        
        # Extract queue information
        queue_match = re.search(self.comfyui_patterns['queue'], full_text)
        if queue_match:
            analysis['queue'] = int(queue_match.group(1))
        
        # Check for completion
        if re.search(self.comfyui_patterns['completion'], full_text, re.IGNORECASE):
            analysis['status'] = 'completed'
        
        # Check for errors
        error_match = re.search(self.comfyui_patterns['error'], full_text)
        if error_match:
            analysis['errors'] = [error_match.group(1)]
        
        return analysis
```

## Usage Examples

### Basic Screenshot and OCR
```python
from desktop_vision import DesktopVision

vision = DesktopVision()

# Capture full screen
screenshot = vision.capture_screen()

# Extract all text
text_data = vision.extract_text(screenshot)

# Print recognized text with confidence
for item in text_data:
    if item['confidence'] > 70:
        print(f"Text: {item['text']} (Confidence: {item['confidence']}%)")
```

### ComfyUI Progress Monitoring
```python
monitor = ComfyUIMonitor(vision)

# Check current progress
progress = monitor.get_generation_progress()

if progress['status'] == 'active':
    print(f"🎨 ComfyUI Progress: {progress['progress']}%")
    print(f"📊 Queue: {progress['queue_size']} items")
else:
    print(f"⚠️ ComfyUI Status: {progress['status']}")
```

### Region-Specific Analysis
```python
# Monitor specific screen region for changes
region = (100, 100, 800, 600)  # x, y, width, height
screenshot = vision.capture_region(*region)
text_content = vision.extract_text(screenshot)

# Analyze for specific patterns
keywords = ['error', 'complete', 'progress', '100%']
detected = vision.find_keywords_in_text(text_content, keywords)
```

## Dependencies and Setup

### Required Software
```bash
# Tesseract OCR Engine
choco install tesseract

# Python packages
pip install pytesseract opencv-python pillow pywin32
```

### Language Data Setup
```bash
# Download Traditional Chinese language pack
# Place in: C:\Program Files\Tesseract-OCR\tessdata\
- chi_tra.traineddata  (Traditional Chinese)
- eng.traineddata      (English - usually included)
```

### Configuration Files
- `configs/ocr-settings.json` - OCR engine configuration
- `configs/window-patterns.json` - Application window detection
- `references/tesseract-setup.md` - Detailed setup instructions

## Integration with OpenClaw

### Tool Registration
```python
# Register as OpenClaw tools
tools = [
    "desktop_screenshot",    # Basic screenshot functionality
    "desktop_ocr",          # Text recognition from images  
    "desktop_monitor",      # Application state monitoring
    "desktop_analyze"       # Comprehensive visual analysis
]
```

### Security Features
- **Privacy protection**: Automatic sensitive content detection
- **Application blacklist**: Skip password managers, banking apps
- **User confirmation**: Prompt before capturing sensitive screens
- **Secure storage**: Encrypted temporary screenshot storage

## Performance Optimization

### Efficient Processing
- **Region targeting**: Capture only necessary screen areas
- **Image compression**: Optimize file sizes for storage and processing
- **Batch processing**: Handle multiple screenshots efficiently
- **Cache management**: Intelligent cleanup of temporary files

### Resource Management
- **Memory limits**: Prevent excessive screenshot storage
- **CPU throttling**: Limit OCR processing intensity
- **Disk cleanup**: Automatic cleanup of old screenshots
- **Process isolation**: Prevent interference with other applications

## Benefits

### Visual Automation
- **Real-time monitoring**: Track application progress visually
- **Error detection**: Automatically detect visual error messages
- **State verification**: Confirm operation success through visuals
- **Progress tracking**: Monitor long-running visual tasks

### Text Intelligence
- **Multilingual OCR**: Support Traditional Chinese and English
- **High accuracy**: Advanced image preprocessing for better results
- **Structured output**: Organized text data with confidence scores
- **Pattern recognition**: Identify specific text patterns and keywords

### System Integration
- **Non-invasive**: Works with any GUI application
- **Platform native**: Uses Windows APIs for optimal performance
- **Secure design**: Privacy-first approach with user control
- **Extensible**: Easy to add new monitoring capabilities

---

**ClawClaw 的視覺超能力 - 看見桌面，理解世界！** 👁️🦞🖥️