"""
test_modules_import.py — 模組 import 驗證

驗證所有 scripts/ 下的模組可以被正常 import（語法正確、無 circular import）。
不需要外部服務（ComfyUI / OpenRouter / Ollama）即可執行。
"""

import ast
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def get_all_scripts():
    """取得所有 Python 腳本。"""
    return sorted(SCRIPTS_DIR.glob("*.py"))


class TestSyntax:
    """所有模組語法驗證。"""

    @pytest.mark.parametrize("script", get_all_scripts(), ids=lambda p: p.name)
    def test_syntax_valid(self, script):
        """每個模組都應該能通過 ast.parse。"""
        with open(script, "r", encoding="utf-8") as f:
            content = f.read()
        # 不應拋出 SyntaxError
        ast.parse(content, filename=str(script))


class TestImports:
    """模組 import 驗證（需要 requests 和 Pillow 已安裝）。"""

    def test_import_openrouter_client(self):
        from openrouter_client import OpenRouterClient
        assert OpenRouterClient is not None

    def test_import_comfyui_client(self):
        from comfyui_client import ComfyUIClient
        assert ComfyUIClient is not None

    def test_import_creative_brief_generator(self):
        from creative_brief_generator import CreativeBriefGenerator
        assert CreativeBriefGenerator is not None

    def test_import_prompt_generator(self):
        from prompt_generator import PromptGenerator
        assert PromptGenerator is not None

    def test_import_image_refiner(self):
        from image_refiner import ImageRefiner
        assert ImageRefiner is not None

    def test_import_defect_detector(self):
        from defect_detector import DefectDetector
        assert DefectDetector is not None

    def test_import_image_describer(self):
        from image_describer import ImageDescriber
        assert ImageDescriber is not None

    def test_import_metadata_embedder(self):
        from metadata_embedder import MetadataEmbedder
        assert MetadataEmbedder is not None

    def test_import_ftp_uploader(self):
        from ftp_uploader import FTPUploader
        assert FTPUploader is not None

    def test_import_upload_preparer(self):
        from upload_preparer import UploadPreparer
        assert UploadPreparer is not None

    def test_import_memory_observer(self):
        from memory_observer import MemoryObserver
        assert MemoryObserver is not None

    def test_import_experience_distiller(self):
        from experience_distiller import ExperienceDistiller
        assert ExperienceDistiller is not None

    def test_import_metrics_collector(self):
        from metrics_collector import MetricsCollector
        assert MetricsCollector is not None

class TestNoHardcodedSecrets:
    """確認沒有硬編碼的敏感資訊。"""

    @pytest.mark.parametrize("script", get_all_scripts(), ids=lambda p: p.name)
    def test_no_api_keys(self, script):
        """不應包含硬編碼的 API key（排除錯誤訊息中的示範格式）。"""
        import re
        with open(script, "r") as f:
            content = f.read()
        # 排除註解和字串中的示範（如 "sk-or-..."）
        lines = [l for l in content.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(lines)
        # 真正的 key 至少有 20+ 字元，示範的 "sk-or-..." 很短
        real_key_pattern = r'sk-or-[A-Za-z0-9]{20,}'
        assert not re.search(real_key_pattern, code), f"{script.name} 包含硬編碼 OpenRouter key"
        real_ant_pattern = r'sk-ant-[A-Za-z0-9]{20,}'
        assert not re.search(real_ant_pattern, code), f"{script.name} 包含硬編碼 Anthropic key"

    @pytest.mark.parametrize("script", get_all_scripts(), ids=lambda p: p.name)
    def test_no_absolute_user_paths(self, script):
        """不應包含硬編碼的使用者目錄路徑。"""
        with open(script, "r") as f:
            content = f.read()
        lines = [l for l in content.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(lines)
        assert "/Users/" not in code, f"{script.name} 包含 macOS 使用者路徑"
        assert "/home/" not in code, f"{script.name} 包含 Linux 使用者路徑"
