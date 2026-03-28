"""
Stage 5.2b + 5.3: Adobe Stock 手動上傳通知 & 批次結算報告

用途:
  - 產出 LXYA 手動上傳 Adobe Stock 的通知
  - 彙總今日所有 Stage 結果為批次結算報告
  - 結算報告寫入 memory/metrics/daily_{date}.json

設計原則:
  - Adobe Stock 不支援 FTP contributor 上傳 → 通知 LXYA 手動操作
  - 批次結算報告包含: 目標/實際/通過率/缺陷摘要/上傳狀態
  - 報告格式對齊設計文件中的 JSON 範例
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"


class UploadPreparer:
    """
    Stage 5.2b + 5.3。

    使用方式:
        preparer = UploadPreparer(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        notification = preparer.prepare_adobe_notification(passed_images, theme)
        report = preparer.generate_batch_report(...)
    """

    def __init__(self, workspace_base: Optional[str] = None):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")

        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()
        self._metrics_dir = self._workspace / "memory" / "metrics"

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ================================================================
    # 5.2b: Adobe Stock 手動上傳通知
    # ================================================================

    def prepare_adobe_notification(
        self,
        embed_results: list,
        theme: str,
        ftp_result: Optional[dict] = None
    ) -> dict:
        """
        產出 LXYA 手動上傳 Adobe Stock 的通知。

        Args:
            embed_results: metadata_embedder 的批次結果
            theme: 主題名
            ftp_result: ftp_uploader 結果（判斷 FTP 失敗的也需要通知）

        Returns:
            通知 dict（供 pipeline_main 顯示給 LXYA）
        """
        # 收集待手動上傳的檔案
        files_for_adobe = []
        for r in embed_results:
            if r.get("metadata_embedded") or r.get("final_path"):
                final_path = r.get("final_path", "")
                # 如果已被 FTP 移到 uploaded/，路徑可能變了
                uploaded_dir = self._workspace / self._schedule_config.get("workspace", {}).get("uploaded_dir", "uploaded")
                filename = Path(final_path).name if final_path else r.get("filename", "unknown")
                uploaded_path = uploaded_dir / filename
                pending_path = Path(final_path) if final_path else None

                actual_path = str(uploaded_path) if uploaded_path.exists() else str(pending_path) if pending_path else ""

                files_for_adobe.append({
                    "filename": filename,
                    "path": actual_path,
                    "image_id": r.get("image_id", "unknown")
                })

        # FTP 失敗的也加入通知（改為手動上傳兩個平台）
        ftp_failed_files = []
        if ftp_result and ftp_result.get("manual_upload_needed"):
            for res in ftp_result.get("results", []):
                if not res.get("success"):
                    ftp_failed_files.append(res.get("filename", "unknown"))

        notification = {
            "type": "adobe_stock_upload_reminder",
            "theme": theme,
            "message": (
                f"今日 {len(files_for_adobe)} 張圖片已完成元數據嵌入，"
                "請至 Adobe Stock Contributor Portal 手動上傳。"
                "\n\n元數據已嵌入，拖拽即可。請記得勾選 'Generative AI' 標記。"
            ),
            "files": files_for_adobe,
            "ftp_failed_files": ftp_failed_files,
            "instructions": [
                "1. 開啟 Adobe Stock Contributor Portal",
                "2. 將圖片拖拽至上傳區域",
                "3. 確認描述和關鍵詞已自動帶入",
                "4. 勾選 'Generative AI' 標記",
                "5. 提交審核"
            ]
        }

        if ftp_failed_files:
            notification["message"] += (
                f"\n\n注意: {len(ftp_failed_files)} 張圖片 Dreamstime FTP 上傳失敗，"
                "也需要手動上傳至 Dreamstime。"
            )

        logger.info(f"Adobe Stock 上傳通知已準備: {len(files_for_adobe)} 張")
        return notification

    # ================================================================
    # 5.3: 批次結算報告
    # ================================================================

    def generate_batch_report(
        self,
        date_str: str,
        theme: str,
        prompt_source: str,
        refiner_results: dict,
        inspection_results: list,
        ftp_result: Optional[dict] = None,
        stage0_used: bool = True,
        total_generation_time_sec: float = 0
    ) -> dict:
        """
        產出每日批次結算報告。

        Args:
            date_str: 日期
            theme: 今日主題
            prompt_source: "creative_brief" | "template_fallback"
            refiner_results: image_refiner.run_daily_batch() 結果
            inspection_results: defect_detector.inspect_batch() 結果
            ftp_result: ftp_uploader.upload_pending() 結果
            stage0_used: 是否使用了 Stage 0 創意簡報
            total_generation_time_sec: 總生產耗時

        Returns:
            完整批次結算報告 dict
        """
        daily_target = self._schedule_config.get("daily_target", 2)

        # 從精煉結果統計
        all_refiner = refiner_results.get("results", [])
        total_generated = len(all_refiner)
        refiner_success = sum(1 for r in all_refiner if r["status"] == "success")
        refiner_discarded = sum(1 for r in all_refiner if r["status"] == "discarded")
        total_retries = refiner_results.get("total_retries_used", 0)

        # 從品質檢測結果統計
        passed = sum(1 for r in inspection_results if r.get("verdict") == "PASS")
        retried_in_inspection = sum(1 for r in inspection_results if r.get("verdict") == "RETRY")
        discarded_in_inspection = sum(1 for r in inspection_results if r.get("verdict") == "DISCARD")

        # 分數統計
        pass_scores = [r["final_score"] for r in inspection_results if r.get("verdict") == "PASS"]
        avg_score = round(sum(pass_scores) / len(pass_scores), 2) if pass_scores else 0

        # 缺陷摘要
        defect_summary = self._summarize_defects(inspection_results)

        # 上傳狀態
        upload_status = {
            "dreamstime_ftp": {
                "uploaded": ftp_result.get("uploaded", 0) if ftp_result else 0,
                "failed": ftp_result.get("failed", 0) if ftp_result else 0
            },
            "adobe_stock_notified": True
        }

        # 通過率計算
        pass_rate = round(passed / total_generated, 2) if total_generated > 0 else 0
        final_pass_rate = round(passed / daily_target, 2) if daily_target > 0 else 0

        report = {
            "date": date_str,
            "session_id": f"ws-{date_str.replace('-', '')}-001",
            "target": daily_target,
            "today_theme": theme,
            "prompt_source": prompt_source,
            "generated": total_generated,
            "passed": passed,
            "retried": total_retries + retried_in_inspection,
            "discarded": refiner_discarded + discarded_in_inspection,
            "pass_rate": pass_rate,
            "final_pass_rate": min(1.0, final_pass_rate),
            "avg_score": avg_score,
            "topic_detail": {
                "theme": theme,
                "target": daily_target,
                "passed": passed,
                "avg_score": avg_score
            },
            "total_generation_time_min": round(total_generation_time_sec / 60, 1),
            "stage0_brief_used": stage0_used,
            "defect_summary": defect_summary,
            "upload_status": upload_status,
            "refiner_observation": refiner_results.get("observation", {}),
            "inspection_details": [
                {
                    "image_id": r.get("image_id"),
                    "verdict": r.get("verdict"),
                    "score": r.get("final_score"),
                    "defect_count": len(r.get("layer3_defects", []))
                }
                for r in inspection_results
            ]
        }

        # 儲存到 metrics
        report_path = self._metrics_dir / f"daily_{date_str}.json"
        self._save_json(report_path, report)
        logger.info(f"批次結算報告已儲存: {report_path}")

        return report

    def _summarize_defects(self, inspection_results: list) -> dict:
        """彙總缺陷統計"""
        summary = {
            "eye_issues": 0,
            "hand_issues": 0,
            "composition": 0,
            "color_issues": 0,
            "anatomy_other": 0,
            "technical": 0
        }

        for r in inspection_results:
            defects = r.get("layer3_defects", []) or []
            for d in defects:
                dtype = d.get("type", "").lower()
                if "eye" in dtype or "pupil" in dtype:
                    summary["eye_issues"] += 1
                elif "finger" in dtype or "hand" in dtype:
                    summary["hand_issues"] += 1
                elif "compos" in dtype or "crop" in dtype:
                    summary["composition"] += 1
                elif "color" in dtype or "saturat" in dtype:
                    summary["color_issues"] += 1
                elif "anatom" in dtype or "propor" in dtype:
                    summary["anatomy_other"] += 1
                else:
                    summary["technical"] += 1

        return summary

    # ================================================================
    # 通知格式化（供顯示給 LXYA）
    # ================================================================

    def format_daily_summary(self, report: dict) -> str:
        """
        將批次結算報告格式化為可讀文字（供 LXYA 閱讀）。
        """
        lines = [
            f"📊 每日生產報告 — {report['date']}",
            f"主題: {report['today_theme']}",
            f"來源: {'創意簡報' if report['prompt_source'] == 'creative_brief' else '模板模式'}",
            "",
            f"目標: {report['target']} 張 | 通過: {report['passed']} 張 | 達成率: {report['final_pass_rate']:.0%}",
            f"平均分數: {report['avg_score']}",
            f"生成總數: {report['generated']} | 重試: {report['retried']} | 丟棄: {report['discarded']}",
            f"總耗時: {report['total_generation_time_min']} 分鐘",
            "",
            "上傳狀態:",
            f"  Dreamstime FTP: {report['upload_status']['dreamstime_ftp']['uploaded']} 成功 / {report['upload_status']['dreamstime_ftp']['failed']} 失敗",
            f"  Adobe Stock: {'已通知手動上傳' if report['upload_status']['adobe_stock_notified'] else '未通知'}",
        ]

        # 缺陷摘要
        ds = report.get("defect_summary", {})
        if any(v > 0 for v in ds.values()):
            lines.append("")
            lines.append("缺陷摘要:")
            if ds.get("eye_issues", 0):
                lines.append(f"  眼部: {ds['eye_issues']}")
            if ds.get("hand_issues", 0):
                lines.append(f"  手部: {ds['hand_issues']}")
            if ds.get("composition", 0):
                lines.append(f"  構圖: {ds['composition']}")

        return "\n".join(lines)

