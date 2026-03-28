"""
pipeline_main.py — Stock Photo Production Pipeline 主流程編排

串接全部模組，依序執行 Stage 0-5 + 觀測/蒸餾/結算。

Daily Flow:
  07:00  Stage 0: 創意素材討論會 (creative_brief_generator)
  09:00  Stage 1: 排程啟動 & 上下文載入 (prompt_generator.load_context)
         Stage 2: 提示詞生成與優化 (prompt_generator.generate_prompts)
         Stage 3: 圖像生成精煉迴圈 (image_refiner.run_daily_batch)
         Stage 4: 品質檢測與篩選 (defect_detector.inspect_batch)
                  → retry loop: 重新生成 prompt → Stage 3 → Stage 4
         Stage 5: 上傳準備 & 批次結算
                  5.1 描述提取 + metadata 嵌入
                  5.2a Dreamstime FTP 上傳
                  5.2b Adobe Stock 手動通知
                  5.3 批次結算報告
         Post:   觀測記錄 + 經驗萃取 (AAR)

Retry Logic:
  - max_retries_per_image: 2 (per image)
  - max_daily_retries: 4 (total)
  - Stage 3.2 全部 < initial_min_score → 回退 Stage 2 (消耗 1 次)
  - Stage 4 verdict=retry_needed → 套用修復策略 → 回退 Stage 3.1 (消耗 1 次)
  - Stage 4 verdict=discard → 不消耗重試，直接放棄

Entry Points:
  run_daily_production()  — 完整每日流程 (Stage 0-5)
  run_stage0_only()       — 僅執行 Stage 0 創意討論會
  run_production_only()   — 僅執行 Stage 1-5 (假設 Stage 0 已完成)
  run_weekly_tasks()      — 週報 + 週分析
  run_monthly_tasks()     — 月度歸檔
"""

import json
import logging
import sys
import time as _time
from pathlib import Path
from datetime import datetime

# ---------- path resolution ----------
SCRIPT_DIR = str(Path(__file__).resolve().parent)
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ---------- lazy imports ----------
# 所有模組在同一 scripts/ 目錄下，透過 sys.path 載入
from creative_brief_generator import CreativeBriefGenerator
from prompt_generator import PromptGenerator
from image_refiner import ImageRefiner
from defect_detector import DefectDetector
from image_describer import ImageDescriber
from metadata_embedder import MetadataEmbedder
from ftp_uploader import FTPUploader
from upload_preparer import UploadPreparer
from memory_observer import MemoryObserver
from experience_distiller import ExperienceDistiller
from metrics_collector import MetricsCollector

logger = logging.getLogger("stock-image.pipeline_main")


