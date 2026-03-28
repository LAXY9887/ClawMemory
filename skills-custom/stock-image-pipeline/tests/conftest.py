"""
共用 fixtures — 所有測試檔共享。
"""

import json
import sys
from pathlib import Path
import pytest

# 讓 tests/ 可以 import scripts/ 下的模組
SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SOURCE_LIB_DIR = CONFIG_DIR / "source-library"


@pytest.fixture
def schedule_config():
    """讀取 schedule.json。"""
    with open(CONFIG_DIR / "schedule.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def topics_config():
    """讀取 topics.json。"""
    with open(CONFIG_DIR / "topics.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def source_lib_index():
    """讀取 source-library/_index.json。"""
    with open(SOURCE_LIB_DIR / "_index.json", "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_prompt_package():
    """測試用的 prompt package。"""
    return {
        "positive": "a futuristic cityscape, neon lights, cyberpunk, 8k detailed",
        "negative": "blurry, low quality, text, watermark",
        "canvas_type": "landscape",
        "width": 1280,
        "height": 960,
        "cfg": 8,
        "steps": 22,
        "sampler": "euler_a",
        "seed": 42,
        "lora": "cyber_graphic",
        "lora_weight": 0.7,
    }


