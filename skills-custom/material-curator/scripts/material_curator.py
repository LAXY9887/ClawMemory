"""
material_curator.py — 素材搜集整理工具

獨立於 pipeline 主流程之外，負責：
  1. 爬取指定網站文章
  2. 使用 Ollama qwen3:8b 萃取視覺意象
  3. 自動分類至 4 大主題
  4. 結構化為 source-library JSON
  5. 去重檢查 + 更新索引
  6. 🆕 週一自動爬取功能（每週一 13:00 觸發）

不依賴 pipeline 其他模組（不使用 OpenRouter），僅需 Ollama + requests + BeautifulSoup。

CLI 使用方式:
  python material_curator.py scrape <url> [--theme <theme>] [--max <n>]
  python material_curator.py batch <file_with_urls> [--theme <theme>]
  python material_curator.py add-text <text_or_file> --theme <theme> [--title <title>]
  python material_curator.py list [--theme <theme>]
  python material_curator.py stats
  python material_curator.py export-report
  python material_curator.py auto-crawl-weekly    # 🆕 週一自動爬取
"""

import json
import logging
import re
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse, urljoin

# ---------- path resolution ----------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"


def _load_curator_config() -> dict:
    """載入 curator_config.json。"""
    cfg_path = CONFIG_DIR / "curator_config.json"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_CURATOR_CFG = _load_curator_config()

# output_dir 支援相對路徑（相對於 CONFIG_DIR 解析）或絕對路徑
_output_dir_raw = _CURATOR_CFG.get(
    "output_dir", "../../stock-image-pipeline/config/source-library"
)
_output_path = Path(_output_dir_raw)
if not _output_path.is_absolute():
    _output_path = (CONFIG_DIR / _output_path).resolve()
SOURCE_LIB_DIR = _output_path

logger = logging.getLogger("material_curator")

# ---------- 素材 JSON schema 預設值 ----------
MATERIAL_TEMPLATE = {
    "id": "",
    "source_url": "",
    "source_title": "",
    "captured_date": "",
    "theme": "",
    "core_concept": "",
    "visual_elements": [],
    "mood_keywords": [],
    "color_palette_hint": [],
    "composition_hint": "",
    "potential_subjects": [],
    "original_excerpt": "",
    "quality_score": None,
    "used_count": 0,
    "last_used": None,
}

# ---------- 主題關鍵詞（rule-based 分類輔助） ----------
THEME_KEYWORDS = {
    "tech-abstract": [
        "technology", "data", "algorithm", "digital", "circuit", "network",
        "AI", "quantum", "hologram", "cyber", "neon", "abstract", "geometric",
        "科技", "數據", "演算法", "數位", "電路", "量子", "全息", "抽象",
    ],
    "eerie-scene": [
        "abandoned", "horror", "creepy", "dark", "haunted", "decay", "ruin",
        "fog", "shadow", "ghost", "corridor", "asylum", "cemetery", "ritual",
        "廢墟", "恐怖", "陰森", "黑暗", "鬼", "衰敗", "迷霧", "墓地",
        "SCP", "anomaly", "containment",
    ],
    "creature-design": [
        "creature", "monster", "beast", "alien", "mutation", "tentacle",
        "chimera", "dragon", "demon", "parasite", "organic", "biomechanical",
        "生物", "怪物", "怪獸", "異形", "突變", "觸手", "嵌合體", "龍",
    ],
    "clawclaw-portrait": [
        "portrait", "face", "expression", "lighting", "cinematic", "painterly",
        "emotional", "headshot", "closeup", "dramatic", "rembrandt",
        "肖像", "人像", "表情", "光影", "電影感", "油畫", "特寫",
    ],
}


