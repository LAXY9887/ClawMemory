"""
metrics_collector.py — 結算報告與週報收集模組

職責：
- 週報彙總: 收集過去 7 天的 daily metrics 產出週報
- 月度歸檔: 歸檔超過 90 天的 daily metrics 為 tar.gz
- 成本追蹤: 彙總 OpenRouter API 成本（從 daily metrics 累計）
- 趨勢分析: 品質/產量/效率 的週/月趨勢

觸發時機：
  週報: 由 heartbeat 在每週日觸發 (schedule.json weekly_report)
  月報: 由 heartbeat 在每月 1 日觸發 (schedule.json monthly_archive)
"""

import json
import logging
import tarfile
from pathlib import Path
from datetime import datetime, timedelta

# ---------- path resolution ----------
SCRIPT_DIR = str(Path(__file__).resolve().parent)
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

logger = logging.getLogger("stock-image.metrics_collector")


class MetricsCollector:
    """
    負責週報生成、月度歸檔、以及成本/趨勢分析。
    """

    def __init__(self):
        self._initialized = False
        self._schedule_config = {}
        self._memory_base = None

    # ------------------------------------------------------------------
    # init
    # ------------------------------------------------------------------
    def _ensure_init(self):
        if self._initialized:
            return
        try:
            with open(CONFIG_DIR / "schedule.json", "r", encoding="utf-8") as f:
                self._schedule_config = json.load(f)
        except Exception as e:
            logger.warning(f"schedule.json 載入失敗: {e}")
            self._schedule_config = {}

        ws_base = self._schedule_config.get("workspace", {}).get(
            "base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline"
        )
        self._memory_base = Path(ws_base).expanduser()/ ".." / ".." / "memory" / "stock-pipeline"
        self._initialized = True

    # ------------------------------------------------------------------
    # 週報生成
    # ------------------------------------------------------------------
    def generate_weekly_report(self, end_date: str = None) -> dict:
        """
        生成過去 7 天的週報。

        Args:
            end_date: 週報截止日 (YYYY-MM-DD)，預設今天

        Returns:
            {
                "status": "completed" | "insufficient_data",
                "report_path": str | None,
                "summary": dict
            }
        """
        self._ensure_init()

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        start_dt = end_dt - timedelta(days=6)
        start_date = start_dt.strftime("%Y-%m-%d")

        # 收集 7 天 daily metrics
        daily_reports = self._load_date_range(start_date, end_date)

        if len(daily_reports) < 1:
            return {
                "status": "insufficient_data",
                "report_path": None,
                "summary": {"message": f"無可用的 daily metrics ({start_date} ~ {end_date})"}
            }

        # 彙總統計
        summary = self._aggregate_weekly(daily_reports)
        summary["period"] = {"start": start_date, "end": end_date, "days_with_data": len(daily_reports)}

        # 趨勢分析
        summary["trends"] = self._compute_trends(daily_reports)

        # 主題表現排名
        summary["topic_ranking"] = self._rank_topics(daily_reports)

        # 組裝完整報告
        report = {
            "type": "weekly_report",
            "generated_at": datetime.now().isoformat(),
            "period": summary["period"],
            "summary": summary,
            "daily_breakdown": [
                {
                    "date": d.get("date"),
                    "theme": d.get("summary", {}).get("theme"),
                    "produced": d.get("summary", {}).get("total_produced", 0),
                    "pass_rate": d.get("summary", {}).get("pass_rate", 0),
                    "openrouter_calls": d.get("summary", {}).get("openrouter_total_calls", 0),
                    "comfyui_calls": d.get("summary", {}).get("comfyui_total_calls", 0),
                }
                for d in daily_reports
            ]
        }

        # 寫入
        weekly_dir = self._memory_base / "metrics" / "weekly"
        weekly_dir.mkdir(parents=True, exist_ok=True)

        filename = f"weekly_{end_date}.json"
        out_path = weekly_dir / filename

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"週報已寫入: {out_path}")
        except Exception as e:
            logger.error(f"寫入週報失敗: {e}")
            return {
                "status": "write_failed",
                "report_path": None,
                "summary": summary
            }

        return {
            "status": "completed",
            "report_path": str(out_path),
            "summary": summary
        }

    # ------------------------------------------------------------------
    # 週彙總統計
    # ------------------------------------------------------------------
    def _aggregate_weekly(self, reports: list) -> dict:
        """彙總 7 天的核心指標。"""
        total_produced = 0
        total_candidates = 0
        total_retries = 0
        total_openrouter = 0
        total_comfyui = 0
        pass_rates = []

        for r in reports:
            s = r.get("summary", {})
            total_produced += s.get("total_produced", 0)
            total_candidates += s.get("total_candidates_generated", 0)
            total_retries += s.get("total_retries_used", 0)
            total_openrouter += s.get("openrouter_total_calls", 0)
            total_comfyui += s.get("comfyui_total_calls", 0)
            rate = s.get("pass_rate")
            if rate is not None:
                pass_rates.append(rate)

        avg_pass_rate = round(sum(pass_rates) / len(pass_rates), 3) if pass_rates else 0.0
        efficiency = round(total_candidates / total_produced, 1) if total_produced > 0 else 0.0

        return {
            "total_produced": total_produced,
            "total_candidates_generated": total_candidates,
            "avg_pass_rate": avg_pass_rate,
            "total_retries": total_retries,
            "candidates_per_output": efficiency,
            "total_openrouter_calls": total_openrouter,
            "total_comfyui_calls": total_comfyui,
        }

    # ------------------------------------------------------------------
    # 趨勢分析
    # ------------------------------------------------------------------
    def _compute_trends(self, reports: list) -> dict:
        """
        計算各指標的趨勢方向。
        """
        if len(reports) < 2:
            return {"direction": "insufficient_data"}

        # 按日期排序
        sorted_reports = sorted(reports, key=lambda x: x.get("date", ""))

        rates = [r.get("summary", {}).get("pass_rate", 0) for r in sorted_reports]
        produced = [r.get("summary", {}).get("total_produced", 0) for r in sorted_reports]

        def trend_direction(values):
            """簡單線性趨勢: 前半 vs 後半平均。"""
            if len(values) < 2:
                return "stable"
            mid = len(values) // 2
            first_half = sum(values[:mid]) / mid if mid > 0 else 0
            second_half = sum(values[mid:]) / (len(values) - mid) if (len(values) - mid) > 0 else 0
            diff = second_half - first_half
            if diff > 0.05:
                return "improving"
            elif diff < -0.05:
                return "declining"
            return "stable"

        return {
            "pass_rate": trend_direction(rates),
            "production": trend_direction(produced),
            "daily_pass_rates": [round(r, 3) for r in rates],
            "daily_production": produced,
        }

    # ------------------------------------------------------------------
    # 主題排名
    # ------------------------------------------------------------------
    def _rank_topics(self, reports: list) -> list:
        """按 pass_rate 對主題排名。"""
        topic_data = {}

        for r in reports:
            s = r.get("summary", {})
            theme = s.get("theme", "unknown")
            rate = s.get("pass_rate")
            produced = s.get("total_produced", 0)

            if theme not in topic_data:
                topic_data[theme] = {"rates": [], "total_produced": 0, "days": 0}
            if rate is not None:
                topic_data[theme]["rates"].append(rate)
            topic_data[theme]["total_produced"] += produced
            topic_data[theme]["days"] += 1

        ranking = []
        for theme, data in topic_data.items():
            avg = round(sum(data["rates"]) / len(data["rates"]), 3) if data["rates"] else 0
            ranking.append({
                "theme": theme,
                "avg_pass_rate": avg,
                "total_produced": data["total_produced"],
                "days_active": data["days"]
            })

        ranking.sort(key=lambda x: x["avg_pass_rate"], reverse=True)
        return ranking

    # ------------------------------------------------------------------
    # 月度歸檔
    # ------------------------------------------------------------------
    def run_monthly_archive(self) -> dict:
        """
        歸檔超過 archive_threshold_days (default 90) 天的 daily metrics。
        壓縮為 tar.gz 存放於 memory/metrics/archive/。
        """
        self._ensure_init()

        threshold_days = self._schedule_config.get(
            "monthly_archive", {}
        ).get("archive_threshold_days", 90)

        cutoff_date = datetime.now() - timedelta(days=threshold_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        metrics_dir = self._memory_base / "metrics"
        if not metrics_dir.exists():
            return {"status": "no_metrics_dir", "archived_count": 0}

        # 找出需要歸檔的檔案
        to_archive = []
        for f in metrics_dir.glob("daily_*.json"):
            # 從檔名提取日期
            try:
                file_date = f.stem.replace("daily_", "")
                if file_date < cutoff_str:
                    to_archive.append(f)
            except Exception:
                continue

        if not to_archive:
            logger.info(f"無需歸檔（cutoff: {cutoff_str}）")
            return {"status": "nothing_to_archive", "archived_count": 0}

        # 建立 archive 目錄
        archive_dir = metrics_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)

        # 壓縮
        archive_month = datetime.now().strftime("%Y-%m")
        archive_path = archive_dir / f"daily_metrics_{archive_month}.tar.gz"

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                for f in to_archive:
                    tar.add(f, arcname=f.name)

            # 壓縮成功後刪除原檔
            for f in to_archive:
                f.unlink()

            logger.info(f"已歸檔 {len(to_archive)} 個檔案 → {archive_path}")
            return {
                "status": "completed",
                "archived_count": len(to_archive),
                "archive_path": str(archive_path),
                "cutoff_date": cutoff_str
            }
        except Exception as e:
            logger.error(f"歸檔失敗: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "archived_count": 0
            }

    # ------------------------------------------------------------------
    # 格式化週報摘要（人類可讀中文）
    # ------------------------------------------------------------------
    def format_weekly_summary_text(self, report: dict) -> str:
        """
        將週報 JSON 轉為 LXYA 友好的中文摘要。
        """
        s = report.get("summary", {})
        period = s.get("period", {})
        trends = s.get("trends", {})
        ranking = s.get("topic_ranking", [])

        lines = [
            f"📊 Stock Pipeline 週報 ({period.get('start', '?')} ~ {period.get('end', '?')})",
            f"   數據天數: {period.get('days_with_data', 0)} 天",
            "",
            "▎ 產量與品質",
            f"   總產出: {s.get('total_produced', 0)} 張",
            f"   平均 pass rate: {s.get('avg_pass_rate', 0):.1%}",
            f"   候選/產出比: {s.get('candidates_per_output', 0):.1f}:1",
            f"   總重試次數: {s.get('total_retries', 0)}",
            "",
            "▎ 資源消耗",
            f"   OpenRouter 呼叫: {s.get('total_openrouter_calls', 0)}",
            f"   ComfyUI 呼叫: {s.get('total_comfyui_calls', 0)}",
            "",
            "▎ 趨勢",
            f"   Pass Rate: {trends.get('pass_rate', 'N/A')}",
            f"   產量: {trends.get('production', 'N/A')}",
            "",
        ]

        if ranking:
            lines.append("▎ 主題排名 (by pass rate)")
            for i, t in enumerate(ranking):
                lines.append(
                    f"   {i+1}. {t['theme']} — "
                    f"avg {t['avg_pass_rate']:.1%}, "
                    f"{t['total_produced']} 張, "
                    f"{t['days_active']} 天"
                )
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 載入日期範圍
    # ------------------------------------------------------------------
    def _load_date_range(self, start_date: str, end_date: str) -> list:
        """載入指定日期範圍的 daily metrics。"""
        self._ensure_init()
        metrics_dir = self._memory_base / "metrics"
        if not metrics_dir.exists():
            return []

        results = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current <= end:
            ds = current.strftime("%Y-%m-%d")
            path = metrics_dir / f"daily_{ds}.json"
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        results.append(json.load(f))
                except Exception as e:
                    logger.warning(f"讀取 {path.name} 失敗: {e}")
            current += timedelta(days=1)

        return results

    # ------------------------------------------------------------------
    # 快速查詢
    # ------------------------------------------------------------------
    def get_latest_stats(self, days: int = 7) -> dict:
        """
        取得最近 N 天的快速統計（供 LXYA 查詢或 prompt_generator 參考）。
        """
        self._ensure_init()
        metrics_dir = self._memory_base / "metrics"
        if not metrics_dir.exists():
            return {"available_days": 0}

        files = sorted(metrics_dir.glob("daily_*.json"), reverse=True)
        reports = []
        for f in files[:days]:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    reports.append(json.load(fh))
            except Exception:
                continue

        if not reports:
            return {"available_days": 0}

        total_produced = sum(r.get("summary", {}).get("total_produced", 0) for r in reports)
        rates = [r.get("summary", {}).get("pass_rate") for r in reports]
        rates = [r for r in rates if r is not None]
        avg_rate = round(sum(rates) / len(rates), 3) if rates else 0.0

        return {
            "available_days": len(reports),
            "total_produced": total_produced,
            "avg_pass_rate": avg_rate,
            "latest_date": reports[0].get("date") if reports else None
        }


