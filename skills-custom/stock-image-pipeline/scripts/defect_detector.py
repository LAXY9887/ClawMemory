"""
Stage 4: 品質檢測與篩選（Defect Detection & Quality Gate）

用途:
  - 接收 Stage 3.5 的 upscale 圖片
  - Layer 1: 快速篩選（檔案完整性、解析度、基礎構圖）
  - Layer 2: OpenRouter 多模態四維矩陣精檢（技術/美學/解剖/商業）
  - Layer 3: 專項缺陷深度檢測（眼部/手部/動物）
  - 判定: PASS (≥8.5) / RETRY (7.0-8.4) / DISCARD (<7.0)
  - RETRY 時: Ollama 推理修復策略，回退 Stage 3 重試

設計原則:
  - 三層遞進: 快速篩選 → 多維精檢 → 專項深檢
  - OpenRouter = 視覺分析（主角），Ollama = 修復策略推理（輔助）
  - 缺陷懲罰制: critical -3.0, major -1.5, minor -0.5
  - 修復策略選擇依缺陷類型: 提示詞強化 / 參數調整 / ControlNet / 構圖迴避
"""

import json
import logging
from pathlib import Path
from datetime import date
from typing import Optional
from PIL import Image

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"

# 四維矩陣權重
WEIGHT_TECHNICAL = 0.30
WEIGHT_AESTHETIC = 0.25
WEIGHT_ANATOMICAL = 0.30
WEIGHT_COMMERCIAL = 0.15

# 缺陷懲罰
PENALTY_CRITICAL = 3.0
PENALTY_MAJOR = 1.5
PENALTY_MINOR = 0.5

# 判定門檻
THRESHOLD_PASS = 8.5
THRESHOLD_RETRY = 7.0


class DefectDetectorError(Exception):
    """缺陷檢測失敗"""
    pass


