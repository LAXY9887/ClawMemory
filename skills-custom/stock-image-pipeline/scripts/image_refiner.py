"""
Stage 3: 圖像生成精煉迴圈（Image Generation & Refinement Loop）

用途:
  - 3.1 初步候選生成（txt2img ×5，不同 seed）
  - 3.2 OpenRouter 第一次自評 → 選最佳 1 張（含 controlnet_advice）
  - 3.3 精煉放大生成（img2img ×5，不同 denoise）
  - 3.4 OpenRouter 第二次自評 → 選最佳 1 張
  - 3.5 ComfyUI 4x Upscale → 商業級最終解析度

設計原則:
  - 每張圖獨立走完 3.1→3.5 完整生命週期
  - 重試預算: max_retries_per_image=2, max_daily_retries=4
  - 3.2 全部 < 5.0 → 回退 Stage 2 重新生成提示詞（消耗 1 次重試）
  - 3.4 全部 < 7.0 → 丟棄本張（不消耗重試）
  - OpenRouter 失敗 → Ollama fallback（文字排序）
  - 所有落選圖片及分數記錄供 insight 分析
"""

import json
import random
import logging
import time
from pathlib import Path
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"


class ImageRefinerError(Exception):
    """圖像精煉流程失敗"""
    pass


class ImageRefiner:
    """
    Stage 3: 圖像生成精煉迴圈。

    使用方式:
        refiner = ImageRefiner(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        result = refiner.process_single_image(prompt_package, retry_budget)
        # result = {"status": "success"|"discarded"|"retry_needed", "final_image": "...", ...}
    """

    def __init__(self, workspace_base: Optional[str] = None):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")
        self._topics_config = self._load_json(CONFIG_DIR / "topics.json")

        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()
        self._temp_dir = self._workspace / self._schedule_config.get("workspace", {}).get("temp_dir", "temp")

        # 精煉配置
        ref_cfg = self._topics_config.get("refinement", {})
        self._initial_candidates = ref_cfg.get("initial_candidates", 5)
        self._refined_candidates = ref_cfg.get("refined_candidates", 5)
        self._denoise_range = ref_cfg.get("denoise_range", [0.25, 0.30, 0.35, 0.40, 0.45])
        self._initial_min_score = ref_cfg.get("initial_min_score", 5.0)
        self._refined_min_score = ref_cfg.get("refined_min_score", 7.0)
        self._max_prompt_retries = ref_cfg.get("max_prompt_retries", 1)

        # Ollama fallback 配置
        ollama_cfg = self._schedule_config.get("ollama", {})
        self._ollama_model = ollama_cfg.get("model", "qwen3:8b")
        self._ollama_host = ollama_cfg.get("host", "http://localhost:11434")

        # 基礎模型
        self._checkpoint = "rinIllusion_v10.safetensors"

        # 客戶端（延遲初始化）
        self._comfyui_client = None
        self._openrouter_client = None

        # 觀測數據
        self._observation = {
            "comfyui_calls": 0,
            "openrouter_eval_calls": 0,
            "ollama_fallback_used": False,
            "total_images_generated": 0,
            "upscale_calls": 0
        }

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _test_comfyui_connection(self) -> dict:
        """
        測試 ComfyUI 服務連線狀態。
        
        Returns:
            {
                "available": bool,
                "status": str,
                "error": str|None,
                "response_time_ms": int|None
            }
        """
        import time
        try:
            client = self._get_comfyui()
            
            start_time = time.time()
            connection_ok = client.check_connection()
            response_time = int((time.time() - start_time) * 1000)
            
            if connection_ok:
                return {
                    "available": True,
                    "status": "ComfyUI 服務可用",
                    "error": None,
                    "response_time_ms": response_time
                }
            else:
                return {
                    "available": False,
                    "status": "ComfyUI 服務無回應", 
                    "error": "連線測試失敗",
                    "response_time_ms": response_time
                }
                
        except Exception as e:
            return {
                "available": False,
                "status": "ComfyUI 服務不可用",
                "error": str(e),
                "response_time_ms": None
            }

    def _handle_comfyui_error(self, error: Exception, stage: str) -> dict:
        """
        處理 ComfyUI 錯誤，提供明確的錯誤資訊。
        
        Args:
            error: 捕獲的異常
            stage: 發生錯誤的階段 (3.1, 3.3, 3.5)
            
        Returns:
            標準化的錯誤回應
        """
        error_msg = str(error)
        
        # 分類錯誤類型
        if "Connection refused" in error_msg or "Connection reset" in error_msg:
            error_type = "connection_refused"
            user_msg = "ComfyUI 服務未啟動或連線被拒絕"
            suggestion = "請檢查 ComfyUI Desktop 是否正在運行，端口 8188 是否可用"
            
        elif "timeout" in error_msg.lower():
            error_type = "timeout" 
            user_msg = "ComfyUI 回應超時"
            suggestion = "圖像生成時間過長，可能需要降低複雜度或檢查 GPU 資源"
            
        elif "queue" in error_msg.lower():
            error_type = "queue_full"
            user_msg = "ComfyUI 工作隊列已滿"
            suggestion = "等待當前任務完成或重啟 ComfyUI 服務"
            
        elif "CUDA" in error_msg or "memory" in error_msg.lower():
            error_type = "gpu_memory"
            user_msg = "GPU 記憶體不足"
            suggestion = "降低解析度、批次大小或啟用 Tiled VAE"
            
        else:
            error_type = "unknown"
            user_msg = f"ComfyUI 未知錯誤: {error_msg}"
            suggestion = "檢查 ComfyUI 日誌以獲得更多資訊"
            
        return {
            "error_type": error_type,
            "user_message": user_msg,
            "suggestion": suggestion,
            "stage": stage,
            "original_error": error_msg,
            "timestamp": time.time()
        }

    def _get_comfyui(self):
        """延遲初始化 ComfyUI 客戶端"""
        if self._comfyui_client is None:
            import sys
            if str(SCRIPT_DIR) not in sys.path:
                sys.path.insert(0, str(SCRIPT_DIR))
            from comfyui_client import ComfyUIClient
            self._comfyui_client = ComfyUIClient(
                config_path=str(CONFIG_DIR / "topics.json")
            )
        return self._comfyui_client

    def _get_openrouter(self):
        """延遲初始化 OpenRouter 客戶端"""
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
    # 主流程: 單張圖完整生命週期
    # ================================================================

    def process_single_image(
        self,
        prompt_package: dict,
        retry_budget: dict,
        output_dir: Optional[str] = None
    ) -> dict:
        """
        執行單張圖的完整精煉迴圈 (3.1 → 3.5)。

        Args:
            prompt_package: Stage 2 產出的 PromptPackage
            retry_budget: {"remaining_image": int, "remaining_daily": int}
            output_dir: 最終圖片儲存目錄

        Returns:
            {
                "status": "success"|"discarded"|"retry_needed",
                "image_id": str,
                "final_image": str|None,      # 最終 upscale 後圖片路徑
                "final_score": float|None,
                "scores_initial": list,        # 3.2 所有初步評分
                "scores_refined": list,        # 3.4 所有精煉評分
                "controlnet_used": str|None,   # 使用的 ControlNet 類型
                "seed_used": int|None,         # 最終圖片的 seed
                "retry_consumed": int,         # 本張圖消耗的重試次數
                "generation_log": list,        # 詳細生成紀錄
                "observation": dict
            }
        """
        image_id = prompt_package["image_id"]
        logger.info(f"=== Stage 3: 圖像精煉迴圈 ({image_id}) ===")

        if output_dir is None:
            output_dir = str(self._workspace / self._schedule_config.get("workspace", {}).get("pending_dir", "pending"))

        result = {
            "status": "discarded",
            "image_id": image_id,
            "final_image": None,
            "final_score": None,
            "scores_initial": [],
            "scores_refined": [],
            "controlnet_used": None,
            "seed_used": None,
            "retry_consumed": 0,
            "generation_log": []
        }

        # --- 3.1 初步候選生成 ---
        initial_images = self._stage_3_1_generate_initial(prompt_package)

        if not initial_images:
            result["generation_log"].append({"stage": "3.1", "error": "ComfyUI 生成失敗"})
            return result

        # --- 3.2 第一次自評 ---
        eval_results = self._stage_3_2_evaluate_initial(
            initial_images, prompt_package
        )
        result["scores_initial"] = eval_results

        best_initial = self._select_best(eval_results, self._initial_min_score)

        # 3.2 全部 < 5.0 → 重試提示詞
        if best_initial is None:
            logger.warning(f"{image_id}: 初步候選全部 < {self._initial_min_score}，需重新生成提示詞")
            result["status"] = "retry_needed"
            result["retry_consumed"] = 1
            result["generation_log"].append({
                "stage": "3.2",
                "action": "retry_prompt",
                "reason": f"所有初步候選分數 < {self._initial_min_score}",
                "max_score": max((e.get("score", 0) for e in eval_results), default=0)
            })
            return result

        best_initial_path = best_initial["image_path"]
        best_initial_score = best_initial["score"]
        controlnet_advice = best_initial.get("controlnet_advice", {})

        result["generation_log"].append({
            "stage": "3.2",
            "selected": best_initial_path,
            "score": best_initial_score,
            "controlnet_advice": controlnet_advice
        })

        # --- 3.3 精煉放大生成 ---
        controlnet_type = None
        if controlnet_advice.get("use"):
            controlnet_type = controlnet_advice.get("type")
            result["controlnet_used"] = controlnet_type
            logger.info(f"{image_id}: 使用 ControlNet {controlnet_type} ({controlnet_advice.get('reason', '')})")

        refined_images = self._stage_3_3_refine(
            best_initial_path, prompt_package, controlnet_type
        )

        if not refined_images:
            result["generation_log"].append({"stage": "3.3", "error": "精煉生成失敗"})
            return result

        # --- 3.4 第二次自評 ---
        refined_results = self._stage_3_4_evaluate_refined(
            refined_images, prompt_package, best_initial_path
        )
        result["scores_refined"] = refined_results

        best_refined = self._select_best(refined_results, self._refined_min_score)

        # 3.4 全部 < 7.0 → 丟棄
        if best_refined is None:
            logger.warning(f"{image_id}: 精煉候選全部 < {self._refined_min_score}，丟棄")
            result["status"] = "discarded"
            result["generation_log"].append({
                "stage": "3.4",
                "action": "discard",
                "reason": f"所有精煉候選分數 < {self._refined_min_score}",
                "max_score": max((e.get("score", 0) for e in refined_results), default=0)
            })
            return result

        best_refined_path = best_refined["image_path"]
        best_refined_score = best_refined["score"]

        result["generation_log"].append({
            "stage": "3.4",
            "selected": best_refined_path,
            "score": best_refined_score
        })

        # --- 3.5 最終 Upscale ---
        final_image = self._stage_3_5_upscale(best_refined_path, output_dir)

        if final_image:
            result["status"] = "success"
            result["final_image"] = final_image
            result["final_score"] = best_refined_score
            result["seed_used"] = best_refined.get("seed")
            result["generation_log"].append({
                "stage": "3.5",
                "upscaled": final_image
            })
            logger.info(f"{image_id}: 精煉迴圈成功，最終分數 {best_refined_score}")
        else:
            result["generation_log"].append({"stage": "3.5", "error": "Upscale 失敗"})

        return result

    # ================================================================
    # Stage 3.1: 初步候選生成
    # ================================================================

    def _stage_3_1_generate_initial(self, pkg: dict) -> list:
        """
        3.1: 使用 txt2img 生成初步候選。

        Returns:
            list of image file paths
        """
        logger.info(f"3.1 初步候選生成 ({self._initial_candidates} 張)")
        comfyui = self._get_comfyui()

        params = pkg["generation_params"]
        w, h = pkg["canvas_size_initial"]

        all_images = []
        output_dir = str(self._temp_dir / pkg["image_id"] / "initial")

        for i in range(self._initial_candidates):
            seed = random.randint(0, 2**32 - 1)
            try:
                images = comfyui.txt2img(
                    prompt=pkg["positive_prompt"],
                    negative_prompt=pkg["negative_prompt"],
                    width=w,
                    height=h,
                    steps=params.get("initial_steps", 22),
                    cfg=params.get("cfg", 8.0),
                    sampler=params.get("sampler", "euler_a"),
                    seed=seed,
                    lora=params.get("lora"),
                    lora_weight=params.get("lora_weight", 0.7),
                    batch_size=1,
                    output_dir=output_dir,
                    checkpoint=self._checkpoint
                )
                for img in images:
                    all_images.append({"path": img, "seed": seed, "index": i})
                self._observation["comfyui_calls"] += 1
                self._observation["total_images_generated"] += 1
            except Exception as e:
                logger.error(f"3.1 ComfyUI 生成失敗 (candidate {i}): {e}")

        logger.info(f"3.1 完成: {len(all_images)} 張初步候選")
        return all_images

    # ================================================================
    # Stage 3.2: 第一次 OpenRouter 自評
    # ================================================================

    def _stage_3_2_evaluate_initial(self, images: list, pkg: dict) -> list:
        """
        3.2: 用 OpenRouter 視覺模型對初步候選評分。

        評估維度: 構圖完整性、主體清晰度、明顯缺陷、主題匹配度
        輸出包含 controlnet_advice。

        Returns:
            list of {image_path, score, reason, controlnet_advice, seed}
        """
        logger.info(f"3.2 初步自評 ({len(images)} 張)")

        image_paths = [img["path"] for img in images]

        eval_prompt = (
            "你是一位專業的圖庫攝影評審。請對以下候選圖片逐一評分。\n\n"
            f"## 原始提示詞:\n{pkg['positive_prompt']}\n\n"
            f"## 圖片概念:\n{pkg.get('brief_concept', '無')}\n\n"
            "## 評分維度 (每張 1-10 分):\n"
            "1. 構圖完整性 — 主體是否完整、構圖是否平衡\n"
            "2. 主體清晰度 — 主要元素是否清晰可辨\n"
            "3. 明顯缺陷 — 是否有畸形、融合、異常\n"
            "4. 主題匹配度 — 是否符合提示詞描述\n\n"
            "## 輸出格式 (JSON):\n"
            "{\n"
            '  "evaluations": [\n'
            "    {\n"
            '      "index": 0,\n'
            '      "score": 7.5,\n'
            '      "reason": "評語（繁體中文簡短說明）",\n'
            '      "controlnet_advice": {\n'
            '        "use": true,\n'
            '        "type": "openpose",\n'
            '        "reason": "建議原因"\n'
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "controlnet_advice 判斷規則:\n"
            "- use: true + openpose: 姿勢好值得保留\n"
            "- use: true + depth: 空間透視好值得保留\n"
            "- use: true + canny: 邊緣輪廓精準\n"
            "- use: false: 不需要或結構有問題需重新探索\n\n"
            f"共 {len(image_paths)} 張圖片，請逐一評分。"
        )

        eval_results = self._call_vision_evaluation(image_paths, eval_prompt)

        # 合併 seed 資訊
        for i, res in enumerate(eval_results):
            if i < len(images):
                res["image_path"] = images[i]["path"]
                res["seed"] = images[i]["seed"]
            if "controlnet_advice" not in res:
                res["controlnet_advice"] = {"use": False, "type": None, "reason": "未提供"}

        self._observation["openrouter_eval_calls"] += 1
        return eval_results

    # ================================================================
    # Stage 3.3: 精煉放大生成
    # ================================================================

    def _stage_3_3_refine(
        self,
        base_image: str,
        pkg: dict,
        controlnet_type: Optional[str] = None
    ) -> list:
        """
        3.3: 以最佳初步候選為基底，img2img 精煉。

        5 張不同 denoise 值 (0.25-0.45)。

        Returns:
            list of {path, seed, denoise}
        """
        logger.info(f"3.3 精煉放大 ({self._refined_candidates} 張, controlnet={controlnet_type})")
        comfyui = self._get_comfyui()

        params = pkg["generation_params"]
        w, h = pkg["canvas_size_refined"]

        all_refined = []
        output_dir = str(self._temp_dir / pkg["image_id"] / "refined")

        for i, denoise in enumerate(self._denoise_range[:self._refined_candidates]):
            seed = random.randint(0, 2**32 - 1)
            try:
                images = comfyui.img2img(
                    init_image=base_image,
                    prompt=pkg["positive_prompt"],
                    negative_prompt=pkg["negative_prompt"],
                    width=w,
                    height=h,
                    steps=params.get("refined_steps", 30),
                    cfg=params.get("cfg", 8.0),
                    sampler=params.get("sampler", "euler_a"),
                    denoise=denoise,
                    seed=seed,
                    lora=params.get("lora"),
                    lora_weight=params.get("lora_weight", 0.7),
                    controlnet_type=controlnet_type,
                    output_dir=output_dir,
                    checkpoint=self._checkpoint
                )
                for img in images:
                    all_refined.append({"path": img, "seed": seed, "denoise": denoise, "index": i})
                self._observation["comfyui_calls"] += 1
                self._observation["total_images_generated"] += 1
            except Exception as e:
                logger.error(f"3.3 精煉生成失敗 (denoise={denoise}): {e}")

        logger.info(f"3.3 完成: {len(all_refined)} 張精煉候選")
        return all_refined

    # ================================================================
    # Stage 3.4: 第二次 OpenRouter 自評
    # ================================================================

    def _stage_3_4_evaluate_refined(
        self,
        images: list,
        pkg: dict,
        original_best: str
    ) -> list:
        """
        3.4: 精煉候選二次評分（比 3.2 更嚴格）。

        評估維度: 細節品質、結構準確性、色彩一致性、與原始候選一致性。
        """
        logger.info(f"3.4 精煉自評 ({len(images)} 張)")

        image_paths = [img["path"] for img in images]

        eval_prompt = (
            "你是一位嚴格的圖庫攝影品質審查員。請對以下精煉候選圖片逐一評分。\n"
            "這些圖片是基於同一張初步候選精煉放大而來。\n\n"
            f"## 原始提示詞:\n{pkg['positive_prompt']}\n\n"
            "## 評分維度 (每張 1-10 分，標準比初步評更嚴格):\n"
            "1. 細節品質 — 放大後是否出現模糊、偽影、噪點\n"
            "2. 結構準確性 — 人體比例、手指數量、對稱性、物件完整性\n"
            "3. 色彩一致性 — 放大後色彩是否失真、飽和度是否自然\n"
            "4. 構圖保留度 — 是否保留了原始最佳構圖的優點\n\n"
            "## 輸出格式 (JSON):\n"
            "{\n"
            '  "evaluations": [\n'
            "    {\n"
            '      "index": 0,\n'
            '      "score": 8.2,\n'
            '      "reason": "評語（繁體中文）",\n'
            '      "defects": ["缺陷1", "缺陷2"]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"共 {len(image_paths)} 張精煉候選，請逐一評分。"
        )

        eval_results = self._call_vision_evaluation(image_paths, eval_prompt)

        # 合併精煉資訊
        for i, res in enumerate(eval_results):
            if i < len(images):
                res["image_path"] = images[i]["path"]
                res["seed"] = images[i]["seed"]
                res["denoise"] = images[i].get("denoise")

        self._observation["openrouter_eval_calls"] += 1
        return eval_results

    # ================================================================
    # Stage 3.5: 最終 Upscale
    # ================================================================

    def _stage_3_5_upscale(self, image_path: str, output_dir: str) -> Optional[str]:
        """
        3.5: 4x Upscale 至商業級解析度。

        Returns:
            upscaled image path，或 None（失敗）
        """
        logger.info(f"3.5 最終 Upscale (4x)")
        comfyui = self._get_comfyui()

        try:
            results = comfyui.upscale(
                image_path=image_path,
                scale=4,
                output_dir=output_dir
            )
            self._observation["upscale_calls"] += 1
            self._observation["comfyui_calls"] += 1

            if results:
                logger.info(f"3.5 Upscale 完成: {results[0]}")
                return results[0]
            else:
                logger.error("3.5 Upscale 回傳空結果")
                return None

        except Exception as e:
            logger.error(f"3.5 Upscale 失敗: {e}")
            return None

    # ================================================================
    # OpenRouter 視覺評估（通用）
    # ================================================================

    def _call_vision_evaluation(self, image_paths: list, prompt: str) -> list:
        """
        呼叫 OpenRouter 多模態評分。失敗時 fallback 到 Ollama 文字排序。

        Returns:
            list of evaluation dicts
        """
        # 嘗試 OpenRouter
        try:
            client = self._get_openrouter()
            response = client.chat_with_images_json(
                prompt=prompt,
                image_paths=image_paths,
                max_tokens=2048,
                temperature=0.2
            )

            evaluations = response.get("evaluations", [])
            if evaluations:
                return evaluations

            # 回應中沒有 evaluations key
            if "raw" in response:
                logger.warning("OpenRouter 回應無法解析為評分格式")
            else:
                # 嘗試直接使用回應（可能格式稍有不同）
                return self._normalize_eval_response(response, len(image_paths))

        except Exception as e:
            logger.warning(f"OpenRouter 評估失敗: {e}，使用 Ollama fallback")
            self._observation["ollama_fallback_used"] = True

        # Ollama fallback: 只做文字推理排序（無法看圖）
        return self._ollama_fallback_ranking(image_paths, prompt)

    def _normalize_eval_response(self, response: dict, expected_count: int) -> list:
        """嘗試標準化非標準格式的評分回應"""
        results = []

        # 可能是直接列出的陣列
        if isinstance(response, list):
            return response

        # 嘗試找其他可能的 key
        for key in ["results", "scores", "images", "ratings"]:
            if key in response and isinstance(response[key], list):
                return response[key]

        # 無法解析，給所有圖片中等分數
        logger.warning("無法解析評分格式，使用預設分數")
        for i in range(expected_count):
            results.append({
                "index": i,
                "score": 6.0,
                "reason": "評分格式解析失敗，使用預設分數",
                "controlnet_advice": {"use": False, "type": None, "reason": "N/A"}
            })
        return results

    def _ollama_fallback_ranking(self, image_paths: list, original_prompt: str) -> list:
        """
        Ollama fallback: 基於提示詞和 seed 差異做簡單推理排序。
        無法看圖，只能給均等分數讓流程繼續。
        """
        import requests

        logger.info("使用 Ollama fallback 文字排序")

        fallback_prompt = (
            "以下是一組候選圖片的資訊（你無法看到圖片）。\n"
            f"共 {len(image_paths)} 張候選，使用相同提示詞、不同隨機種子生成。\n"
            f"提示詞: {original_prompt[:300]}\n\n"
            "由於你無法看到圖片，請為每張圖片給出一個基於統計推理的預設分數。\n"
            "建議: 給第一張和最後一張稍高分（隨機性分佈的兩端通常較有趣），中間給中等分。\n"
            "輸出 JSON: {\"evaluations\": [{\"index\": 0, \"score\": 6.5, \"reason\": \"...\"}]}"
        )

        try:
            resp = requests.post(
                f"{self._ollama_host}/api/generate",
                json={
                    "model": self._ollama_model,
                    "prompt": fallback_prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.3, "num_predict": 512}
                },
                timeout=60
            )
            if resp.status_code == 200:
                result = resp.json()
                parsed = json.loads(result.get("response", "{}"))
                evals = parsed.get("evaluations", [])
                if evals:
                    for e in evals:
                        if e.get("index", 0) < len(image_paths):
                            e["image_path"] = image_paths[e["index"]]
                        e.setdefault("controlnet_advice", {"use": False, "type": None, "reason": "Ollama fallback"})
                    return evals
        except Exception as e:
            logger.warning(f"Ollama fallback 也失敗: {e}")

        # 最終 fallback: 給所有圖片均等分數
        return [
            {
                "index": i,
                "image_path": image_paths[i] if i < len(image_paths) else None,
                "score": 6.0,
                "reason": "所有評估方式均失敗，使用預設分數",
                "controlnet_advice": {"use": False, "type": None, "reason": "無評估可用"}
            }
            for i in range(len(image_paths))
        ]

    # ================================================================
    # 輔助方法
    # ================================================================

    def _select_best(self, eval_results: list, min_score: float) -> Optional[dict]:
        """
        從評分結果中選出最佳候選。

        Args:
            eval_results: 評分結果列表
            min_score: 最低分數門檻

        Returns:
            最佳候選 dict，或 None（全部低於門檻）
        """
        valid = [e for e in eval_results if e.get("score", 0) >= min_score]
        if not valid:
            return None
        return max(valid, key=lambda e: e.get("score", 0))

    # ================================================================
    # 批次處理: 今日所有圖片
    # ================================================================

    def run_daily_batch(
        self,
        prompt_packages: list,
        date_str: Optional[str] = None
    ) -> dict:
        """
        執行今日所有圖片的精煉迴圈。

        管理重試預算和跨圖片的資源分配。

        Args:
            prompt_packages: Stage 2 產出的 PromptPackage 列表
            date_str: 日期

        Returns:
            {
                "date": str,
                "results": list,          # 每張圖的 process_single_image 結果
                "success_count": int,
                "discard_count": int,
                "total_retries_used": int,
                "observation": dict
            }
        """
        if date_str is None:
            date_str = date.today().isoformat()

        max_retries_per_image = self._schedule_config.get("max_retries_per_image", 2)
        max_daily_retries = self._schedule_config.get("max_daily_retries", 4)

        daily_retries_used = 0
        all_results = []

        logger.info(f"=== Stage 3 批次處理: {len(prompt_packages)} 張圖 ===")

        for pkg in prompt_packages:
            image_retries_used = 0

            retry_budget = {
                "remaining_image": max_retries_per_image - image_retries_used,
                "remaining_daily": max_daily_retries - daily_retries_used
            }

            # 首次嘗試
            result = self.process_single_image(pkg, retry_budget)

            # 處理 retry_needed（3.2 全部 < 5.0，需重新生成提示詞）
            while (
                result["status"] == "retry_needed"
                and image_retries_used < max_retries_per_image
                and daily_retries_used < max_daily_retries
            ):
                image_retries_used += 1
                daily_retries_used += 1
                logger.info(
                    f"{pkg['image_id']}: 重試 {image_retries_used}/{max_retries_per_image} "
                    f"(daily: {daily_retries_used}/{max_daily_retries})"
                )

                # 重試時標記需要上層 (pipeline_main) 重新呼叫 Stage 2
                # 這裡直接重新嘗試相同提示詞（簡化版）
                # 完整版中 pipeline_main 會重新調用 prompt_generator
                retry_budget = {
                    "remaining_image": max_retries_per_image - image_retries_used,
                    "remaining_daily": max_daily_retries - daily_retries_used
                }
                result = self.process_single_image(pkg, retry_budget)

            # 3.2 重試後仍失敗
            if result["status"] == "retry_needed":
                result["status"] = "discarded"
                result["generation_log"].append({
                    "stage": "retry_exhausted",
                    "reason": "prompt_quality_failure",
                    "retries_used": image_retries_used
                })
                logger.warning(f"{pkg['image_id']}: 重試用盡，丟棄 (prompt_quality_failure)")

            result["retry_consumed"] = image_retries_used
            all_results.append(result)

        # 統整
        success_count = sum(1 for r in all_results if r["status"] == "success")
        discard_count = sum(1 for r in all_results if r["status"] == "discarded")

        logger.info(
            f"Stage 3 批次完成: {success_count} 成功, {discard_count} 丟棄, "
            f"重試 {daily_retries_used} 次"
        )

        return {
            "date": date_str,
            "results": all_results,
            "success_count": success_count,
            "discard_count": discard_count,
            "total_retries_used": daily_retries_used,
            "observation": self._observation
        }

    @property
    def observation(self) -> dict:
        return self._observation.copy()

