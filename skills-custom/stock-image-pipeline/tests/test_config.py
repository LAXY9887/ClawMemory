"""
test_config.py — Config 檔案完整性與一致性測試

驗證:
  - schedule.json / topics.json 格式正確
  - 必要欄位存在
  - 主題名稱在兩個 config 中一致
  - source-library 目錄與 _index.json 對齊
"""

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SOURCE_LIB_DIR = CONFIG_DIR / "source-library"

EXPECTED_THEMES = ["tech-abstract", "eerie-scene", "creature-design", "clawclaw-portrait"]


class TestScheduleConfig:
    """schedule.json 結構驗證。"""

    def test_file_exists(self):
        assert (CONFIG_DIR / "schedule.json").exists()

    def test_valid_json(self, schedule_config):
        assert isinstance(schedule_config, dict)

    def test_daily_target(self, schedule_config):
        assert "daily_target" in schedule_config
        assert isinstance(schedule_config["daily_target"], int)
        assert schedule_config["daily_target"] > 0

    def test_retry_budget(self, schedule_config):
        assert "max_retries_per_image" in schedule_config
        assert "max_daily_retries" in schedule_config
        assert schedule_config["max_daily_retries"] >= schedule_config["max_retries_per_image"]

    def test_openrouter_config(self, schedule_config):
        or_cfg = schedule_config.get("openrouter", {})
        assert "model" in or_cfg, "openrouter.model 必須設定"

    def test_ollama_config(self, schedule_config):
        ollama = schedule_config.get("ollama", {})
        assert "model" in ollama
        assert "host" in ollama

    def test_workspace_paths(self, schedule_config):
        ws = schedule_config.get("workspace", {})
        required_dirs = ["pending_dir", "uploaded_dir", "rejected_dir", "briefs_dir", "temp_dir"]
        for d in required_dirs:
            assert d in ws, f"workspace.{d} 缺失"

    def test_dreamstime_ftp(self, schedule_config):
        ftp = schedule_config.get("dreamstime_ftp", {})
        assert "host" in ftp
        assert "port" in ftp
        # 密碼不應出現在 config 中
        assert "password" not in ftp
        assert "pass" not in ftp

    def test_topic_rotation(self, schedule_config):
        rotation = schedule_config.get("topic_rotation", {})
        cycle = rotation.get("cycle_order", [])
        assert len(cycle) == 4
        for theme in EXPECTED_THEMES:
            assert theme in cycle, f"topic_rotation 缺少 {theme}"


class TestTopicsConfig:
    """topics.json 結構驗證。"""

    def test_file_exists(self):
        assert (CONFIG_DIR / "topics.json").exists()

    def test_valid_json(self, topics_config):
        assert isinstance(topics_config, dict)

    def test_all_themes_present(self, topics_config):
        topics = topics_config.get("topics", {})
        for theme in EXPECTED_THEMES:
            assert theme in topics, f"topics 缺少 {theme}"

    def test_canvas_types(self, topics_config):
        canvas = topics_config.get("canvas_types", {})
        for ctype in ["square", "portrait", "landscape"]:
            assert ctype in canvas, f"canvas_types 缺少 {ctype}"
            sizes = canvas[ctype]
            assert "initial" in sizes
            assert "refined" in sizes
            assert "final_4x" in sizes
            assert len(sizes["initial"]) == 2
            assert len(sizes["refined"]) == 2

    def test_topic_has_required_fields(self, topics_config):
        required = ["display_name", "default_canvas", "base_cfg", "initial_steps",
                     "refined_steps", "sampler", "negative_boost"]
        for theme_key, theme_data in topics_config.get("topics", {}).items():
            for field in required:
                assert field in theme_data, f"{theme_key} 缺少欄位 {field}"

    def test_quality_thresholds(self, topics_config):
        qt = topics_config.get("quality_thresholds", {})
        assert "pass" in qt
        assert "retry" in qt
        assert qt["pass"] > qt["retry"], "pass 門檻應高於 retry"

    def test_refinement_config(self, topics_config):
        ref = topics_config.get("refinement", {})
        assert ref.get("initial_candidates", 0) > 0
        assert ref.get("refined_candidates", 0) > 0
        denoise = ref.get("denoise_range", [])
        assert len(denoise) > 0
        assert all(0 < d < 1 for d in denoise), "denoise 值應在 0-1 之間"


class TestSourceLibrary:
    """source-library 目錄結構驗證。"""

    def test_directory_exists(self):
        assert SOURCE_LIB_DIR.exists()

    def test_index_exists(self):
        assert (SOURCE_LIB_DIR / "_index.json").exists()

    def test_index_valid_json(self, source_lib_index):
        assert "topics" in source_lib_index

    def test_theme_directories_exist(self):
        for theme in EXPECTED_THEMES:
            theme_dir = SOURCE_LIB_DIR / theme
            assert theme_dir.exists(), f"目錄缺失: source-library/{theme}/"

    def test_themes_consistency(self, schedule_config, topics_config, source_lib_index):
        """三份 config 中的主題名稱必須一致。"""
        schedule_themes = set(schedule_config.get("topic_rotation", {}).get("cycle_order", []))
        topics_themes = set(topics_config.get("topics", {}).keys())
        index_dirs = set(
            d.name for d in SOURCE_LIB_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

        assert schedule_themes == topics_themes, (
            f"schedule vs topics 不一致: {schedule_themes.symmetric_difference(topics_themes)}"
        )
        assert topics_themes == index_dirs, (
            f"topics vs source-library 不一致: {topics_themes.symmetric_difference(index_dirs)}"
        )
