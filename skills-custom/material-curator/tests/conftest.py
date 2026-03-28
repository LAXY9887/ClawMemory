"""
共用 fixtures — Material Curator 測試專用。
"""

import json
import sys
from pathlib import Path
import pytest

# 讓 tests/ 可以 import scripts/ 下的模組
SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


@pytest.fixture
def sample_raw_article():
    """測試用的爬取原始文章。"""
    return {
        "url": "https://example.com/test-story",
        "title": "The Abandoned Hospital",
        "content": (
            "The corridor stretched endlessly before me, lit only by the "
            "flickering fluorescent tubes overhead. Rust-colored stains "
            "marked the walls where gurneys had scraped against the tiles "
            "for decades. At the far end, a surgical lamp hung at an "
            "impossible angle, casting long shadows across the floor. "
            "I could hear the drip of water echoing from somewhere deep "
            "within the building. The air smelled of decay and antiseptic, "
            "a nauseating combination that made my stomach turn. "
            "Each step I took produced a hollow echo that seemed to "
            "reverberate through the entire abandoned wing."
        ),
        "source_site": "example.com",
    }


@pytest.fixture
def sample_material():
    """測試用的結構化素材。"""
    return {
        "id": "",
        "source_url": "https://example.com/test",
        "source_title": "Test Story",
        "captured_date": "2026-03-27",
        "theme": "eerie-scene",
        "core_concept": "廢棄醫院走廊中，閃爍的日光燈照亮無盡長廊",
        "visual_elements": [
            "閃爍日光燈", "生鏽推車", "破損磁磚",
            "傾斜手術燈", "長廊陰影"
        ],
        "mood_keywords": [
            "abandoned", "clinical horror", "decay", "isolation", "dread"
        ],
        "color_palette_hint": [
            "desaturated green", "rust orange", "cold blue shadow"
        ],
        "composition_hint": "低角度仰視手術燈，強調壓迫感",
        "potential_subjects": [
            "endless hospital corridor with flickering lights",
            "rusted surgical equipment in abandoned room"
        ],
        "original_excerpt": "The corridor stretched endlessly...",
        "quality_score": None,
        "used_count": 0,
        "last_used": None,
    }


@pytest.fixture
def tmp_source_lib(tmp_path):
    """建立臨時 source-library 目錄（不影響真實資料）。"""
    lib = tmp_path / "source-library"
    for theme in ["tech-abstract", "eerie-scene", "creature-design", "clawclaw-portrait"]:
        (lib / theme).mkdir(parents=True)
    # 空 index
    index = {
        "version": "1.0",
        "topics": {
            t: {"display_name": t, "materials": [], "total_count": 0}
            for t in ["tech-abstract", "eerie-scene", "creature-design", "clawclaw-portrait"]
        }
    }
    with open(lib / "_index.json", "w") as f:
        json.dump(index, f)
    return lib
