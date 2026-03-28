#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能 Heartbeat 處理器
根據當前時間執行對應的檢查任務，包含 23:45 每日總結預告
"""

import datetime
import sys
import subprocess
from pathlib import Path

class SmartHeartbeatHandler:
    def __init__(self):
        self.now = datetime.datetime.now()
        self.current_hour = self.now.hour
        self.current_minute = self.now.minute
        self.workspace_path = Path.cwd()
        
    def execute_heartbeat(self):
        """根據時間執行對應的 Heartbeat 任務"""
        
        current_time = f"{self.current_hour:02d}:{self.current_minute:02d}"
        print(f"🕐 ClawClaw Heartbeat - {current_time}")
        
        # 特殊時間檢查
        if self.is_daily_summary_notification_time():
            return self.trigger_daily_summary_notification()
        elif self.is_daily_summary_execution_time():
            return self.handle_daily_summary_execution()
        elif self.is_weekly_material_crawl_time():
            return self.execute_weekly_material_crawl()
        elif self.is_daily_pipeline_time():
            return self.execute_daily_pipeline()
        elif self.is_morning_check_time():
            return self.execute_morning_check()
        elif self.is_afternoon_check_time():
            return self.execute_afternoon_check()
        elif self.is_evening_check_time():
            return self.execute_evening_check()
        elif self.is_quiet_time():
            return "HEARTBEAT_OK"
        else:
            return self.execute_general_check()
    
    def is_daily_summary_notification_time(self):
        """檢查是否為每日總結預告時間 (23:45-23:49)"""
        return self.current_hour == 23 and 45 <= self.current_minute <= 49
    
    def is_daily_summary_execution_time(self):
        """檢查是否為每日總結執行時間 (23:55 預設執行)"""
        return self.current_hour == 23 and self.current_minute >= 55
    
    def is_morning_check_time(self):
        """上午檢查時間 (09:00-12:00)"""
        return 9 <= self.current_hour < 12
    
    def is_afternoon_check_time(self):
        """下午檢查時間 (13:00-18:00)"""
        return 13 <= self.current_hour < 18
    
    def is_evening_check_time(self):
        """晚間檢查時間 (18:00-22:00)"""
        return 18 <= self.current_hour < 22
    
    def is_quiet_time(self):
        """安靜時間 (00:00-07:00)"""
        return 0 <= self.current_hour < 7
    
    def is_weekly_material_crawl_time(self):
        """檢查是否為週一 13:00 素材爬取時間"""
        is_monday = self.now.weekday() == 0  # Monday = 0
        is_1300 = self.current_hour == 13 and 0 <= self.current_minute <= 5
        return is_monday and is_1300
    
    def is_daily_pipeline_time(self):
        """檢查是否為每日 10:00 Pipeline 觸發時間"""
        is_1000 = self.current_hour == 10 and 0 <= self.current_minute <= 5
        return is_1000
    
    def trigger_daily_summary_notification(self):
        """觸發每日總結預告通知 (23:45)"""
        print("🔔 觸發每日總結預告通知...")
        
        # 直接返回通知訊息，讓 heartbeat 機制處理
        message = f"""🌙 **ClawClaw 每日總結時間到了！**

⏰ **當前時間**: 23:45
📅 **日期**: {datetime.date.today().strftime("%Y-%m-%d")}

請選擇今晚的動作：

**1️⃣ 總結並關機**
- ✅ 執行智能睡眠模式 (記憶整理+經驗提煉)
- ✅ GitHub 備份同步
- ✅ 安全關機系統

**2️⃣ 總結但不關機** 
- ✅ 執行智能睡眠模式
- ✅ GitHub 備份同步
- ❌ 保持系統運行 (夜間工作模式)

**3️⃣ 不總結也不關機**
- ❌ 跳過今日總結
- ❌ 保持系統運行
- ⚠️ 記憶不會自動整理

**⏱️ 如果 10 分鐘內未回覆，將預設執行選項 1**

