"""
experience_distiller.py — 經驗萃取模組 (AAR: After Action Review)

職責：
- 批次完成後分析觀測數據，萃取可執行的洞察
- 使用 Ollama qwen3:8b 進行推理（非 OpenRouter，節省成本）
- 產出 insight 寫入 memory/insights/（帶 YAML frontmatter）
- 標記 source: realtime_aar，供 prompt_generator 讀取

觸發時機：
  pipeline_main 在 Stage 5 完成後呼叫

分析維度：
  1. 品質趨勢  — 近期 pass_rate 是否下降
  2. 主題表現  — 哪個主題表現最好/最差
  3. 缺陷模式  — 重複出現的缺陷類型
  4. 提示詞效能 — brief vs template 模式的成功率差異
  5. 資源效率  — 候選圖/通過圖 比例
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# ---------- path resolution ----------
SCRIPT_DIR = str(Path(__file__).resolve().parent)
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

logger = logging.getLogger("stock-image.experience_distiller")


class ExperienceDistiller:
    """
    從歷史觀測中萃取經驗洞察，寫入記憶系統。
    """

    def __init__(self):
        self._initialized = False
        self._schedule_config = {}
        self._memory_base = None
        self._ollama_config = {}

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
        self._ollama_config = self._schedule_config.get("ollama", {
            "model": "qwen3:8b",
            "host": "http://localhost:11434"
        })
        self._initialized = True

    # ------------------------------------------------------------------
    # 主入口：批次後 AAR
    # ------------------------------------------------------------------
    def run_aar(self, today_observation: dict, date_str: str = None) -> dict:
        """
        After Action Review — 批次完成後的經驗萃取。

        Args:
            today_observation: MemoryObserver.get_observations() 回傳的完整觀測
            date_str: 日期字串 (YYYY-MM-DD)

        Returns:
            {
                "insights_generated": int,
                "insight_files": [str],
                "analysis_summary": str
            }
        """
        self._ensure_init()

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 載入近 7 天歷史
        recent_data = self._load_recent_metrics(days=7)

        # 分析各維度
        analyses = []
        analyses.append(self._analyze_quality_trend(today_observation, recent_data))
        analyses.append(self._analyze_topic_performance(today_observation, recent_data))
        analyses.append(self._analyze_defect_patterns(today_observation, recent_data))
        analyses.append(self._analyze_prompt_effectiveness(today_observation, recent_data))
        analyses.append(self._analyze_resource_efficiency(today_observation, recent_data))

        # 過濾出有效分析（非 None）
        valid_analyses = [a for a in analyses if a is not None]

        if not valid_analyses:
            logger.info("今日無顯著洞察可萃取")
            return {
                "insights_generated": 0,
                "insight_files": [],
                "analysis_summary": "今日生產數據正常，無顯著洞察"
            }

        # 嘗試用 Ollama 綜合推理
        synthesized = self._synthesize_with_ollama(valid_analyses, today_observation, date_str)
        if synthesized is None:
            # Ollama 不可用時，直接用 rule-based 結論
            synthesized = valid_analyses

        # 寫入 insights
        insight_files = []
        for i, insight in enumerate(synthesized):
            path = self._save_insight(insight, date_str, i)
            if path:
                insight_files.append(path)

        summary = f"萃取 {len(insight_files)} 條洞察: " + "; ".join(
            ins.get("title", "?") for ins in synthesized
        )
        logger.info(summary)

        return {
            "insights_generated": len(insight_files),
            "insight_files": insight_files,
            "analysis_summary": summary
        }

    # ------------------------------------------------------------------
    # 分析維度 1: 品質趨勢
    # ------------------------------------------------------------------
    def _analyze_quality_trend(self, today: dict, history: list) -> dict:
        """
        檢查 pass_rate 是否持續下降。
        """
        if len(history) < 3:
            return None  # 數據不足

        today_summary = today.get("pipeline_meta", {})
        today_pass = today_summary.get("pass_rate", None)

        # 從歷史提取 pass_rate
        rates = []
        for h in history:
            s = h.get("summary", {})
            r = s.get("pass_rate")
            if r is not None:
                rates.append(r)

        if not rates or today_pass is None:
            return None

        avg_recent = sum(rates) / len(rates)

        # 若今日低於 7 天平均 15% 以上，產出洞察
        if today_pass < avg_recent - 0.15:
            return {
                "dimension": "quality_trend",
                "title": "品質下降警告",
                "finding": f"今日 pass_rate {today_pass:.1%} 低於近 {len(rates)} 天平均 {avg_recent:.1%}",
                "suggestion": "建議檢查提示詞品質、ComfyUI 模型狀態、或降低品質門檻暫時適應",
                "severity": "warning",
                "tags": ["quality", "trend", "pass-rate"]
            }

        # 連續 3 天下降
        if len(rates) >= 3:
            declining = all(rates[i] > rates[i+1] for i in range(min(3, len(rates))-1))
            if declining and today_pass is not None:
                return {
                    "dimension": "quality_trend",
                    "title": "品質連續下降趨勢",
                    "finding": f"近 {len(rates)} 天 pass_rate 持續下降: {[f'{r:.1%}' for r in rates[:3]]}",
                    "suggestion": "建議切換模型策略或調整 refinement 參數",
                    "severity": "info",
                    "tags": ["quality", "trend", "declining"]
                }

        return None

    # ------------------------------------------------------------------
    # 分析維度 2: 主題表現
    # ------------------------------------------------------------------
    def _analyze_topic_performance(self, today: dict, history: list) -> dict:
        """
        比較不同主題的通過率。
        """
        # 統計各主題的 pass_rate
        topic_stats = {}
        for h in history:
            s = h.get("summary", {})
            theme = s.get("theme", "unknown")
            rate = s.get("pass_rate")
            if rate is not None and theme != "unknown":
                if theme not in topic_stats:
                    topic_stats[theme] = []
                topic_stats[theme].append(rate)

        if len(topic_stats) < 2:
            return None  # 至少要有 2 個主題才能比較

        # 計算各主題平均
        avgs = {}
        for theme, rates in topic_stats.items():
            avgs[theme] = sum(rates) / len(rates)

        best = max(avgs, key=avgs.get)
        worst = min(avgs, key=avgs.get)

        # 差距超過 20% 才產出洞察
        if avgs[best] - avgs[worst] > 0.20:
            return {
                "dimension": "topic_performance",
                "title": f"主題表現差異顯著",
                "finding": f"最佳: {best} ({avgs[best]:.1%}), 最差: {worst} ({avgs[worst]:.1%})",
                "suggestion": f"建議為 {worst} 主題調整提示詞策略或 LoRA 權重",
                "severity": "info",
                "tags": ["topic", "performance", best, worst]
            }

        return None

    # ------------------------------------------------------------------
    # 分析維度 3: 缺陷模式
    # ------------------------------------------------------------------
    def _analyze_defect_patterns(self, today: dict, history: list) -> dict:
        """
        檢查是否有重複出現的缺陷類型。
        """
        defect_obs = today.get("defect_detector", {})

        # 無缺陷數據
        if not defect_obs:
            return None

        # 統計今日缺陷 (假設 defect_detector observation 包含 common_defects)
        layer1_rejects = defect_obs.get("layer1_rejects", 0)
        ollama_repairs = defect_obs.get("ollama_repair_calls", 0)

        # 若 layer1 reject 比例高，說明基礎品質問題
        if layer1_rejects > 0:
            return {
                "dimension": "defect_patterns",
                "title": "基礎品質篩選異常",
                "finding": f"Layer1 快速篩選淘汰 {layer1_rejects} 張圖（解析度/色彩問題）",
                "suggestion": "檢查 ComfyUI 輸出設定，確認解析度與色彩空間正確",
                "severity": "warning",
                "tags": ["defect", "layer1", "basic-quality"]
            }

        return None

    # ------------------------------------------------------------------
    # 分析維度 4: 提示詞效能
    # ------------------------------------------------------------------
    def _analyze_prompt_effectiveness(self, today: dict, history: list) -> dict:
        """
        比較 brief 模式 vs template 模式的品質差異。
        """
        brief_rates = []
        template_rates = []

        all_data = history + [{"summary": today.get("pipeline_meta", {}),
                                "stages": today}]

        for h in history:
            s = h.get("summary", {})
            src = s.get("prompt_source", "")
            rate = s.get("pass_rate")
            if rate is None:
                continue
            if src == "creative_brief":
                brief_rates.append(rate)
            elif src == "template_fallback":
                template_rates.append(rate)

        if len(brief_rates) >= 2 and len(template_rates) >= 2:
            avg_brief = sum(brief_rates) / len(brief_rates)
            avg_template = sum(template_rates) / len(template_rates)
            diff = avg_brief - avg_template

            if abs(diff) > 0.10:
                better = "creative_brief" if diff > 0 else "template_fallback"
                return {
                    "dimension": "prompt_effectiveness",
                    "title": f"提示詞模式效能差異",
                    "finding": (
                        f"creative_brief 平均 {avg_brief:.1%} vs "
                        f"template_fallback 平均 {avg_template:.1%}"
                    ),
                    "suggestion": (
                        f"{better} 模式表現較佳，建議優先確保其可用性"
                        if better == "creative_brief"
                        else "template_fallback 意外表現較佳，建議改善 creative_brief 對話品質"
                    ),
                    "severity": "info",
                    "tags": ["prompt", "effectiveness", better]
                }

        return None

    # ------------------------------------------------------------------
    # 分析維度 5: 資源效率
    # ------------------------------------------------------------------
    def _analyze_resource_efficiency(self, today: dict, history: list) -> dict:
        """
        計算候選圖/通過圖比例，評估資源浪費程度。
        """
        refiner_obs = today.get("image_refiner", {})
        meta = today.get("pipeline_meta", {})

        total_gen = refiner_obs.get("total_images_generated", 0)
        total_produced = meta.get("total_produced", 0)

        if total_gen == 0 or total_produced == 0:
            return None

        ratio = total_gen / total_produced

        # 理想比例: 每張通過圖約 10-15 張候選（初步5 + 精煉5）
        # 若超過 25 張，說明效率低下
        if ratio > 25:
            return {
                "dimension": "resource_efficiency",
                "title": "資源效率偏低",
                "finding": f"生成 {total_gen} 張候選圖才產出 {total_produced} 張，比例 {ratio:.1f}:1",
                "suggestion": "建議提升初步評分的篩選精度，或調整 denoise range 縮小精煉範圍",
                "severity": "info",
                "tags": ["efficiency", "resource", "candidate-ratio"]
            }

        return None

    # ------------------------------------------------------------------
    # Ollama 綜合推理
    # ------------------------------------------------------------------
    def _synthesize_with_ollama(self, analyses: list, today_obs: dict, date_str: str) -> list:
        """
        使用 Ollama 綜合多維分析結果，產出更精練的洞察。
        失敗時回傳 None（fallback 到 rule-based）。
        """
        try:
            import requests
        except ImportError:
            logger.warning("requests 模組不可用，跳過 Ollama 綜合推理")
            return None

        host = self._ollama_config.get("host", "http://localhost:11434")
        model = self._ollama_config.get("model", "qwen3:8b")

        prompt = self._build_synthesis_prompt(analyses, today_obs, date_str)

        payload = {
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 1024
            }
        }

        try:
            resp = requests.post(
                f"{host}/api/generate",
                json=payload,
                timeout=60
            )
            resp.raise_for_status()
            result = resp.json()
            text = result.get("response", "")
            parsed = json.loads(text)

            # 期望格式: {"insights": [{"title": ..., "finding": ..., "suggestion": ..., ...}]}
            insights = parsed.get("insights", [])
            if not insights:
                return None

            # 補充必要欄位
            for ins in insights:
                ins.setdefault("severity", "info")
                ins.setdefault("tags", [])
                ins.setdefault("dimension", "synthesized")

            logger.info(f"Ollama 綜合推理產出 {len(insights)} 條洞察")
            return insights

        except requests.exceptions.ConnectionError:
            logger.warning("Ollama 不可用，使用 rule-based 洞察")
            return None
        except Exception as e:
            logger.warning(f"Ollama 綜合推理失敗: {e}")
            return None

    def _build_synthesis_prompt(self, analyses: list, today_obs: dict, date_str: str) -> str:
        """構建 Ollama 推理 prompt。"""
        meta = today_obs.get("pipeline_meta", {})

        analyses_text = ""
        for a in analyses:
            analyses_text += (
                f"\n- 維度: {a.get('dimension')}\n"
                f"  發現: {a.get('finding')}\n"
                f"  建議: {a.get('suggestion')}\n"
            )

        return f"""你是 AI 圖片生產 Pipeline 的經驗分析師。
