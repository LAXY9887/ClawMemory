#!/usr/bin/env python3
"""
快速測試 HackerNoon 爬取能力。
在你的本地環境跑: python test_hackernoon.py
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE = "https://hackernoon.com"

print("=" * 60)
print("測試 1: 爬取 hackernoon.com/c（分類總覽頁）")
print("=" * 60)

try:
    resp = requests.get(f"{BASE}/c", headers=HEADERS, timeout=30)
    print(f"  Status: {resp.status_code}")
    print(f"  Content length: {len(resp.text)}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # 找文章連結（hackernoon 文章 URL 通常很長、以 / 開頭）
    seen = set()
    article_urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        # 過濾：文章路徑通常是 /some-title-slug 格式，夠長、無子路徑
        if (href.startswith("/")
            and len(href) > 20
            and href.count("/") == 1
            and not href.startswith("/c/")
            and not href.startswith("/u/")
            and not href.startswith("/tagged/")
            and not href.startswith("/signup")
            and not href.startswith("/login")
            and href not in seen):
            seen.add(href)
            full = urljoin(BASE, href)
            article_urls.append((full, text[:80] if text else "(no title)"))

    print(f"\n  找到 {len(article_urls)} 個潛在文章連結:")
    for url, title in article_urls[:10]:
        print(f"    📄 {title}")
        print(f"       {url}")

    # 也看看分類子頁面
    cat_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/c/" in href and href != "/c":
            cat_links.add(href)
    if cat_links:
        print(f"\n  分類子頁面:")
        for cl in sorted(cat_links)[:10]:
            print(f"    📁 {cl}")

except Exception as e:
    print(f"  ❌ 失敗: {e}")

print()
print("=" * 60)
print("測試 2: 爬取單篇 HackerNoon 文章（用通用爬取器邏輯）")
print("=" * 60)

# 用一個已知的 hackernoon 文章測試
# 如果測試 1 有找到文章，會用第一篇；否則用備用 URL
test_url = article_urls[0][0] if article_urls else f"{BASE}/ai-and-creativity"

print(f"\n  目標: {test_url}")

try:
    resp = requests.get(test_url, headers=HEADERS, timeout=30)
    print(f"  Status: {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # 標題
    title = ""
    for sel in ["h1", "title"]:
        tag = soup.find(sel)
        if tag:
            title = tag.get_text(strip=True)
            break
    print(f"  標題: {title[:80]}")

    # 正文 — 嘗試幾種常見容器
    content = ""
    for selector in [
        "article",
        ".markup",
        ".story-body",
        ".post-content",
        "main",
        "[class*='article']",
        "[class*='content']",
    ]:
        container = soup.select_one(selector)
        if container:
            # 移除噪音
            for noise in container.select("script, style, nav, footer, .ad, .sidebar"):
                noise.decompose()
            content = container.get_text(separator="\n", strip=True)
            if len(content) > 200:
                print(f"  正文容器: {selector}")
                break

    if content:
        print(f"  正文長度: {len(content)} 字元")
        print(f"  前 300 字:")
        print(f"  ---")
        print(f"  {content[:300]}")
        print(f"  ---")
    else:
        print("  ⚠️ 找不到正文容器")
        # 顯示頁面結構供偵錯
        print("  頁面主要 class/id:")
        for tag in soup.find_all(True, class_=True):
            for c in tag.get("class", []):
                if any(kw in c.lower() for kw in ["article", "content", "body", "story", "post", "markup"]):
                    print(f"    <{tag.name} class='{c}'>")

    # 檢查是否 JS 渲染（內容極少可能是 SPA）
    if len(soup.get_text(strip=True)) < 500:
        print("\n  ⚠️ 頁面文字極少，HackerNoon 可能是 JS SPA 渲染，")
        print("     requests 無法取得完整內容，可能需要 API 或其他方式。")

except Exception as e:
    print(f"  ❌ 失敗: {e}")

print()
print("=" * 60)
print("測試 3: 檢查 HackerNoon 是否有 API")
print("=" * 60)

# HackerNoon 有公開的搜尋 API
try:
    api_url = "https://hackernoon.com/api/search"
    params = {"query": "artificial intelligence", "page": 0}
    resp = requests.get(api_url, headers=HEADERS, params=params, timeout=15)
    print(f"  /api/search status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
        if data:
            print(f"  ✅ API 可用！回傳格式: {type(data).__name__}")
            if isinstance(data, list):
                print(f"  結果數量: {len(data)}")
                if data:
                    print(f"  範例: {str(data[0])[:200]}")
            elif isinstance(data, dict):
                print(f"  Keys: {list(data.keys())[:10]}")
        else:
            print(f"  回傳非 JSON: {resp.text[:200]}")
    else:
        print(f"  API 不可用")
except Exception as e:
    print(f"  API 測試: {e}")

# 也試試 /api/stories
try:
    api_url2 = "https://hackernoon.com/api/stories"
    resp2 = requests.get(api_url2, headers=HEADERS, timeout=15)
    print(f"  /api/stories status: {resp2.status_code}")
except Exception as e:
    print(f"  /api/stories: {e}")

print("\n✅ 測試完成")