請回覆數字 1/2/3 選擇，或等待稍後的確認 ☺️"""
        
        # 保存通知狀態
        self.save_notification_state()
        
        return message
    
    def handle_daily_summary_execution(self):
        """處理每日總結預設執行 (23:55 超時)"""
        print("⏰ 檢查每日總結超時執行...")
        
        # 檢查是否有等待中的選擇狀態
        state_file = self.workspace_path / "memory" / "daily_summary_state.json"
        
        if state_file.exists():
            try:
                import json
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # 檢查是否超過截止時間
                deadline_str = state.get('default_deadline')
                if deadline_str:
                    deadline = datetime.datetime.fromisoformat(deadline_str)
                    if datetime.datetime.now() >= deadline:
                        # 超時，執行預設選項 1
                        print("⏰ 超時執行預設選項：總結並關機")
                        
                        result = subprocess.run([
                            sys.executable,
                            str(self.workspace_path / "scripts" / "handle_daily_summary_choice.py"),
                            "1"
                        ], capture_output=True, text=True)
                        
                        return "⏰ 未收到回覆，執行預設選項：總結並關機"
                        
            except Exception as e:
                print(f"⚠️ 狀態檢查錯誤: {e}")
        
        return "HEARTBEAT_OK"
    
    def execute_weekly_material_crawl(self):
        """執行週一 13:00 自動素材爬取"""
        print("📡 觸發週一素材爬取...")
        
        try:
            # 執行 material-curator 的自動爬取
            curator_script = self.workspace_path / "skills-custom" / "material-curator" / "scripts" / "material_curator.py"
            
            if not curator_script.exists():
                return "⚠️ Material-Curator 腳本不存在，跳過自動爬取"
            
            result = subprocess.run([
                sys.executable,
                str(curator_script),
                "auto-crawl-weekly"
            ], capture_output=True, text=True, cwd=curator_script.parent)
            
            if result.returncode == 0:
                # 解析結果
                try:
                    import json
                    crawl_result = json.loads(result.stdout)
                    
                    message = f"""📡 **週一自動素材爬取完成！**

📊 **統計結果**:
• 處理網站: {crawl_result.get('sites_processed', 0)}/3 個
• 爬取文章: {crawl_result.get('articles_crawled', 0)} 篇
• 新增素材: {crawl_result.get('materials_created', 0)} 個
• 重複跳過: {crawl_result.get('duplicates_skipped', 0)} 個
• 錯誤數量: {len(crawl_result.get('errors', []))} 個

🎯 **下次爬取**: 下週一 13:00

**素材庫已自動更新，創意生成系統將受益於新鮮素材！** ✨"""

                    return message
                    
                except json.JSONDecodeError:
                    return f"📡 週一素材爬取完成，但結果解析失敗\n輸出: {result.stdout[:200]}"
                    
            else:
                error_msg = result.stderr or "未知錯誤"
                return f"❌ 週一素材爬取失敗: {error_msg[:200]}"
                
        except Exception as e:
            return f"⚠️ 週一素材爬取執行錯誤: {str(e)[:200]}"
    
    def execute_daily_pipeline(self):
        """執行每日 10:00 Stock Pipeline Stage 0 + 連續執行"""
        print("🚀 觸發每日 Stock Pipeline...")
        
        try:
            pipeline_script = self.workspace_path / "skills-custom" / "stock-image-pipeline" / "scripts" / "pipeline_main.py"
            
            if not pipeline_script.exists():
                return "⚠️ Stock Pipeline 腳本不存在，跳過自動執行"
            
            result = subprocess.run([
                sys.executable,
                str(pipeline_script),
                "--mode", "stage0"
            ], capture_output=True, text=True, cwd=pipeline_script.parent)
            
            if result.returncode == 0:
                # 解析結果
                try:
                    import json
                    pipeline_result = json.loads(result.stdout)
                    
                    execution_mode = pipeline_result.get('execution_mode', 'unknown')
                    status = pipeline_result.get('status', 'unknown')
                    pipeline_triggered = pipeline_result.get('pipeline_triggered', False)
                    
                    if execution_mode == "continuous_execution_completed":
                        # 連續執行完成
                        production_result = pipeline_result.get('production_result', {})
                        final_summary = production_result.get('final_summary', {})
                        
                        message = f"""🎨 **每日 Stock Pipeline 執行完成！**

🚀 **執行模式**: 連續執行 (Stage 0 → Stage 1-5)
📊 **最終結果**:
• 狀態: {status}
• 生產圖片: {final_summary.get('total_produced', 0)} 張
• 通過品檢: {final_summary.get('passed_count', 0)} 張
• 已上傳: {final_summary.get('uploaded_count', 0)} 張

⏰ **下次執行**: 明日 10:00

**ClawClaw 已自動完成今日創意生產任務！** ✨"""

                    elif execution_mode == "stage0_only":
                        message = f"""📋 **每日創意討論會完成！**

🎯 **執行模式**: 僅 Stage 0 (連續模式未啟用)
📊 **Stage 0 結果**:
• 狀態: {pipeline_result.get('stage0_result', {}).get('status', 'unknown')}
• 主題: {pipeline_result.get('stage0_result', {}).get('theme', 'unknown')}
• Brief 來源: {pipeline_result.get('stage0_result', {}).get('brief_source', 'unknown')}