今日日期: {date_str}
今日主題: {meta.get('theme', 'unknown')}
今日產出: {meta.get('total_produced', 0)} 張

以下是今日各維度的分析結果:
{analyses_text}

請綜合以上分析，產出精煉的洞察清單。每條洞察需包含:
- title: 簡短標題 (中文)
- finding: 具體發現
- suggestion: 可執行的建議
- tags: 相關標籤列表
- severity: info / warning / critical

回傳 JSON 格式:
{{"insights": [{{"title": "...", "finding": "...", "suggestion": "...", "tags": [...], "severity": "..."}}]}}

只保留有價值的洞察（避免重複或無意義的建議），最多 3 條。"""

    # ------------------------------------------------------------------
    # 寫入 insight 到 memory/insights/
    # ------------------------------------------------------------------
    def _save_insight(self, insight: dict, date_str: str, seq: int) -> str:
        """
        寫入單條 insight 到 memory/insights/。
        檔名: {date}_{seq}_{dimension}.md
        """
        self._ensure_init()
        insights_dir = self._memory_base / "insights"
        insights_dir.mkdir(parents=True, exist_ok=True)

        dimension = insight.get("dimension", "general")
        title = insight.get("title", "洞察")
        finding = insight.get("finding", "")
        suggestion = insight.get("suggestion", "")
        severity = insight.get("severity", "info")
        tags = insight.get("tags", [])

        tags_str = ", ".join(tags) if tags else "stock-pipeline"

        content = f"""---
