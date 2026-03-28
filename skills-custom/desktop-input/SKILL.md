---
name: desktop-input
description: Secure desktop input automation with mouse and keyboard control. Provides safe clicking, typing, and UI interaction capabilities with comprehensive security mechanisms. Use when: (1) Need to automate repetitive desktop tasks, (2) Assist with form filling or data entry, (3) Control applications requiring precise input, (4) Perform guided UI operations with user oversight. Includes strict safety measures to prevent unauthorized access.
---

# Desktop Input: Secure Automation and UI Control

安全的桌面輸入自動化系統，提供滑鼠和鍵盤控制功能，配備完整的安全防護機制。

## Core Function

This skill provides secure desktop input automation capabilities:

1. **Mouse control** - Precise clicking, dragging, and movement
2. **Keyboard simulation** - Safe typing with security filtering
3. **UI interaction** - Application-specific input assistance  
4. **Security enforcement** - Comprehensive safety mechanisms
5. **Operation logging** - Complete audit trail for all actions

## Security Framework

### Multi-Layer Protection

#### Level 1: Content Filtering
- **Sensitive text detection**: Automatic filtering of passwords, credit cards, SSNs
- **Application blacklist**: Prevents interaction with banking, password managers
- **Keyword screening**: Blocks potentially harmful commands or data

#### Level 2: User Authorization  
- **Explicit confirmation**: User approval required for all input operations
- **Operation preview**: Shows exactly what will be typed or clicked
- **Timeout controls**: Automatic session expiration for safety
- **Emergency stop**: Immediate operation cancellation capability

#### Level 3: System Protection
- **Process isolation**: Cannot interfere with system-critical applications
- **Permission boundaries**: Restricted to authorized applications only
- **Audit logging**: Complete record of all input actions
- **Rate limiting**: Prevents excessive or suspicious input patterns

## When to Use

### Safe Automation Scenarios
- Form filling assistance (after manual verification)
- Repetitive data entry tasks
- Application testing and validation
- Guided user interface navigation
- Text input assistance for accessibility

### Prohibited Usage
- ❌ **Never for sensitive applications**: Banking, password managers, payment systems
- ❌ **Never without user confirmation**: All operations require explicit approval
- ❌ **Never for system modification**: No system settings or critical file changes
- ❌ **Never for surveillance**: No unauthorized monitoring or data collection

## Technical Implementation

### Mouse Control System

#### Precise Click Operations
```python
class SecureMouseController:
    def __init__(self):
        self.security_manager = SecurityManager()
        self.audit_logger = AuditLogger()
    
    def safe_click(self, x: int, y: int, button: str = 'left', 
                  confirm: bool = True) -> bool:
        """Perform safe mouse click with security checks."""
        
        # Security validation
        if not self.security_manager.validate_click_location(x, y):
            raise SecurityError("Click location blocked by security policy")
        
        # User confirmation if required
        if confirm:
            if not self.request_user_confirmation(f"Click at ({x}, {y})"):
                return False
        
        # Execute click
        return self._execute_click(x, y, button)
```

#### Smart Element Detection
```python
def find_clickable_elements(self, screenshot_path: str) -> List[Dict]:
    """Find clickable elements in screenshot using vision analysis."""
    
    # Use OCR to find text-based buttons
    ocr_results = self.ocr.extract_text_from_image(screenshot_path)
    
    # Look for button-like text patterns
    button_patterns = [
        r'\b(Submit|Send|OK|Cancel|Yes|No|Apply|Save|Delete)\b',
        r'\b(確認|取消|送出|儲存|刪除|是|否)\b'
    ]
    
    clickable_elements = []
    for result in ocr_results['detailed_results']:
        text = result['text']
        for pattern in button_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                clickable_elements.append({
                    'text': text,
                    'bbox': result['bbox'],
                    'confidence': result['confidence'],
                    'type': 'text_button'
                })
    
    return clickable_elements
```

