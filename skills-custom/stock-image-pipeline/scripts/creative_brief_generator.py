"""
Stage 0: 創意素材討論會（Creative Brief Session）

用途:
  - 每日 07:00 自動觸發（或 LXYA 手動觸發）
  - 從素材庫抽取今日主題素材
  - 雙 Agent 對話（Creative Director + Visual Artist）產出創意簡報
  - 產出 brief_{date}.json 供 Stage 2 提示詞生成使用

設計原則:
  - Stage 0 失敗永遠不阻斷 Pipeline，最差退化為模板模式
  - 素材選取避免短期重複（依 _index.json 的 used_count / last_used）
  - 對話輪次上限 4 輪，時間上限 1200 秒
  - 完整對話紀錄寫入 discussion_{date}.md
"""

import json
import time
import random
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# --- 相對路徑解析 ---
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_ROOT / "config"
SOURCE_LIBRARY_DIR = CONFIG_DIR / "source-library"
INDEX_FILE = SOURCE_LIBRARY_DIR / "_index.json"


class CreativeBriefError(Exception):
    """創意簡報產生失敗"""
    pass


class CreativeBriefGenerator:
    """
    Stage 0: 創意素材討論會。

    使用方式:
        generator = CreativeBriefGenerator(workspace_base="~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        result = generator.run(date_str="2026-03-28", theme_override=None)
        # result = {"brief_path": "...", "discussion_path": "...", "status": "complete"|"partial"|"fallback"}
    """

    def __init__(self, workspace_base: Optional[str] = None):
        """
        初始化。

        Args:
            workspace_base: 工作區根目錄。若為 None，從 schedule.json 讀取。
        """
        self._schedule_config = self._load_json(CONFIG_DIR / "schedule.json")
        self._topics_config = self._load_json(CONFIG_DIR / "topics.json")

        # 工作區路徑
        if workspace_base is None:
            ws = self._schedule_config.get("workspace", {})
            workspace_base = ws.get("base_path", "~/.openclaw/workspace/skills-custom/stock-image-pipeline")
        self._workspace = Path(workspace_base).expanduser()
        self._briefs_dir = self._workspace / self._schedule_config.get("workspace", {}).get("briefs_dir", "briefs")

        # 對話配置
        brief_config = self._schedule_config.get("creative_brief_session", {})
        self._max_rounds = brief_config.get("max_discussion_rounds", 4)
        self._max_time_sec = brief_config.get("max_discussion_time_sec", 1200)
        self._retry_on_api = brief_config.get("retry_on_api_failure", 2)
        self._retry_interval = brief_config.get("retry_interval_sec", 30)

        # OpenRouter client（延遲初始化，失敗不影響建構）
        self._or_client = None

    def _load_json(self, path: Path) -> dict:
        """安全載入 JSON，檔案不存在回傳空 dict"""
        if not path.exists():
            logger.warning(f"Config 不存在: {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_json(self, path: Path, data: dict):
        """寫入 JSON 檔案"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _get_openrouter_client(self):
        """延遲初始化 OpenRouter 客戶端"""
        if self._or_client is None:
            import sys
            if str(SCRIPT_DIR) not in sys.path:
                sys.path.insert(0, str(SCRIPT_DIR))
            from openrouter_client import OpenRouterClient
            self._or_client = OpenRouterClient(
                config_path=str(CONFIG_DIR / "schedule.json")
            )
        return self._or_client

    # --- 主題輪替 ---

    def determine_today_theme(self, date_str: str, theme_override: Optional[str] = None) -> str:
        """
        決定今日主題。

        Args:
            date_str: 日期字串 (YYYY-MM-DD)
            theme_override: LXYA 手動指定的主題（優先）

        Returns:
            主題名稱 (e.g. "eerie-scene")
        """
        # 手動覆蓋
        manual = self._schedule_config.get("manual_topic_override")
        if theme_override:
            manual = theme_override
        if manual:
            logger.info(f"使用手動指定主題: {manual}")
            return manual

        # 自動輪替：基於日期的等比例輪替
        rotation = self._schedule_config.get("topic_rotation", {})
        cycle_order = rotation.get("cycle_order", [
            "tech-abstract", "eerie-scene", "clawclaw-portrait", "creature-design"
        ])

        # 用日期轉換為 cycle index
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_of_year = dt.timetuple().tm_yday
        theme_index = day_of_year % len(cycle_order)
        theme = cycle_order[theme_index]

        logger.info(f"自動輪替主題: {theme} (day {day_of_year}, index {theme_index})")
        return theme

    # --- 素材選取 ---

    def select_source_material(self, theme: str) -> Optional[dict]:
        """
        從素材庫選取今日素材。

        選取策略:
        1. 過濾出該主題所有素材
        2. 按 used_count 升序排列（優先未使用或少用的）
        3. 同 used_count 中隨機選取
        4. 若素材庫為空回傳 None

        Args:
            theme: 主題名稱

        Returns:
            素材 dict（含 file, title, content 等）或 None
        """
        index_data = self._load_json(INDEX_FILE)
        topics = index_data.get("topics", {})
        theme_data = topics.get(theme, {})
        theme_materials = theme_data.get("materials", [])

        if not theme_materials:
            logger.warning(f"主題 '{theme}' 素材庫為空")
            return None

        # 按 used_count 排序，取最少使用的一批
        theme_materials.sort(key=lambda m: m.get("used_count", 0))
        min_count = theme_materials[0].get("used_count", 0)
        least_used = [m for m in theme_materials if m.get("used_count", 0) == min_count]

        # 隨機選取
        selected = random.choice(least_used)

        # 讀取素材全文  
        material_path = SOURCE_LIBRARY_DIR / theme / selected["filename"]
        if material_path.exists():
            with open(material_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 分離 YAML frontmatter 和正文
            body = self._extract_body(content)
            selected["content"] = body
        else:
            logger.warning(f"素材檔案不存在: {material_path}")
            selected["content"] = f"[素材檔案遺失: {selected['filename']}]"

        logger.info(f"選取素材: {selected['source_title']} ({selected['filename']}, used_count={selected.get('used_count', 0)})")
        return selected

    def _extract_body(self, content: str) -> str:
        """從含 YAML frontmatter 的 markdown 中提取正文"""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content.strip()

    def _update_material_usage(self, material_file: str, date_str: str):
        """更新素材使用紀錄"""
        index_data = self._load_json(INDEX_FILE)
        topics = index_data.get("topics", {})
        
        # 搜尋所有主題中的素材
        for topic_name, topic_data in topics.items():
            materials = topic_data.get("materials", [])
            for m in materials:
                if m.get("filename") == material_file:
                    m["used_count"] = m.get("used_count", 0) + 1
                    m["last_used"] = date_str
                    index_data["last_updated"] = date_str
                    self._save_json(INDEX_FILE, index_data)
                    logger.info(f"已更新素材使用紀錄: {material_file}")
                    return

        logger.warning(f"未找到素材檔案: {material_file}")

    # --- 雙 Agent 創意對話 ---

    def _build_system_context(self, theme: str, material: dict, insights: list) -> str:
        """建構對話的系統上下文"""
        topic_config = self._topics_config.get("topics", {}).get(theme, {})

        return (
            f"# 今日創意素材討論會\n\n"
            f"## 主題: {topic_config.get('display_name', theme)}\n"
            f"## 素材: {material.get('title', '未知')}\n"
            f"## 素材來源: {material.get('file', '未知')}\n\n"
            f"## 素材全文:\n{material.get('content', '[無內容]')}\n\n"
            f"## 今日目標: 產出 2 張圖的創意概念和視覺指導\n\n"
            f"## 主題預設畫布: {topic_config.get('default_canvas', 'square')}\n"
            f"## 可用替代畫布: {topic_config.get('alt_canvas', 'portrait')}\n"
            f"## LoRA: {topic_config.get('lora', 'none')} (weight: {topic_config.get('lora_weight', 0)})\n"
            f"## 負面提示詞基底: {', '.join(topic_config.get('negative_boost', []))}\n\n"
            + (f"## 過往相關 Insights:\n{''.join(f'- {i}' + chr(10) for i in insights)}\n" if insights else "")
        )

    def _run_dual_agent_dialogue(
        self,
        system_context: str,
        theme: str
    ) -> tuple:
        """
        執行雙 Agent 創意對話。

        Returns:
            (dialogue_messages: list, elapsed_sec: float)
            dialogue_messages 格式: [{"role": "creative_director"|"visual_artist", "content": "..."}]

        Raises:
            CreativeBriefError: API 呼叫失敗（含重試）
        """
        client = self._get_openrouter_client()

        # 角色系統提示
        cd_system = (
            "你是一位資深的創意總監（Creative Director），專精於圖庫攝影的故事性構思。\n"
            "你的職責：\n"
            "1. 從素材中提取核心敘事元素\n"
            "2. 定義情緒基調和故事角度\n"
            "3. 評估商業價值和關鍵詞潛力\n\n"
            "你的回應風格：精準、有洞察力、注重市場差異化。\n"
            "每次發言控制在 200-300 字以內。"
        )

        va_system = (
            "你是一位經驗豐富的視覺藝術家（Visual Artist），專精於 AI 圖像生成技術。\n"
            "你的職責：\n"
            "1. 將敘事元素轉化為具體的構圖方案\n"
            "2. 評估 ComfyUI + Stable Diffusion 的技術可行性\n"
            "3. 建議色彩方案、光影設計、畫布類型\n"
            "4. 預判可能的圖像缺陷並提出預防措施\n\n"
            "你熟悉 SD1.5 模型的能力和限制，知道哪些構圖容易產生畸形。\n"
            "每次發言控制在 200-300 字以內。"
        )

        # 初始訊息：Creative Director 先發言
        cd_opening_prompt = (
            f"以下是今日的素材和主題背景資訊：\n\n{system_context}\n\n"
            "請閱讀素材後，提出 3 個不同的故事角度。每個角度包含：\n"
            "1. 核心場景描述（一句話）\n"
            "2. 情緒關鍵詞（3-5 個）\n"
            "3. 為什麼這個角度有商業價值\n\n"
            "請以繁體中文回應。"
        )

        dialogue = []
        start_time = time.time()

        # Round 1: Creative Director 提出 3 個角度
        logger.info("Stage 0 對話 Round 1: Creative Director 提案")
        cd_messages = [
            {"role": "system", "content": cd_system},
            {"role": "user", "content": cd_opening_prompt}
        ]
        cd_response = client.chat(messages=cd_messages, temperature=0.8, max_tokens=1500)
        dialogue.append({"role": "creative_director", "round": 1, "content": cd_response})

        if time.time() - start_time > self._max_time_sec:
            return dialogue, time.time() - start_time

        # Round 2: Visual Artist 對每個角度回應可行性
        logger.info("Stage 0 對話 Round 2: Visual Artist 可行性評估")
        va_prompt = (
            f"以下是今日主題背景：\n{system_context}\n\n"
            f"以下是創意總監提出的 3 個故事角度：\n\n{cd_response}\n\n"
            "請對每個角度回應：\n"
            "1. 視覺化可行性評估（SD1.5 + ComfyUI 能否實現？技術風險？）\n"
            "2. 建議的構圖方式和色彩方案\n"
            "3. 推薦的畫布類型（portrait/square/landscape）\n\n"
            "請以繁體中文回應。"
        )
        va_messages = [
            {"role": "system", "content": va_system},
            {"role": "user", "content": va_prompt}
        ]
        va_response = client.chat(messages=va_messages, temperature=0.7, max_tokens=1500)
        dialogue.append({"role": "visual_artist", "round": 2, "content": va_response})

        if time.time() - start_time > self._max_time_sec or len(dialogue) >= self._max_rounds * 2:
            return dialogue, time.time() - start_time

        # Round 3: Creative Director 選定最佳 2 個方案
        logger.info("Stage 0 對話 Round 3: Creative Director 最終選定")
        cd_select_prompt = (
            f"視覺藝術家的可行性評估如下：\n\n{va_response}\n\n"
            "請綜合你的故事構思和藝術家的可行性評估，選定最佳 2 個方案（對應今日 2 張圖）。\n"
            "對每個方案說明：\n"
            "1. 為什麼選這個方案\n"
            "2. 精確的故事概念（1-2 句話描述畫面）\n"
            "3. 最關鍵的情緒關鍵詞\n\n"
            "請以繁體中文回應。"
        )
        cd_messages_r3 = [
            {"role": "system", "content": cd_system},
            {"role": "user", "content": cd_opening_prompt},
            {"role": "assistant", "content": cd_response},
            {"role": "user", "content": cd_select_prompt}
        ]
        cd_select_response = client.chat(messages=cd_messages_r3, temperature=0.6, max_tokens=1200)
        dialogue.append({"role": "creative_director", "round": 3, "content": cd_select_response})

        if time.time() - start_time > self._max_time_sec:
            return dialogue, time.time() - start_time

        # Round 4: Visual Artist 對選定方案產出詳細視覺指導
        logger.info("Stage 0 對話 Round 4: Visual Artist 視覺指導")
        va_detail_prompt = (
            f"創意總監已選定以下 2 個方案：\n\n{cd_select_response}\n\n"
            "請對每個方案產出詳細視覺指導，包含：\n"
            "1. 正面提示詞建議（英文，適合 Stable Diffusion）\n"
            "2. 負面提示詞建議（英文）\n"
            "3. 建議的畫布類型和理由\n"
            "4. LoRA 權重微調建議（是否需要調整預設值）\n"
            "5. 需要特別注意的缺陷預防點\n"
            "6. 構圖方式、色彩方案、光影設計\n\n"
            "請以結構化格式回應，方便程式解析。繁體中文說明，提示詞用英文。"
        )
        va_messages_r4 = [
            {"role": "system", "content": va_system},
            {"role": "user", "content": va_prompt},
            {"role": "assistant", "content": va_response},
            {"role": "user", "content": va_detail_prompt}
        ]
        va_detail_response = client.chat(messages=va_messages_r4, temperature=0.5, max_tokens=2048)
        dialogue.append({"role": "visual_artist", "round": 4, "content": va_detail_response})

        elapsed = time.time() - start_time
        logger.info(f"Stage 0 對話完成，共 {len(dialogue)} 則，耗時 {elapsed:.0f}s")
        return dialogue, elapsed

    # --- 簡報解析與產出 ---

    def _parse_brief_from_dialogue(
        self,
        dialogue: list,
        theme: str,
        material: dict,
        date_str: str
    ) -> dict:
        """
        從對話紀錄中提取結構化創意簡報。

        使用 OpenRouter JSON 模式解析 Visual Artist 的最終視覺指導。

        Args:
            dialogue: 對話紀錄
            theme: 主題
            material: 素材
            date_str: 日期

        Returns:
            brief dict（完整的 brief_{date}.json 格式）
        """
        # 找到最後一則 Visual Artist 的回應（詳細視覺指導）
        va_final = None
        cd_selection = None
        for msg in reversed(dialogue):
            if msg["role"] == "visual_artist" and va_final is None:
                va_final = msg["content"]
            if msg["role"] == "creative_director" and cd_selection is None:
                cd_selection = msg["content"]
            if va_final and cd_selection:
                break

        if not va_final:
            logger.warning("對話中找不到 Visual Artist 最終回應，使用空白簡報")
            return self._build_fallback_brief(theme, material, date_str, reason="no_va_response")

        # 用 OpenRouter JSON 模式解析視覺指導
        try:
            client = self._get_openrouter_client()
            topic_config = self._topics_config.get("topics", {}).get(theme, {})

            parse_prompt = (
                "請從以下創意對話中提取結構化的創意簡報。\n\n"
                f"## 創意總監選定方案:\n{cd_selection}\n\n"
                f"## 視覺藝術家詳細指導:\n{va_final}\n\n"
                f"## 主題預設畫布: {topic_config.get('default_canvas', 'square')}\n"
                f"## 可用替代畫布: {topic_config.get('alt_canvas', 'portrait')}\n\n"
                "請輸出 JSON 格式，包含 2 張圖的資訊。每張圖的結構如下：\n"
                '{\n'
                '  "images": [\n'
                '    {\n'
                '      "image_id": "brief-001",\n'
                '      "concept": "畫面概念描述（繁體中文）",\n'
                '      "mood_keywords": ["keyword1", "keyword2", ...],\n'
                '      "visual_direction": {\n'
                '        "composition": "構圖描述（繁體中文）",\n'
                '        "color_palette": "色彩方案（繁體中文）",\n'
                '        "lighting": "光影設計（繁體中文）",\n'
                '        "canvas_type": "portrait|square|landscape",\n'
                '        "positive_prompt_hints": ["english prompt 1", ...],\n'
                '        "negative_prompt_hints": ["english negative 1", ...],\n'
                '        "lora_weight_adjustment": null 或 {"lora_name": 0.1},\n'
                '        "defect_warnings": ["注意事項1", ...]\n'
                '      }\n'
                '    }\n'
                '  ]\n'
                '}\n\n'
                "嚴格按照此 JSON 結構輸出，不要加其他說明文字。"
            )

            parsed = client.chat_json(
                messages=[{"role": "user", "content": parse_prompt}],
                max_tokens=2048,
                temperature=0.2
            )

            # 確認解析結果包含 images
            images = parsed.get("images", [])
            if not images or "raw" in parsed:
                logger.warning("JSON 解析結果不完整，嘗試手動建構")
                return self._build_fallback_brief(theme, material, date_str, reason="parse_incomplete")

            # 補齊 image_id
            for i, img in enumerate(images):
                if "image_id" not in img:
                    img["image_id"] = f"brief-{i+1:03d}"

        except Exception as e:
            logger.error(f"解析創意簡報失敗: {e}")
            return self._build_fallback_brief(theme, material, date_str, reason=str(e))

        # 組裝完整 brief
        brief = {
            "date": date_str,
            "theme": theme,
            "source_material": {
                "file": material.get("file", ""),
                "title": material.get("title", "")
            },
            "images": images,
            "discussion_log": f"briefs/discussion_{date_str}.md",
            "total_discussion_time_sec": None,  # 由呼叫方填入
            "openrouter_cost": None,  # 由呼叫方填入
            "partial": False,
            "fallback": False
        }
        return brief

    def _build_fallback_brief(
        self,
        theme: str,
        material: Optional[dict],
        date_str: str,
        reason: str = "unknown"
    ) -> dict:
        """
        建構退化模式的簡報骨架。

        Stage 2 收到此簡報後會自動退化為模板模式補足缺失的視覺指導。
        """
        topic_config = self._topics_config.get("topics", {}).get(theme, {})
        default_canvas = topic_config.get("default_canvas", "square")

        fallback_images = []
        for i in range(2):
            fallback_images.append({
                "image_id": f"brief-{i+1:03d}",
                "concept": None,
                "mood_keywords": [],
                "visual_direction": {
                    "composition": None,
                    "color_palette": None,
                    "lighting": None,
                    "canvas_type": default_canvas,
                    "positive_prompt_hints": [],
                    "negative_prompt_hints": [],
                    "lora_weight_adjustment": None,
                    "defect_warnings": []
                }
            })

        brief = {
            "date": date_str,
            "theme": theme,
            "source_material": {
                "file": material.get("file", "") if material else "",
                "title": material.get("title", "") if material else ""
            },
            "images": fallback_images,
            "discussion_log": None,
            "total_discussion_time_sec": 0,
            "openrouter_cost": 0,
            "partial": False,
            "fallback": True,
            "fallback_reason": reason
        }

        logger.info(f"已建構退化模式簡報 (原因: {reason})")
        return brief

    def _save_discussion_log(self, dialogue: list, date_str: str, theme: str, material: dict) -> str:
        """儲存完整對話紀錄為 markdown"""
        log_path = self._briefs_dir / f"discussion_{date_str}.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        role_labels = {
            "creative_director": "Creative Director",
            "visual_artist": "Visual Artist"
        }

        lines = [
            f"# 創意素材討論會紀錄 — {date_str}\n",
            f"- **主題**: {theme}\n",
            f"- **素材**: {material.get('title', '未知')} ({material.get('file', '未知')})\n",
            f"- **對話輪次**: {len(dialogue)}\n",
            "---\n"
        ]

        for msg in dialogue:
            role = role_labels.get(msg["role"], msg["role"])
            round_num = msg.get("round", "?")
            lines.append(f"\n## Round {round_num} — {role}\n")
            lines.append(msg["content"])
            lines.append("\n")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"對話紀錄已儲存: {log_path}")
        return str(log_path)

    # --- 查詢過往 insights（簡化版） ---

    def _load_relevant_insights(self, theme: str) -> list:
        """
        載入與主題相關的過往 insights。

        目前為簡化版：掃描 memory/insights/ 中含有主題關鍵字的檔案標題。
        完整版將在 Phase 8（memory 模組）實作後補完。

        Returns:
            insight 摘要字串列表
        """
        # insights 目錄（可能還不存在）
        insights_dir = self._workspace / "memory" / "insights"
        if not insights_dir.exists():
            return []

        relevant = []
        try:
            for f in sorted(insights_dir.glob("*.md"), reverse=True)[:20]:
                content = f.read_text(encoding="utf-8")
                # 簡單的關鍵字匹配
                if theme in content.lower() or theme.replace("-", " ") in content.lower():
                    # 取第一行作為摘要
                    first_line = content.split("\n")[0].strip("# ").strip()
                    if first_line:
                        relevant.append(first_line)
                if len(relevant) >= 5:
                    break
        except Exception as e:
            logger.warning(f"載入 insights 失敗: {e}")

        return relevant

    # --- 主執行流程 ---

    def run(
        self,
        date_str: Optional[str] = None,
        theme_override: Optional[str] = None,
        manual_brief: Optional[dict] = None
    ) -> dict:
        """
        執行 Stage 0 完整流程。

        Args:
            date_str: 日期 (YYYY-MM-DD)，預設今天
            theme_override: LXYA 手動指定主題
            manual_brief: LXYA 直接指定的簡報內容（跳過 Stage 0 對話）

        Returns:
            {
                "brief_path": str,       # 簡報檔案路徑
                "discussion_path": str,   # 對話紀錄路徑（若有）
                "status": str,            # "complete" | "partial" | "fallback"
                "theme": str,
                "brief": dict             # 完整簡報內容
            }
        """
        if date_str is None:
            date_str = date.today().isoformat()

        logger.info(f"=== Stage 0: 創意素材討論會 ({date_str}) ===")

        # 0.1 決定今日主題
        theme = self.determine_today_theme(date_str, theme_override)
        logger.info(f"今日主題: {theme}")

        # 0.1b LXYA 手動指定簡報 → 直接使用
        if manual_brief:
            return self._handle_manual_brief(manual_brief, theme, date_str)

        # 0.2 從素材庫選取素材
        material = self.select_source_material(theme)

        # 失敗情境 3: 素材庫為空
        if material is None:
            logger.warning(f"主題 '{theme}' 素材庫為空，跳過 Stage 0，退化為模板模式")
            brief = self._build_fallback_brief(theme, None, date_str, reason=f"主題 {theme} 素材庫為空，請 LXYA 補充")
            brief_path = self._save_brief(brief, date_str)
            return {
                "brief_path": brief_path,
                "discussion_path": None,
                "status": "fallback",
                "theme": theme,
                "brief": brief
            }

        # 0.3 載入相關 insights
        insights = self._load_relevant_insights(theme)

        # 0.3b 執行雙 Agent 對話
        system_context = self._build_system_context(theme, material, insights)

        dialogue = None
        elapsed = 0
        api_error = None

        for attempt in range(self._retry_on_api + 1):
            try:
                dialogue, elapsed = self._run_dual_agent_dialogue(system_context, theme)
                api_error = None
                break
            except Exception as e:
                api_error = str(e)
                logger.warning(f"Stage 0 對話失敗 (attempt {attempt + 1}): {e}")
                if attempt < self._retry_on_api:
                    time.sleep(self._retry_interval)

        # 失敗情境 1: API 連線失敗
        if api_error:
            logger.error(f"Stage 0 API 連線失敗，退化為模板模式: {api_error}")
            brief = self._build_fallback_brief(theme, material, date_str, reason=f"API 失敗: {api_error}")
            brief_path = self._save_brief(brief, date_str)
            self._update_material_usage(material["file"], date_str)
            return {
                "brief_path": brief_path,
                "discussion_path": None,
                "status": "fallback",
                "theme": theme,
                "brief": brief
            }

        # 0.4 解析對話為結構化簡報
        brief = self._parse_brief_from_dialogue(dialogue, theme, material, date_str)
        brief["total_discussion_time_sec"] = round(elapsed)

        # 取得 OpenRouter 成本
        try:
            client = self._get_openrouter_client()
            brief["openrouter_cost"] = client.session_stats.get("estimated_cost", 0)
        except Exception:
            brief["openrouter_cost"] = 0

        # 失敗情境 2: 部分簡報
        complete_images = [img for img in brief.get("images", [])
                          if img.get("concept") is not None]

        if len(complete_images) < 2 and len(complete_images) >= 1:
            brief["partial"] = True
            status = "partial"
            logger.warning("Stage 0 簡報不完整，部分圖片將退化為模板模式")
        elif len(complete_images) == 0 and not brief.get("fallback"):
            brief["fallback"] = True
            brief["fallback_reason"] = "對話產出無法解析為有效簡報"
            status = "fallback"
        else:
            status = "complete"

        # 儲存
        discussion_path = self._save_discussion_log(dialogue, date_str, theme, material)
        brief_path = self._save_brief(brief, date_str)
        self._update_material_usage(material["file"], date_str)

        logger.info(f"Stage 0 完成: status={status}, brief={brief_path}")

        return {
            "brief_path": brief_path,
            "discussion_path": discussion_path,
            "status": status,
            "theme": theme,
            "brief": brief
        }

    def _handle_manual_brief(self, manual_brief: dict, theme: str, date_str: str) -> dict:
        """
        處理 LXYA 手動指定的簡報。
        失敗情境 4: 補齊缺失欄位。
        """
        topic_config = self._topics_config.get("topics", {}).get(theme, {})

        # 確保基本結構
        if "date" not in manual_brief:
            manual_brief["date"] = date_str
        if "theme" not in manual_brief:
            manual_brief["theme"] = theme

        # 補齊 images 中的缺失欄位
        for img in manual_brief.get("images", []):
            vd = img.get("visual_direction", {})
            if not vd.get("canvas_type"):
                vd["canvas_type"] = topic_config.get("default_canvas", "square")
            # 將缺失的欄位設為 None（Stage 2 會退化為模板模式補足）
            for key in ["composition", "color_palette", "lighting"]:
                if key not in vd:
                    vd[key] = None
            for key in ["positive_prompt_hints", "negative_prompt_hints", "defect_warnings"]:
                if key not in vd:
                    vd[key] = []
            if "lora_weight_adjustment" not in vd:
                vd["lora_weight_adjustment"] = None
            img["visual_direction"] = vd

        manual_brief["partial"] = False
        manual_brief["fallback"] = False
        manual_brief["discussion_log"] = None
        manual_brief["total_discussion_time_sec"] = 0
        manual_brief["openrouter_cost"] = 0

        brief_path = self._save_brief(manual_brief, date_str)
        logger.info(f"已儲存 LXYA 手動指定簡報: {brief_path}")

        return {
            "brief_path": brief_path,
            "discussion_path": None,
            "status": "complete",
            "theme": theme,
            "brief": manual_brief
        }

    def _save_brief(self, brief: dict, date_str: str) -> str:
        """儲存簡報 JSON"""
        brief_path = self._briefs_dir / f"brief_{date_str}.json"
        self._save_json(brief_path, brief)
        logger.info(f"簡報已儲存: {brief_path}")
        return str(brief_path)