date: {date_str}
source: realtime_aar
type: pipeline-insight
dimension: {dimension}
severity: {severity}
tags: [{tags_str}]
---

# {title}

## 發現
{finding}

## 建議
{suggestion}
"""

        filename = f"{date_str}_{seq:02d}_{dimension}.md"
        out_path = insights_dir / filename

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Insight 已寫入: {out_path}")
            return str(out_path)
        except Exception as e:
            logger.error(f"寫入 insight 失敗: {e}")
            return None

    # ------------------------------------------------------------------
    # 載入歷史 metrics
    # ------------------------------------------------------------------
    def _load_recent_metrics(self, days: int = 7) -> list:
        """讀取最近 N 天的 daily metrics。"""
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
    # 週期性深度分析（週報觸發）
    # ------------------------------------------------------------------
    def run_weekly_analysis(self) -> dict:
        """
        每週綜合分析，產出更高層次的經驗洞察。
        由 metrics_collector 的週報流程呼叫。
        """
        self._ensure_init()
        recent = self._load_recent_metrics(days=7)

        if len(recent) < 3:
            return {
                "status": "insufficient_data",
                "message": f"僅有 {len(recent)} 天數據，不足以進行週分析"
            }

        # 統計週彙總
        total_produced = sum(
            h.get("summary", {}).get("total_produced", 0) for h in recent
        )
        avg_pass_rate = 0.0
        rates = [h.get("summary", {}).get("pass_rate", 0) for h in recent if h.get("summary", {}).get("pass_rate") is not None]
        if rates:
            avg_pass_rate = sum(rates) / len(rates)

        # 主題分布
        theme_counts = {}
        for h in recent:
            theme = h.get("summary", {}).get("theme", "unknown")
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

        return {
            "status": "completed",
            "period_days": len(recent),
            "total_produced": total_produced,
            "avg_pass_rate": round(avg_pass_rate, 3),
            "theme_distribution": theme_counts,
            "total_openrouter_calls": sum(
                h.get("summary", {}).get("openrouter_total_calls", 0) for h in recent
            ),
            "total_comfyui_calls": sum(
                h.get("summary", {}).get("comfyui_total_calls", 0) for h in recent
            )
        }


