"""
test_material_curator.py — 素材搜集整理工具測試

分為三層:
  1. 離線測試 (不需網路/Ollama) — 分類、去重、存檔、索引
  2. Ollama 測試 (需本地 Ollama) — 萃取
  3. 網路測試 (需網路) — 爬取

標記:
  - 無標記: 離線測試，CI 可跑
  - @pytest.mark.ollama: 需要 Ollama 服務
  - @pytest.mark.network: 需要網路
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from material_curator import MaterialCurator, THEME_KEYWORDS, MATERIAL_TEMPLATE


# ==================================================================
# 離線測試
# ==================================================================
class TestClassifier:
    """主題分類測試。"""

    def test_classify_eerie_keywords(self):
        curator = MaterialCurator()
        material = {
            "core_concept": "abandoned hospital corridor",
            "original_excerpt": "dark shadows in the haunted asylum",
            "mood_keywords": ["horror", "creepy", "decay"],
            "visual_elements": [],
        }
        assert curator._classify_by_keywords(material) == "eerie-scene"

    def test_classify_tech_keywords(self):
        curator = MaterialCurator()
        material = {
            "core_concept": "quantum data network visualization",
            "original_excerpt": "digital algorithm processing",
            "mood_keywords": ["futuristic", "abstract"],
            "visual_elements": ["neon", "circuit"],
        }
        assert curator._classify_by_keywords(material) == "tech-abstract"

    def test_classify_creature_keywords(self):
        curator = MaterialCurator()
        material = {
            "core_concept": "biomechanical dragon creature",
            "original_excerpt": "tentacle monster mutation",
            "mood_keywords": [],
            "visual_elements": ["creature", "alien"],
        }
        assert curator._classify_by_keywords(material) == "creature-design"

    def test_classify_portrait_keywords(self):
        curator = MaterialCurator()
        material = {
            "core_concept": "cinematic portrait with dramatic lighting",
            "original_excerpt": "emotional expression closeup",
            "mood_keywords": ["painterly"],
            "visual_elements": [],
        }
        assert curator._classify_by_keywords(material) == "clawclaw-portrait"

    def test_classify_empty_defaults_to_tech(self):
        curator = MaterialCurator()
        material = {
            "core_concept": "something generic",
            "original_excerpt": "",
            "mood_keywords": [],
            "visual_elements": [],
        }
        result = curator._classify_by_keywords(material)
        assert result == "tech-abstract"  # 預設

    def test_classify_preserves_existing_theme(self):
        curator = MaterialCurator()
        material = {"theme": "creature-design"}
        assert curator.classify(material) == "creature-design"


class TestDedup:
    """去重測試。"""

    def test_no_duplicate_in_empty_dir(self, tmp_source_lib, sample_material):
        curator = MaterialCurator()
        # 暫時替換 SOURCE_LIB_DIR
        import material_curator
        original = material_curator.SOURCE_LIB_DIR
        material_curator.SOURCE_LIB_DIR = tmp_source_lib
        try:
            result = curator.dedup(sample_material, "eerie-scene")
            assert result["is_duplicate"] is False
            assert result["similarity"] == 0.0
        finally:
            material_curator.SOURCE_LIB_DIR = original

    def test_duplicate_detected(self, tmp_source_lib, sample_material):
        curator = MaterialCurator()
        import material_curator
        original = material_curator.SOURCE_LIB_DIR
        material_curator.SOURCE_LIB_DIR = tmp_source_lib
        try:
            # 先存一份
            theme_dir = tmp_source_lib / "eerie-scene"
            existing = dict(sample_material)
            existing["id"] = "eerie-001"
            with open(theme_dir / "eerie-001.json", "w") as f:
                json.dump(existing, f)

            # 再去重 — 相同 core_concept 應被偵測
            result = curator.dedup(sample_material, "eerie-scene")
            assert result["is_duplicate"] is True
            assert result["similarity"] >= 0.7
            assert result["similar_to"] == "eerie-001"
        finally:
            material_curator.SOURCE_LIB_DIR = original

    def test_different_concept_not_duplicate(self, tmp_source_lib, sample_material):
        curator = MaterialCurator()
        import material_curator
        original = material_curator.SOURCE_LIB_DIR
        material_curator.SOURCE_LIB_DIR = tmp_source_lib
        try:
            theme_dir = tmp_source_lib / "eerie-scene"
            existing = dict(sample_material)
            existing["id"] = "eerie-001"
            existing["core_concept"] = "一座燃燒中的摩天大樓從雲層中墜落"
            with open(theme_dir / "eerie-001.json", "w") as f:
                json.dump(existing, f)

            result = curator.dedup(sample_material, "eerie-scene")
            assert result["is_duplicate"] is False
        finally:
            material_curator.SOURCE_LIB_DIR = original


class TestSaveAndIndex:
    """存檔與索引更新測試。"""

    def test_save_creates_file(self, tmp_source_lib, sample_material):
        curator = MaterialCurator()
        import material_curator
        original = material_curator.SOURCE_LIB_DIR
        material_curator.SOURCE_LIB_DIR = tmp_source_lib
        curator._index = {
            "version": "1.0",
            "topics": {
                "eerie-scene": {"display_name": "eerie-scene", "materials": [], "total_count": 0}
            }
        }
        try:
            path = curator.save(sample_material, "eerie-scene")
            assert path
            assert Path(path).exists()

            # 讀取驗證
            with open(path) as f:
                saved = json.load(f)
            assert saved["theme"] == "eerie-scene"
            assert saved["id"].startswith("eerie-")
            assert saved["core_concept"] == sample_material["core_concept"]
        finally:
            material_curator.SOURCE_LIB_DIR = original

    def test_save_updates_index(self, tmp_source_lib, sample_material):
        curator = MaterialCurator()
        import material_curator
        original_lib = material_curator.SOURCE_LIB_DIR
        material_curator.SOURCE_LIB_DIR = tmp_source_lib
        curator._index = {
            "version": "1.0",
            "topics": {
                "eerie-scene": {"display_name": "eerie-scene", "materials": [], "total_count": 0}
            }
        }
        try:
            curator.save(sample_material, "eerie-scene")

            # 重新讀取 index
            with open(tmp_source_lib / "_index.json") as f:
                index = json.load(f)
            topic = index["topics"]["eerie-scene"]
            assert topic["total_count"] == 1
            assert len(topic["materials"]) == 1
            assert topic["materials"][0]["id"].startswith("eerie-")
        finally:
            material_curator.SOURCE_LIB_DIR = original_lib

    def test_id_auto_increment(self, tmp_source_lib, sample_material):
        curator = MaterialCurator()
        import material_curator
        original = material_curator.SOURCE_LIB_DIR
        material_curator.SOURCE_LIB_DIR = tmp_source_lib
        curator._index = {
            "version": "1.0",
            "topics": {
                "eerie-scene": {"display_name": "eerie-scene", "materials": [], "total_count": 0}
            }
        }
        try:
            # 存兩筆
            m1 = dict(sample_material)
            m1["core_concept"] = "概念一"
            curator.save(m1, "eerie-scene")

            m2 = dict(sample_material)
            m2["core_concept"] = "概念二"
            curator.save(m2, "eerie-scene")

            # 檢查 ID 遞增
            files = sorted((tmp_source_lib / "eerie-scene").glob("eerie-*.json"))
            assert len(files) == 2
            assert "eerie-001" in files[0].name
            assert "eerie-002" in files[1].name
        finally:
            material_curator.SOURCE_LIB_DIR = original


class TestRuleBasedExtraction:
    """Ollama 不可用時的 fallback 萃取測試。"""

    def test_fallback_extraction(self, sample_raw_article):
        curator = MaterialCurator()
        material = curator._rule_based_extraction(sample_raw_article, "eerie-scene")

        assert material["theme"] == "eerie-scene"
        assert material["source_url"] == sample_raw_article["url"]
        assert material["source_title"] == sample_raw_article["title"]
        assert material["captured_date"]  # 應有日期
        assert len(material["original_excerpt"]) > 0

    def test_fallback_auto_classifies(self, sample_raw_article):
        curator = MaterialCurator()
        material = curator._rule_based_extraction(sample_raw_article, theme_hint=None)
        # "abandoned" 等關鍵詞應被分類為 eerie-scene
        assert material["theme"] == "eerie-scene"


class TestStats:
    """統計功能測試。"""

    def test_stats_returns_all_themes(self):
        curator = MaterialCurator()
        result = curator.stats()
        for theme in THEME_KEYWORDS:
            assert theme in result
        assert "total" in result


class TestAdapterRegistration:
    """適配器註冊測試。"""

    def test_builtin_scrapers_registered(self):
        curator = MaterialCurator()
        assert "creepypasta.fandom.com" in curator._scrapers
        assert "reddit.com" in curator._scrapers

    def test_custom_scraper_registration(self):
        curator = MaterialCurator()
        mock_fn = MagicMock(return_value=[])
        curator.register_scraper("example.com", mock_fn)
        assert "example.com" in curator._scrapers

    def test_scrape_dispatches_to_adapter(self):
        curator = MaterialCurator()
        mock_fn = MagicMock(return_value=[{"url": "test", "title": "t", "content": "c" * 200, "source_site": "test"}])
        curator._scrapers["test-site.com"] = mock_fn

        # 模擬 URL 匹配
        with patch.object(curator, 'scrape', wraps=curator.scrape):
            result = curator.scrape("https://test-site.com/page", mode="auto")
            mock_fn.assert_called_once()


# ==================================================================
# Ollama 測試（需要本地 Ollama 服務）
# ==================================================================
@pytest.mark.ollama
class TestOllamaExtraction:
    """需要 Ollama qwen3:8b 的萃取測試。"""

    def test_extraction_returns_valid_material(self, sample_raw_article):
        """Ollama 萃取應回傳完整結構。"""
        curator = MaterialCurator()
        material = curator.extract(sample_raw_article, theme_hint="eerie-scene")

        assert material["theme"] == "eerie-scene"
        assert material["core_concept"]  # 非空
        assert len(material["visual_elements"]) > 0
        assert len(material["mood_keywords"]) > 0

    def test_extraction_auto_classifies(self, sample_raw_article):
        """不給 theme_hint 時應自動分類。"""
        curator = MaterialCurator()
        material = curator.extract(sample_raw_article, theme_hint=None)
        assert material["theme"] in THEME_KEYWORDS


# ==================================================================
# 網路測試（需要網路連線）
# ==================================================================
@pytest.mark.network
class TestCreepypastaFandomScraper:
    """Creepypasta Fandom Wiki 爬取測試。"""

    def test_scrape_single_article(self):
        curator = MaterialCurator()
        results = curator.scrape(
            "https://creepypasta.fandom.com/wiki/The_Rake",
            mode="auto"
        )
        assert len(results) >= 1
        assert results[0]["title"]
        assert len(results[0]["content"]) > 200

    def test_scrape_category(self):
        curator = MaterialCurator()
        results = curator.scrape(
            "https://creepypasta.fandom.com/wiki/Category:Monsters",
            max_pages=3
        )
        assert len(results) >= 1
        for r in results:
            assert r["source_site"] == "creepypasta.fandom.com"


@pytest.mark.network
class TestRedditScraper:
    """Reddit r/nosleep 爬取測試。"""

    def test_scrape_subreddit_listing(self):
        curator = MaterialCurator()
        results = curator.scrape(
            "https://www.reddit.com/r/nosleep/top/?t=all",
            max_pages=3
        )
        assert len(results) >= 1
        for r in results:
            assert r["source_site"] == "reddit.com"
            assert len(r["content"]) >= 200
            assert "score" in r

    def test_scrape_filters_deleted_posts(self):
        """已刪除帖子不應出現在結果中。"""
        curator = MaterialCurator()
        results = curator.scrape(
            "https://www.reddit.com/r/nosleep/top/?t=all",
            max_pages=5
        )
        for r in results:
            assert r["content"] not in ("[removed]", "[deleted]")
