#!/usr/bin/env python3
"""
Desktop Screenshot Manager
=========================

Advanced screenshot capabilities for desktop monitoring and visual automation.
Supports full screen, regional, and application-specific capture with Windows API.

Author: ClawClaw AI Services
Version: 1.0
"""

import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

try:
    import ctypes
    from ctypes import wintypes
    import win32gui
    import win32ui
    import win32con
    from PIL import Image
    WINDOWS_APIS_AVAILABLE = True
except ImportError:
    WINDOWS_APIS_AVAILABLE = False
    print("⚠️ Windows APIs not available. Install pywin32 for full functionality.")

class ScreenshotManager:
    def __init__(self, output_dir: str = "screenshots"):
        """Initialize screenshot manager."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Screen dimensions
        self.screen_width = self._get_screen_width()
        self.screen_height = self._get_screen_height()
        
        # Screenshot quality settings
        self.default_quality = 90
        self.default_format = 'PNG'
        
        print(f"🖥️ Screen resolution: {self.screen_width}x{self.screen_height}")
        print(f"📁 Output directory: {self.output_dir}")
    
    def _get_screen_width(self) -> int:
        """Get screen width using Windows API."""
        if WINDOWS_APIS_AVAILABLE:
            return ctypes.windll.user32.GetSystemMetrics(0)
        return 1920  # fallback
    
    def _get_screen_height(self) -> int:
        """Get screen height using Windows API.""" 
        if WINDOWS_APIS_AVAILABLE:
            return ctypes.windll.user32.GetSystemMetrics(1)
        return 1080  # fallback
    
    def capture_fullscreen(self, filename: Optional[str] = None) -> str:
        """Capture full screen screenshot."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"fullscreen-{timestamp}.png"
        
        try:
            if WINDOWS_APIS_AVAILABLE:
                screenshot_path = self._capture_with_windows_api(
                    0, 0, self.screen_width, self.screen_height, filename
                )
            else:
                screenshot_path = self._capture_with_powershell(filename)
            
            print(f"📸 Full screen captured: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            print(f"❌ Full screen capture failed: {e}")
            raise
    
    def capture_region(self, x: int, y: int, width: int, height: int, 
                      filename: Optional[str] = None) -> str:
        """Capture specific screen region."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"region-{x}-{y}-{width}x{height}-{timestamp}.png"
        
        # Validate coordinates
        if x < 0 or y < 0 or x + width > self.screen_width or y + height > self.screen_height:
            raise ValueError(f"Invalid region coordinates: ({x},{y},{width},{height})")
        
        try:
            if WINDOWS_APIS_AVAILABLE:
                screenshot_path = self._capture_with_windows_api(x, y, width, height, filename)
            else:
                screenshot_path = self._capture_region_powershell(x, y, width, height, filename)
            
            print(f"📸 Region captured: {width}x{height} at ({x},{y}) → {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            print(f"❌ Region capture failed: {e}")
            raise
    
    def capture_application_window(self, app_name: str, filename: Optional[str] = None) -> Optional[str]:
        """Capture specific application window."""
        if not WINDOWS_APIS_AVAILABLE:
            print("❌ Application window capture requires Windows APIs")
            return None
        
        try:
            # Find application windows
            windows = self._find_application_windows(app_name)
            
            if not windows:
                print(f"⚠️ No windows found for application: {app_name}")
                return None
            
            # Use the first visible window
            target_window = windows[0]
            rect = target_window['rect']
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                safe_app_name = "".join(c for c in app_name if c.isalnum())
                filename = f"app-{safe_app_name}-{timestamp}.png"
            
            # Capture window region
            screenshot_path = self._capture_with_windows_api(
                rect[0], rect[1], 
                rect[2] - rect[0], rect[3] - rect[1],
                filename
            )
            
            print(f"📸 Application window captured: {app_name} → {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            print(f"❌ Application capture failed: {e}")
            return None
    
    def _find_application_windows(self, app_name: str) -> List[Dict]:
        """Find application windows by name."""
        windows = []
        
        def enum_handler(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                if app_name.lower() in window_text.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        'hwnd': hwnd,
                        'title': window_text,
                        'rect': rect
                    })
        
        win32gui.EnumWindows(enum_handler, windows)
        return windows
    
    def _capture_with_windows_api(self, x: int, y: int, width: int, height: int, filename: str) -> Path:
        """Capture screenshot using Windows API."""
        output_path = self.output_dir / filename
        
        # Get device contexts
        desktop_dc = win32gui.GetWindowDC(0)
        img_dc = win32ui.CreateDCFromHandle(desktop_dc)
        mem_dc = img_dc.CreateCompatibleDC()
        
        # Create bitmap
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(img_dc, width, height)
        mem_dc.SelectObject(bitmap)
        
        # Copy screen content to bitmap
        mem_dc.BitBlt((0, 0), (width, height), img_dc, (x, y), win32con.SRCCOPY)
        
        # Convert to PIL Image and save
        bitmap_info = bitmap.GetInfo()
        bitmap_buffer = bitmap.GetBitmapBits(True)
        
        img = Image.frombuffer(
            'RGB', 
            (bitmap_info['bmWidth'], bitmap_info['bmHeight']),
            bitmap_buffer, 'raw', 'BGRX', 0, 1
        )
        
        img.save(output_path, self.default_format, quality=self.default_quality)
        
        # Cleanup
        mem_dc.DeleteDC()
        img_dc.DeleteDC()
        win32gui.ReleaseDC(0, desktop_dc)
        
        return output_path
    
    def _capture_with_powershell(self, filename: str) -> Path:
        """Fallback screenshot using PowerShell."""
        output_path = self.output_dir / filename
        
        powershell_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save('{output_path}', [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", powershell_script],
            capture_output=True, text=True, check=True
        )
        
        return output_path
    
    def _capture_region_powershell(self, x: int, y: int, width: int, height: int, filename: str) -> Path:
        """Capture region using PowerShell."""
        output_path = self.output_dir / filename
        
        powershell_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $bounds = New-Object System.Drawing.Rectangle {x}, {y}, {width}, {height}
        $bitmap = New-Object System.Drawing.Bitmap {width}, {height}
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen({x}, {y}, 0, 0, [System.Drawing.Size]::new({width}, {height}))
        $bitmap.Save('{output_path}', [System.Drawing.Imaging.ImageFormat]::Png)
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command", powershell_script],
            capture_output=True, text=True, check=True
        )
        
        return output_path
    
    def get_screen_info(self) -> Dict:
        """Get comprehensive screen information."""
        info = {
            "screen_count": 1,  # Will be enhanced for multi-monitor
            "primary_screen": {
                "width": self.screen_width,
                "height": self.screen_height,
                "dpi": self._get_dpi()
            },
            "capture_capabilities": {
                "fullscreen": True,
                "region": True,
                "application_windows": WINDOWS_APIS_AVAILABLE,
                "multi_monitor": False  # Future enhancement
            }
        }
        
        if WINDOWS_APIS_AVAILABLE:
            info["available_windows"] = self._list_visible_windows()
        
        return info
    
    def _get_dpi(self) -> int:
        """Get screen DPI setting."""
        if WINDOWS_APIS_AVAILABLE:
            try:
                dc = ctypes.windll.user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, dc)
                return dpi
            except:
                pass
        return 96  # Standard DPI fallback
    
    def _list_visible_windows(self) -> List[Dict]:
        """List all visible windows."""
        windows = []
        
        def enum_handler(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if title:  # Only include windows with titles
                        rect = win32gui.GetWindowRect(hwnd)
                        windows.append({
                            'title': title,
                            'rect': rect,
                            'size': (rect[2] - rect[0], rect[3] - rect[1])
                        })
                except:
                    pass
        
        win32gui.EnumWindows(enum_handler, windows)
        return windows
    
    def cleanup_old_screenshots(self, max_age_hours: int = 24, max_files: int = 100):
        """Clean up old screenshot files."""
        try:
            screenshot_files = list(self.output_dir.glob("*.png"))
            screenshot_files.extend(self.output_dir.glob("*.jpg"))
            
            # Sort by creation time
            screenshot_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            current_time = time.time()
            removed_count = 0
            
            # Remove files older than max_age_hours
            for file_path in screenshot_files:
                file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
                
                if file_age_hours > max_age_hours:
                    file_path.unlink()
                    removed_count += 1
                    continue
                
                # Keep only the most recent max_files
                if len(screenshot_files) - removed_count > max_files:
                    file_path.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                print(f"🧹 Cleaned up {removed_count} old screenshot files")
            
        except Exception as e:
            print(f"⚠️ Screenshot cleanup warning: {e}")

def main():
    """Example usage and testing."""
    manager = ScreenshotManager("test_screenshots")
    
    try:
        print("🦞 ClawClaw Desktop Vision - Screenshot Testing")
        print("=" * 50)
        
        # Test 1: Full screen capture
        print("\\n🧪 Test 1: Full Screen Capture")
        fullscreen_path = manager.capture_fullscreen()
        print(f"✅ Full screen saved to: {fullscreen_path}")
        
        # Test 2: Region capture
        print("\\n🧪 Test 2: Region Capture") 
        region_path = manager.capture_region(100, 100, 800, 600)
        print(f"✅ Region saved to: {region_path}")
        
        # Test 3: Application window (if available)
        print("\\n🧪 Test 3: Application Window Capture")
        if WINDOWS_APIS_AVAILABLE:
            app_path = manager.capture_application_window("ComfyUI")
            if app_path:
                print(f"✅ Application window saved to: {app_path}")
            else:
                print("ℹ️ ComfyUI window not found")
        else:
            print("⚠️ Windows API not available for application capture")
        
        # Test 4: Screen information
        print("\\n🧪 Test 4: Screen Information")
        screen_info = manager.get_screen_info()
        print(f"📊 Screen info: {json.dumps(screen_info, indent=2)}")
        
        # Test 5: Cleanup test
        print("\\n🧪 Test 5: Cleanup Test")
        manager.cleanup_old_screenshots(max_age_hours=0, max_files=2)  # Aggressive cleanup for test
        
        print("\\n✅ All screenshot tests completed!")
        
    except Exception as e:
        print(f"❌ Screenshot test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()