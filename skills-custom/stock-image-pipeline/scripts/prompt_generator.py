"""
Stage 1-2: 排程上下文載入 & 提示詞生成與優化

用途:
  - Stage 1: 讀取 Stage 0 創意簡報 + 經驗 insights + 主題配置
  - Stage 2: 基於簡報（或退化模板）產出正面/負面提示詞
  - Stage 2.2: Ollama qwen3:8b 本地 LLM 智能優化
  - Stage 2.3: 提示詞去重（7 天 85% 相似度閾值）

設計原則:
  - 簡報模式 (creative_brief) 優先；簡報不存在時退化為模板模式 (template_fallback)
  - 所有提示詞一律經 Ollama 優化
  - 畫布類型由簡報指定或依主題/canvas_override_rules 決定
  - 每張圖輸出完整的 PromptPackage（正面、負面、畫布、生成參數）
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# --- 相對路徑解析 ---
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"


class PromptGeneratorError(Exception):
    """提示詞生成失敗"""
    pass


class PromptGenerator:
    """
    Stage 1-2: 上下文載入 + 提示詞生成。

    使用方式:
        gen = PromptGenerator(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        packages = gen.run(date_str="2026-03-28", theme="eerie-scene")
        # packages = [PromptPackage, PromptPackage]  (2 張圖)
    """

    def __init__(self, workspace_base: Optional[str] = None):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")
        self._topics_config = self._load_json(CONFIG_DIR / "topics.json")

        # 工作區路徑
        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()
        self._briefs_dir = self._workspace / self._schedule_config.get("workspace", {}).get("briefs_dir", "briefs")

        # Ollama 配置
        ollama_cfg = self._schedule_config.get("ollama", {})
        self._ollama_model = ollama_cfg.get("model", "qwen3:8b")
        self._ollama_host = ollama_cfg.get("host", "http://localhost:11434")

        # 去重配置
        dedup_cfg = self._topics_config.get("prompt_dedup", {})
        self._dedup_history_days = dedup_cfg.get("history_days", 7)
        self._dedup_threshold = dedup_cfg.get("similarity_threshold", 0.85)
        self._dedup_history_file = dedup_cfg.get("history_file", "prompt_history.json")

        # 觀測數據（供 03 模組使用）
        self._observation = {
            "memory_reads_count": 0,
            "insight_applied": [],
            "context_load_time_ms": 0,
            "prompt_source": None  # "creative_brief" | "template_fallback"
        }

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            logger.warning(f"Config 不存在: {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ================================================================
    # Stage 1: 上下文載入
    # ================================================================

    def load_context(self, date_str: str, theme: str) -> dict:
        """
        Stage 1: 載入今日生產所需的完整上下文。

        Returns:
            {
                "brief": dict|None,        # Stage 0 簡報（None = 退化模板模式）
                "mode": str,               # "creative_brief" | "template_fallback"
                "theme": str,
                "topic_config": dict,       # topics.json 中該主題的配置
                "daily_target": int,
                "insights": list,           # 過往相關 insights
                "yesterday_stats": dict|None
            }
        """
        start = time.time()
        logger.info(f"=== Stage 1: 上下文載入 ({date_str}, {theme}) ===")

        # 1. 讀取創意簡報
        brief_path = self._briefs_dir / f"brief_{date_str}.json"
        brief = None
        mode = "template_fallback"

        if brief_path.exists():
            brief = self._load_json(brief_path)
            self._observation["memory_reads_count"] += 1
            # 判斷簡報是否為退化模式
            if brief.get("fallback"):
                mode = "template_fallback"
                logger.info("簡報存在但為 fallback 模式，使用模板生成")
            else:
                mode = "creative_brief"
                logger.info("簡報載入成功，使用創意簡報模式")
        else:
            logger.info(f"簡報不存在 ({brief_path})，退化為模板模式")

        # 2. 主題配置
        topic_config = self._topics_config.get("topics", {}).get(theme, {})

        # 3. 目標產量
        daily_target = self._schedule_config.get("daily_target", 2)

        # 4. 過往 insights（簡化版，與 Phase 3 同模式）
        insights = self._load_relevant_insights(theme)

        # 5. 昨日統計
        yesterday_stats = self._load_yesterday_stats(date_str)

        elapsed = (time.time() - start) * 1000
        self._observation["context_load_time_ms"] = round(elapsed)
        self._observation["prompt_source"] = mode

        logger.info(f"Stage 1 完成: mode={mode}, insights={len(insights)}, elapsed={elapsed:.0f}ms")

        return {
            "brief": brief,
            "mode": mode,
            "theme": theme,
            "topic_config": topic_config,
            "daily_target": daily_target,
            "insights": insights,
            "yesterday_stats": yesterday_stats
        }

    def _load_relevant_insights(self, theme: str) -> list:
        """載入主題相關 insights（簡化版）"""
        insights_dir = self._workspace / "memory" / "insights"
        if not insights_dir.exists():
            return []

        relevant = []
        try:
            for f in sorted(insights_dir.glob("*.md"), reverse=True)[:20]:
                content = f.read_text(encoding="utf-8")
                theme_variations = [theme, theme.replace("-", " "), theme.replace("-", "_")]
                if any(v in content.lower() for v in theme_variations):
                    first_line = content.split("\n")[0].strip("# ").strip()
                    if first_line:
                        relevant.append(first_line)
                        self._observation["insight_applied"].append(str(f))
                        self._observation["memory_reads_count"] += 1
                if len(relevant) >= 5:
                    break
        except Exception as e:
            logger.warning(f"載入 insights 失敗: {e}")
        return relevant

    def _load_yesterday_stats(self, today_str: str) -> Optional[dict]:
        """載入昨日生產統計"""
        try:
            yesterday = (datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            metrics_dir = self._workspace / "memory" / "metrics"
            stats_file = metrics_dir / f"daily_{yesterday}.json"
            if stats_file.exists():
                self._observation["memory_reads_count"] += 1
                return self._load_json(stats_file)
        except Exception as e:
            logger.warning(f"載入昨日統計失敗: {e}")
        return None

    # ================================================================
    # Stage 2: 提示詞生成
    # ================================================================

    def generate_prompts(self, context: dict) -> list:
        """
        Stage 2: 為今日所有圖片生成提示詞。

        Args:
            context: Stage 1 load_context() 的回傳值

        Returns:
            list of PromptPackage dicts:
            [
                {
                    "image_id": "brief-001",
                    "prompt_source": "creative_brief"|"template_fallback",
                    "positive_prompt": "...",
                    "negative_prompt": "...",
                    "canvas_type": "portrait"|"square"|"landscape",
                    "canvas_size_initial": [w, h],
                    "canvas_size_refined": [w, h],
                    "generation_params": {
                        "cfg": float, "steps": int, "sampler": str,
                        "lora": str|None, "lora_weight": float
                    },
                    "brief_concept": str|None,
                    "defect_warnings": list
                }, ...
            ]
        """
        logger.info(f"=== Stage 2: 提示詞生成 ({context['mode']}) ===")

        mode = context["mode"]
        theme = context["theme"]
        topic_config = context["topic_config"]
        brief = context["brief"]
        daily_target = context["daily_target"]

        packages = []

        if mode == "creative_brief" and brief:
            # --- 創意簡報模式 ---
            images = brief.get("images", [])
            for i, img in enumerate(images[:daily_target]):
                pkg = self._generate_from_brief(img, theme, topic_config, context["insights"])
                packages.append(pkg)

            # 若簡報圖片數不足目標，用模板補足
            if len(packages) < daily_target:
                logger.info(f"簡報圖片 {len(packages)} 張不足目標 {daily_target}，模板補足")
                for i in range(daily_target - len(packages)):
                    pkg = self._generate_from_template(
                        theme, topic_config, context["insights"],
                        image_index=len(packages) + i
                    )
                    packages.append(pkg)
        else:
            # --- 模板退化模式 ---
            for i in range(daily_target):
                pkg = self._generate_from_template(theme, topic_config, context["insights"], image_index=i)
                packages.append(pkg)

        # 2.2 Ollama 優化所有提示詞
        for pkg in packages:
            self._optimize_with_ollama(pkg, mode)

        # 2.3 去重檢查
        for pkg in packages:
            self._dedup_check(pkg)

        logger.info(f"Stage 2 完成: {len(packages)} 組提示詞")
        return packages

    # --- 創意簡報模式 ---

    def _generate_from_brief(
        self,
        image_brief: dict,
        theme: str,
        topic_config: dict,
        insights: list
    ) -> dict:
        """
        從創意簡報生成提示詞。

        映射規則:
          brief.concept              → 概念參考（不直接入提示詞，由 Ollama 融合）
          brief.visual_direction.positive_prompt_hints → 正面提示詞核心
          brief.visual_direction.negative_prompt_hints → 負面提示詞核心
          brief.visual_direction.canvas_type           → 畫布類型
          brief.visual_direction.lora_weight_adjustment → LoRA 微調
        """
        vd = image_brief.get("visual_direction", {})

        # 正面提示詞：組合 hints + 品質詞
        pos_hints = vd.get("positive_prompt_hints", [])
        quality_boost = ["masterpiece", "best quality", "highly detailed", "sharp focus"]
        positive_raw = ", ".join(pos_hints + quality_boost)

        # 負面提示詞：組合 hints + 主題預設 negative_boost
        neg_hints = vd.get("negative_prompt_hints", [])
        neg_boost = topic_config.get("negative_boost", [])
        base_negatives = ["worst quality", "low quality", "blurry", "watermark", "text", "signature"]
        negative_raw = ", ".join(list(set(neg_hints + neg_boost + base_negatives)))

        # 畫布
        canvas_type = vd.get("canvas_type", topic_config.get("default_canvas", "square"))
        canvas_type = self._apply_canvas_override(canvas_type, positive_raw)

        # 畫布尺寸
        canvas_types = self._topics_config.get("canvas_types", {})
        canvas_def = canvas_types.get(canvas_type, {})
        initial_size = canvas_def.get("initial", [768, 768])
        refined_size = canvas_def.get("refined", [1280, 1280])

        # 生成參數
        lora = topic_config.get("lora")
        lora_weight = topic_config.get("lora_weight", 0.7)

        # LoRA 微調（來自簡報）
        lora_adj = vd.get("lora_weight_adjustment")
        if lora_adj and isinstance(lora_adj, dict) and lora:
            adj_value = lora_adj.get(lora, 0)
            lora_weight = max(0, min(1.0, lora_weight + adj_value))

        # ClawClaw 特殊風格關鍵詞
        style_keywords = topic_config.get("style_keywords", [])
        if style_keywords:
            positive_raw = ", ".join(pos_hints + style_keywords + quality_boost)

        return {
            "image_id": image_brief.get("image_id", f"brief-{hash(str(image_brief)) % 1000:03d}"),
            "prompt_source": "creative_brief",
            "positive_prompt": positive_raw,
            "negative_prompt": negative_raw,
            "canvas_type": canvas_type,
            "canvas_size_initial": initial_size,
            "canvas_size_refined": refined_size,
            "generation_params": {
                "cfg": topic_config.get("base_cfg", 8),
                "initial_steps": topic_config.get("initial_steps", 22),
                "refined_steps": topic_config.get("refined_steps", 30),
                "sampler": topic_config.get("sampler", "euler_a"),
                "lora": lora,
                "lora_weight": lora_weight
            },
            "brief_concept": image_brief.get("concept"),
            "mood_keywords": image_brief.get("mood_keywords", []),
            "defect_warnings": vd.get("defect_warnings", []),
            "optimized": False  # Ollama 優化後設為 True
        }

    # --- 模板退化模式 ---

    # 每主題的提示詞模板庫（inline 定義，不使用外部 template 檔案）
    TEMPLATE_LIBRARY = {
        "tech-abstract": {
            "concepts": [
                "futuristic neural network visualization, abstract data flow, glowing nodes and connections",
                "quantum computing concept art, entangled particles, ethereal energy streams",
                "holographic interface design, floating data panels, blue light projections",
                "abstract circuit board landscape, neon traces, microscopic technology world",
                "digital DNA helix, bio-tech fusion, translucent molecular structure"
            ],
            "style": "digital art, clean lines, volumetric lighting, sci-fi aesthetic",
            "variation_dims": ["concept_type", "color_temperature", "complexity", "perspective"]
        },
        "eerie-scene": {
            "concepts": [
                "abandoned hospital corridor, flickering fluorescent lights, peeling paint walls, long shadows",
                "foggy forest path at midnight, twisted dead trees, faint moonlight, overgrown trail",
                "derelict amusement park, rusted ferris wheel, overcast sky, dried leaves scattered",
                "dimly lit underground tunnel, dripping water, cracked concrete walls, distant echo",
                "empty victorian mansion hallway, dusty chandeliers, faded wallpaper, creaking floorboards"
            ],
            "style": "atmospheric horror, cinematic photography, moody lighting, desaturated colors",
            "variation_dims": ["location_type", "time_of_day", "weather", "fear_level"]
        },
        "creature-design": {
            "concepts": [
                "bioluminescent deep sea creature, translucent exoskeleton, glowing tendrils, dark ocean depth",
                "alien forest guardian spirit, bark-like skin texture, moss covered, ancient sentient tree being",
                "mutant insectoid hybrid, iridescent chitin armor, compound eyes, biomechanical joints",
                "ethereal jellyfish-like sky creature, floating membrane wings, trailing light filaments",
                "prehistoric cave-dwelling beast, blind albino form, echolocation sensors, crystalline growths"
            ],
            "style": "concept art, creature design, detailed anatomy, dramatic lighting, dark fantasy",
            "variation_dims": ["species_base", "mutation_type", "habitat", "scale"]
        },
        "clawclaw-portrait": {
            "concepts": [
                "ethereal portrait of a young woman, melancholic expression, soft golden hour lighting, windswept hair",
                "contemplative figure in rain, reflection in puddle, neon city lights bokeh, emotional depth",
                "silhouette portrait against sunset, warm amber tones, painterly brushstrokes, artistic composition",
                "close-up portrait with dramatic side lighting, intense gaze, subtle skin texture, shallow depth of field",
                "dreamy double exposure portrait, nature elements overlay, soft focus, muted earth tones"
            ],
            "style": "cinematic lighting, painterly, soft focus background, emotional expression, detailed skin texture",
            "variation_dims": ["character_feature", "mood", "light_direction", "color_tone", "background_complexity"]
        }
    }

    def _generate_from_template(
        self,
        theme: str,
        topic_config: dict,
        insights: list,
        image_index: int = 0
    ) -> dict:
        """從模板庫生成提示詞（fallback 模式）"""
        import random

        templates = self.TEMPLATE_LIBRARY.get(theme, self.TEMPLATE_LIBRARY.get("tech-abstract"))

        # 隨機選概念
        concepts = templates["concepts"]
        concept = concepts[image_index % len(concepts)]

        # 組合提示詞
        style = templates["style"]
        quality_boost = "masterpiece, best quality, highly detailed, sharp focus"
        positive_raw = f"{concept}, {style}, {quality_boost}"

        # 負面提示詞
        neg_boost = topic_config.get("negative_boost", [])
        base_negatives = ["worst quality", "low quality", "blurry", "watermark", "text", "signature",
                          "deformed", "disfigured", "bad anatomy"]
        negative_raw = ", ".join(list(set(neg_boost + base_negatives)))

        # 畫布
        canvas_type = topic_config.get("default_canvas", "square")
        canvas_type = self._apply_canvas_override(canvas_type, positive_raw)

        canvas_types = self._topics_config.get("canvas_types", {})
        canvas_def = canvas_types.get(canvas_type, {})
        initial_size = canvas_def.get("initial", [768, 768])
        refined_size = canvas_def.get("refined", [1280, 1280])

        lora = topic_config.get("lora")
        lora_weight = topic_config.get("lora_weight", 0.7)

        # ClawClaw 風格關鍵詞
        style_keywords = topic_config.get("style_keywords", [])
        if style_keywords:
            positive_raw = f"{concept}, {', '.join(style_keywords)}, {quality_boost}"

        return {
            "image_id": f"template-{image_index + 1:03d}",
            "prompt_source": "template_fallback",
            "positive_prompt": positive_raw,
            "negative_prompt": negative_raw,
            "canvas_type": canvas_type,
            "canvas_size_initial": initial_size,
            "canvas_size_refined": refined_size,
            "generation_params": {
                "cfg": topic_config.get("base_cfg", 8),
                "initial_steps": topic_config.get("initial_steps", 22),
                "refined_steps": topic_config.get("refined_steps", 30),
                "sampler": topic_config.get("sampler", "euler_a"),
                "lora": lora,
                "lora_weight": lora_weight
            },
            "brief_concept": None,
            "mood_keywords": [],
            "defect_warnings": [],
            "optimized": False
        }

    # --- 畫布覆蓋規則 ---

    def _apply_canvas_override(self, current_canvas: str, prompt_text: str) -> str:
        """
        套用 canvas_override_rules 強制規則。

        規則優先順序: highest > 其他
        人形相關關鍵詞 → 強制 portrait
        臉部特寫關鍵詞 → 強制 square
        """
        override_rules = self._topics_config.get("canvas_override_rules", [])
        prompt_lower = prompt_text.lower()

        for rule in override_rules:
            keywords = rule.get("condition_keywords", [])
            if any(kw.lower() in prompt_lower for kw in keywords):
                forced = rule.get("force_canvas", current_canvas)
                if forced != current_canvas:
                    logger.info(
                        f"畫布覆蓋: {current_canvas} → {forced} "
                        f"(原因: {rule.get('reason', '匹配關鍵詞')})"
                    )
                return forced

        return current_canvas

    # --- Ollama 優化 ---

    def _optimize_with_ollama(self, package: dict, mode: str):
        """
        Stage 2.2: 使用 Ollama qwen3:8b 優化提示詞。

        對正面和負面提示詞進行智能優化：
        - 增加視覺細節
        - 加入風格一致性關鍵詞
        - 缺陷預防詞
        - [creative_brief 模式] 保留核心故事元素
        """
        import requests

        original_positive = package["positive_prompt"]
        original_negative = package["negative_prompt"]
        brief_concept = package.get("brief_concept", "")

        # 建構優化指令
        if mode == "creative_brief" and brief_concept:
            optimize_instruction = (
                "你是一位 Stable Diffusion 提示詞專家。請優化以下圖片生成提示詞。\n\n"
                f"## 原始故事概念（必須保留核心元素）:\n{brief_concept}\n\n"
                f"## 原始正面提示詞:\n{original_positive}\n\n"
                f"## 原始負面提示詞:\n{original_negative}\n\n"
                "## 優化要求:\n"
                "1. 增加具體的視覺細節描述（材質、光線角度、景深等）\n"
                "2. 確保故事概念的核心元素不被稀釋\n"
                "3. 加入適當的品質保證詞和缺陷預防詞\n"
                "4. 保持提示詞總長度在 75-150 個 token 之間\n"
                "5. 負面提示詞也需要針對此場景的潛在缺陷補強\n\n"
                "請以 JSON 格式回應:\n"
                '{"positive": "優化後的正面提示詞(英文)", "negative": "優化後的負面提示詞(英文)"}'
            )
        else:
            optimize_instruction = (
                "你是一位 Stable Diffusion 提示詞專家。請優化以下圖片生成提示詞。\n\n"
                f"## 原始正面提示詞:\n{original_positive}\n\n"
                f"## 原始負面提示詞:\n{original_negative}\n\n"
                "## 優化要求:\n"
                "1. 增加視覺細節描述（材質、光線、氛圍細節）\n"
                "2. 加入風格一致性關鍵詞\n"
                "3. 插入品質保證詞（如 masterpiece, best quality）\n"
                "4. 加入缺陷預防詞（如 anatomically correct, proper proportions）\n"
                "5. 保持提示詞總長度在 75-150 個 token 之間\n"
                "6. 負面提示詞也需要補強常見缺陷預防\n\n"
                "請以 JSON 格式回應:\n"
                '{"positive": "優化後的正面提示詞(英文)", "negative": "優化後的負面提示詞(英文)"}'
            )

        try:
            resp = requests.post(
                f"{self._ollama_host}/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": optimize_instruction,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.6,
                        "num_predict": 1024
                    }
                },
                timeout=120
            )

            if resp.status_code == 200:
                result = resp.json()
                response_text = result.get("response", "")
                try:
                    optimized = json.loads(response_text)
                    if "positive" in optimized and "negative" in optimized:
                        package["positive_prompt"] = optimized["positive"]
                        package["negative_prompt"] = optimized["negative"]
                        package["optimized"] = True
                        logger.info(f"Ollama 優化成功: {package['image_id']}")
                        return
                except json.JSONDecodeError:
                    logger.warning(f"Ollama 回應非合法 JSON: {response_text[:200]}")
            else:
                logger.warning(f"Ollama API 錯誤 (HTTP {resp.status_code})")

        except requests.exceptions.ConnectionError:
            logger.warning(f"Ollama 連線失敗 ({self._ollama_host})，使用原始提示詞")
        except requests.exceptions.Timeout:
            logger.warning("Ollama 請求超時，使用原始提示詞")
        except Exception as e:
            logger.warning(f"Ollama 優化異常: {e}，使用原始提示詞")

        # 失敗時保留原始提示詞（不阻斷流程）
        package["optimized"] = False
        logger.info(f"使用未優化提示詞: {package['image_id']}")

    # --- 提示詞去重 ---

    def _dedup_check(self, package: dict):
        """
        Stage 2.3: 檢查提示詞是否與近期歷史重複。

        若相似度 > 85% 則標記需重新生成。
        """
        history = self._load_prompt_history()
        current_prompt = package["positive_prompt"]

        for entry in history:
            similarity = SequenceMatcher(
                None,
                current_prompt.lower(),
                entry.get("positive_prompt", "").lower()
            ).ratio()

            if similarity > self._dedup_threshold:
                package["dedup_warning"] = {
                    "similar_to": entry.get("date", "unknown"),
                    "similarity": round(similarity, 3),
                    "original_image_id": entry.get("image_id", "unknown")
                }
                logger.warning(
                    f"提示詞重複警告: {package['image_id']} 與 "
                    f"{entry.get('image_id')} 相似度 {similarity:.1%}"
                )
                return

        package["dedup_warning"] = None

    def _load_prompt_history(self) -> list:
        """載入近 N 天的提示詞歷史"""
        history_path = self._workspace / "memory" / "metrics" / self._dedup_history_file
        if not history_path.exists():
            return []

        try:
            data = self._load_json(history_path)
            entries = data.get("entries", [])

            # 只保留近 N 天
            cutoff = (date.today() - timedelta(days=self._dedup_history_days)).isoformat()
            return [e for e in entries if e.get("date", "") >= cutoff]
        except Exception as e:
            logger.warning(f"載入提示詞歷史失敗: {e}")
            return []

    def save_to_prompt_history(self, packages: list, date_str: str, theme: str = "unknown"):
        """
        將本次產出的提示詞寫入歷史（供未來去重使用）。
        通常在 Stage 3 生成完成後由 pipeline_main 呼叫。
        """
        history_path = self._workspace / "memory" / "metrics" / self._dedup_history_file

        existing = self._load_json(history_path) if history_path.exists() else {"entries": []}

        for pkg in packages:
            existing["entries"].append({
                "date": date_str,
                "image_id": pkg["image_id"],
                "positive_prompt": pkg["positive_prompt"],
                "prompt_source": pkg["prompt_source"],
                "theme": theme
            })

        # 清理超過歷史天數的舊紀錄
        cutoff = (date.today() - timedelta(days=self._dedup_history_days * 2)).isoformat()
        existing["entries"] = [e for e in existing["entries"] if e.get("date", "") >= cutoff]

        self._save_json(history_path, existing)
        logger.info(f"提示詞歷史已更新: {len(packages)} 筆新增")

    # ================================================================
    # 主執行流程
    # ================================================================

    def run(
        self,
        date_str: Optional[str] = None,
        theme: Optional[str] = None,
        brief: Optional[dict] = None
    ) -> dict:
        """
        執行 Stage 1-2 完整流程。

        Args:
            date_str: 日期
            theme: 主題名（從 Stage 0 結果或手動指定）
            brief: 可選的直接傳入簡報（避免重複讀取檔案）

        Returns:
            {
                "packages": list,        # PromptPackage 列表
                "mode": str,             # "creative_brief"|"template_fallback"
                "observation": dict,     # 觀測數據（供 03 模組使用）
                "context": dict          # 完整上下文
            }
        """
        if date_str is None:
            date_str = date.today().isoformat()

        # 若從 Stage 0 直接傳入 brief，存到 briefs_dir 供 load_context 讀取
        if brief is not None and theme is None:
            theme = brief.get("theme", "tech-abstract")

        if theme is None:
            # 嘗試從簡報讀取
            brief_path = self._briefs_dir / f"brief_{date_str}.json"
            if brief_path.exists():
                loaded = self._load_json(brief_path)
                theme = loaded.get("theme", "tech-abstract")
            else:
                # 用輪替策略
                rotation = self._schedule_config.get("topic_rotation", {})
                cycle_order = rotation.get("cycle_order", ["tech-abstract"])
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                theme = cycle_order[dt.timetuple().tm_yday % len(cycle_order)]

        # Stage 1: 載入上下文
        context = self.load_context(date_str, theme)

        # Stage 2: 生成提示詞
        packages = self.generate_prompts(context)

        logger.info(
            f"Stage 1-2 完成: {len(packages)} 組提示詞, "
            f"mode={context['mode']}, optimized={sum(1 for p in packages if p.get('optimized'))}"
        )

        return {
            "packages": packages,
            "mode": context["mode"],
            "observation": self._observation,
            "context": context
        }

    @property
    def observation(self) -> dict:
        """取得本次執行的觀測數據"""
        return self._observation.copy()