class StockPipeline:
    """
    Stock Photo Production Pipeline 主編排器。
    """

    def __init__(self):
        self._schedule_config = {}
        self._topics_config = {}
        self._load_config()

        # 子模組實例（延遲使用，但預先建立以保持 observation 狀態）
        self.brief_gen = CreativeBriefGenerator()
        self.prompt_gen = PromptGenerator()
        self.refiner = ImageRefiner()
        self.detector = DefectDetector()
        self.describer = ImageDescriber()
        self.embedder = MetadataEmbedder()
        self.uploader = FTPUploader()
        self.preparer = UploadPreparer()
        self.observer = MemoryObserver()
        self.distiller = ExperienceDistiller()
        self.metrics = MetricsCollector()

    # ------------------------------------------------------------------
    # 每日產量檢查
    # ------------------------------------------------------------------
    def _check_daily_production_count(self, date_str: str) -> int:
        """
        檢查指定日期已生產的圖片數量。
        
        Args:
            date_str: 日期字串 (YYYY-MM-DD)
            
        Returns:
            已生產的圖片數量
        """
        try:
            # 檢查 uploaded/ 目錄中今日的檔案
            uploaded_dir = self._schedule_config.get("workspace", {}).get("uploaded_dir", "uploaded")
            uploaded_path = Path("~/.openclaw/workspace/skills-custom/stock-image-pipeline").expanduser() / uploaded_dir
            
            if not uploaded_path.exists():
                return 0
                
            # 計算今日上傳的檔案數量
            today_files = []
            for img_file in uploaded_path.glob("*.jpg"):
                try:
                    # 檢查檔案的修改時間或檔名中的日期
                    if date_str in img_file.name:
                        today_files.append(img_file)
                    else:
                        # 檢查檔案修改時間
                        import datetime
                        file_date = datetime.datetime.fromtimestamp(img_file.stat().st_mtime)
                        if file_date.strftime("%Y-%m-%d") == date_str:
                            today_files.append(img_file)
                except Exception:
                    continue
                    
            for img_file in uploaded_path.glob("*.png"):
                try:
                    if date_str in img_file.name:
                        today_files.append(img_file)
                    else:
                        import datetime
                        file_date = datetime.datetime.fromtimestamp(img_file.stat().st_mtime)
                        if file_date.strftime("%Y-%m-%d") == date_str:
                            today_files.append(img_file)
                except Exception:
                    continue
                    
            logger.info(f"檢查每日產量: {date_str} = {len(today_files)} 張")
            return len(today_files)
            
        except Exception as e:
            logger.warning(f"每日產量檢查失敗: {e}")
            return 0

    # ------------------------------------------------------------------
    # config
    # ------------------------------------------------------------------
    def _load_config(self):
        try:
            with open(CONFIG_DIR / "schedule.json", "r", encoding="utf-8") as f:
                self._schedule_config = json.load(f)
        except Exception as e:
            logger.error(f"schedule.json 載入失敗: {e}")

        try:
            with open(CONFIG_DIR / "topics.json", "r", encoding="utf-8") as f:
                self._topics_config = json.load(f)
        except Exception as e:
            logger.error(f"topics.json 載入失敗: {e}")

    # ==================================================================
    # Entry Point: 完整每日流程
    # ==================================================================
    def run_daily_production(self, theme_override: str = None, manual_brief: dict = None) -> dict:
        """
        完整每日生產流程: Stage 0 → Stage 1-5 → 觀測 → AAR。

        Args:
            theme_override: 手動指定今日主題 (覆蓋輪替)
            manual_brief: 手動提供 brief (跳過 Stage 0 對話)

        Returns:
            完整的每日生產結果 dict
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        pipeline_start = _time.time()

        # 檢查每日產量上限
        daily_target = self._schedule_config.get("daily_target", 2)
        produced_today = self._check_daily_production_count(date_str)
        
        if produced_today >= daily_target:
            logger.info(f"每日產量已達上限: {produced_today}/{daily_target} 張，停止生產")
            return {
                "date": date_str,
                "status": "daily_limit_reached",
                "message": f"今日已完成 {produced_today} 張圖片，達到每日目標 {daily_target} 張",
                "daily_target": daily_target,
                "produced_count": produced_today,
                "stage_results": {},
                "final_summary": {
                    "total_produced": produced_today,
                    "target_met": True,
                    "limit_protection_triggered": True
                }
            }

        logger.info(f"=== Stock Pipeline 每日生產開始 === {date_str} (已產出 {produced_today}/{daily_target})")
        self.observer.reset()

        result = {
            "date": date_str,
            "status": "running",
            "stage_results": {},
            "final_summary": None,
        }

        # ----------------------------------------------------------
        # Stage 0: 創意素材討論會
        # ----------------------------------------------------------
        stage0_result = self._run_stage0(date_str, theme_override, manual_brief)
        result["stage_results"]["stage0"] = stage0_result
        theme = stage0_result.get("theme", "tech-abstract")
        brief = stage0_result.get("brief")
        stage0_used = stage0_result.get("stage0_used", False)

        if stage0_result.get("status") == "fatal":
            result["status"] = "failed"
            result["error"] = "Stage 0 致命錯誤，無法繼續"
            self._finalize(result, date_str, theme, pipeline_start, stage0_used)
            return result

        # ----------------------------------------------------------
        # Stage 1-5: 生產流程
        # ----------------------------------------------------------
        production_result = self._run_production(
            date_str, theme, brief, stage0_used
        )
        result["stage_results"].update(production_result.get("stage_results", {}))
        result["status"] = production_result.get("status", "completed")
        result["final_summary"] = production_result.get("final_summary")

        # ----------------------------------------------------------
        # Post: 觀測 + AAR
        # ----------------------------------------------------------
        self._finalize(result, date_str, theme, pipeline_start, stage0_used)

        logger.info(f"=== Stock Pipeline 每日生產結束 === status={result['status']}")
        return result

    # ==================================================================
    # Entry Point: 僅 Stage 0
    # ==================================================================
    def run_stage0_only(self, theme_override: str = None) -> dict:
        """
        僅執行 Stage 0 創意討論會。
        
        🆕 在連續執行模式下，Stage 0 完成後會自動觸發後續所有 Stage。
        這是 10:00 heartbeat 觸發的標準入口點。
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        pipeline_start = _time.time()
        
        logger.info(f"=== Stage 0 觸發 === {date_str}")
        self.observer.reset()
        
        # 檢查每日產量上限
        daily_target = self._schedule_config.get("daily_target", 2)
        produced_today = self._check_daily_production_count(date_str)
        
        if produced_today >= daily_target:
            logger.info(f"每日產量已達上限: {produced_today}/{daily_target} 張，跳過 Pipeline")
            return {
                "date": date_str,
                "status": "daily_limit_reached",
                "message": f"今日已完成 {produced_today} 張圖片，達到每日目標 {daily_target} 張",
                "daily_target": daily_target,
                "produced_count": produced_today,
                "pipeline_triggered": False
            }
        
        # 執行 Stage 0 (可能觸發連續執行)
        stage0_result = self._run_stage0(date_str, theme_override, manual_brief=None)
        
        # 如果連續執行模式被觸發，包含完整結果
        if stage0_result.get("auto_production_triggered"):
            result = {
                "date": date_str,
                "status": "continuous_execution_completed",
                "stage0_result": {k: v for k, v in stage0_result.items() if k != "production_result"},
                "production_result": stage0_result.get("production_result"),
                "pipeline_triggered": True,
                "execution_mode": "continuous"
            }
            
            # 完成觀測和 AAR
            theme = stage0_result.get("theme", "tech-abstract")
            stage0_used = stage0_result.get("stage0_used", False)
            self._finalize(result, date_str, theme, pipeline_start, stage0_used)
            
        else:
            result = {
                "date": date_str,
                "status": "stage0_only_completed", 
                "stage0_result": stage0_result,
                "pipeline_triggered": False,
                "execution_mode": "stage0_only"
            }
        
        logger.info(f"=== Stage 0 結束 === mode={result['execution_mode']}")
        return result

    # ==================================================================
    # Entry Point: 僅 Stage 1-5
    # ==================================================================
    def run_production_only(self, theme_override: str = None) -> dict:
        """
        僅執行 Stage 1-5（假設 Stage 0 已完成或使用 fallback）。
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        pipeline_start = _time.time()
        self.observer.reset()

        # 嘗試讀取今日 brief
        theme = self.brief_gen.determine_today_theme(date_str, theme_override)
        brief = self._try_load_today_brief(date_str)
        stage0_used = brief is not None
        
        # 檢查 Brief 是否存在
        if brief is None:
            error_msg = (
                f"未找到今日創意簡報檔案 (brief_{date_str}.json)。"
                "請先執行 Stage 0 創意素材討論會："
                "\n  python pipeline_main.py --mode stage0"
                "\n或使用完整每日流程："
                "\n  python pipeline_main.py --mode daily"
            )
            logger.error(error_msg)
            
            return {
                "date": date_str,
                "status": "failed",
                "error": "missing_creative_brief",
                "message": error_msg,
                "suggested_action": "執行 Stage 0 或完整每日流程",
                "stage_results": {},
                "final_summary": None
            }

        result = self._run_production(date_str, theme, brief, stage0_used)
        self._finalize(result, date_str, theme, pipeline_start, stage0_used)
        return result

    # ==================================================================
    # Stage 0: 創意素材討論會
    # ==================================================================
    def _run_stage0(self, date_str: str, theme_override: str, manual_brief: dict) -> dict:
        """
        執行 Stage 0 創意素材討論會。
        
        🆕 支援連續執行模式：如果 schedule.json 中設定 pipeline_mode.type = "continuous"，
        Stage 0 完成後會自動觸發後續所有 Stage。
        """
        logger.info("▶ Stage 0: 創意素材討論會")

        try:
            stage0_result = self.brief_gen.run(
                date_str=date_str,
                theme_override=theme_override,
                manual_brief=manual_brief
            )

            theme = stage0_result.get("theme", "tech-abstract")
            brief = stage0_result.get("brief")
            stage0_used = stage0_result.get("brief_source") == "dual_agent_dialogue"

            # 收集觀測
            if "observation" in stage0_result:
                self.observer.collect("creative_brief", stage0_result["observation"])

            logger.info(
                f"  Stage 0 完成: theme={theme}, "
                f"source={stage0_result.get('brief_source', 'unknown')}"
            )

            result = {
                "status": "ok",
                "theme": theme,
                "brief": brief,
                "stage0_used": stage0_used,
                "brief_source": stage0_result.get("brief_source"),
            }
            
            # 🆕 檢查是否啟用連續執行模式
            pipeline_mode = self._schedule_config.get("pipeline_mode", {})
            if pipeline_mode.get("type") == "continuous" and pipeline_mode.get("auto_proceed"):
                logger.info("🚀 連續執行模式：Stage 0 完成，自動觸發後續 Stage...")
                
                # 延遲一小段時間，讓 Stage 0 結果可以被觀察
                stage_interval = pipeline_mode.get("stage_interval_sec", 30)
                if stage_interval > 0:
                    logger.info(f"   延遲 {stage_interval} 秒後開始...")
                    _time.sleep(stage_interval)
                
                # 觸發完整生產流程
                production_result = self._run_production(date_str, theme, brief, stage0_used)
                result["auto_production_triggered"] = True
                result["production_result"] = production_result
                
                logger.info("✅ 連續執行模式：完整 Pipeline 自動執行完成")

            return result

        except Exception as e:
            logger.error(f"  Stage 0 失敗: {e}")
            # Stage 0 失敗不致命，fallback 到 template 模式
            theme = self.brief_gen.determine_today_theme(date_str, theme_override)
            return {
                "status": "fallback",
                "theme": theme,
                "brief": None,
                "stage0_used": False,
                "brief_source": "fallback_after_error",
                "error": str(e),
            }

    # ==================================================================
    # Stage 1-5: 生產流程
    # ==================================================================
    def _run_production(self, date_str: str, theme: str, brief: dict,
                        stage0_used: bool) -> dict:
        """
        執行 Stage 1-5 完整生產流程，包含 retry loop。
        """
        production_start = _time.time()
        daily_target = self._schedule_config.get("daily_target", 2)
        max_daily_retries = self._schedule_config.get("max_daily_retries", 4)
        daily_retries_used = 0

        result = {
            "stage_results": {},
            "status": "running",
            "final_summary": None,
        }

        # ==============================================================
        # Stage 1-2: 提示詞生成
        # ==============================================================
        logger.info("▶ Stage 1-2: 提示詞生成與優化")
        prompt_packages = self._run_stage1_2(date_str, theme, brief)
        result["stage_results"]["stage1_2"] = {
            "packages_count": len(prompt_packages),
            "prompt_source": self.prompt_gen.observation().get("prompt_source", "unknown"),
        }

        if not prompt_packages:
            logger.error("  Stage 1-2 失敗: 無法生成提示詞")
            result["status"] = "failed"
            result["error"] = "提示詞生成失敗"
            return result

        # 收集觀測
        self.observer.collect("prompt_generator", self.prompt_gen.observation())

        # ==============================================================
        # Stage 3-4 Loop (with retry)
        # ==============================================================
        all_passed = []         # 最終通過的 {image_path, prompt_package, score}
        all_discarded = []      # 已丟棄的
        packages_to_process = list(prompt_packages)  # 待處理的 prompt packages

        round_num = 0
        while packages_to_process and daily_retries_used <= max_daily_retries:
            round_num += 1
            logger.info(
                f"▶ Stage 3-4 Round {round_num}: "
                f"{len(packages_to_process)} packages, "
                f"retries used {daily_retries_used}/{max_daily_retries}"
            )

            # Stage 3: 圖像生成精煉
            refiner_result = self.refiner.run_daily_batch(
                prompt_packages=packages_to_process,
                date_str=date_str
            )
            result["stage_results"][f"stage3_round{round_num}"] = {
                "status": refiner_result.get("status"),
                "results_count": len(refiner_result.get("results", [])),
            }

            # Stage 4: 品質檢測
            successful_images = [
                r for r in refiner_result.get("results", [])
                if r.get("status") == "success"
            ]

            if not successful_images:
                logger.warning(f"  Round {round_num}: Stage 3 無成功產出")
                break

            inspection_result = self.detector.inspect_batch(
                image_results=successful_images,
                prompt_packages=packages_to_process
            )
            result["stage_results"][f"stage4_round{round_num}"] = {
                "pass": len([r for r in inspection_result if r.get("verdict") == "pass"]),
                "retry": len([r for r in inspection_result if r.get("verdict") == "retry_needed"]),
                "discard": len([r for r in inspection_result if r.get("verdict") == "discard"]),
            }

            # 分類結果
            next_round_packages = []
            for insp in inspection_result:
                verdict = insp.get("verdict", "discard")
                image_idx = insp.get("image_index", -1)

                if verdict == "pass":
                    all_passed.append({
                        "image_path": insp.get("image_path"),
                        "prompt_package": packages_to_process[image_idx] if image_idx < len(packages_to_process) else {},
                        "score": insp.get("final_score", 0),
                        "inspection": insp,
                    })
                elif verdict == "retry_needed" and daily_retries_used < max_daily_retries:
                    # 套用修復策略
                    repair = insp.get("repair_strategy", {})
                    if repair and image_idx < len(packages_to_process):
                        repaired_pkg = self.detector.apply_repair_to_package(
                            packages_to_process[image_idx], repair
                        )
                        next_round_packages.append(repaired_pkg)
                        daily_retries_used += 1
                        logger.info(
                            f"  Image {image_idx}: retry → 修復策略 applied, "
                            f"retries {daily_retries_used}/{max_daily_retries}"
                        )
                    else:
                        all_discarded.append(insp)
                else:
                    all_discarded.append(insp)

            packages_to_process = next_round_packages

            # 已達目標數量，提前結束
            if len(all_passed) >= daily_target:
                logger.info(f"  已達每日目標 {daily_target} 張，結束 Stage 3-4 loop")
                break

        # 收集觀測
        self.observer.collect("image_refiner", self.refiner.observation())
        self.observer.collect("defect_detector", self.detector.observation())

        # ==============================================================
        # Stage 5: 上傳準備
        # ==============================================================
        if all_passed:
            stage5_result = self._run_stage5(
                all_passed, theme, date_str, stage0_used,
                refiner_result, inspection_result, daily_retries_used,
                production_start
            )
            result["stage_results"]["stage5"] = stage5_result
        else:
            logger.warning("無通過品質檢測的圖片，跳過 Stage 5")
            result["stage_results"]["stage5"] = {"status": "skipped", "reason": "no_passed_images"}

        # 設定最終狀態
        result["status"] = "completed"
        result["final_summary"] = {
            "total_produced": len(all_passed),
            "total_discarded": len(all_discarded),
            "total_retries_used": daily_retries_used,
            "daily_target": daily_target,
            "target_met": len(all_passed) >= daily_target,
        }

        return result

    # ------------------------------------------------------------------
    # Stage 1-2 實作
    # ------------------------------------------------------------------
    def _run_stage1_2(self, date_str: str, theme: str, brief: dict) -> list:
        """執行 Stage 1 (上下文載入) + Stage 2 (提示詞生成)。"""
        try:
            result = self.prompt_gen.run(
                date_str=date_str,
                theme=theme,
                brief=brief
            )
            packages = result.get("packages", [])

            # 寫入歷史
            if packages:
                self.prompt_gen.save_to_prompt_history(packages, date_str, theme)

            logger.info(f"  Stage 1-2: 生成 {len(packages)} 個 prompt packages")
            return packages

        except Exception as e:
            logger.error(f"  Stage 1-2 失敗: {e}")
            return []

    # ------------------------------------------------------------------
    # Stage 5 實作
    # ------------------------------------------------------------------
    def _run_stage5(self, passed_images: list, theme: str, date_str: str,
                    stage0_used: bool, refiner_result: dict,
                    inspection_result, daily_retries_used: int,
                    production_start: float) -> dict:
        """執行 Stage 5: 描述 → 嵌入 → FTP → 通知 → 結算。"""
        logger.info(f"▶ Stage 5: 上傳準備 ({len(passed_images)} 張)")
        stage5 = {}

        # ----------------------------------------------------------
        # 5.1 圖片描述提取
        # ----------------------------------------------------------
        logger.info("  5.1 圖片描述提取")
        try:
            descriptions = self.describer.describe_batch(
                passed_images=[
                    {"image_path": p["image_path"], "prompt_package": p["prompt_package"]}
                    for p in passed_images
                ],
                prompt_packages=[p["prompt_package"] for p in passed_images],
                theme=theme
            )
            stage5["describe"] = {"count": len(descriptions), "status": "ok"}
        except Exception as e:
            logger.error(f"  5.1 描述提取失敗: {e}")
            descriptions = []
            stage5["describe"] = {"count": 0, "status": "failed", "error": str(e)}

        # ----------------------------------------------------------
        # 5.1b Metadata 嵌入 + 重命名
        # ----------------------------------------------------------
        logger.info("  5.1b Metadata 嵌入")
        embed_results = []
        if descriptions:
            try:
                scores = {
                    p["image_path"]: p["score"]
                    for p in passed_images
                    if "image_path" in p
                }
                embed_results = self.embedder.embed_batch(
                    descriptions=descriptions,
                    theme=theme,
                    date_str=date_str,
                    scores=scores
                )
                stage5["embed"] = {"count": len(embed_results), "status": "ok"}
            except Exception as e:
                logger.error(f"  5.1b 嵌入失敗: {e}")
                stage5["embed"] = {"count": 0, "status": "failed", "error": str(e)}

        # ----------------------------------------------------------
        # 5.2a Dreamstime FTP 上傳
        # ----------------------------------------------------------
        logger.info("  5.2a Dreamstime FTP 上傳")
        ftp_result = {"status": "skipped"}
        if embed_results:
            try:
                file_paths = [
                    r["final_path"] for r in embed_results
                    if r.get("final_path")
                ]
                if file_paths:
                    ftp_result = self.uploader.upload_pending(file_paths=file_paths)
                stage5["ftp"] = {
                    "uploaded": ftp_result.get("uploaded_count", 0),
                    "failed": ftp_result.get("failed_count", 0),
                    "status": "ok" if not ftp_result.get("manual_upload_needed") else "manual_needed",
                }
            except Exception as e:
                logger.error(f"  5.2a FTP 上傳失敗: {e}")
                ftp_result = {"status": "failed", "manual_upload_needed": True, "error": str(e)}
                stage5["ftp"] = {"status": "failed", "error": str(e)}

        # ----------------------------------------------------------
        # 5.2b Adobe Stock 手動通知
        # ----------------------------------------------------------
        logger.info("  5.2b Adobe Stock 手動通知")
        try:
            adobe_notification = self.preparer.prepare_adobe_notification(
                embed_results=embed_results,
                theme=theme,
                ftp_result=ftp_result
            )
            stage5["adobe_notification"] = {"status": "ok"}
            logger.info(f"  Adobe 通知: {adobe_notification.get('message', '')[:80]}")
        except Exception as e:
            logger.error(f"  5.2b 通知生成失敗: {e}")
            stage5["adobe_notification"] = {"status": "failed", "error": str(e)}

        # ----------------------------------------------------------
        # 5.3 批次結算報告
        # ----------------------------------------------------------
        logger.info("  5.3 批次結算報告")
        try:
            total_time = _time.time() - production_start
            prompt_source = self.prompt_gen.observation().get("prompt_source", "unknown")

            report = self.preparer.generate_batch_report(
                date_str=date_str,
                theme=theme,
                prompt_source=prompt_source,
                refiner_results={
                    "results": [
                        {"status": "success", "image_path": p["image_path"]}
                        for p in passed_images
                    ],
                    "total_retries_used": daily_retries_used,
                    "observation": self.refiner.observation(),
                },
                inspection_results=inspection_result if isinstance(inspection_result, list) else [],
                ftp_result=ftp_result,
                stage0_used=stage0_used,
                total_generation_time_sec=total_time,
            )
            stage5["report"] = {"status": "ok", "path": report.get("report_path")}

            # 人類友好摘要
            summary_text = self.preparer.format_daily_summary(report)
            logger.info(f"\n{summary_text}")
            stage5["summary_text"] = summary_text

        except Exception as e:
            logger.error(f"  5.3 結算報告失敗: {e}")
            stage5["report"] = {"status": "failed", "error": str(e)}

        return stage5

    # ==================================================================
    # Post: 觀測 + AAR
    # ==================================================================
    def _finalize(self, result: dict, date_str: str, theme: str,
                  pipeline_start: float, stage0_used: bool):
        """生產後的觀測記錄和經驗萃取。"""
        total_time = _time.time() - pipeline_start
        final = result.get("final_summary", {}) or {}

        # 收集 pipeline 元數據
        self.observer.collect_pipeline_meta({
            "theme": theme,
            "date": date_str,
            "daily_target": self._schedule_config.get("daily_target", 2),
            "total_produced": final.get("total_produced", 0),
            "total_retries": final.get("total_retries_used", 0),
            "total_time_sec": round(total_time, 1),
            "stage0_used": stage0_used,
            "status": result.get("status", "unknown"),
            "pass_rate": self._calc_pass_rate(final),
        })

        # 寫入每日觀測
        try:
            obs_path = self.observer.save_daily_observation(date_str)
            md_path = self.observer.save_daily_summary_md(date_str)
            logger.info(f"  觀測寫入: {obs_path}")
            logger.info(f"  摘要寫入: {md_path}")
        except Exception as e:
            logger.error(f"  觀測寫入失敗: {e}")

        # AAR 經驗萃取
        try:
            aar_result = self.distiller.run_aar(
                today_observation=self.observer.get_observations(),
                date_str=date_str
            )
            logger.info(
                f"  AAR: {aar_result.get('insights_generated', 0)} 條洞察, "
                f"{aar_result.get('analysis_summary', '')[:80]}"
            )
            result["aar"] = aar_result
        except Exception as e:
            logger.error(f"  AAR 失敗: {e}")
            result["aar"] = {"status": "failed", "error": str(e)}

    def _calc_pass_rate(self, final_summary: dict) -> float:
        """計算 pass rate。"""
        produced = final_summary.get("total_produced", 0)
        discarded = final_summary.get("total_discarded", 0)
        total = produced + discarded
        return round(produced / total, 3) if total > 0 else 0.0

    # ==================================================================
    # 嘗試載入今日 brief
    # ==================================================================
    def _try_load_today_brief(self, date_str: str) -> dict:
        """嘗試從 briefs/ 目錄載入今日 brief。"""
        ws_base = self._schedule_config.get("workspace", {}).get(
            "base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline"
        )
        briefs_dir = Path(ws_base).expanduser() / self._schedule_config.get(
            "workspace", {}
        ).get("briefs_dir", "briefs")
        brief_path = briefs_dir / f"brief_{date_str}.json"

        if brief_path.exists():
            try:
                with open(brief_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"載入今日 brief 失敗: {e}")
        return None

    # ==================================================================
    # Weekly / Monthly Tasks
    # ==================================================================
    def run_weekly_tasks(self) -> dict:
        """
        每週日觸發: 週報 + 週分析。
        """
        logger.info("=== 週報生成 ===")
        result = {}

        # 週報
        try:
            weekly = self.metrics.generate_weekly_report()
            result["weekly_report"] = weekly

            if weekly.get("status") == "completed":
                summary_text = self.metrics.format_weekly_summary_text(weekly)
                logger.info(f"\n{summary_text}")
                result["summary_text"] = summary_text
        except Exception as e:
            logger.error(f"週報失敗: {e}")
            result["weekly_report"] = {"status": "failed", "error": str(e)}

        # 週分析
        try:
            analysis = self.distiller.run_weekly_analysis()
            result["weekly_analysis"] = analysis
        except Exception as e:
            logger.error(f"週分析失敗: {e}")
            result["weekly_analysis"] = {"status": "failed", "error": str(e)}

        return result

    def run_monthly_tasks(self) -> dict:
        """
        每月 1 日觸發: 歸檔。
        """
        logger.info("=== 月度歸檔 ===")
        try:
            return self.metrics.run_monthly_archive()
        except Exception as e:
            logger.error(f"月度歸檔失敗: {e}")
            return {"status": "failed", "error": str(e)}

    # ==================================================================
    # CLI entry
    # ==================================================================
    def run_cli(self, mode: str = "daily", **kwargs) -> dict:
        """
        CLI 入口，支援多種模式。

        Modes:
            daily    — 完整每日流程
            stage0   — 僅 Stage 0
            produce  — 僅 Stage 1-5
            weekly   — 週報
            monthly  — 月度歸檔
            stats    — 快速統計
        """
        if mode == "daily":
            return self.run_daily_production(**kwargs)
        elif mode == "stage0":
            return self.run_stage0_only(**kwargs)
        elif mode == "produce":
            return self.run_production_only(**kwargs)
        elif mode == "weekly":
            return self.run_weekly_tasks()
        elif mode == "monthly":
            return self.run_monthly_tasks()
        elif mode == "stats":
            days = kwargs.get("days", 7)
            return self.metrics.get_latest_stats(days=days)
        else:
            return {"error": f"Unknown mode: {mode}"}


# ==================================================================
# __main__
# ==================================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Stock Photo Pipeline")
    parser.add_argument(
        "mode",
        nargs="?",
        default="daily",
        choices=["daily", "stage0", "produce", "weekly", "monthly", "stats"],
        help="執行模式"
    )
    parser.add_argument("--theme", default=None, help="手動指定主題")
    parser.add_argument("--days", type=int, default=7, help="統計天數 (stats mode)")

    args = parser.parse_args()

    pipeline = StockPipeline()
    kwargs = {}
    if args.theme:
        kwargs["theme_override"] = args.theme
    if args.mode == "stats":
        kwargs["days"] = args.days

    result = pipeline.run_cli(mode=args.mode, **kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