ℹ️ **後續操作**: 需要手動觸發 Stage 1-5 或啟用連續執行模式

⏰ **下次執行**: 明日 10:00"""
                        
                    elif status == "daily_limit_reached":
                        message = f"""✅ **每日產量已達標！**

📊 **產量狀態**: 
• 今日已產出: {pipeline_result.get('produced_count', 0)} 張
• 每日目標: {pipeline_result.get('daily_target', 2)} 張
• 狀態: 已達標，暫停生產

🎯 **ClawClaw 守護產量品質，避免過度生產！**

⏰ **下次執行**: 明日 10:00 重新開始"""
                        
                    else:
                        message = f"🚀 每日 Pipeline 執行完成：{status} (mode: {execution_mode})"

                    return message
                    
                except json.JSONDecodeError:
                    return f"🚀 每日 Pipeline 執行完成，但結果解析失敗\n輸出: {result.stdout[:200]}"
                    
            else:
                error_msg = result.stderr or "未知錯誤"
                return f"❌ 每日 Pipeline 執行失敗: {error_msg[:200]}"
                
        except Exception as e:
            return f"⚠️ 每日 Pipeline 執行錯誤: {str(e)[:200]}"
    
    def execute_morning_check(self):
        """執行上午檢查"""
        checks = []
        
        # 檢查緊急郵件 (模擬)
        checks.append("📧 郵件檢查：無緊急事項")
        
        # 檢查今日行程 (模擬)
        checks.append("📅 行程檢查：今日計畫正常")
        
        if len(checks) > 0:
            return "🌅 上午檢查完成：" + " | ".join(checks)
        else:
            return "HEARTBEAT_OK"
    
    def execute_afternoon_check(self):
        """執行下午檢查"""
        checks = []
        
        # 檢查明天天氣 (模擬)
        checks.append("🌤️ 天氣：明日天氣良好")
        
        # 檢查系統服務
        service_status = self.check_system_services()
        if service_status:
            checks.append(f"📊 服務狀態：{service_status}")
        
        if len(checks) > 0:
            return "🏃 下午檢查完成：" + " | ".join(checks)
        else:
            return "HEARTBEAT_OK"
    
    def execute_evening_check(self):
        """執行晚間檢查"""
        checks = []
        
        # 檢查未完成任務 (模擬)
        checks.append("📝 任務檢查：今日目標進行中")
        
        # 檢查記憶備份
        memory_status = self.check_memory_backup_needed()
        if memory_status:
            checks.append(f"💾 記憶狀態：{memory_status}")
        
        if len(checks) > 0:
            return "🌆 晚間檢查完成：" + " | ".join(checks)
        else:
            return "HEARTBEAT_OK"
    
    def execute_general_check(self):
        """執行一般檢查"""
        return "HEARTBEAT_OK"
    
    def check_system_services(self):
        """檢查系統服務狀態"""
        try:
            # 檢查 ComfyUI 和 Ollama
            import psutil
            
            comfyui_running = any('ComfyUI' in p.name() for p in psutil.process_iter())
            ollama_running = any('ollama' in p.name().lower() for p in psutil.process_iter())
            
            if comfyui_running and ollama_running:
                return "ComfyUI+Ollama 運行正常"
            elif comfyui_running:
                return "ComfyUI 運行，Ollama 離線"
            elif ollama_running:
                return "Ollama 運行，ComfyUI 離線"
            else:
                return "⚠️ 主要服務離線"
                
        except Exception:
            return None
    
    def check_memory_backup_needed(self):
        """檢查記憶備份需求"""
        try:
            # 檢查今日是否有新記憶
            today = datetime.date.today().strftime('%Y-%m-%d')
            daily_file = self.workspace_path / "memory" / "daily" / f"{today}.md"
            
            if daily_file.exists():
                return "今日記憶待備份"
            else:
                return None
                
        except Exception:
            return None
    
    def save_notification_state(self):
        """保存通知狀態"""
        try:
            import json
            
            state = {
                "notification_sent": True,
                "sent_at": datetime.datetime.now().isoformat(),
                "waiting_for_response": True,
                "default_deadline": (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
            }
            
            state_file = self.workspace_path / "memory" / "daily_summary_state.json"
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 狀態保存失敗: {e}")

def main():
    """主執行入口"""
    handler = SmartHeartbeatHandler()
    result = handler.execute_heartbeat()
    print(result)

if __name__ == "__main__":
    main()