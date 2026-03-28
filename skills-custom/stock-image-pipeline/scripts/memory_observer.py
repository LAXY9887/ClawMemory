"""
memory_observer.py — 觀測記錄模組

職責：
- 收集各 Stage 的 _observation 數據
- 寫入 memory/metrics/ 目錄供後續分析
- 寫入 memory/daily/ 作為當日自然語言摘要
- 不觸發 RICE+S，純觀測數據落地

資料來源：
  prompt_generator._observation
  image_refiner._observation
  defect_detector._observation
  upload_preparer.generate_batch_report()

寫入目標：
  memory/metrics/daily_{date}.json    — 結構化每日觀測
  memory/daily/{date}_stock.md        — 自然語言摘要（帶 YAML frontmatter）
"""

import json
import logging
from pathlib import Path
from datetime import datetime

# ---------- path resolution ----------
SCRIPT_DIR = str(Path(__file__).resolve().parent)
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

logger = logging.getLogger("stock-image.memory_observer")


class MemoryObserver:
    """
    收集 pipeline 各階段的觀測數據，統一寫入記憶系統。
    """

    def __init__(self):
        self._initialized = False
        self._schedule_config = {}
        self._memory_base = None
        self._observations = {}

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
    # 收集觀測
    # ------------------------------------------------------------------
    def collect(self, stage_name: str, observation: dict):
        """
        收集單一階段的觀測。
        stage_name: "prompt_generator" | "image_refiner" | "defect_detector" | "upload_preparer"
        observation: 各模組回傳的 _observation dict
        """
        self._observations[stage_name] = observation
        logger.info(f"收集觀測: {stage_name} ({len(observation)} fields)")

    def collect_pipeline_meta(self, meta: dict):
        """
        收集 pipeline 級別的元數據。
        meta: {"theme", "date", "daily_target", "total_produced", "total_retries",
               "start_time", "end_time", ...}
        """
        self._observations["pipeline_meta"] = meta
        logger.info(f"收集 pipeline 元數據: {list(meta.keys())}")

    # ------------------------------------------------------------------
    # 寫入結構化觀測 → memory/metrics/daily_{date}.json
    # ------------------------------------------------------------------
    def save_daily_observation(self, date_str: str = None):
        """
        將所有已收集的觀測合併為一份每日報告，寫入 memory/metrics/。
        回傳寫入路徑。
        """
        self._ensure_init()

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        metrics_dir = self._memory_base / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        report = {
            "date": date_str,
            "generated_at": datetime.now().isoformat(),
            "pipeline_meta": self._observations.get("pipeline_meta", {}),
            "stages": {}
        }

        # 各 Stage 觀測
        stage_keys = [
            "creative_brief",
            "prompt_generator",
            "image_refiner",
            "defect_detector",
            "upload_preparer"
        ]
        for key in stage_keys:
            if key in self._observations:
                report["stages"][key] = self._observations[key]

        # 計算摘要統計
        report["summary"] = self._compute_summary(report)

        out_path = metrics_dir / f"daily_{date_str}.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"每日觀測已寫入: {out_path}")
            return str(out_path)
        except Exception as e:
            logger.error(f"寫入每日觀測失敗: {e}")
            return None

    # ------------------------------------------------------------------
    # 寫入自然語言摘要 → memory/daily/{date}_stock.md
    # ------------------------------------------------------------------
    def save_daily_summary_md(self, date_str: str = None):
        """
        產出帶 YAML frontmatter 的自然語言摘要，寫入 memory/daily/。
        回傳寫入路徑。
        """
        self._ensure_init()

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        daily_dir = self._memory_base / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        meta = self._observations.get("pipeline_meta", {})
        theme = meta.get("theme", "unknown")
        total_produced = meta.get("total_produced", 0)
        total_retries = meta.get("total_retries", 0)

        # 各階段摘要
        refiner_obs = self._observations.get("image_refiner", {})
        defect_obs = self._observations.get("defect_detector", {})
        prompt_obs = self._observations.get("prompt_generator", {})

        total_gen = refiner_obs.get("total_images_generated", 0)
        pass_count = defect_obs.get("pass_count", 0)
        retry_count = defect_obs.get("retry_count", 0)
        discard_count = defect_obs.get("discard_count", 0)
        prompt_src = prompt_obs.get("prompt_source", "unknown")
        insight_applied = prompt_obs.get("insight_applied", [])

        # 組裝 frontmatter
        frontmatter_lines = [
            "---",
            f"date: {date_str}",
            f"source: stock-image-pipeline",
            f"type: daily-production-summary",
            f"theme: {theme}",
            f"produced: {total_produced}",
            "---",
        ]

        # 組裝內容
        body_lines = [
            f"# Stock Pipeline 每日摘要 — {date_str}",
            "",
            f"今日主題: **{theme}**",
            f"提示詞來源: {prompt_src}",
            "",
            f"## 生產數據",
            f"- 候選圖生成總數: {total_gen}",
            f"- 通過品質檢測: {pass_count}",
            f"- 需要重試: {retry_count}",
            f"- 已丟棄: {discard_count}",
            f"- 最終上架數量: {total_produced}",
            f"- 總重試次數: {total_retries}",
            "",
        ]

        if insight_applied:
            body_lines.append("## 應用的經驗洞察")
            for ins in insight_applied:
                body_lines.append(f"- {ins}")
            body_lines.append("")

        # OpenRouter / ComfyUI 使用量
        openrouter_calls = (
            refiner_obs.get("openrouter_eval_calls", 0) +
            defect_obs.get("layer2_calls", 0) +
            defect_obs.get("layer3_calls", 0)
        )
        comfyui_calls = refiner_obs.get("comfyui_calls", 0)

        body_lines.extend([
            "## 資源消耗",
            f"- OpenRouter 呼叫次數: {openrouter_calls}",
            f"- ComfyUI 呼叫次數: {comfyui_calls}",
            f"- Ollama fallback 使用: {'是' if refiner_obs.get('ollama_fallback_used') else '否'}",
            "",
        ])

        # 寫入
        content = "\n".join(frontmatter_lines) + "\n\n" + "\n".join(body_lines) + "\n"

        out_path = daily_dir / f"{date_str}_stock.md"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"每日摘要已寫入: {out_path}")
            return str(out_path)
        except Exception as e:
            logger.error(f"寫入每日摘要失敗: {e}")
            return None

    # ------------------------------------------------------------------
    # 摘要統計計算
    # ------------------------------------------------------------------
    def _compute_summary(self, report: dict) -> dict:
        """
        從 stages 中提取摘要統計。
        """
        stages = report.get("stages", {})
        meta = report.get("pipeline_meta", {})

        refiner = stages.get("image_refiner", {})
        defect = stages.get("defect_detector", {})
        prompt = stages.get("prompt_generator", {})

        total_generated = refiner.get("total_images_generated", 0)
        pass_count = defect.get("pass_count", 0)
        discard_count = defect.get("discard_count", 0)

        # 計算 pass rate
        inspected = pass_count + defect.get("retry_count", 0) + discard_count
        pass_rate = round(pass_count / inspected, 3) if inspected > 0 else 0.0

        return {
            "theme": meta.get("theme", "unknown"),
            "total_produced": meta.get("total_produced", 0),
            "total_candidates_generated": total_generated,
            "pass_rate": pass_rate,
            "total_retries_used": meta.get("total_retries", 0),
            "prompt_source": prompt.get("prompt_source", "unknown"),
            "insight_count": len(prompt.get("insight_applied", [])),
            "openrouter_total_calls": (
                refiner.get("openrouter_eval_calls", 0) +
                defect.get("layer2_calls", 0) +
                defect.get("layer3_calls", 0)
            ),
            "comfyui_total_calls": refiner.get("comfyui_calls", 0),
        }

    # ------------------------------------------------------------------
    # 讀取歷史觀測
    # ------------------------------------------------------------------
    def load_daily_observation(self, date_str: str) -> dict:
        """讀取指定日期的每日觀測報告。"""
        self._ensure_init()
        path = self._memory_base / "metrics" / f"daily_{date_str}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"找不到觀測: {path}")
            return {}
        except Exception as e:
            logger.error(f"讀取觀測失敗: {e}")
            return {}

    def load_recent_observations(self, days: int = 7) -> list:
        """讀取最近 N 天的觀測報告（用於趨勢分析）。"""
        self._ensure_init()
        metrics_dir = self._memory_base / "metrics"
        if not metrics_dir.exists():
            return []

        files = sorted(metrics_dir.glob("daily_*.json"), reverse=True)
        results = []
        for f in files[:days]:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    results.append(json.load(fh))
            except Exception as e:
                logger.warning(f"讀取 {f.name} 失敗: {e}")
        return results

    # ------------------------------------------------------------------
    # 公開介面
    # ------------------------------------------------------------------
    def get_observations(self) -> dict:
        """回傳所有已收集的觀測（供 pipeline_main 傳遞給其他模組）。"""
        return self._observations.copy()

    def reset(self):
        """重置觀測（每日生產前呼叫）。"""
        self._observations = {}
        logger.info("觀測數據已重置")