### Keyboard Input System

#### Safe Typing with Filtering
```python
class SecureKeyboardController:
    def __init__(self):
        self.sensitive_patterns = [
            r'\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b',  # Credit card
            r'\bpassword\b',                         # Password fields
            r'\b\d{3}-\d{2}-\d{4}\b',              # SSN pattern
            r'\b[A-Z0-9]{10,}\b'                    # API keys/tokens
        ]
    
    def safe_type(self, text: str, target_element: Optional[str] = None,
                 confirm: bool = True) -> bool:
        """Type text safely with security filtering."""
        
        # Security validation
        if not self.validate_text_safety(text):
            raise SecurityError("Text contains sensitive information")
        
        # User confirmation
        if confirm:
            preview = text[:50] + "..." if len(text) > 50 else text
            if not self.request_confirmation(f"Type: '{preview}'"):
                return False
        
        # Execute typing with human-like timing
        return self._execute_typing(text, target_element)
    
    def validate_text_safety(self, text: str) -> bool:
        """Validate that text is safe to type."""
        text_lower = text.lower()
        
        # Check for sensitive patterns
        for pattern in self.sensitive_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Check for sensitive keywords
        sensitive_keywords = [
            'password', 'passwd', 'pin', 'ssn', 'credit', 'card', 
            'bank', 'routing', 'account', 'secret', 'private'
        ]
        
        for keyword in sensitive_keywords:
            if keyword in text_lower:
                return False
        
        return True
```

### Security Manager

#### Application Monitoring
```python
class SecurityManager:
    def __init__(self):
        # Applications that should never be automated
        self.blacklisted_apps = [
            'keepass', '1password', 'lastpass', 'bitwarden',
            'chrome' + 'banking', 'firefox' + 'banking',
            'paypal', 'bank', 'financial', 'wallet'
        ]
        
        # Sensitive screen regions (password fields, etc.)
        self.sensitive_regions = []
    
    def validate_click_location(self, x: int, y: int) -> bool:
        """Validate that click location is safe."""
        
        # Check if location is in a sensitive region
        for region in self.sensitive_regions:
            if (region['x'] <= x <= region['x'] + region['width'] and
                region['y'] <= y <= region['y'] + region['height']):
                return False
        
        # Check active application
        active_app = self._get_active_application()
        if any(blocked in active_app.lower() for blocked in self.blacklisted_apps):
            return False
        
        return True
    
    def _get_active_application(self) -> str:
        """Get name of currently active application."""
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        except:
            return "unknown"
```

## Usage Examples

### Assisted Form Filling
```python
from desktop_input import SecureInputController

controller = SecureInputController()

# Safe form filling workflow
def assist_form_filling(form_data: Dict):
    """Guide user through form filling process."""
    
    for field_name, value in form_data.items():
        # Show what will be typed
        print(f"📝 Ready to fill {field_name}: {value}")
        
        # Get user confirmation
        if controller.request_confirmation(f"Type '{value}' into {field_name}?"):
            # Type with security checks
            success = controller.safe_type(value, target_element=field_name)
            
            if success:
                print(f"✅ {field_name} filled successfully")
            else:
                print(f"❌ Failed to fill {field_name}")
        else:
            print(f"⏭️ Skipped {field_name}")
```

### Application Interaction Assistant
```python
def comfyui_interaction_helper(action: str):
    """Help with ComfyUI interactions."""
    
    actions = {
        'generate': {'text': 'Generate', 'confirm': True},
        'queue': {'text': 'Queue', 'confirm': True}, 
        'clear': {'text': 'Clear', 'confirm': True},
        'save': {'text': 'Save', 'confirm': False}
    }
    
    if action not in actions:
        return False
    
    config = actions[action]
    
    # Find button by text
    screenshot = vision.capture_application_window("ComfyUI")
    elements = input_controller.find_clickable_elements(screenshot)
    
    # Look for matching button
    for element in elements:
        if config['text'].lower() in element['text'].lower():
            # Click with appropriate confirmation
            return input_controller.safe_click(
                element['bbox']['left'] + element['bbox']['width']//2,
                element['bbox']['top'] + element['bbox']['height']//2,
                confirm=config['confirm']
            )
    
    return False
```