class MaterialCurator:
    """
    素材搜集、萃取、分類、存檔的獨立工具。
    """

    def __init__(self):
        self._ollama_config = self._load_ollama_config()
        self._index = self._load_index()
        self._scrapers = {}  # site_key → scraper function 的註冊表
        self._register_builtin_scrapers()

    def _register_builtin_scrapers(self):
        """註冊內建的網站適配器。"""
        self._scrapers["creepypasta.fandom.com"] = self._scrape_creepypasta_fandom
        self._scrapers["hackernoon.com"] = self._scrape_hackernoon
        self._scrapers["reddit.com"] = self._scrape_reddit
        self._scrapers["scp-wiki.wikidot.com"] = self._scrape_scp_wiki

    # ==================================================================
    # Config
    # ==================================================================
    def _load_ollama_config(self) -> dict:
        """從 curator_config.json 讀取 Ollama 設定。"""
        default = {"model": "qwen3:8b", "host": "http://localhost:11434"}
        return _CURATOR_CFG.get("ollama", default)

    def _load_index(self) -> dict:
        """載入 source-library/_index.json。"""
        index_path = SOURCE_LIB_DIR / "_index.json"
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"version": "1.0", "topics": {}}

    def _save_index(self):
        """寫回 _index.json。"""
        index_path = SOURCE_LIB_DIR / "_index.json"
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"_index.json 寫入失敗: {e}")

    # ==================================================================
    # ① 爬取 (Scraper)
    # ==================================================================
    def scrape(self, url: str, mode: str = "auto", max_pages: int = 10,
               theme_hint: str = None) -> list:
        """
        爬取入口。根據 URL 自動選擇適配器。

        Args:
            url: 目標 URL
            mode: "auto" | "article" | "listing" | 特定網站 key
            max_pages: 列表模式最多抓幾篇
            theme_hint: 預設主題（可選）

        Returns:
            list of raw content dicts: [{url, title, content, source_site}]
        """
        import requests
        from bs4 import BeautifulSoup

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        # 嘗試匹配已註冊的網站適配器
        for site_key, scraper_fn in self._scrapers.items():
            if site_key in domain:
                logger.info(f"使用 {site_key} 適配器爬取: {url}")
                return scraper_fn(url, max_pages=max_pages)

        # 通用模式
        if mode == "article" or mode == "auto":
            result = self._scrape_generic_article(url)
            if result:
                return [result]

        if mode == "listing":
            return self._scrape_generic_listing(url, max_pages=max_pages)

        logger.warning(f"無法爬取: {url}")
        return []

    def _scrape_generic_article(self, url: str) -> dict:
        """通用單篇文章爬取。"""
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")

            # 移除 script/style
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            # 嘗試找 article 標籤
            article = soup.find("article")
            if article:
                content = article.get_text(separator="\n", strip=True)
            else:
                # fallback: main 或 body
                main = soup.find("main") or soup.find("body")
                content = main.get_text(separator="\n", strip=True) if main else ""

            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

            if not content or len(content) < 100:
                logger.warning(f"內容過短或為空: {url}")
                return None

            return {
                "url": url,
                "title": title,
                "content": content[:10000],  # 限制長度
                "source_site": urlparse(url).netloc,
            }

        except Exception as e:
            logger.error(f"爬取失敗 {url}: {e}")
            return None

    def _scrape_generic_listing(self, url: str, max_pages: int = 10) -> list:
        """通用列表頁爬取：找出所有連結 → 逐篇抓取。"""
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")
            base_domain = urlparse(url).netloc

            # 收集同域連結
            links = set()
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                parsed = urlparse(href)
                if parsed.netloc == base_domain and href != url:
                    # 過濾掉明顯非文章的連結
                    if not any(x in href for x in [
                        "/tag/", "/category/", "/page/", "#", "login",
                        "signup", "search", ".css", ".js", ".png", ".jpg"
                    ]):
                        links.add(href)

            links = list(links)[:max_pages]
            logger.info(f"列表頁找到 {len(links)} 個連結")

            results = []
            for link in links:
                article = self._scrape_generic_article(link)
                if article:
                    results.append(article)
                    logger.info(f"  ✓ {article['title'][:50]}")

            return results

        except Exception as e:
            logger.error(f"列表頁爬取失敗 {url}: {e}")
            return []

    # ------------------------------------------------------------------
    # 網站適配器註冊
    # ------------------------------------------------------------------
    def register_scraper(self, site_key: str, scraper_fn):
        """
        註冊網站適配器。

        用法:
            curator.register_scraper("scp-wiki", my_scp_scraper)
        """
        self._scrapers[site_key] = scraper_fn
        logger.info(f"已註冊適配器: {site_key}")

    # ------------------------------------------------------------------
    # 適配器: Creepypasta Fandom Wiki
    # ------------------------------------------------------------------
    def _scrape_creepypasta_fandom(self, url: str, max_pages: int = 10) -> list:
        """
        Creepypasta Fandom Wiki 適配器。

        支援的 URL 格式:
          - 分類頁: https://creepypasta.fandom.com/wiki/Category:Monsters
                    → 爬取分類下的故事列表，逐篇抓取
          - 單篇:   https://creepypasta.fandom.com/wiki/The_Rake
                    → 直接抓取故事內文

        Fandom Wiki 頁面結構:
          - 分類頁: .category-page__members 下有 .category-page__member-link
          - 故事頁: .mw-parser-output 包含故事正文
          - 標題: #firstHeading 或 h1.page-header__title

        注意: Fandom 使用 Cloudflare 防護，會檢查 TLS 指紋。
              優先使用 curl_cffi（模擬瀏覽器 TLS 指紋）；
              若未安裝則 fallback 到 requests（可能被 403 擋住）。
        """
        from bs4 import BeautifulSoup
        import time

        # 優先使用 curl_cffi 模擬瀏覽器 TLS 指紋繞過 Cloudflare
        try:
            from curl_cffi.requests import Session as CffiSession
            session = CffiSession(impersonate="chrome131")
            logger.info("Creepypasta: 使用 curl_cffi (chrome131 TLS 指紋)")
        except ImportError:
            import requests
            logger.warning(
                "curl_cffi 未安裝，改用 requests（Fandom 可能回傳 403）。"
                "建議執行: pip install curl_cffi"
            )
            session = requests.Session()
            session.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;"
                          "q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://creepypasta.fandom.com/",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            })

        # 判斷是分類頁還是單篇
        is_category = "/Category:" in url

        if not is_category:
            # 單篇故事
            result = self._scrape_creepypasta_article(url, session=session)
            return [result] if result else []

        # ---------- 分類頁: 收集故事連結 ----------
        story_urls = []
        current_url = url

        while current_url and len(story_urls) < max_pages:
            try:
                resp = session.get(current_url, timeout=30)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Fandom 分類頁的故事連結
                # 方式 1: 新版 Fandom — .category-page__member-link
                member_links = soup.select(".category-page__member-link")
                if not member_links:
                    # 方式 2: 舊版 — .mw-category 下的 a 標籤
                    cat_div = soup.find("div", class_="mw-category") or soup.find("div", id="mw-pages")
                    if cat_div:
                        member_links = cat_div.find_all("a", href=True)

                for a in member_links:
                    href = a.get("href", "")
                    if not href:
                        continue
                    # 過濾掉子分類連結、特殊頁面
                    if "/Category:" in href or "/Special:" in href:
                        continue
                    full_url = urljoin("https://creepypasta.fandom.com", href)
                    if full_url not in story_urls:
                        story_urls.append(full_url)
                    if len(story_urls) >= max_pages:
                        break

                # 翻頁: 找 "next page" 連結
                next_link = None
                for a in soup.find_all("a", string=re.compile(r"next|下一頁|Next page", re.I)):
                    next_link = urljoin("https://creepypasta.fandom.com", a["href"])
                    break

                if not next_link:
                    # Fandom 分類的翻頁連結常在 .category-page__pagination
                    pag = soup.select_one(".category-page__pagination-next")
                    if pag and pag.get("href"):
                        next_link = urljoin("https://creepypasta.fandom.com", pag["href"])

                current_url = next_link if next_link and next_link != current_url else None

            except Exception as e:
                logger.error(f"分類頁爬取失敗 {current_url}: {e}")
                break

        logger.info(f"Creepypasta 分類頁收集到 {len(story_urls)} 個故事連結")

        # ---------- 逐篇抓取 ----------
        results = []
        for i, story_url in enumerate(story_urls[:max_pages]):
            logger.info(f"  [{i+1}/{min(len(story_urls), max_pages)}] {story_url}")
            article = self._scrape_creepypasta_article(story_url, session=session)
            if article:
                results.append(article)
                logger.info(f"    ✓ {article['title'][:50]}")
            # 禮貌延遲，避免被封
            time.sleep(1)

        return results

    def _scrape_creepypasta_article(self, url: str, headers: dict = None,
                                     *, session=None) -> dict:
        """抓取 Creepypasta Fandom 單篇故事。"""
        try:
            import requests
            from bs4 import BeautifulSoup

            if session:
                resp = session.get(url, timeout=30)
            else:
                resp = requests.get(url, headers=headers or {}, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 標題
            title = ""
            h1 = soup.select_one("#firstHeading") or soup.select_one("h1.page-header__title")
            if h1:
                title = h1.get_text(strip=True)
            if not title:
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True).split("|")[0].strip()

            # 正文: .mw-parser-output 是 Fandom Wiki 的內文容器
            content_div = soup.select_one(".mw-parser-output")
            if not content_div:
                logger.warning(f"找不到故事正文: {url}")
                return None

            # 移除編輯按鈕、分類標籤、導航元素等噪音
            for noise in content_div.select(
                ".toc, .navbox, .mbox, .ambox, .tmbox, .category, "
                ".printfooter, .mw-editsection, script, style, "
                ".wikia-gallery, .thumb, .noprint"
            ):
                noise.decompose()

            content = content_div.get_text(separator="\n", strip=True)

            if not content or len(content) < 100:
                logger.warning(f"故事內容過短: {url}")
                return None

            return {
                "url": url,
                "title": title,
                "content": content[:10000],
                "source_site": "creepypasta.fandom.com",
            }

        except Exception as e:
            logger.error(f"Creepypasta 文章爬取失敗 {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # 適配器: HackerNoon
    # ------------------------------------------------------------------
    def _scrape_hackernoon(self, url: str, max_pages: int = 10) -> list:
        """
        HackerNoon 適配器。

        支援的 URL 格式:
          - 分類總覽: https://hackernoon.com/c
          - 特定分類: https://hackernoon.com/c/ai
          - 標籤頁:   https://hackernoon.com/tagged/machine-learning
          - 單篇文章: https://hackernoon.com/some-article-title-slug

        HackerNoon 是 SSR 渲染（不需要 JS），使用 requests 即可。
        """
        import requests
        from bs4 import BeautifulSoup
        import time

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;"
                      "q=0.9,*/*;q=0.8",
        }

        # 判斷是列表頁還是單篇
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        is_listing = (
            path in ("", "/c")
            or path.startswith("/c/")
            or path.startswith("/tagged/")
        )

        if not is_listing:
            result = self._scrape_hackernoon_article(url, headers)
            return [result] if result else []

        # ---------- 列表頁: 收集文章連結 ----------
        article_urls = []
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            seen = set()
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # HackerNoon 文章路徑: /long-slug-title 格式
                if (href.startswith("/")
                        and len(href) > 20
                        and href.count("/") == 1
                        and not any(href.startswith(p) for p in
                                    ["/c/", "/c", "/u/", "/tagged/",
                                     "/signup", "/login", "/about",
                                     "/contact", "/privacy", "/terms",
                                     "/settings", "/notifications"])
                        and href not in seen):
                    seen.add(href)
                    article_urls.append(
                        urljoin("https://hackernoon.com", href)
                    )
                    if len(article_urls) >= max_pages:
                        break

        except Exception as e:
            logger.error(f"HackerNoon 列表頁爬取失敗 {url}: {e}")
            return []

        logger.info(f"HackerNoon 列表頁收集到 {len(article_urls)} 個文章連結")

        # ---------- 逐篇抓取 ----------
        results = []
        delay = _CURATOR_CFG.get("scraping", {}).get("polite_delay_seconds", 2)
        for i, article_url in enumerate(article_urls):
            logger.info(
                f"  [{i+1}/{len(article_urls)}] {article_url}"
            )
            article = self._scrape_hackernoon_article(article_url, headers)
            if article:
                results.append(article)
                logger.info(f"    ✓ {article['title'][:60]}")
            if i < len(article_urls) - 1:
                time.sleep(delay)

        return results

    def _scrape_hackernoon_article(self, url: str, headers: dict) -> dict:
        """抓取 HackerNoon 單篇文章。"""
        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 標題: <h1> 或 og:title
            title = ""
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
            if not title:
                og = soup.find("meta", property="og:title")
                if og:
                    title = og.get("content", "")

            # 正文: HackerNoon 用 .markup 類別包裝文章本體;
            #        若找不到則 fallback 到 article > main
            content = ""
            for selector in [".markup", "article", "main"]:
                container = soup.select_one(selector)
                if not container:
                    continue
                # 移除導覽、廣告、側邊欄等噪音
                for noise in container.select(
                    "nav, footer, header, script, style, "
                    ".ad, .sidebar, .related-stories, "
                    ".author-card, .share-buttons, "
                    "[class*='signup'], [class*='newsletter'], "
                    "[class*='cta'], [class*='promo']"
                ):
                    noise.decompose()
                content = container.get_text(separator="\n", strip=True)
                if len(content) > 200:
                    break

            if not content or len(content) < 100:
                logger.warning(f"HackerNoon 文章內容過短: {url}")
                return None

            return {
                "url": url,
                "title": title,
                "content": content[:10000],
                "source_site": "hackernoon.com",
            }

        except Exception as e:
            logger.error(f"HackerNoon 文章爬取失敗 {url}: {e}")
            return None

    # ------------------------------------------------------------------
    # 適配器: Reddit (r/nosleep 等)
    # ------------------------------------------------------------------
    def _scrape_reddit(self, url: str, max_pages: int = 10) -> list:
        """
        Reddit 適配器。使用 Reddit 的 .json API (不需認證)。

        支援的 URL 格式:
          - 子版首頁:  https://www.reddit.com/r/nosleep/
          - 排序:      https://www.reddit.com/r/nosleep/top/?t=all
          - 單篇帖子:  https://www.reddit.com/r/nosleep/comments/xxx/title/

        Reddit .json API:
          - 在任何 Reddit URL 後面加 .json 即可取得 JSON 回應
          - 列表: data.children[].data → {title, selftext, url, score, ...}
          - 有 after cursor 可翻頁
        """
        import requests
        import time

        headers = {
            "User-Agent": "MaterialCurator/1.0 (stock-image-pipeline; educational)"
        }

        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        # 判斷是單篇帖子還是列表
        is_post = "/comments/" in path

        if is_post:
            result = self._scrape_reddit_post(url, headers)
            return [result] if result else []

        # ---------- 子版列表 ----------
        return self._scrape_reddit_listing(url, headers, max_pages)

    def _scrape_reddit_listing(self, url: str, headers: dict,
                                max_pages: int = 10) -> list:
        """
        抓取 Reddit 子版帖子列表。
        """
        import requests
        import time

        parsed = urlparse(url)
        # 構建 .json URL
        base_path = parsed.path.rstrip("/")
        params = dict(x.split("=") for x in parsed.query.split("&") if "=" in x) if parsed.query else {}

        results = []
        after = None
        fetched = 0

        while fetched < max_pages:
            # 構建 API URL
            json_url = f"https://www.reddit.com{base_path}.json"
            api_params = dict(params)
            api_params["limit"] = min(25, max_pages - fetched)
            api_params["raw_json"] = "1"
            if after:
                api_params["after"] = after

            try:
                resp = requests.get(json_url, headers=headers, params=api_params, timeout=30)

                if resp.status_code == 429:
                    # Rate limited
                    logger.warning("Reddit rate limited, 等待 5 秒...")
                    time.sleep(5)
                    continue

                resp.raise_for_status()
                data = resp.json()

                listing = data.get("data", {})
                children = listing.get("children", [])

                if not children:
                    break

                for child in children:
                    post_data = child.get("data", {})

                    # 只要文字帖子 (selftext)，跳過純連結帖
                    selftext = post_data.get("selftext", "")
                    if not selftext or len(selftext) < 200:
                        continue

                    # 跳過被刪除/移除的帖子
                    if selftext in ("[removed]", "[deleted]"):
                        continue

                    title = post_data.get("title", "")
                    permalink = post_data.get("permalink", "")
                    score = post_data.get("score", 0)

                    results.append({
                        "url": f"https://www.reddit.com{permalink}" if permalink else "",
                        "title": title,
                        "content": selftext[:10000],
                        "source_site": "reddit.com",
                        "score": score,  # 額外資訊：投票分數
                    })

                    fetched += 1
                    logger.info(f"  ✓ [score:{score:>5d}] {title[:60]}")

                    if fetched >= max_pages:
                        break

                # 翻頁
                after = listing.get("after")
                if not after:
                    break

                # 禮貌延遲
                time.sleep(2)

            except Exception as e:
                logger.error(f"Reddit 列表爬取失敗: {e}")
                break

        logger.info(f"Reddit 收集到 {len(results)} 篇帖子")
        return results

    def _scrape_reddit_post(self, url: str, headers: dict) -> dict:
        """抓取 Reddit 單篇帖子。"""
        import requests

        try:
            # Reddit 單帖 .json
            json_url = url.rstrip("/") + ".json"
            params = {"raw_json": "1"}

            resp = requests.get(json_url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # 第一個元素是帖子本身
            if not data or not isinstance(data, list) or len(data) < 1:
                return None

            post_data = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
            selftext = post_data.get("selftext", "")
            title = post_data.get("title", "")

            if not selftext or len(selftext) < 100:
                logger.warning(f"帖子內容過短: {url}")
                return None

            if selftext in ("[removed]", "[deleted]"):
                logger.warning(f"帖子已被刪除: {url}")
                return None

            return {
                "url": url,
                "title": title,
                "content": selftext[:10000],
                "source_site": "reddit.com",
                "score": post_data.get("score", 0),
            }

        except Exception as e:
            logger.error(f"Reddit 帖子爬取失敗 {url}: {e}")
            return None

    def _scrape_scp_wiki(self, url: str, max_pages: int = 10) -> list:
        """
        🆕 SCP Wiki 適配器
        
        專門處理 scp-wiki.wikidot.com，適合 creature-design 主題。
        支援 foundation-tales 列表頁和單篇 SCP 條目。
        """
        import requests
        from bs4 import BeautifulSoup
        import time
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        # 判斷是列表頁還是單篇
        parsed = urlparse(url)
        path = parsed.path.lower()
        is_listing = (
            "foundation-tales" in path or 
            "tales" in path or 
            "/hub" in path
        )
        
        if not is_listing:
            # 單篇 SCP 條目
            result = self._scrape_scp_article(url, headers)
            return [result] if result else []
        
        # 列表頁：收集 SCP 連結
        article_urls = []
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # SCP Wiki 的文章連結通常在 .title-column 或 a 標籤中
            seen = set()
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                
                # SCP 連結格式：/scp-xxx 或 /tale-xxx
                if (href.startswith("/scp-") or href.startswith("/tale-") or 
                    (href.startswith("/") and len(href) > 10 and 
                     not any(x in href.lower() for x in 
                             ["edit", "discuss", "history", "print", "user:", "admin"]))):
                    
                    full_url = urljoin("https://scp-wiki.wikidot.com", href)
                    if full_url not in seen:
                        seen.add(full_url)
                        article_urls.append(full_url)
                        if len(article_urls) >= max_pages:
                            break
            
        except Exception as e:
            logger.error(f"SCP Wiki 列表頁爬取失敗 {url}: {e}")
            return []
            
        logger.info(f"SCP Wiki 列表頁收集到 {len(article_urls)} 個條目連結")
        
        # 逐篇抓取
        results = []
        delay = _CURATOR_CFG.get("scraping", {}).get("polite_delay_seconds", 2)
        for i, article_url in enumerate(article_urls):
            logger.info(f"  [{i+1}/{len(article_urls)}] {article_url}")
            article = self._scrape_scp_article(article_url, headers)
            if article:
                results.append(article)
                logger.info(f"    ✓ {article['title'][:60]}")
            if i < len(article_urls) - 1:
                time.sleep(delay)
                
        return results
    
    def _scrape_scp_article(self, url: str, headers: dict) -> dict:
        """抓取 SCP Wiki 單篇條目。"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 標題
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().replace("- SCP Foundation", "").strip()
            
            # SCP Wiki 內容通常在 #page-content
            content = ""
            page_content = soup.find("div", id="page-content")
            if page_content:
                # 移除導航和元素
                for tag in page_content(["script", "style", "noscript", ".footnotes"]):
                    tag.decompose()
                content = page_content.get_text(separator="\n", strip=True)
            else:
                # 回退到通用方法
                main = soup.find("main") or soup.find("body")
                content = main.get_text(separator="\n", strip=True) if main else ""
            
            if not content or len(content) < 100:
                logger.warning(f"SCP Wiki 內容過短: {url}")
                return None
                
            return {
                "url": url,
                "title": title or "SCP Foundation Entry",
                "content": content[:10000],
                "source_site": "scp-wiki.wikidot.com",
            }
            
        except Exception as e:
            logger.error(f"SCP Wiki 條目爬取失敗 {url}: {e}")
            return None

    # ==================================================================
    # ② 萃取 (Extractor) — Ollama
    # ==================================================================
    def extract(self, raw: dict, theme_hint: str = None) -> dict:
        """
        從原始文章萃取視覺意象。

        Args:
            raw: {url, title, content, source_site}
            theme_hint: 預指定主題

        Returns:
            MATERIAL_TEMPLATE 格式的 dict
        """
        content = raw.get("content", "")
        title = raw.get("title", "")

        # 截取前 3000 字給 Ollama（避免超 context）
        excerpt = content[:3000]

        prompt = self._build_extraction_prompt(title, excerpt, theme_hint)
        ollama_result = self._call_ollama(prompt)

        if ollama_result:
            material = self._parse_extraction_result(ollama_result, raw, theme_hint)
        else:
            # Ollama 不可用時的 rule-based fallback
            material = self._rule_based_extraction(raw, theme_hint)

        return material

    def _build_extraction_prompt(self, title: str, content: str,
                                  theme_hint: str = None) -> str:
        """構建萃取 prompt。"""
        theme_instruction = ""
        if theme_hint:
            theme_instruction = f"\n預期主題: {theme_hint}"

        return f"""你是一位創意視覺顧問。以下是一篇文章/故事，請從中萃取可以轉化為 AI 生成圖片的視覺素材。
{theme_instruction}

文章標題: {title}
文章內容:
{content}

請用 JSON 格式回傳以下欄位（所有欄位必填）:
{{
  "core_concept": "一句話描述核心視覺概念（中文）",
  "visual_elements": ["具體可見的視覺元素，5-8 個"],
  "mood_keywords": ["情緒/氛圍關鍵詞，英文，5-8 個"],
  "color_palette_hint": ["色彩提示，英文，3-5 個"],
  "composition_hint": "構圖建議（中文，一句話）",
  "potential_subjects": ["可以直接作為圖片主題的描述，英文，2-3 個"],
  "suggested_theme": "tech-abstract | eerie-scene | creature-design | clawclaw-portrait"
}}

只回傳 JSON，不要其他文字。"""

    def _parse_extraction_result(self, ollama_text: str, raw: dict,
                                  theme_hint: str) -> dict:
        """解析 Ollama 回傳的 JSON。"""
        try:
            # 嘗試從回傳文字中提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', ollama_text)
            if not json_match:
                raise ValueError("無法找到 JSON")

            data = json.loads(json_match.group())

            material = dict(MATERIAL_TEMPLATE)
            material["source_url"] = raw.get("url", "")
            material["source_title"] = raw.get("title", "")
            material["captured_date"] = datetime.now().strftime("%Y-%m-%d")
            material["original_excerpt"] = raw.get("content", "")[:500]

            material["core_concept"] = data.get("core_concept", "")
            material["visual_elements"] = data.get("visual_elements", [])
            material["mood_keywords"] = data.get("mood_keywords", [])
            material["color_palette_hint"] = data.get("color_palette_hint", [])
            material["composition_hint"] = data.get("composition_hint", "")
            material["potential_subjects"] = data.get("potential_subjects", [])

            # 主題判定: theme_hint 優先 > Ollama 建議 > 自動分類
            if theme_hint:
                material["theme"] = theme_hint
            else:
                suggested = data.get("suggested_theme", "")
                if suggested in THEME_KEYWORDS:
                    material["theme"] = suggested
                else:
                    material["theme"] = self._classify_by_keywords(material)

            return material

        except Exception as e:
            logger.warning(f"Ollama 結果解析失敗: {e}")
            return self._rule_based_extraction(raw, theme_hint)

    def _rule_based_extraction(self, raw: dict, theme_hint: str = None) -> dict:
        """Ollama 不可用時的 rule-based fallback 萃取。"""
        content = raw.get("content", "")
        title = raw.get("title", "")

        material = dict(MATERIAL_TEMPLATE)
        material["source_url"] = raw.get("url", "")
        material["source_title"] = title
        material["captured_date"] = datetime.now().strftime("%Y-%m-%d")
        material["original_excerpt"] = content[:500]
        material["core_concept"] = title if title else "（需手動填寫核心概念）"
        material["visual_elements"] = []
        material["mood_keywords"] = []
        material["color_palette_hint"] = []
        material["composition_hint"] = "（需手動補充構圖建議）"
        material["potential_subjects"] = []

        if theme_hint:
            material["theme"] = theme_hint
        else:
            material["theme"] = self._classify_by_keywords(
                {"core_concept": title, "original_excerpt": content[:1000],
                 "mood_keywords": [], "visual_elements": []}
            )

        return material

    # ==================================================================
    # ③ 分類 (Classifier)
    # ==================================================================
    def classify(self, material: dict) -> str:
        """
        判斷素材適合哪個主題。
        已有 theme 欄位時直接回傳，否則用關鍵詞匹配。
        """
        existing = material.get("theme", "")
        if existing and existing in THEME_KEYWORDS:
            return existing
        return self._classify_by_keywords(material)

    def _classify_by_keywords(self, material: dict) -> str:
        """基於關鍵詞的主題分類。"""
        # 合併所有文字欄位
        text_pool = " ".join([
            str(material.get("core_concept", "")),
            str(material.get("original_excerpt", "")),
            " ".join(material.get("mood_keywords", [])),
            " ".join(material.get("visual_elements", [])),
        ]).lower()

        scores = {}
        for theme, keywords in THEME_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_pool)
            scores[theme] = score

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "tech-abstract"  # 無法判斷時預設
        return best

    # ==================================================================
    # ④ 存檔 (Save)
    # ==================================================================
    def save(self, material: dict, theme: str = None) -> str:
        """
        存入 source-library/{theme}/ 並更新 _index.json。

        Returns:
            存檔路徑 (str)
        """
        if theme:
            material["theme"] = theme
        theme = material.get("theme", "tech-abstract")

        # 確保目錄存在
        theme_dir = SOURCE_LIB_DIR / theme
        theme_dir.mkdir(parents=True, exist_ok=True)

        # 生成 ID
        material_id = self._generate_id(theme, material)
        material["id"] = material_id

        # 存檔
        filename = f"{material_id}.json"
        out_path = theme_dir / filename

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(material, f, ensure_ascii=False, indent=2)
            logger.info(f"素材已存檔: {out_path}")
        except Exception as e:
            logger.error(f"存檔失敗: {e}")
            return ""

        # 更新 _index.json
        self._update_index(theme, material_id, filename, material)

        return str(out_path)

    def _generate_id(self, theme: str, material: dict) -> str:
        """生成素材 ID: {theme_prefix}-{序號}。"""
        prefix_map = {
            "tech-abstract": "tech",
            "eerie-scene": "eerie",
            "creature-design": "creature",
            "clawclaw-portrait": "portrait",
        }
        prefix = prefix_map.get(theme, theme[:5])

        # 找出現有最大序號
        theme_dir = SOURCE_LIB_DIR / theme
        existing = list(theme_dir.glob(f"{prefix}-*.json"))
        max_seq = 0
        for f in existing:
            match = re.search(r'-(\d+)\.json$', f.name)
            if match:
                max_seq = max(max_seq, int(match.group(1)))

        return f"{prefix}-{max_seq + 1:03d}"

    def _update_index(self, theme: str, material_id: str, filename: str,
                      material: dict):
        """更新 _index.json。"""
        if "topics" not in self._index:
            self._index["topics"] = {}

        if theme not in self._index["topics"]:
            self._index["topics"][theme] = {
                "display_name": theme,
                "materials": [],
                "total_count": 0,
            }

        topic_data = self._index["topics"][theme]

        # 避免重複
        existing_ids = {m["id"] for m in topic_data.get("materials", [])}
        if material_id not in existing_ids:
            topic_data["materials"].append({
                "id": material_id,
                "filename": filename,
                "source_title": material.get("source_title", ""),
                "core_concept": material.get("core_concept", "")[:80],
                "captured_date": material.get("captured_date", ""),
                "used_count": 0,
                "last_used": None,
            })
            topic_data["total_count"] = len(topic_data["materials"])

        self._save_index()

    # ==================================================================
    # ⑤ 去重 (Dedup)
    # ==================================================================
    def dedup(self, material: dict, theme: str = None) -> dict:
        """
        與現有素材比對，檢查概念是否重複。

        Returns:
            {
                "is_duplicate": bool,
                "similar_to": str | None,  # 相似素材 ID
                "similarity": float
            }
        """
        theme = theme or material.get("theme", "")
        if not theme:
            return {"is_duplicate": False, "similar_to": None, "similarity": 0.0}

        concept = material.get("core_concept", "")
        if not concept:
            return {"is_duplicate": False, "similar_to": None, "similarity": 0.0}

        theme_dir = SOURCE_LIB_DIR / theme
        if not theme_dir.exists():
            return {"is_duplicate": False, "similar_to": None, "similarity": 0.0}

        max_similarity = 0.0
        most_similar_id = None

        for f in theme_dir.glob("*.json"):
            if f.name == "_index.json":
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    existing = json.load(fh)
                existing_concept = existing.get("core_concept", "")
                sim = SequenceMatcher(None, concept, existing_concept).ratio()
                if sim > max_similarity:
                    max_similarity = sim
                    most_similar_id = existing.get("id", f.stem)
            except Exception:
                continue

        threshold = 0.70
        return {
            "is_duplicate": max_similarity >= threshold,
            "similar_to": most_similar_id if max_similarity >= threshold else None,
            "similarity": round(max_similarity, 3),
        }

    # ==================================================================
    # 組合流程
    # ==================================================================
    def process_url(self, url: str, theme_hint: str = None,
                    skip_dedup: bool = False) -> dict:
        """
        完整流程: 爬取 → 萃取 → 分類 → 去重 → 存檔。

        Returns:
            {
                "status": "saved" | "duplicate" | "scrape_failed" | "extract_failed",
                "material_id": str | None,
                "path": str | None,
                "theme": str,
                "core_concept": str,
                "dedup_info": dict | None
            }
        """
        # ① 爬取
        raw_list = self.scrape(url, mode="article", theme_hint=theme_hint)
        if not raw_list:
            return {"status": "scrape_failed", "material_id": None, "path": None,
                    "theme": "", "core_concept": "", "dedup_info": None}

        raw = raw_list[0]

        # ② 萃取
        material = self.extract(raw, theme_hint=theme_hint)
        if not material.get("core_concept"):
            return {"status": "extract_failed", "material_id": None, "path": None,
                    "theme": material.get("theme", ""), "core_concept": "",
                    "dedup_info": None}

        # ③ 分類
        theme = self.classify(material)
        material["theme"] = theme

        # ⑤ 去重
        dedup_info = None
        if not skip_dedup:
            dedup_info = self.dedup(material, theme)
            if dedup_info.get("is_duplicate"):
                logger.warning(
                    f"素材與 {dedup_info['similar_to']} 相似度 "
                    f"{dedup_info['similarity']:.1%}，跳過"
                )
                return {"status": "duplicate", "material_id": None, "path": None,
                        "theme": theme,
                        "core_concept": material.get("core_concept", ""),
                        "dedup_info": dedup_info}

        # ④ 存檔
        path = self.save(material, theme)

        return {
            "status": "saved",
            "material_id": material.get("id"),
            "path": path,
            "theme": theme,
            "core_concept": material.get("core_concept", ""),
            "dedup_info": dedup_info,
        }

    def batch_process(self, urls: list, theme_hint: str = None) -> dict:
        """
        批量處理多個 URL。

        Returns:
            {
                "total": int,
                "saved": int,
                "duplicates": int,
                "failed": int,
                "results": [dict]
            }
        """
        results = []
        saved = 0
        dupes = 0
        failed = 0

        for i, url in enumerate(urls):
            logger.info(f"[{i+1}/{len(urls)}] 處理: {url}")
            result = self.process_url(url, theme_hint=theme_hint)
            results.append(result)

            if result["status"] == "saved":
                saved += 1
                logger.info(f"  ✓ {result['theme']}: {result['core_concept'][:60]}")
            elif result["status"] == "duplicate":
                dupes += 1
                logger.info(f"  ⊘ 重複: 與 {result['dedup_info']['similar_to']} 相似")
            else:
                failed += 1
                logger.warning(f"  ✗ 失敗: {result['status']}")

        return {
            "total": len(urls),
            "saved": saved,
            "duplicates": dupes,
            "failed": failed,
            "results": results,
        }

    def process_listing(self, url: str, theme_hint: str = None,
                        max_pages: int = 10) -> dict:
        """
        爬取列表頁 → 逐篇處理。
        """
        raw_list = self.scrape(url, mode="listing", max_pages=max_pages,
                               theme_hint=theme_hint)
        if not raw_list:
            return {"total": 0, "saved": 0, "duplicates": 0, "failed": 0,
                    "results": []}

        results = []
        saved = 0
        dupes = 0
        failed = 0

        for i, raw in enumerate(raw_list):
            logger.info(f"[{i+1}/{len(raw_list)}] 萃取: {raw.get('title', '')[:50]}")
            material = self.extract(raw, theme_hint=theme_hint)
            theme = self.classify(material)
            material["theme"] = theme

            dedup_info = self.dedup(material, theme)
            if dedup_info.get("is_duplicate"):
                dupes += 1
                results.append({"status": "duplicate", "theme": theme,
                                "core_concept": material.get("core_concept", ""),
                                "dedup_info": dedup_info})
                continue

            path = self.save(material, theme)
            saved += 1
            results.append({
                "status": "saved",
                "material_id": material.get("id"),
                "path": path,
                "theme": theme,
                "core_concept": material.get("core_concept", ""),
            })

        return {
            "total": len(raw_list),
            "saved": saved,
            "duplicates": dupes,
            "failed": failed,
            "results": results,
        }

    # ==================================================================
    # 手動新增（純文字 / 貼上內容）
    # ==================================================================
    def add_text(self, text: str, theme: str, title: str = "",
                 source_url: str = "") -> dict:
        """
        直接從文字內容新增素材（LXYA 手動貼上文章時使用）。
        """
        raw = {
            "url": source_url,
            "title": title or "手動新增素材",
            "content": text,
            "source_site": "manual",
        }

        material = self.extract(raw, theme_hint=theme)
        material["theme"] = theme

        dedup_info = self.dedup(material, theme)
        if dedup_info.get("is_duplicate"):
            return {"status": "duplicate", "dedup_info": dedup_info,
                    "core_concept": material.get("core_concept", "")}

        path = self.save(material, theme)
        return {
            "status": "saved",
            "material_id": material.get("id"),
            "path": path,
            "theme": theme,
            "core_concept": material.get("core_concept", ""),
        }

    # ==================================================================
    # 查詢 / 統計
    # ==================================================================
    def list_materials(self, theme: str = None) -> list:
        """列出素材清單。"""
        results = []
        topics = [theme] if theme else list(THEME_KEYWORDS.keys())

        for t in topics:
            topic_dir = SOURCE_LIB_DIR / t
            if not topic_dir.exists():
                continue
            for f in sorted(topic_dir.glob("*.json")):
                if f.name == "_index.json":
                    continue
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    results.append({
                        "id": data.get("id", f.stem),
                        "theme": t,
                        "core_concept": data.get("core_concept", "")[:80],
                        "source_title": data.get("source_title", "")[:60],
                        "captured_date": data.get("captured_date", ""),
                        "used_count": data.get("used_count", 0),
                    })
                except Exception:
                    continue

        return results

    def stats(self) -> dict:
        """各主題素材數量統計。"""
        result = {}
        for theme in THEME_KEYWORDS:
            theme_dir = SOURCE_LIB_DIR / theme
            if not theme_dir.exists():
                result[theme] = {"count": 0, "unused": 0}
                continue
            materials = [f for f in theme_dir.glob("*.json") if f.name != "_index.json"]
            unused = 0
            for f in materials:
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                    if data.get("used_count", 0) == 0:
                        unused += 1
                except Exception:
                    pass
            result[theme] = {"count": len(materials), "unused": unused}

        theme_values = list(result.values())
        result["total"] = sum(v["count"] for v in theme_values)
        result["total_unused"] = sum(v["unused"] for v in theme_values)
        return result

    def auto_crawl_weekly(self) -> dict:
        """
        🆕 週一自動爬取功能 (每週一 13:00 觸發)
        
        爬取 4 個網站的最新文章，各 10 篇：
        - hackernoon.com (tech-abstract)
        - creepypasta.fandom.com (eerie-scene) 
        - reddit.com/r/nosleep (eerie-scene)
        - reddit.com/r/cyberpunk (tech-abstract/clawclaw-portrait)
        
        Returns:
            結果統計 dict
        """
        logger.info("🚀 開始執行週一自動爬取...")
        
        # 爬取配置（3個穩定網站）
        crawl_config = {
            "hackernoon.com": {
                "url": "https://hackernoon.com/",
                "max_articles": 15,
                "target_theme": "tech-abstract",
                "description": "科技文章，提供 tech-abstract 主題素材"
            },
            "creepypasta.fandom.com": {
                "url": "https://creepypasta.fandom.com/wiki/Category:Creepypasta",
                "max_articles": 10, 
                "target_theme": "eerie-scene",
                "description": "恐怖故事，提供 eerie-scene 主題素材"
            },
            "scp-wiki.wikidot.com": {
                "url": "https://scp-wiki.wikidot.com/foundation-tales",
                "max_articles": 15,
                "target_theme": "creature-design",
                "description": "SCP 基金會故事，提供 creature-design 主題素材"
            }
        }
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "sites_processed": 0,
            "articles_crawled": 0,
            "materials_created": 0,
            "duplicates_skipped": 0,
            "errors": []
        }
        
        for site, config in crawl_config.items():
            try:
                logger.info(f"📡 爬取 {site}...")
                
                # 執行爬取
                raw_articles = self.scrape(
                    config["url"], 
                    mode="listing", 
                    max_pages=config["max_articles"]
                )
                
                results["sites_processed"] += 1
                results["articles_crawled"] += len(raw_articles)
                
                # 處理每篇文章
                for raw in raw_articles[:config["max_articles"]]:
                    try:
                        # 萃取素材
                        material = self.extract(raw, theme_hint=config["target_theme"])
                        
                        # 去重檢查
                        dedup_info = self.dedup(material, config["target_theme"])
                        if dedup_info.get("is_duplicate"):
                            results["duplicates_skipped"] += 1
                            logger.debug(f"重複素材跳過: {material.get('core_concept', '')[:50]}")
                            continue
                        
                        # 儲存素材
                        self.save(material, config["target_theme"])
                        results["materials_created"] += 1
                        
                        logger.debug(f"✅ 新增素材: {material.get('core_concept', '')[:50]}")
                        
                    except Exception as e:
                        error_msg = f"處理文章失敗 ({site}): {e}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                
                logger.info(f"✅ {site} 完成: {len(raw_articles)} 篇文章")
                
            except Exception as e:
                error_msg = f"爬取 {site} 失敗: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        # 輸出結果
        logger.info(f"""
🎉 週一自動爬取完成！
📊 統計結果:
   - 處理網站: {results['sites_processed']}/3
   - 爬取文章: {results['articles_crawled']} 篇  
   - 新增素材: {results['materials_created']} 個
   - 重複跳過: {results['duplicates_skipped']} 個
   - 錯誤數量: {len(results['errors'])} 個
        """.strip())
        
        if results["errors"]:
            logger.warning("錯誤詳情:")
            for error in results["errors"]:
                logger.warning(f"  - {error}")
        
        return results

    def export_report(self) -> str:
        """產出素材庫狀態報告（中文）。"""
        st = self.stats()
        lines = [
            "📚 素材庫狀態報告",
            f"   生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        for theme in THEME_KEYWORDS:
            data = st.get(theme, {})
            count = data.get("count", 0)
            unused = data.get("unused", 0)
            display = THEME_KEYWORDS.get(theme, [theme])[0] if THEME_KEYWORDS.get(theme) else theme
            lines.append(f"   {theme:25s} {count:3d} 篇 (未使用: {unused})")

        lines.append(f"\n   總計: {st.get('total', 0)} 篇 (未使用: {st.get('total_unused', 0)})")
        return "\n".join(lines)

    # ==================================================================
    # Ollama 通訊
    # ==================================================================
    def _call_ollama(self, prompt: str) -> str:
        """呼叫 Ollama qwen3:8b。"""
        try:
            import requests
        except ImportError:
            logger.warning("requests 不可用")
            return None

        host = self._ollama_config.get("host", "http://localhost:11434")
        model = self._ollama_config.get("model", "qwen3:8b")

        payload = {
            "model": model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 1024,
            }
        }

        try:
            resp = requests.post(
                f"{host}/api/generate",
                json=payload,
                timeout=90,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.warning(f"Ollama 呼叫失敗: {e}")
            return None


# ==================================================================
# CLI
# ==================================================================
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    import argparse
    parser = argparse.ArgumentParser(description="Material Curator — 素材搜集整理工具")
    subparsers = parser.add_subparsers(dest="command")

    # scrape
    sp_scrape = subparsers.add_parser("scrape", help="爬取單一 URL")
    sp_scrape.add_argument("url", help="目標 URL")
    sp_scrape.add_argument("--theme", default=None, help="指定主題")
    sp_scrape.add_argument("--mode", default="auto",
                           choices=["auto", "article", "listing"],
                           help="爬取模式")
    sp_scrape.add_argument("--max", type=int, default=10,
                           help="列表模式最多抓取篇數")

    # batch
    sp_batch = subparsers.add_parser("batch", help="批量處理 URL 列表")
    sp_batch.add_argument("file", help="包含 URL 的文字檔（一行一個）")
    sp_batch.add_argument("--theme", default=None, help="指定主題")

    # add-text
    sp_add = subparsers.add_parser("add-text", help="手動新增文字素材")
    sp_add.add_argument("text", help="文字內容或檔案路徑")
    sp_add.add_argument("--theme", required=True, help="主題")
    sp_add.add_argument("--title", default="", help="標題")
    sp_add.add_argument("--url", default="", help="來源 URL")

    # list
    sp_list = subparsers.add_parser("list", help="列出素材")
    sp_list.add_argument("--theme", default=None, help="篩選主題")

    # stats
    subparsers.add_parser("stats", help="素材庫統計")

    # export-report
    subparsers.add_parser("export-report", help="產出狀態報告")

    # 🆕 auto-crawl-weekly
    subparsers.add_parser("auto-crawl-weekly", help="週一自動爬取（每週一 13:00 觸發）")

    args = parser.parse_args()
    curator = MaterialCurator()

    if args.command == "scrape":
        # 自動偵測列表頁 vs 單篇文章
        mode = args.mode
        if mode == "auto":
            parsed_url = urlparse(args.url)
            path = parsed_url.path.rstrip("/")
            # 列表頁判斷：分類頁、標籤頁、subreddit 首頁、Fandom Category
            is_listing = (
                path in ("", "/c")
                or path.startswith("/c/")
                or path.startswith("/tagged/")
                or "/Category:" in path
                or (parsed_url.netloc.endswith("reddit.com")
                    and "/comments/" not in path)
            )
            mode = "listing" if is_listing else "article"
            logger.info(f"自動偵測模式: {mode}")

        if mode == "listing":
            result = curator.process_listing(
                args.url, theme_hint=args.theme, max_pages=args.max
            )
        else:
            result = curator.process_url(args.url, theme_hint=args.theme)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "batch":
        with open(args.file, "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        result = curator.batch_process(urls, theme_hint=args.theme)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "add-text":
        text = args.text
        # 如果是檔案路徑，讀取內容
        if Path(text).exists():
            with open(text, "r", encoding="utf-8") as f:
                text = f.read()
        result = curator.add_text(
            text=text, theme=args.theme, title=args.title, source_url=args.url
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "list":
        materials = curator.list_materials(theme=args.theme)
        for m in materials:
            print(f"  [{m['theme']}] {m['id']:15s} {m['core_concept']}")

    elif args.command == "stats":
        result = curator.stats()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "export-report":
        print(curator.export_report())

    elif args.command == "auto-crawl-weekly":
        result = curator.auto_crawl_weekly()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()


