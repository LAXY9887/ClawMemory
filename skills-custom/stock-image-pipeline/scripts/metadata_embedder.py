"""
Stage 5.1b: EXIF/IPTC 元數據嵌入 + 檔案重命名

用途:
  - 將 image_describer 產出的描述和關鍵詞嵌入圖片 EXIF/IPTC
  - 按規範重命名檔案: {topic}_{date}_{sequence}_{score}.png
  - 嵌入後 Dreamstime/Adobe Stock 可自動讀取元數據

設計原則:
  - 使用 Pillow PngInfo（PNG）或 piexif（JPEG）嵌入
  - 不依賴 exiftool CLI（減少外部依賴）
  - AI 揭露標記必嵌入
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"


class MetadataEmbedderError(Exception):
    """元數據嵌入失敗"""
    pass


class MetadataEmbedder:
    """
    Stage 5.1b: EXIF/IPTC 元數據嵌入。

    使用方式:
        embedder = MetadataEmbedder(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        result = embedder.embed_and_rename(
            image_path="...",
            metadata={title, description, keywords, ...},
            theme="eerie-scene",
            date_str="2026-03-28",
            sequence=1,
            score=8.7
        )
    """

    def __init__(self, workspace_base: Optional[str] = None):
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")

        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()
        self._pending_dir = self._workspace / self._schedule_config.get("workspace", {}).get("pending_dir", "pending")

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def embed_and_rename(
        self,
        image_path: str,
        metadata: dict,
        theme: str,
        date_str: str,
        sequence: int,
        score: float
    ) -> dict:
        """
        嵌入元數據並重命名檔案。

        Args:
            image_path: 原始圖片路徑
            metadata: image_describer 產出的元數據
            theme: 主題名
            date_str: 日期 (YYYY-MM-DD)
            sequence: 序號
            score: 最終評分

        Returns:
            {
                "original_path": str,
                "final_path": str,      # 重命名後的路徑（在 pending/ 中）
                "filename": str,
                "metadata_embedded": bool,
                "embed_method": str
            }
        """
        logger.info(f"5.1b 元數據嵌入: {image_path}")
        src = Path(image_path)

        if not src.exists():
            raise MetadataEmbedderError(f"圖片不存在: {image_path}")

        # 1. 檔案重命名
        date_compact = date_str.replace("-", "")
        score_str = f"{score:.1f}"
        new_filename = f"{theme}_{date_compact}_{sequence:03d}_{score_str}{src.suffix}"

        self._pending_dir.mkdir(parents=True, exist_ok=True)
        dest = self._pending_dir / new_filename

        # 2. 嵌入元數據
        embed_method = "none"
        embedded = False

        suffix = src.suffix.lower()
        if suffix == ".png":
            embedded = self._embed_png_metadata(src, dest, metadata)
            embed_method = "png_text_chunk" if embedded else "copy_only"
        elif suffix in (".jpg", ".jpeg"):
            embedded = self._embed_jpeg_metadata(src, dest, metadata)
            embed_method = "piexif" if embedded else "copy_only"
        else:
            # 不支援的格式，直接複製
            shutil.copy2(str(src), str(dest))
            embed_method = "unsupported_format"

        if not embedded and not dest.exists():
            # 確保檔案至少被複製
            shutil.copy2(str(src), str(dest))

        logger.info(f"元數據嵌入完成: {new_filename} (method={embed_method})")

        return {
            "original_path": str(src),
            "final_path": str(dest),
            "filename": new_filename,
            "metadata_embedded": embedded,
            "embed_method": embed_method
        }

    def _embed_png_metadata(self, src: Path, dest: Path, metadata: dict) -> bool:
        """
        PNG 元數據嵌入（使用 Pillow PngInfo text chunks）。

        PNG 不支援 EXIF/IPTC 原生，但支援 tEXt/iTXt chunks。
        圖庫平台可讀取部分 text chunk 作為描述。
        """
        try:
            from PIL import Image
            from PIL.PngImagePlugin import PngInfo

            img = Image.open(src)
            png_info = PngInfo()

            # 嵌入描述欄位
            png_info.add_text("Title", metadata.get("title", ""))
            png_info.add_text("Description", metadata.get("description", ""))
            png_info.add_text("Keywords", ", ".join(metadata.get("keywords", [])))
            png_info.add_text("Author", "ClawClaw AI Pipeline")
            png_info.add_text("Comment", metadata.get("ai_disclosure", "AI Generated"))
            png_info.add_text("Category", metadata.get("category", ""))

            # 平台標記
            platform_tags = metadata.get("platform_tags", {})
            if platform_tags:
                png_info.add_text("PlatformTags", json.dumps(platform_tags, ensure_ascii=False))

            img.save(str(dest), pnginfo=png_info)
            return True

        except Exception as e:
            logger.warning(f"PNG 元數據嵌入失敗: {e}")
            return False

    def _embed_jpeg_metadata(self, src: Path, dest: Path, metadata: dict) -> bool:
        """
        JPEG 元數據嵌入（使用 piexif）。

        嵌入 EXIF ImageDescription 和 UserComment。
        """
        try:
            import piexif

            exif_dict = piexif.load(str(src))

            # EXIF ImageDescription
            description = metadata.get("description", "")
            exif_dict["0th"][piexif.ImageIFD.ImageDescription] = description.encode("utf-8")

            # EXIF UserComment (AI disclosure)
            ai_tag = metadata.get("ai_disclosure", "AI Generated")
            # UserComment 需要特定格式: charset + content
            user_comment = b"ASCII\x00\x00\x00" + ai_tag.encode("ascii", errors="replace")
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = user_comment

            # 寫入
            exif_bytes = piexif.dump(exif_dict)
            from PIL import Image
            img = Image.open(src)
            img.save(str(dest), exif=exif_bytes, quality=95)
            return True

        except ImportError:
            logger.warning("piexif 未安裝，使用 Pillow 基礎嵌入")
            return self._embed_jpeg_pillow_fallback(src, dest, metadata)
        except Exception as e:
            logger.warning(f"JPEG 元數據嵌入失敗: {e}")
            return self._embed_jpeg_pillow_fallback(src, dest, metadata)

    def _embed_jpeg_pillow_fallback(self, src: Path, dest: Path, metadata: dict) -> bool:
        """JPEG fallback: 用 Pillow 複製（無法嵌入完整 EXIF）"""
        try:
            from PIL import Image
            img = Image.open(src)
            img.save(str(dest), quality=95)
            return False  # 標記為未嵌入
        except Exception as e:
            logger.warning(f"JPEG Pillow fallback 也失敗: {e}")
            shutil.copy2(str(src), str(dest))
            return False

    # --- 批次操作 ---

    def embed_batch(
        self,
        descriptions: list,
        theme: str,
        date_str: str,
        scores: dict
    ) -> list:
        """
        批次嵌入元數據。

        Args:
            descriptions: image_describer.describe_batch() 的結果
            theme: 主題
            date_str: 日期
            scores: {image_id: score} 映射

        Returns:
            list of embed_and_rename() 結果
        """
        results = []
        for i, desc in enumerate(descriptions):
            image_id = desc.get("image_id", f"img-{i}")
            image_path = desc.get("image_path", "")
            score = scores.get(image_id, 0.0)

            try:
                result = self.embed_and_rename(
                    image_path=image_path,
                    metadata=desc,
                    theme=theme,
                    date_str=date_str,
                    sequence=i + 1,
                    score=score
                )
                result["image_id"] = image_id
                results.append(result)
            except Exception as e:
                logger.error(f"嵌入失敗 ({image_id}): {e}")
                results.append({
                    "image_id": image_id,
                    "error": str(e),
                    "metadata_embedded": False
                })

        return results

