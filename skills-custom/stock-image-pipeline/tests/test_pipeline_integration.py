"""
test_pipeline_integration.py — Pipeline 整合測試

驗證模組間的介面一致性，不需要外部服務。
主要測試 observation 格式、config 讀取、path 解析等。
"""

import json
from pathlib import Path

import pytest


class TestObservationFormat:
    """各模組 observation 格式一致性。"""

    def test_prompt_generator_observation(self):
        from prompt_generator import PromptGenerator
        pg = PromptGenerator()
        obs = pg.observation
        assert isinstance(obs, dict)
        # 應包含預期的 key
        expected_keys = ["memory_reads_count", "prompt_source", "insight_applied"]
        for key in expected_keys:
            assert key in obs, f"prompt_generator observation 缺少 {key}"

    def test_image_refiner_observation(self):
        from image_refiner import ImageRefiner
        ir = ImageRefiner()
        obs = ir.observation
        assert isinstance(obs, dict)
        expected_keys = [
            "comfyui_calls", "openrouter_eval_calls",
            "total_images_generated", "upscale_calls"
        ]
        for key in expected_keys:
            assert key in obs, f"image_refiner observation 缺少 {key}"

    def test_defect_detector_observation(self):
        from defect_detector import DefectDetector
        dd = DefectDetector()
        obs = dd.observation
        assert isinstance(obs, dict)
        expected_keys = [
            "layer1_rejects", "layer2_calls", "layer3_calls",
            "pass_count", "retry_count", "discard_count"
        ]
        for key in expected_keys:
            assert key in obs, f"defect_detector observation 缺少 {key}"


class TestMemoryObserverCollect:
    """MemoryObserver 的收集與組裝。"""

    def test_collect_and_retrieve(self):
        from memory_observer import MemoryObserver
        obs = MemoryObserver()
        obs.reset()

        obs.collect("prompt_generator", {"prompt_source": "creative_brief"})
        obs.collect("image_refiner", {"comfyui_calls": 15})
        obs.collect_pipeline_meta({"theme": "tech-abstract", "total_produced": 2})

        result = obs.get_observations()
        assert "prompt_generator" in result
        assert "image_refiner" in result
        assert "pipeline_meta" in result
        assert result["pipeline_meta"]["theme"] == "tech-abstract"

    def test_reset_clears(self):
        from memory_observer import MemoryObserver
        obs = MemoryObserver()
        obs.collect("test", {"data": 1})
        obs.reset()
        assert obs.get_observations() == {}

    def test_save_daily_observation(self, tmp_path):
        from memory_observer import MemoryObserver
        obs = MemoryObserver()
        obs._initialized = True
        obs._memory_base = tmp_path / "memory"
        obs._schedule_config = {}

        obs.collect("prompt_generator", {"prompt_source": "template_fallback"})
        obs.collect_pipeline_meta({"theme": "eerie-scene", "total_produced": 1})

        path = obs.save_daily_observation("2026-03-27")
        assert path
        assert Path(path).exists()

        with open(path) as f:
            data = json.load(f)
        assert data["date"] == "2026-03-27"
        assert "stages" in data
        assert "summary" in data

    def test_save_daily_summary_md(self, tmp_path):
        from memory_observer import MemoryObserver
        obs = MemoryObserver()
        obs._initialized = True
        obs._memory_base = tmp_path / "memory"
        obs._schedule_config = {}

        obs.collect_pipeline_meta({"theme": "tech-abstract", "total_produced": 2})
        path = obs.save_daily_summary_md("2026-03-27")
        assert path
        content = Path(path).read_text()
        assert "---" in content  # YAML frontmatter
        assert "tech-abstract" in content


class TestMetricsCollector:
    """MetricsCollector 基礎功能。"""

    def test_get_latest_stats_empty(self, tmp_path):
        from metrics_collector import MetricsCollector
        mc = MetricsCollector()
        mc._initialized = True
        mc._memory_base = tmp_path / "memory"
        mc._schedule_config = {}

        result = mc.get_latest_stats()
        assert result["available_days"] == 0

    def test_weekly_report_insufficient_data(self, tmp_path):
        from metrics_collector import MetricsCollector
        mc = MetricsCollector()
        mc._initialized = True
        mc._memory_base = tmp_path / "memory"
        (tmp_path / "memory" / "metrics").mkdir(parents=True)
        mc._schedule_config = {}

        result = mc.generate_weekly_report()
        assert result["status"] == "insufficient_data"


class TestExperienceDistiller:
    """ExperienceDistiller 基礎功能。"""

    def test_aar_no_insights_when_empty(self, tmp_path):
        from experience_distiller import ExperienceDistiller
        ed = ExperienceDistiller()
        ed._initialized = True
        ed._memory_base = tmp_path / "memory"
        (tmp_path / "memory" / "metrics").mkdir(parents=True)
        (tmp_path / "memory" / "insights").mkdir(parents=True)

        result = ed.run_aar(today_observation={}, date_str="2026-03-27")
        assert result["insights_generated"] == 0

    def test_weekly_analysis_insufficient(self, tmp_path):
        from experience_distiller import ExperienceDistiller
        ed = ExperienceDistiller()
        ed._initialized = True
        ed._memory_base = tmp_path / "memory"
        (tmp_path / "memory" / "metrics").mkdir(parents=True)

        result = ed.run_weekly_analysis()
        assert result["status"] == "insufficient_data"


class TestPathResolution:
    """所有模組的 path 解析一致性。"""

    def test_all_modules_use_resolve_parent(self):
        """每個模組都應使用 Path(__file__).resolve().parent 模式。"""
        scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
        for f in scripts_dir.glob("*.py"):
            content = f.read_text()
            if "CONFIG_DIR" in content:
                assert "Path(__file__).resolve().parent" in content, (
                    f"{f.name} 的 CONFIG_DIR 未使用 resolve().parent 模式"
                )