class DefectDetector:
    """
    Stage 4: 品質檢測與篩選。

    使用方式:
        detector = DefectDetector(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        result = detector.inspect(image_path="...", prompt_package={...})
        # result = {"verdict": "PASS"|"RETRY"|"DISCARD", "final_score": 8.7, ...}
    """

    def __init__(self, workspace_base: Optional[str] = None):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")
        self._topics_config = self._load_json(CONFIG_DIR / "topics.json")

        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()

        # Ollama 配置
        ollama_cfg = self._schedule_config.get("ollama", {})
        self._ollama_model = ollama_cfg.get("model", "qwen3:8b")
        self._ollama_host = ollama_cfg.get("host", "http://localhost:11434")

        # 客戶端
        self._openrouter_client = None

        # 觀測數據
        self._observation = {
            "layer1_rejects": 0,
            "layer2_calls": 0,
            "layer3_calls": 0,
            "ollama_repair_calls": 0,
            "pass_count": 0,
            "retry_count": 0,
            "discard_count": 0
        }

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_openrouter(self):
        if self._openrouter_client is None:
            import sys
            if str(SCRIPT_DIR) not in sys.path:
                sys.path.insert(0, str(SCRIPT_DIR))
            from openrouter_client import OpenRouterClient
            self._openrouter_client = OpenRouterClient(
                config_path=str(CONFIG_DIR / "schedule.json")
            )
        return self._openrouter_client

    # ================================================================
    # 主流程: 單張圖品質檢測
    # ================================================================

    def inspect(
        self,
        image_path: str,
        prompt_package: dict,
        refiner_score: Optional[float] = None
    ) -> dict:
        """
        執行單張圖的完整品質檢測 (Layer 1 → 2 → 3)。

        Args:
            image_path: Stage 3.5 upscale 後的圖片路徑
            prompt_package: Stage 2 的 PromptPackage（含 canvas_type 等）
            refiner_score: Stage 3.4 的精煉評分（參考用）

        Returns:
            {
                "verdict": "PASS"|"RETRY"|"DISCARD",
                "final_score": float,
                "layer1_passed": bool,
                "layer2_scores": {技術/美學/解剖/商業 各維度},
                "layer3_defects": list,
                "defect_penalties": float,
                "repair_strategy": dict|None,  # RETRY 時的修復建議
                "inspection_log": list
            }
        """
        image_id = prompt_package.get("image_id", "unknown")
        logger.info(f"=== Stage 4: 品質精檢 ({image_id}) ===")

        result = {
            "verdict": "DISCARD",
            "final_score": 0.0,
            "layer1_passed": False,
            "layer2_scores": {},
            "layer3_defects": [],
            "defect_penalties": 0.0,
            "repair_strategy": None,
            "inspection_log": []
        }

        # --- Layer 1: 快速篩選 ---
        l1_result = self._layer1_quick_filter(image_path, prompt_package)
        result["layer1_passed"] = l1_result["passed"]
        result["inspection_log"].append({"layer": 1, "result": l1_result})

        if not l1_result["passed"]:
            result["final_score"] = 0.0
            result["verdict"] = "DISCARD"
            self._observation["layer1_rejects"] += 1
            logger.warning(f"{image_id}: Layer 1 篩選不通過 — {l1_result.get('reason', '')}")
            return result

        # --- Layer 2: OpenRouter 多維精檢 ---
        l2_result = self._layer2_detailed_evaluation(image_path, prompt_package)
        result["layer2_scores"] = l2_result.get("dimension_scores", {})
        result["inspection_log"].append({"layer": 2, "result": l2_result})
        self._observation["layer2_calls"] += 1

        # --- Layer 3: 專項缺陷深檢 ---
        l3_result = self._layer3_specialized_detection(image_path, prompt_package, l2_result)
        result["layer3_defects"] = l3_result.get("defects", [])
        result["inspection_log"].append({"layer": 3, "result": l3_result})
        if l3_result.get("defects"):
            self._observation["layer3_calls"] += 1

        # --- 綜合評分計算 ---
        base_score = self._calculate_weighted_score(l2_result.get("dimension_scores", {}))
        penalties = self._calculate_penalties(l3_result.get("defects", []))
        final_score = max(0, min(10, base_score - penalties))

        result["final_score"] = round(final_score, 2)
        result["defect_penalties"] = round(penalties, 2)

        # --- 判定 ---
        if final_score >= THRESHOLD_PASS:
            result["verdict"] = "PASS"
            self._observation["pass_count"] += 1
            logger.info(f"{image_id}: PASS (score={final_score})")

        elif final_score >= THRESHOLD_RETRY:
            # 檢查重試預算
            current_retries = prompt_package.get("retry_count", 0)
            budget_check = self._check_retry_budget(image_id, current_retries)
            
            if budget_check["allowed"]:
                result["verdict"] = "RETRY"
                self._observation["retry_count"] += 1
                
                # 呼叫 Ollama 推理修復策略
                repair = self._generate_repair_strategy(
                    l2_result, l3_result, prompt_package
                )
                result["repair_strategy"] = repair
                
                # 生成 ControlNet 建議
                controlnet_advice = self._generate_controlnet_advice(
                    l3_result.get("defects", []),
                    l2_result.get("dimension_scores", {})
                )
                result["controlnet_advice"] = controlnet_advice
                result["retry_budget"] = budget_check
                
                logger.info(f"{image_id}: RETRY (score={final_score}, strategy={repair.get('primary_strategy', 'N/A')}, controlnet={controlnet_advice.get('type', 'none')})")
            else:
                # 預算不足，降級為 DISCARD
                result["verdict"] = "DISCARD"
                result["discard_reason"] = "retry_budget_exceeded"
                result["retry_budget"] = budget_check
                self._observation["discard_count"] += 1
                
                logger.warning(f"{image_id}: DISCARD (預算不足) - {budget_check['reason']}")

        else:
            result["verdict"] = "DISCARD"
            self._observation["discard_count"] += 1
            logger.info(f"{image_id}: DISCARD (score={final_score})")

        return result

    # ================================================================
    # Layer 1: 快速篩選
    # ================================================================

    def _layer1_quick_filter(self, image_path: str, pkg: dict) -> dict:
        """
        Layer 1: 規則式快速篩選（< 2 秒/張）。

        檢查: 檔案完整性、解析度、非單色、基礎構圖。
        """
        checks = []

        # 1. 檔案可讀
        path = Path(image_path)
        if not path.exists():
            return {"passed": False, "reason": "檔案不存在", "checks": []}

        try:
            img = Image.open(path)
            img.verify()
            # 重新開啟（verify 之後需重新開啟）
            img = Image.open(path)
            w, h = img.size
            checks.append({"check": "file_readable", "passed": True})
        except Exception as e:
            return {"passed": False, "reason": f"檔案損壞: {e}", "checks": []}

        # 2. 解析度檢查（±5% 容差）
        canvas_type = pkg.get("canvas_type", "square")
        canvas_types = self._topics_config.get("canvas_types", {})
        expected = canvas_types.get(canvas_type, {}).get("final_4x", [5120, 5120])
        exp_w, exp_h = expected

        tolerance = 0.05
        w_ok = abs(w - exp_w) / exp_w <= tolerance if exp_w > 0 else True
        h_ok = abs(h - exp_h) / exp_h <= tolerance if exp_h > 0 else True
        resolution_ok = w_ok and h_ok

        checks.append({
            "check": "resolution",
            "passed": resolution_ok,
            "actual": [w, h],
            "expected": expected,
            "note": f"容差 ±{tolerance*100}%"
        })

        if not resolution_ok:
            # 解析度不符不一定要擋，可能是 upscale 模型差異
            # 只記錄警告，不直接 reject
            logger.warning(f"解析度偏差: actual={w}x{h}, expected={exp_w}x{exp_h}")

        # 3. 非單色檢查
        try:
            # 取中心 100x100 區域檢查顏色多樣性
            cx, cy = w // 2, h // 2
            crop_size = min(100, w // 4, h // 4)
            crop = img.crop((cx - crop_size, cy - crop_size, cx + crop_size, cy + crop_size))
            colors = crop.getcolors(maxcolors=256)

            is_monochrome = colors is not None and len(colors) <= 3
            checks.append({
                "check": "not_monochrome",
                "passed": not is_monochrome,
                "unique_colors": len(colors) if colors else ">256"
            })

            if is_monochrome:
                return {"passed": False, "reason": "圖片為單色/空白", "checks": checks}

        except Exception as e:
            checks.append({"check": "not_monochrome", "passed": True, "note": f"檢查異常，跳過: {e}"})

        # 4. 非全黑/全白
        try:
            extrema = img.convert("L").getextrema()
            is_all_black = extrema[1] < 10
            is_all_white = extrema[0] > 245

            checks.append({
                "check": "not_extreme",
                "passed": not (is_all_black or is_all_white),
                "min_brightness": extrema[0],
                "max_brightness": extrema[1]
            })

            if is_all_black or is_all_white:
                return {"passed": False, "reason": "全黑或全白", "checks": checks}

        except Exception as e:
            checks.append({"check": "not_extreme", "passed": True, "note": f"檢查異常: {e}"})

        return {"passed": True, "checks": checks}

    # ================================================================
    # Layer 2: OpenRouter 多維精檢
    # ================================================================

    def _layer2_detailed_evaluation(self, image_path: str, pkg: dict) -> dict:
        """
        Layer 2: OpenRouter 多模態四維矩陣評估。

        維度: 技術品質 / 美學品質 / 解剖準確性 / 商業價值
        """
        eval_prompt = (
            "你是一位專業的商業圖庫品質審查專家。請對這張圖片進行四維度精密品質評估。\n\n"
            f"## 圖片的提示詞:\n{pkg.get('positive_prompt', '')}\n\n"
            f"## 圖片概念:\n{pkg.get('brief_concept', '無')}\n\n"
            "## 四維評估矩陣 (每項 1-10 分):\n\n"
            "### 1. 技術品質 (Technical Quality)\n"
            "- 清晰度: 主體邊緣是否銳利\n"
            "- 雜訊: 是否有不自然的顆粒或模糊\n"
            "- 色彩: 色彩是否自然、對比是否適當\n"
            "- 一致性: 光影方向是否統一\n\n"
            "### 2. 美學品質 (Aesthetic Quality)\n"
            "- 構圖: 主體位置、空間分佈\n"
            "- 色彩和諧: 色調搭配是否協調\n"
            "- 視覺重心: 是否有明確的焦點\n"
            "- 氛圍: 是否與主題一致\n\n"
            "### 3. 解剖準確性 (Anatomical Accuracy)\n"
            "- 若含人物: 眼部對稱、手指數量、身體比例、姿態自然度\n"
            "- 若含動物/生物: 物種一致性、解剖邏輯、毛髮方向\n"
            "- 若為抽象/場景: 結構邏輯、透視準確性\n\n"
            "### 4. 商業價值 (Commercial Value)\n"
            "- 市場相關性、關鍵詞潛力、使用場景、獨特性\n\n"
            "## 輸出格式 (嚴格 JSON):\n"
            "{\n"
            '  "dimension_scores": {\n'
            '    "technical": 8.0,\n'
            '    "aesthetic": 7.5,\n'
            '    "anatomical": 9.0,\n'
            '    "commercial": 7.0\n'
            "  },\n"
            '  "defects_found": [\n'
            "    {\n"
            '      "type": "缺陷類型 (eye_asymmetry/extra_fingers/blurry/color_shift/etc.)",\n'
            '      "severity": "critical|major|minor",\n'
            '      "description": "具體描述（繁體中文）",\n'
            '      "repairable": true\n'
            "    }\n"
            "  ],\n"
            '  "pros": ["優點1", "優點2"],\n'
            '  "cons": ["缺點1"],\n'
            '  "overall_impression": "總評（繁體中文）"\n'
            "}\n"
        )

        try:
            client = self._get_openrouter()
            response = client.chat_with_images_json(
                prompt=eval_prompt,
                image_paths=[image_path],
                max_tokens=2048,
                temperature=0.2
            )

            # 確認回應包含必要欄位
            dim_scores = response.get("dimension_scores", {})
            if not dim_scores:
                logger.warning("OpenRouter 回應缺少 dimension_scores")
                return self._fallback_evaluation(response)

            return response

        except Exception as e:
            logger.error(f"Layer 2 OpenRouter 評估失敗: {e}")
            return {
                "dimension_scores": {
                    "technical": 6.0,
                    "aesthetic": 6.0,
                    "anatomical": 6.0,
                    "commercial": 6.0
                },
                "defects_found": [],
                "error": str(e)
            }

    def _fallback_evaluation(self, response: dict) -> dict:
        """從非標準回應中嘗試提取評分"""
        # 如果有 raw 回應，給預設中等分數
        return {
            "dimension_scores": {
                "technical": 6.5,
                "aesthetic": 6.5,
                "anatomical": 6.5,
                "commercial": 6.5
            },
            "defects_found": [],
            "note": "評分格式解析失敗，使用預設分數",
            "raw_response": response.get("raw", str(response))[:500]
        }

    # ================================================================
    # Layer 3: 專項缺陷深檢
    # ================================================================

    def _layer3_specialized_detection(
        self,
        image_path: str,
        pkg: dict,
        layer2_result: dict
    ) -> dict:
        """
        Layer 3: 根據 Layer 2 標記的缺陷進行深度檢測。

        只在 Layer 2 發現可疑缺陷時才觸發。
        """
        defects = layer2_result.get("defects_found", [])

        if not defects:
            return {"defects": [], "note": "Layer 2 未發現缺陷，跳過深檢"}

        # 檢查是否有需要深度檢測的缺陷類型
        needs_eye_check = any(
            d.get("type", "").startswith("eye") or "eye" in d.get("description", "").lower()
            for d in defects
        )
        needs_hand_check = any(
            "finger" in d.get("type", "") or "hand" in d.get("type", "")
            or "finger" in d.get("description", "").lower()
            for d in defects
        )
        needs_anatomy_check = any(
            d.get("severity") in ("critical", "major")
            for d in defects
        )

        if not (needs_eye_check or needs_hand_check or needs_anatomy_check):
            # 只有 minor 缺陷，不需要深檢
            return {"defects": defects, "note": "僅 minor 缺陷，不觸發深檢"}

        # 深度檢測 prompt
        focus_areas = []
        if needs_eye_check:
            focus_areas.append("眼部: 對稱性、瞳孔、虹膜、高光位置、眼瞼完整性")
        if needs_hand_check:
            focus_areas.append("手部: 嚴格5指檢查、關節方向、比例關係、拇指位置")
        if needs_anatomy_check:
            focus_areas.append("整體解剖: 身體比例、姿態自然度、透視一致性")

        deep_prompt = (
            "你是 AI 生成圖片的缺陷檢測專家。前一輪檢測發現了以下可疑缺陷:\n"
            f"{json.dumps(defects, ensure_ascii=False, indent=2)}\n\n"
            "請對這張圖片進行深度檢測，重點關注:\n"
            + "\n".join(f"- {area}" for area in focus_areas) +
            "\n\n"
            "## 輸出格式 (JSON):\n"
            "{\n"
            '  "defects": [\n'
            "    {\n"
            '      "type": "缺陷類型代碼",\n'
            '      "severity": "critical|major|minor",\n'
            '      "description": "精確描述",\n'
            '      "location": "缺陷位置（如左眼、右手）",\n'
            '      "repairable": true,\n'
            '      "confidence": 0.95\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )

        try:
            client = self._get_openrouter()
            response = client.chat_with_images_json(
                prompt=deep_prompt,
                image_paths=[image_path],
                max_tokens=1500,
                temperature=0.1
            )
            return response if "defects" in response else {"defects": defects}

        except Exception as e:
            logger.warning(f"Layer 3 深檢失敗: {e}，使用 Layer 2 缺陷列表")
            return {"defects": defects, "error": str(e)}

    # ================================================================
    # 評分計算
    # ================================================================

    def _calculate_weighted_score(self, dimension_scores: dict) -> float:
        """
        計算四維加權分數。

        technical * 0.30 + aesthetic * 0.25 + anatomical * 0.30 + commercial * 0.15
        """
        tech = dimension_scores.get("technical", 5.0)
        aes = dimension_scores.get("aesthetic", 5.0)
        anat = dimension_scores.get("anatomical", 5.0)
        comm = dimension_scores.get("commercial", 5.0)

        score = (
            tech * WEIGHT_TECHNICAL +
            aes * WEIGHT_AESTHETIC +
            anat * WEIGHT_ANATOMICAL +
            comm * WEIGHT_COMMERCIAL
        )
        return round(score, 2)

    def _calculate_penalties(self, defects: list) -> float:
        """
        計算缺陷懲罰分數。

        critical: -3.0, major: -1.5, minor: -0.5
        """
        total = 0.0
        for d in defects:
            severity = d.get("severity", "minor")
            if severity == "critical":
                total += PENALTY_CRITICAL
            elif severity == "major":
                total += PENALTY_MAJOR
            elif severity == "minor":
                total += PENALTY_MINOR
        return total

    # ================================================================
    # 修復策略生成（Ollama 推理）
    # ================================================================

    def _generate_repair_strategy(
        self,
        layer2_result: dict,
        layer3_result: dict,
        pkg: dict
    ) -> dict:
        """
        使用 Ollama 推理修復策略。

        根據缺陷類型選擇:
        - 提示詞強化 (prompt_enhancement)
        - 參數調整 (parameter_tuning)
        - ControlNet 輔助 (controlnet_assist)
        - 構圖迴避 (composition_avoidance)
        """
        import requests

        defects = layer3_result.get("defects", []) or layer2_result.get("defects_found", [])
        dim_scores = layer2_result.get("dimension_scores", {})

        repair_prompt = (
            "你是 AI 圖像生成的修復策略專家。以下圖片通過了品質檢測但有缺陷需要修復。\n\n"
            f"## 四維評分:\n{json.dumps(dim_scores, ensure_ascii=False)}\n\n"
            f"## 發現的缺陷:\n{json.dumps(defects, ensure_ascii=False, indent=2)}\n\n"
            f"## 原始正面提示詞:\n{pkg.get('positive_prompt', '')}\n\n"
            f"## 原始負面提示詞:\n{pkg.get('negative_prompt', '')}\n\n"
            f"## 生成參數:\nCFG={pkg.get('generation_params', {}).get('cfg', 8)}, "
            f"Steps={pkg.get('generation_params', {}).get('refined_steps', 30)}, "
            f"LoRA={pkg.get('generation_params', {}).get('lora', 'none')}\n\n"
            "## 可用修復策略:\n"
            "1. prompt_enhancement: 追加特定提示詞修正缺陷\n"
            "2. parameter_tuning: 調整 CFG/Steps/Seed\n"
            "3. controlnet_assist: 使用 ControlNet (openpose/depth/canny) 約束結構\n"
            "4. composition_avoidance: 修改構圖隱藏問題區域\n"
            "5. lora_adjustment: 調整 LoRA 權重\n\n"
            "請選擇最佳修復策略並給出具體修改建議。\n\n"
            "## 輸出格式 (JSON):\n"
            "{\n"
            '  "primary_strategy": "策略名稱",\n'
            '  "changes": {\n'
            '    "positive_append": "要追加的正面提示詞（英文）或 null",\n'
            '    "negative_append": "要追加的負面提示詞（英文）或 null",\n'
            '    "cfg_delta": 0,\n'
            '    "steps_delta": 0,\n'
            '    "lora_weight_delta": 0,\n'
            '    "controlnet_type": null,\n'
            '    "new_seed": true\n'
            "  },\n"
            '  "reasoning": "修復邏輯說明（繁體中文）",\n'
            '  "estimated_improvement": 0.5\n'
            "}\n"
        )

        try:
            resp = requests.post(
                f"{self._ollama_host}/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": repair_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.4, "num_predict": 1024}
                },
                timeout=120
            )

            if resp.status_code == 200:
                result = resp.json()
                parsed = json.loads(result.get("response", "{}"))
                if "primary_strategy" in parsed:
                    self._observation["ollama_repair_calls"] += 1
                    logger.info(f"修復策略: {parsed['primary_strategy']}")
                    return parsed

        except Exception as e:
            logger.warning(f"Ollama 修復策略推理失敗: {e}")

        # Fallback: 基於缺陷類型的規則式策略選擇
        return self._rule_based_repair_strategy(defects, pkg)

    def _rule_based_repair_strategy(self, defects: list, pkg: dict) -> dict:
        """
        規則式修復策略（Ollama fallback）。

        根據缺陷類型選擇預設修復策略。
        """
        strategy = {
            "primary_strategy": "parameter_tuning",
            "changes": {
                "positive_append": None,
                "negative_append": None,
                "cfg_delta": 0,
                "steps_delta": 0,
                "lora_weight_delta": 0,
                "controlnet_type": None,
                "new_seed": True
            },
            "reasoning": "規則式 fallback 策略",
            "estimated_improvement": 0.3
        }

        for d in defects:
            dtype = d.get("type", "").lower()
            severity = d.get("severity", "minor")

            if "eye" in dtype or "pupil" in dtype:
                strategy["primary_strategy"] = "prompt_enhancement"
                strategy["changes"]["positive_append"] = "symmetrical eyes, perfect eye alignment, detailed iris"
                strategy["changes"]["negative_append"] = "asymmetric eyes, malformed pupils, crossed eyes"
                strategy["changes"]["cfg_delta"] = 1
                strategy["changes"]["steps_delta"] = 5

            elif "finger" in dtype or "hand" in dtype:
                strategy["primary_strategy"] = "prompt_enhancement"
                strategy["changes"]["positive_append"] = "anatomically correct hands, five fingers on each hand, natural hand pose"
                strategy["changes"]["negative_append"] = "extra fingers, missing fingers, deformed hands, fused fingers"
                strategy["changes"]["lora_weight_delta"] = -0.1

            elif "blur" in dtype or "noise" in dtype:
                strategy["primary_strategy"] = "parameter_tuning"
                strategy["changes"]["steps_delta"] = 10
                strategy["changes"]["cfg_delta"] = 1

            elif severity == "critical":
                strategy["primary_strategy"] = "parameter_tuning"
                strategy["changes"]["new_seed"] = True
                strategy["changes"]["steps_delta"] = 5

        return strategy

    def _generate_controlnet_advice(self, defects: list, dimension_scores: dict) -> dict:
        """
        根據缺陷類型和品質分數生成 ControlNet 建議。
        
        Args:
            defects: 檢測到的缺陷列表
            dimension_scores: 四維品質分數
            
        Returns:
            {
                "use": bool,           # 是否建議使用 ControlNet
                "type": str,           # ControlNet 類型 (canny, depth, openpose, lineart, scribble)
                "reason": str          # 建議原因說明
            }
        """
        advice = {
            "use": False,
            "type": None,
            "reason": "品質良好，無需 ControlNet 輔助"
        }
        
        # 檢查是否有需要 ControlNet 的缺陷
        needs_controlnet = False
        suggested_type = "canny"  # 預設
        reasons = []
        
        # 分析缺陷類型
        for defect in defects:
            defect_type = defect.get("type", "").lower()
            severity = defect.get("severity", "minor")
            
            if "composition" in defect_type or "layout" in defect_type:
                needs_controlnet = True
                suggested_type = "canny"
                reasons.append("構圖問題需要邊緣控制")
                
            elif "perspective" in defect_type or "depth" in defect_type:
                needs_controlnet = True  
                suggested_type = "depth"
                reasons.append("透視問題需要深度控制")
                
            elif "pose" in defect_type or "anatomy" in defect_type or "hand" in defect_type:
                needs_controlnet = True
                suggested_type = "openpose"
                reasons.append("姿態問題需要骨架控制")
                
            elif "line" in defect_type or "edge" in defect_type:
                needs_controlnet = True
                suggested_type = "lineart"
                reasons.append("線條問題需要線稿控制")
                
            elif severity == "critical":
                needs_controlnet = True
                suggested_type = "canny"
                reasons.append(f"嚴重缺陷 ({defect_type}) 需要結構控制")
        
        # 檢查維度分數
        technical = dimension_scores.get("technical", 8.0)
        anatomical = dimension_scores.get("anatomical", 8.0)
        
        if technical < 7.0:
            needs_controlnet = True
            suggested_type = "canny"
            reasons.append("技術品質過低需要邊緣輔助")
            
        if anatomical < 6.0:
            needs_controlnet = True
            suggested_type = "openpose" 
            reasons.append("解剖結構問題需要姿態控制")
        
        # 設定建議
        if needs_controlnet:
            advice["use"] = True
            advice["type"] = suggested_type
            advice["reason"] = "; ".join(reasons[:2])  # 最多顯示2個原因
        
        return advice

    def _check_retry_budget(self, image_id: str, current_retries: int = 0) -> dict:
        """
        檢查重試預算是否允許再次嘗試。
        
        Args:
            image_id: 圖片識別ID
            current_retries: 該圖片當前已重試次數
            
        Returns:
            {
                "allowed": bool,           # 是否允許重試
                "reason": str,            # 原因說明
                "per_image_limit": int,   # 單張圖片限制
                "daily_limit": int,       # 每日限制
                "daily_used": int,        # 每日已用
                "image_retries": int      # 該圖片已重試次數
            }
        """
        # 從配置獲取限制
        max_per_image = self._schedule_config.get("max_retries_per_image", 2)
        max_daily = self._schedule_config.get("max_daily_retries", 4) 
        
        # 從觀察器獲取當日使用情況
        daily_used = self._observation.get("retry_count", 0)
        
        # 檢查單張圖片限制
        if current_retries >= max_per_image:
            return {
                "allowed": False,
                "reason": f"圖片 {image_id} 已達最大重試次數 ({current_retries}/{max_per_image})",
                "per_image_limit": max_per_image,
                "daily_limit": max_daily,
                "daily_used": daily_used,
                "image_retries": current_retries
            }
            
        # 檢查每日限制
        if daily_used >= max_daily:
            return {
                "allowed": False,
                "reason": f"今日重試預算已耗盡 ({daily_used}/{max_daily})",
                "per_image_limit": max_per_image,
                "daily_limit": max_daily,
                "daily_used": daily_used,
                "image_retries": current_retries
            }
            
        # 預算充足
        return {
            "allowed": True,
            "reason": f"預算充足，可重試 (圖片:{current_retries}/{max_per_image}, 每日:{daily_used}/{max_daily})",
            "per_image_limit": max_per_image,
            "daily_limit": max_daily,
            "daily_used": daily_used,
            "image_retries": current_retries
        }

    def _consume_retry_budget(self, image_id: str) -> dict:
        """
        消耗重試預算（當實際執行重試時調用）。
        
        Args:
            image_id: 圖片識別ID
            
        Returns:
            {
                "consumed": bool,
                "remaining_daily": int,
                "total_daily_used": int
            }
        """
        # 增加重試計數
        self._observation["retry_count"] += 1
        
        daily_limit = self._schedule_config.get("max_daily_retries", 4)
        daily_used = self._observation["retry_count"]
        remaining = max(0, daily_limit - daily_used)
        
        logger.info(f"消耗重試預算: {image_id}, 每日已用 {daily_used}/{daily_limit}")
        
        return {
            "consumed": True,
            "remaining_daily": remaining,
            "total_daily_used": daily_used
        }

    # ================================================================
    # 修復參數應用
    # ================================================================

    def apply_repair_to_package(self, pkg: dict, repair_strategy: dict) -> dict:
        """
        將修復策略應用到 PromptPackage，產出修復版本。

        Args:
            pkg: 原始 PromptPackage
            repair_strategy: inspect() 回傳的 repair_strategy

        Returns:
            修復後的 PromptPackage（新 dict，不修改原始）
        """
        import copy
        repaired = copy.deepcopy(pkg)
        changes = repair_strategy.get("changes", {})

        # 追加提示詞
        pos_append = changes.get("positive_append")
        if pos_append:
            repaired["positive_prompt"] = f"{repaired['positive_prompt']}, {pos_append}"

        neg_append = changes.get("negative_append")
        if neg_append:
            repaired["negative_prompt"] = f"{repaired['negative_prompt']}, {neg_append}"

        # 參數調整
        params = repaired.get("generation_params", {})

        cfg_delta = changes.get("cfg_delta", 0)
        if cfg_delta:
            params["cfg"] = max(1, min(20, params.get("cfg", 8) + cfg_delta))

        steps_delta = changes.get("steps_delta", 0)
        if steps_delta:
            params["initial_steps"] = max(10, params.get("initial_steps", 22) + steps_delta)
            params["refined_steps"] = max(10, params.get("refined_steps", 30) + steps_delta)

        lora_delta = changes.get("lora_weight_delta", 0)
        if lora_delta and params.get("lora"):
            params["lora_weight"] = max(0, min(1.0, params.get("lora_weight", 0.7) + lora_delta))

        repaired["generation_params"] = params
        repaired["repair_applied"] = True
        repaired["repair_strategy"] = repair_strategy.get("primary_strategy", "unknown")

        return repaired

    # ================================================================
    # 批次與觀測
    # ================================================================

    def inspect_batch(self, image_results: list, prompt_packages: list) -> list:
        """
        批次檢測 Stage 3 的所有成功圖片。

        Args:
            image_results: Stage 3 run_daily_batch 的 results（只檢測 status=success）
            prompt_packages: 對應的 PromptPackage 列表

        Returns:
            list of inspect() 結果
        """
        inspections = []
        pkg_map = {p["image_id"]: p for p in prompt_packages}

        for res in image_results:
            if res["status"] != "success" or not res.get("final_image"):
                continue

            pkg = pkg_map.get(res["image_id"])
            if pkg is None:
                logger.warning(f"找不到 {res['image_id']} 的 PromptPackage")
                continue

            inspection = self.inspect(
                image_path=res["final_image"],
                prompt_package=pkg,
                refiner_score=res.get("final_score")
            )
            inspection["image_id"] = res["image_id"]
            inspections.append(inspection)

        return inspections

    @property
    def observation(self) -> dict:
        return self._observation.copy()

