"""
Stage 5.1: 圖片描述提取（Image Description Extractor）

用途:
  - 用 OpenRouter 多模態視覺模型讀取最終圖片
  - 產出英文商業描述 (100-150 字)
  - 產出 15-25 個搜尋關鍵詞
  - 建議 Adobe Stock 類別
  - 產出簡短標題

設計原則:
  - 描述基於「圖片實際內容」，而非只是提示詞
  - 全英文輸出（符合國際圖庫要求）
  - 平台特殊標記: AI Generated, Generative AI, fictional people
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"


class ImageDescriberError(Exception):
    """圖片描述提取失敗"""
    pass


class ImageDescriber:
    """
    Stage 5.1: OpenRouter 圖片描述提取。

    使用方式:
        describer = ImageDescriber()
        metadata = describer.describe(image_path="...", prompt_package={...})
    """

    def __init__(self):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")
        self._openrouter_client = None

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

    def describe(
        self,
        image_path: str,
        prompt_package: dict,
        theme: str = "unknown"
    ) -> dict:
        """
        為單張圖片產出商業描述和元數據。

        Args:
            image_path: 最終 upscale 圖片路徑
            prompt_package: PromptPackage（參考用）
            theme: 主題名（用於平台標記）

        Returns:
            {
                "title": str,              # 簡短標題 (5-10 words)
                "description": str,        # 100-150 字商業描述
                "keywords": list[str],     # 15-25 個搜尋關鍵詞
                "category": str,           # Adobe Stock 類別建議
                "ai_disclosure": str,      # AI 揭露標記
                "platform_tags": dict      # 各平台特殊標記
            }
        """
        logger.info(f"5.1 圖片描述提取: {image_path}")

        describe_prompt = (
            "You are a professional stock photography metadata specialist. "
            "Analyze this image and produce commercial metadata in English.\n\n"
            f"## Context (for reference only, describe what you SEE, not the prompt):\n"
            f"Theme: {theme}\n"
            f"Original concept: {prompt_package.get('brief_concept', 'N/A')}\n\n"
            "## Required Output (strict JSON):\n"
            "{\n"
            '  "title": "Short descriptive title, 5-10 words, no quotes in title",\n'
            '  "description": "Commercial description, 100-150 words. Describe the visual content, '
            'mood, composition, and potential use cases. Write for stock photo buyers.",\n'
            '  "keywords": ["keyword1", "keyword2", ...],\n'
            '  "category": "Best matching Adobe Stock category"\n'
            "}\n\n"
            "## Rules:\n"
            "- Title: concise, descriptive, starts with capital letter\n"
            "- Description: professional, third-person, present tense\n"
            "- Keywords: 15-25 relevant terms, single words or two-word phrases, lowercase\n"
            "- Category: choose from (Illustrations, Abstract, Technology, Nature, People, Animals, "
            "Architecture, Fantasy, Horror, Conceptual Art)\n"
            "- DO NOT mention AI generation in the description or keywords\n"
            "- Describe what is visually present, not what was intended"
        )

        try:
            client = self._get_openrouter()
            response = client.chat_with_images_json(
                prompt=describe_prompt,
                image_paths=[image_path],
                max_tokens=1500,
                temperature=0.3
            )

            # 驗證必要欄位
            metadata = self._validate_response(response)

        except Exception as e:
            logger.error(f"OpenRouter 描述提取失敗: {e}")
            metadata = self._fallback_metadata(prompt_package, theme)

        # 加入 AI 揭露和平台標記
        metadata["ai_disclosure"] = "AI Generated"
        metadata["platform_tags"] = self._build_platform_tags(theme)

        logger.info(f"描述提取完成: title='{metadata['title']}', keywords={len(metadata.get('keywords', []))}")
        return metadata

    def _validate_response(self, response: dict) -> dict:
        """驗證並標準化 OpenRouter 回應"""
        title = response.get("title", "Untitled Stock Image")
        description = response.get("description", "")
        keywords = response.get("keywords", [])
        category = response.get("category", "Illustrations")

        # 標題清理
        title = title.strip('"\'').strip()
        if len(title) > 200:
            title = title[:197] + "..."

        # 關鍵詞清理
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",")]
        keywords = [k.strip().lower() for k in keywords if k.strip()]

        # 確保關鍵詞數量
        if len(keywords) < 15:
            logger.warning(f"關鍵詞不足 15 個 (got {len(keywords)})")
        keywords = keywords[:50]  # 上限防護

        return {
            "title": title,
            "description": description,
            "keywords": keywords,
            "category": category
        }

    def _fallback_metadata(self, pkg: dict, theme: str) -> dict:
        """OpenRouter 失敗時的 fallback 元數據"""
        concept = pkg.get("brief_concept", "")
        positive = pkg.get("positive_prompt", "")

        # 從提示詞提取簡單描述
        title = f"Digital {theme.replace('-', ' ').title()} Artwork"
        description = (
            f"A digitally created {theme.replace('-', ' ')} artwork. "
            f"This image features carefully composed visual elements with "
            f"attention to detail and atmospheric lighting. "
            f"Suitable for editorial, web design, and creative projects."
        )

        # 從提示詞提取關鍵詞
        raw_keywords = positive.replace(",", " ").split()
        keywords = list(set(
            k.strip().lower() for k in raw_keywords
            if len(k.strip()) > 2 and k.strip().lower() not in
            {"masterpiece", "best", "quality", "highly", "detailed", "sharp", "focus"}
        ))[:25]

        return {
            "title": title,
            "description": description,
            "keywords": keywords if keywords else ["digital art", "illustration", "creative"],
            "category": "Illustrations"
        }

    def _build_platform_tags(self, theme: str) -> dict:
        """建構各平台的特殊標記"""
        tags = {
            "dreamstime": {
                "ai_generated_tag": True,
                "description_suffix": " [AI generated image]"
            },
            "adobe_stock": {
                "generative_ai_flag": True,
                "ai_tool": "Stable Diffusion"
            }
        }

        # ClawClaw 肖像: 人物虛構聲明
        if theme == "clawclaw-portrait":
            tags["dreamstime"]["model_release_note"] = "People and Property are fictional"
            tags["adobe_stock"]["fictional_people"] = True

        return tags

    def describe_batch(self, passed_images: list, prompt_packages: list, theme: str) -> list:
        """
        批次描述提取。

        Args:
            passed_images: PASS 圖片的路徑列表
            prompt_packages: 對應的 PromptPackage
            theme: 主題名

        Returns:
            list of describe() 結果
        """
        pkg_map = {p["image_id"]: p for p in prompt_packages}
        results = []

        for img_info in passed_images:
            image_path = img_info.get("final_image") or img_info.get("image_path")
            image_id = img_info.get("image_id", "unknown")
            pkg = pkg_map.get(image_id, {})

            metadata = self.describe(image_path, pkg, theme)
            metadata["image_id"] = image_id
            metadata["image_path"] = image_path
            results.append(metadata)

        return results
