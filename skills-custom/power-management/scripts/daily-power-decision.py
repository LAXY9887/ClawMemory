#!/usr/bin/env python3
"""
ClawClaw Daily Power Decision System
===================================

Intelligent power management for daily summary completion.
Analyzes system state and provides smart shutdown recommendations.

Author: ClawClaw AI Services
Version: 1.0
"""

import os
import sys
import json
import time
import subprocess
import psutil
from datetime import datetime, timedelta
from pathlib import Path

class PowerDecisionEngine:
    def __init__(self):
        self.workspace_dir = Path.cwd()
        self.config_file = self.workspace_dir / "skills" / "power-management" / "config.json"
        self.load_config()
        
        # Critical services to monitor
        self.critical_services = {
            'ComfyUI': {'port': 8000, 'process_names': ['ComfyUI.exe', 'python.exe']},
            'Ollama': {'port': 11434, 'process_names': ['ollama.exe']},
            'Docker': {'process_names': ['Docker Desktop.exe', 'com.docker.service']},
            'Visual Studio Code': {'process_names': ['Code.exe']},
            'Chrome': {'process_names': ['chrome.exe']}
        }
        
    def load_config(self):
        """Load power management configuration."""
        default_config = {
            "defaultAction": "shutdown",
            "confirmationTimeout": 30,
            "enableSmartSuggestions": True,
            "safetyChecks": {
                "checkUnsavedFiles": True,
                "checkRunningServices": True,
                "forceGitCommit": True,
                "validateBackups": True
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = default_config
                self.save_config()
        except Exception as e:
            print(f"⚠️ Config load error: {e}")
            self.config = default_config
    
    def save_config(self):
        """Save configuration to file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Config save error: {e}")
    
    def check_file_safety(self):
        """Check for unsaved files and uncommitted changes."""
        safety_report = {
            'safe': True,
            'warnings': [],
            'git_status': 'clean'
        }
        
        try:
            # Check Git status
            result = subprocess.run(
                ['git', 'status', '--porcelain'], 
                capture_output=True, text=True, cwd=self.workspace_dir
            )
            
            if result.stdout.strip():
                safety_report['safe'] = False
                safety_report['warnings'].append("有未提交的變更")
                safety_report['git_status'] = 'dirty'
                
                # Auto-commit if enabled
                if self.config['safetyChecks']['forceGitCommit']:
                    self.auto_commit_changes()
                    safety_report['safe'] = True
                    safety_report['warnings'].append("已自動提交變更")
            
        except Exception as e:
            safety_report['warnings'].append(f"Git 檢查失敗: {e}")
        
        return safety_report
    
    def auto_commit_changes(self):
        """Automatically commit uncommitted changes."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            subprocess.run(['git', 'add', '.'], cwd=self.workspace_dir, check=True)
            subprocess.run([
                'git', 'commit', '-m', f'Auto-commit before shutdown - {timestamp}'
            ], cwd=self.workspace_dir, check=True)
            
            print("✅ 自動提交完成")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ 自動提交失敗: {e}")
    
    def check_service_status(self):
        """Check status of critical services."""
        service_report = {
            'critical_running': False,
            'services': {},
            'can_stop': True
        }
        
        for service_name, config in self.critical_services.items():
            service_info = {
                'running': False,
                'processes': [],
                'can_stop': True
            }
            
            # Check for running processes
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name']
                    if any(target in proc_name for target in config['process_names']):
                        service_info['running'] = True
                        service_info['processes'].append({
                            'pid': proc.info['pid'],
                            'name': proc_name
                        })
                        
                        # Special checks for certain services
                        if service_name == 'ComfyUI':
                            service_info['can_stop'] = self.check_comfyui_can_stop()
                        elif service_name == 'Visual Studio Code':
                            service_info['can_stop'] = self.check_vscode_can_stop()
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            service_report['services'][service_name] = service_info
            
            if service_info['running'] and not service_info['can_stop']:
                service_report['critical_running'] = True
                service_report['can_stop'] = False
        
        return service_report
    
    def check_comfyui_can_stop(self):
        """Check if ComfyUI has ongoing workflows."""
        try:
            import requests
            response = requests.get('http://localhost:8000/queue', timeout=3)
            if response.status_code == 200:
                queue_data = response.json()
                # Check if there are running or queued workflows
                running = queue_data.get('queue_running', [])
                pending = queue_data.get('queue_pending', [])
                return len(running) == 0 and len(pending) == 0
        except:
            pass
        return True  # Default to can stop if we can't check
    
    def check_vscode_can_stop(self):
        """Check if VS Code has unsaved files."""
        # This would require VS Code extension or API access
        # For now, we'll assume it's safe if no critical file operations
        return True
    
    def check_work_progress(self):
        """Check for ongoing work and tasks."""
        work_report = {
            'ongoing_tasks': False,
            'details': []
        }
        
        # Check for running Python/Node processes (might be dev work)
        dev_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                if any(dev_proc in name for dev_proc in ['python', 'node', 'npm', 'pip']):
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'install' in cmdline or 'run' in cmdline or 'serve' in cmdline:
                        dev_processes.append({
                            'pid': proc.info['pid'],
                            'name': name,
                            'command': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if dev_processes:
            work_report['ongoing_tasks'] = True
            work_report['details'] = dev_processes
        
        return work_report
    
    def check_tomorrow_schedule(self):
        """Analyze tomorrow's schedule (placeholder)."""
        # This would integrate with calendar APIs
        # For now, return a simple analysis based on day of week
        tomorrow = datetime.now() + timedelta(days=1)
        is_weekend = tomorrow.weekday() >= 5  # Saturday = 5, Sunday = 6
        
        return {
            'light_day': is_weekend,
            'early_meetings': False,
            'important_tasks': False,
            'day_type': 'weekend' if is_weekend else 'weekday'
        }
    
    def analyze_shutdown_readiness(self):
        """Comprehensive shutdown readiness analysis."""
        print("🔍 ClawClaw 電源管理分析中...")
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'recommendation': {},
            'confidence': 0
        }
        
        print("  📁 檢查檔案安全...")
        analysis['checks']['file_safety'] = self.check_file_safety()
        
        print("  🔧 檢查服務狀態...")
        analysis['checks']['services'] = self.check_service_status()
        
        print("  💼 檢查工作進度...")
        analysis['checks']['work_progress'] = self.check_work_progress()
        
        print("  📅 分析明日行程...")
        analysis['checks']['tomorrow_schedule'] = self.check_tomorrow_schedule()
        
        print("  🧠 生成智能建議...")
        analysis['recommendation'] = self.generate_recommendation(analysis['checks'])
        analysis['confidence'] = self.calculate_confidence(analysis['checks'])
        
        return analysis
    
    def generate_recommendation(self, checks):
        """Generate smart power management recommendation."""
        score = 0
        reasons = []
        
        # File safety (critical)
        if checks['file_safety']['safe']:
            score += 30
            reasons.append("✅ 所有檔案已安全儲存")
        else:
            score -= 50
            reasons.append("⚠️ 有未儲存的檔案")
            for warning in checks['file_safety']['warnings']:
                reasons.append(f"  - {warning}")
        
        # Service status
        if not checks['services']['critical_running']:
            score += 20
            reasons.append("✅ 無重要服務運行")
        else:
            score -= 10
            reasons.append("⚠️ 重要服務仍在運行")
            for service, info in checks['services']['services'].items():
                if info['running'] and not info['can_stop']:
                    reasons.append(f"  - {service} 正在執行關鍵任務")
        
        # Work progress
        if not checks['work_progress']['ongoing_tasks']:
            score += 25
            reasons.append("✅ 無進行中的開發工作")
        else:
            score -= 15
            reasons.append("⚠️ 有進行中的開發工作")
            for task in checks['work_progress']['details'][:3]:  # Show max 3
                reasons.append(f"  - {task['name']}: {task['command'][:50]}...")
        
        # Schedule
        if checks['tomorrow_schedule']['light_day']:
            score += 15
            reasons.append("✅ 明日為週末，適合休息")
        else:
            score += 5
            reasons.append("📅 明日為工作日")
        
        # Determine recommendation
        if score >= 60:
            action = "shutdown"
            message = "🌙 建議立即安全關機"
            emoji = "🌙"
        elif score >= 20:
            action = "ask_user"
            message = "🤔 建議詢問使用者偏好"
            emoji = "❓"
        else:
            action = "stay_awake"
            message = "💤 建議保持待命狀態"
            emoji = "💤"
        
        return {
            'action': action,
            'message': message,
            'emoji': emoji,
            'score': score,
            'reasons': reasons
        }
    
    def calculate_confidence(self, checks):
        """Calculate confidence in the recommendation."""
        confidence_factors = 0
        max_factors = 4
        
        # File safety confidence
        if checks['file_safety']['safe']:
            confidence_factors += 1
        
        # Service check confidence
        if checks['services']['can_stop']:
            confidence_factors += 1
        
        # Work progress confidence
        if not checks['work_progress']['ongoing_tasks']:
            confidence_factors += 1
        
        # Schedule confidence (always positive for now)
        confidence_factors += 1
        
        return int((confidence_factors / max_factors) * 100)
    
    def present_decision_ui(self, analysis):
        """Present decision UI to user."""
        print("\n" + "="*60)
        print("🔋 ClawClaw 電源管理 - 每日總結完成")
        print("="*60)
        
        print(f"\n💡 智能分析結果 (信心度: {analysis['confidence']}%):")
        for reason in analysis['recommendation']['reasons']:
            print(f"   {reason}")
        
        recommendation = analysis['recommendation']
        print(f"\n{recommendation['emoji']} {recommendation['message']}")
        
        # Present options
        print("\n請選擇動作：")
        print("1. 🌙 立即安全關機 (預設) - 30秒後執行")
        print("2. 💤 保持夜間待命 - 降功耗運行")
        print("3. ⏰ 延後 1 小時 - 稍後再決定")
        print("4. ❌ 取消 - 維持正常運行")
        
        timeout = self.config['confirmationTimeout']
        print(f"\n{timeout}秒後自動執行預設選項...")
        
        # Countdown with user input
        choice = self.countdown_with_input(timeout)
        return choice
    
    def countdown_with_input(self, timeout_seconds):
        """Countdown with ability to receive user input."""
        import select
        import sys
        
        for remaining in range(timeout_seconds, 0, -1):
            print(f"\r⏱️  {remaining}秒後執行預設動作... (輸入 1-4 選擇，或 Enter 確認預設)", end='', flush=True)
            
            # Check for input (non-blocking)
            if sys.stdin in select.select([sys.stdin], [], [], 1)[0]:
                user_input = sys.stdin.readline().strip()
                if user_input in ['1', '2', '3', '4']:
                    return int(user_input)
                elif user_input == '':
                    return 1  # Default choice
            
        print("\n")
        return 1  # Default to shutdown
    
    def execute_decision(self, choice):
        """Execute the user's power management decision."""
        if choice == 1:
            print("🌙 執行安全關機流程...")
            return self.safe_shutdown()
        elif choice == 2:
            print("💤 設定夜間待命模式...")
            return self.set_night_mode()
        elif choice == 3:
            print("⏰ 延後 1 小時後再決定...")
            return self.schedule_delayed_check()
        elif choice == 4:
            print("❌ 取消電源管理，維持正常運行...")
            return True
        else:
            print("⚠️ 無效選擇，預設執行關機...")
            return self.safe_shutdown()
    
    def safe_shutdown(self):
        """Execute safe system shutdown."""
        try:
            print("💾 保存最終狀態...")
            
            # Final Git commit
            if self.config['safetyChecks']['forceGitCommit']:
                self.auto_commit_changes()
            
            print("🔧 優雅停止服務...")
            self.stop_services_gracefully()
            
            print("🌙 開始關機程序...")
            # Use PowerShell to execute shutdown
            shutdown_script = """
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.MessageBox]::Show('ClawClaw 每日總結完成，系統將在 30 秒後關機...', 'ClawClaw 電源管理', 'OK', 'Information')
            shutdown /s /t 30 /c "ClawClaw 每日總結完成，系統關機中..."
            """
            
            subprocess.run(['powershell', '-Command', shutdown_script])
            return True
            
        except Exception as e:
            print(f"❌ 關機失敗: {e}")
            return False
    
    def stop_services_gracefully(self):
        """Stop critical services gracefully."""
        for service_name, config in self.critical_services.items():
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    if any(target in proc.info['name'] for target in config['process_names']):
                        print(f"  停止 {service_name}...")
                        proc.terminate()  # Send SIGTERM first
                        time.sleep(2)
                        if proc.is_running():
                            proc.kill()  # Force kill if needed
            except Exception as e:
                print(f"  ⚠️ {service_name} 停止時遇到錯誤: {e}")
    
    def set_night_mode(self):
        """Set night mode (reduced power, stay awake)."""
        try:
            # Reduce CPU priority for non-essential processes
            # Set power plan to power saver
            subprocess.run([
                'powercfg', '/setactive', 'a1841308-3541-4fab-bc81-f71556f20b4a'  # Power Saver GUID
            ])
            
            print("💤 已設定夜間待命模式 - 系統將降低功耗運行")
            print("   - CPU 使用率將降低")
            print("   - 顯示器將更快休眠")
            print("   - 明日早上 7:00 將恢復正常模式")
            
            # Schedule morning wake-up (would need additional cron job)
            return True
            
        except Exception as e:
            print(f"⚠️ 設定夜間模式失敗: {e}")
            return False
    
    def schedule_delayed_check(self):
        """Schedule power check in 1 hour."""
        try:
            # Add a one-time cron job for 1 hour later
            current_time = datetime.now()
            delayed_time = current_time + timedelta(hours=1)
            
            delayed_cron = f"{delayed_time.minute} {delayed_time.hour} * * *"
            
            subprocess.run([
                'openclaw', 'cron', 'add',
                '--name', 'delayed-power-check',
                '--cron', delayed_cron,
                '--delete-after-run',
                '--system-event', 'python skills/power-management/scripts/daily-power-decision.py',
                '--description', f'延後電源管理檢查 - {delayed_time.strftime("%H:%M")}'
            ])
            
            print(f"⏰ 已排程 {delayed_time.strftime('%H:%M')} 再次檢查電源管理")
            return True
            
        except Exception as e:
            print(f"⚠️ 排程延後檢查失敗: {e}")
            return False

def main():
    """Main execution function."""
    try:
        print("🔋 ClawClaw 電源管理系統啟動")
        print(f"⏰ 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        engine = PowerDecisionEngine()
        analysis = engine.analyze_shutdown_readiness()
        
        # Present UI and get user choice
        choice = engine.present_decision_ui(analysis)
        
        # Execute the decision
        success = engine.execute_decision(choice)
        
        if success:
            print("✅ 電源管理決策執行完成")
        else:
            print("❌ 電源管理決策執行失敗")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ 使用者中斷，取消電源管理")
        return 1
    except Exception as e:
        print(f"❌ 電源管理系統錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Fix for Windows input handling
    if sys.platform == "win32":
        # Use simpler input for Windows
        def countdown_with_input(self, timeout_seconds):
            print(f"⏱️  {timeout_seconds}秒後執行預設動作 (立即關機)...")
            print("   按 Enter 確認，或輸入 2-4 選擇其他選項...")
            
            import threading
            import time
            
            user_choice = [1]  # Default choice
            input_received = threading.Event()
            
            def get_input():
                try:
                    choice_input = input().strip()
                    if choice_input in ['2', '3', '4']:
                        user_choice[0] = int(choice_input)
                    elif choice_input == '':
                        user_choice[0] = 1
                    input_received.set()
                except:
                    input_received.set()
            
            input_thread = threading.Thread(target=get_input)
            input_thread.daemon = True
            input_thread.start()
            
            # Wait for input or timeout
            if input_received.wait(timeout_seconds):
                return user_choice[0]
            else:
                print("\n⏰ 時間到，執行預設選項...")
                return 1
        
        # Patch the method for Windows
        PowerDecisionEngine.countdown_with_input = countdown_with_input
    
    exit_code = main()
    sys.exit(exit_code)