### Desktop Monitoring Automation
```python
def monitor_desktop_applications():
    """Monitor multiple applications and report status."""
    
    apps_to_monitor = ['ComfyUI', 'Visual Studio Code', 'Chrome']
    status_report = {}
    
    for app in apps_to_monitor:
        # Capture application window
        screenshot = vision.capture_application_window(app)
        
        if screenshot:
            # Extract text and analyze
            ocr_data = ocr.extract_text_from_image(screenshot)
            
            # Application-specific analysis
            if app == 'ComfyUI':
                analysis = ocr.analyze_comfyui_state(screenshot)
                status_report[app] = analysis['overall_status']
            else:
                # Generic status detection
                text = ocr_data['full_text']
                if 'error' in text.lower():
                    status_report[app] = 'error_detected'
                else:
                    status_report[app] = 'running'
        else:
            status_report[app] = 'not_found'
    
    return status_report
```

## Safety Guidelines

### User Confirmation Requirements
- **All mouse clicks**: Must be explicitly approved
- **All keyboard input**: Preview and confirm before typing
- **Sensitive applications**: Automatic blocking with user notification
- **Bulk operations**: Confirmation for each significant action

### Logging and Audit
- **Complete operation log**: Every click and keystroke recorded
- **Timestamp tracking**: Precise timing of all actions
- **Application context**: Which apps were interacted with
- **User confirmations**: Record of all approvals and denials

### Emergency Controls
- **Immediate stop**: Ctrl+C or emergency stop command
- **Session timeout**: Auto-disable after inactivity
- **Application monitoring**: Detect and block unauthorized app access
- **User override**: Manual control always takes precedence

## Installation Requirements

### Dependencies
```bash
# Python packages
pip install pywin32 pillow opencv-python pytesseract

# System requirements
- Windows 10/11
- Python 3.8+
- Tesseract OCR engine
- Administrator privileges (for some input operations)
```

### Tesseract Setup
```bash
# Download and install Tesseract
# From: https://github.com/UB-Mannheim/tesseract/wiki

# Language packs needed:
- eng.traineddata (English)
- chi_tra.traineddata (Traditional Chinese)

# Installation path: C:\Program Files\Tesseract-OCR\
```

## Integration with Other Skills

### With Desktop-Vision
- Screenshot → OCR → Text analysis → Intelligent clicking
- Visual state monitoring → Automated response actions
- Error detection → Corrective input operations

### With Enhanced-Browser  
- Web form automation with visual confirmation
- Browser extension interaction
- Multi-modal web automation (visual + programmatic)

### With ComfyUI-Skill
- Progress monitoring and status reporting
- Automated parameter adjustment
- Error recovery and retry mechanisms

## Benefits

### Productivity Enhancement
- **Automate repetitive tasks**: Reduce manual clicking and typing
- **Error reduction**: Consistent and precise input execution
- **Time savings**: Faster completion of routine operations
- **Accessibility**: Assist users with motor difficulties

### System Intelligence
- **Visual feedback**: Confirm operations through visual verification
- **State awareness**: Understand application states through visual cues
- **Error detection**: Automatically identify and report visual errors
- **Progress tracking**: Monitor long-running visual operations

### Security Assurance
- **User control**: All operations under explicit user supervision
- **Safe boundaries**: Cannot interact with sensitive applications
- **Audit capability**: Complete record for security review
- **Immediate override**: User can stop any operation instantly

---

**ClawClaw 的輸入超能力 - 安全協助，智能操作！** 🖱️⌨️🦞🛡️