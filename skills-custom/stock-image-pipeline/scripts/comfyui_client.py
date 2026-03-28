"""
ComfyUI API Client — 統一封裝所有 ComfyUI 呼叫

用途:
  - Stage 3.1: txt2img 初步候選生成
  - Stage 3.3: img2img 精煉放大生成（含可選 ControlNet）
  - Stage 3.5: 4x Upscale 最終放大

設計原則:
  - ComfyUI API 預設在 localhost:8188
  - 畫布尺寸和生成參數從 config/topics.json 讀取
  - 支援 queue 管理和生成狀態輪詢
  - 所有 workflow 以 API JSON 格式提交
"""

import json
import time
import uuid
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_COMFYUI_HOST = "127.0.0.1"
DEFAULT_COMFYUI_PORT = 8188
POLL_INTERVAL = 2  # seconds
MAX_POLL_TIME = 600  # 10 minutes max per generation


class ComfyUIError(Exception):
    """ComfyUI API 呼叫失敗"""
    pass


class ComfyUIClient:
    """
    ComfyUI API 統一客戶端。

    使用方式:
        client = ComfyUIClient()
        # txt2img 生成
        images = client.txt2img(prompt="...", negative="...", width=768, height=1280, ...)
        # img2img 精煉
        images = client.img2img(init_image="path.png", prompt="...", denoise=0.35, ...)
        # 4x Upscale
        result = client.upscale(image_path="path.png", scale=4)
    """

    def __init__(
        self,
        host: str = DEFAULT_COMFYUI_HOST,
        port: int = DEFAULT_COMFYUI_PORT,
        config_path: Optional[str] = None
    ):
        self.base_url = f"http://{host}:{port}"
        self.client_id = str(uuid.uuid4())

        # 載入 topics.json 取得畫布和模型配置
        self._topics_config = self._load_topics_config(config_path)
        self._upscale_config = self._topics_config.get("upscale", {})

    def _load_topics_config(self, config_path: Optional[str]) -> dict:
        """載入 topics.json"""
        if config_path is None:
            script_dir = Path(__file__).resolve().parent
            config_path = script_dir.parent / "config" / "topics.json"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Topics config 不存在: {config_path}，使用預設值")
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _post_prompt(self, workflow: dict) -> str:
        """
        提交 workflow 到 ComfyUI queue。

        Args:
            workflow: ComfyUI API 格式的 workflow JSON

        Returns:
            prompt_id: 用於追蹤生成進度的 ID
        """
        import requests

        payload = {
            "prompt": workflow,
            "client_id": self.client_id
        }

        try:
            resp = requests.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30
            )
            if resp.status_code != 200:
                raise ComfyUIError(
                    f"ComfyUI queue 提交失敗 (HTTP {resp.status_code}): "
                    f"{resp.text[:300]}"
                )
            result = resp.json()
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                raise ComfyUIError(f"ComfyUI 回應缺少 prompt_id: {result}")
            logger.info(f"ComfyUI 任務提交成功: {prompt_id}")
            return prompt_id

        except requests.exceptions.ConnectionError:
            raise ComfyUIError(
                f"無法連線 ComfyUI ({self.base_url})。"
                "請確認 ComfyUI Desktop 已啟動且 API 模式開啟。"
            )

    def _poll_result(self, prompt_id: str) -> dict:
        """
        輪詢等待生成完成。

        Args:
            prompt_id: 任務 ID

        Returns:
            生成結果的 history dict
        """
        import requests

        start_time = time.time()
        while time.time() - start_time < MAX_POLL_TIME:
            try:
                resp = requests.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=10
                )
                if resp.status_code == 200:
                    history = resp.json()
                    if prompt_id in history:
                        status = history[prompt_id].get("status", {})
                        if status.get("completed", False):
                            logger.info(f"ComfyUI 生成完成: {prompt_id}")
                            return history[prompt_id]
                        if status.get("status_str") == "error":
                            error_msg = status.get("messages", [])
                            raise ComfyUIError(
                                f"ComfyUI 生成錯誤: {error_msg}"
                            )
            except requests.exceptions.ConnectionError:
                logger.warning("ComfyUI 連線中斷，等待重連...")

            time.sleep(POLL_INTERVAL)

        raise ComfyUIError(
            f"ComfyUI 生成超時 ({MAX_POLL_TIME}s): {prompt_id}"
        )

    def _get_output_images(self, history: dict, output_dir: str) -> list:
        """
        從生成結果中下載輸出圖片。

        Args:
            history: ComfyUI history 結果
            output_dir: 圖片儲存目錄

        Returns:
            儲存的圖片路徑列表
        """
        import requests

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        outputs = history.get("outputs", {})

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for img_info in node_output["images"]:
                    filename = img_info.get("filename", "unknown.png")
                    subfolder = img_info.get("subfolder", "")
                    img_type = img_info.get("type", "output")

                    # 下載圖片
                    params = {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": img_type
                    }
                    resp = requests.get(
                        f"{self.base_url}/view",
                        params=params,
                        timeout=60
                    )
                    if resp.status_code == 200:
                        save_path = output_dir / filename
                        with open(save_path, "wb") as f:
                            f.write(resp.content)
                        saved_paths.append(str(save_path))
                        logger.info(f"圖片已儲存: {save_path}")

        return saved_paths

    # --- 公開 API ---

    def txt2img(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 768,
        height: int = 768,
        steps: int = 22,
        cfg: float = 8.0,
        sampler: str = "euler_a",
        seed: int = -1,
        lora: Optional[str] = None,
        lora_weight: float = 0.7,
        batch_size: int = 1,
        output_dir: str = "/tmp/comfyui_output",
        checkpoint: str = "rinIllusion_v10.safetensors"
    ) -> list:
        """
        txt2img 生成（Stage 3.1 初步候選）。

        Args:
            prompt: 正面提示詞
            negative_prompt: 負面提示詞
            width, height: 畫布尺寸（從 topics.json canvas_types 讀取）
            steps: 採樣步數
            cfg: CFG Scale
            sampler: 採樣器名稱
            seed: 隨機種子（-1 = 隨機）
            lora: LoRA 模型名稱（None = 不使用）
            lora_weight: LoRA 權重
            batch_size: 批次大小
            output_dir: 輸出目錄
            checkpoint: 基礎模型檔名

        Returns:
            生成的圖片路徑列表
        """
        if seed == -1:
            import random
            seed = random.randint(0, 2**32 - 1)

        # 建構基礎 workflow
        workflow = self._build_txt2img_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            seed=seed,
            lora=lora,
            lora_weight=lora_weight,
            batch_size=batch_size,
            checkpoint=checkpoint
        )

        prompt_id = self._post_prompt(workflow)
        history = self._poll_result(prompt_id)
        return self._get_output_images(history, output_dir)

    def img2img(
        self,
        init_image: str,
        prompt: str,
        negative_prompt: str = "",
        width: int = 900,
        height: int = 1400,
        steps: int = 30,
        cfg: float = 8.0,
        sampler: str = "euler_a",
        denoise: float = 0.35,
        seed: int = -1,
        lora: Optional[str] = None,
        lora_weight: float = 0.7,
        controlnet_type: Optional[str] = None,
        output_dir: str = "/tmp/comfyui_output",
        checkpoint: str = "rinIllusion_v10.safetensors"
    ) -> list:
        """
        img2img 精煉生成（Stage 3.3）。

        Args:
            init_image: 初始圖片路徑（3.2 選出的最佳候選）
            denoise: 去噪強度（0.25-0.45，由精煉參數定義）
            controlnet_type: ControlNet 類型（"openpose"/"depth"/"canny"/None）
            其他參數同 txt2img

        Returns:
            生成的圖片路徑列表
        """
        if seed == -1:
            import random
            seed = random.randint(0, 2**32 - 1)

        workflow = self._build_img2img_workflow(
            init_image=init_image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            denoise=denoise,
            seed=seed,
            lora=lora,
            lora_weight=lora_weight,
            controlnet_type=controlnet_type,
            checkpoint=checkpoint
        )

        prompt_id = self._post_prompt(workflow)
        history = self._poll_result(prompt_id)
        return self._get_output_images(history, output_dir)

    def upscale(
        self,
        image_path: str,
        scale: int = 4,
        model: Optional[str] = None,
        output_dir: str = "/tmp/comfyui_output"
    ) -> list:
        """
        Upscale 放大（Stage 3.5）。

        Args:
            image_path: 待放大圖片路徑
            scale: 放大倍率（預設 4x）
            model: Upscale 模型名（預設從 config 讀取）
            output_dir: 輸出目錄

        Returns:
            放大後的圖片路徑列表
        """
        if model is None:
            model = self._upscale_config.get("model", "4x-UltraSharp")

        workflow = self._build_upscale_workflow(
            image_path=image_path,
            scale=scale,
            model=model
        )

        prompt_id = self._post_prompt(workflow)
        history = self._poll_result(prompt_id)
        return self._get_output_images(history, output_dir)

    def get_canvas_size(self, canvas_type: str, stage: str = "initial") -> tuple:
        """
        從 config 取得畫布尺寸。

        Args:
            canvas_type: "square" / "portrait" / "landscape"
            stage: "initial" / "refined" / "final_4x"

        Returns:
            (width, height) tuple
        """
        canvas_types = self._topics_config.get("canvas_types", {})
        canvas = canvas_types.get(canvas_type, {})
        size = canvas.get(stage, [768, 768])
        return tuple(size)

    def check_connection(self) -> bool:
        """
        檢查 ComfyUI 是否可連線。

        Returns:
            True = 可連線, False = 不可連線
        """
        import requests
        try:
            resp = requests.get(
                f"{self.base_url}/system_stats",
                timeout=5
            )
            return resp.status_code == 200
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            return False

    # --- Workflow 建構 ---
    # 注意: 以下 workflow 結構為 ComfyUI API 格式的骨架。
    # 實際 node ID 和連線需根據 LXYA 的 ComfyUI workflow 調整。
    # 這些是示範結構，首次測試時需校準。

    def _build_txt2img_workflow(self, **params) -> dict:
        """
        建構 txt2img workflow。

        這是 ComfyUI API 格式的 workflow 骨架。
        Node ID 和具體連線關係需要根據 LXYA 實際使用的 ComfyUI workflow 校準。
        首次測試時，建議從 ComfyUI UI 匯出一個可用的 workflow JSON，
        然後替換此處的骨架。
        """
        # TODO: 首次測試時從 ComfyUI UI 匯出實際 workflow 替換
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": params["seed"],
                    "steps": params["steps"],
                    "cfg": params["cfg"],
                    "sampler_name": params["sampler"],
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": params["checkpoint"]
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": params["width"],
                    "height": params["height"],
                    "batch_size": params["batch_size"]
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params["prompt"],
                    "clip": ["4", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params["negative_prompt"],
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "pipeline",
                    "images": ["8", 0]
                }
            }
        }

        # LoRA 插入（如果有）
        if params.get("lora") and params["lora_weight"] > 0:
            workflow["10"] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": f"{params['lora']}.safetensors",
                    "strength_model": params["lora_weight"],
                    "strength_clip": params["lora_weight"],
                    "model": ["4", 0],
                    "clip": ["4", 1]
                }
            }
            # 重新連線：KSampler 和 CLIP 改接 LoRA 輸出
            workflow["3"]["inputs"]["model"] = ["10", 0]
            workflow["6"]["inputs"]["clip"] = ["10", 1]
            workflow["7"]["inputs"]["clip"] = ["10", 1]

        return workflow

    def _build_img2img_workflow(self, **params) -> dict:
        """
        建構 img2img workflow（精煉用）。
        TODO: 首次測試時從 ComfyUI UI 匯出實際 workflow 替換
        """
        workflow = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": params["init_image"]
                }
            },
            "2": {
                "class_type": "ImageScale",
                "inputs": {
                    "width": params["width"],
                    "height": params["height"],
                    "upscale_method": "lanczos",
                    "crop": "disabled",
                    "image": ["1", 0]
                }
            },
            "3": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["2", 0],
                    "vae": ["4", 2]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": params["checkpoint"]
                }
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": params["seed"],
                    "steps": params["steps"],
                    "cfg": params["cfg"],
                    "sampler_name": params["sampler"],
                    "scheduler": "normal",
                    "denoise": params["denoise"],
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["3", 0]
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params["prompt"],
                    "clip": ["4", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": params["negative_prompt"],
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "pipeline_refined",
                    "images": ["8", 0]
                }
            }
        }

        # LoRA 插入
        if params.get("lora") and params["lora_weight"] > 0:
            workflow["10"] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": f"{params['lora']}.safetensors",
                    "strength_model": params["lora_weight"],
                    "strength_clip": params["lora_weight"],
                    "model": ["4", 0],
                    "clip": ["4", 1]
                }
            }
            workflow["5"]["inputs"]["model"] = ["10", 0]
            workflow["6"]["inputs"]["clip"] = ["10", 1]
            workflow["7"]["inputs"]["clip"] = ["10", 1]

        # ControlNet 插入（由 Stage 3.2 自評建議驅動）
        if params.get("controlnet_type"):
            cn_model_map = {
                "openpose": "control_v11p_sd15_openpose.pth",
                "depth": "control_v11f1p_sd15_depth.pth",
                "canny": "control_v11p_sd15_canny.pth"
            }
            cn_model = cn_model_map.get(
                params["controlnet_type"],
                "control_v11p_sd15_openpose.pth"
            )
            # ControlNet preprocessor + apply
            workflow["11"] = {
                "class_type": "ControlNetLoader",
                "inputs": {
                    "control_net_name": cn_model
                }
            }
            workflow["12"] = {
                "class_type": "ControlNetApply",
                "inputs": {
                    "conditioning": ["6", 0],
                    "control_net": ["11", 0],
                    "image": ["2", 0],
                    "strength": 0.6
                }
            }
            # 重新連線：KSampler positive 改接 ControlNet 輸出
            workflow["5"]["inputs"]["positive"] = ["12", 0]

        return workflow

    def _build_upscale_workflow(self, **params) -> dict:
        """
        建構 Upscale workflow（4x 放大）。
        TODO: 首次測試時從 ComfyUI UI 匯出實際 workflow 替換
        """
        workflow = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {
                    "image": params["image_path"]
                }
            },
            "2": {
                "class_type": "UpscaleModelLoader",
                "inputs": {
                    "model_name": params['model'] if '.' in params['model'] else f"{params['model']}.pth"
                }
            },
            "3": {
                "class_type": "ImageUpscaleWithModel",
                "inputs": {
                    "upscale_model": ["2", 0],
                    "image": ["1", 0]
                }
            },
            "4": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "pipeline_upscaled",
                    "images": ["3", 0]
                }
            }
        }
        return workflow
