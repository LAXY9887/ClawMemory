"""
OpenRouter API Client — 統一封裝所有 OpenRouter 呼叫

用途:
  - Stage 0: 雙 Agent 創意對話（純文字）
  - Stage 3.2/3.4: 圖片候選自評（多模態）
  - Stage 4: 品質精檢（多模態）
  - Stage 5.1: 圖片描述提取（多模態）

設計原則:
  - API Key 從環境變數 OPENROUTER_API_KEY 讀取
  - 模型名從 config/schedule.json 讀取（全局切換）
  - 內建重試機制和成本追蹤
  - 支援純文字和多模態（圖片）兩種呼叫模式
"""

import os
import json
import time
import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# --- Constants ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_INTERVAL = 15  # seconds
DEFAULT_TIMEOUT = 120  # seconds


class OpenRouterError(Exception):
    """OpenRouter API 呼叫失敗"""
    pass


class OpenRouterClient:
    """
    OpenRouter API 統一客戶端。

    使用方式:
        client = OpenRouterClient(config_path="config/schedule.json")
        # 純文字對話
        response = client.chat(messages=[...])
        # 多模態（圖片評分）
        response = client.chat_with_images(prompt="評分...", image_paths=[...])
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化客戶端。

        Args:
            config_path: schedule.json 的路徑。若為 None，使用預設相對路徑。
        """
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise OpenRouterError(
                "環境變數 OPENROUTER_API_KEY 未設定。"
                "請執行: export OPENROUTER_API_KEY=sk-or-..."
            )

        # 載入 config 取得模型名
        self._config = self._load_config(config_path)
        or_config = self._config.get("openrouter", {})
        self.model = or_config.get("model", "google/gemini-flash-1.5")
        self.fallback_model = or_config.get("fallback_model")

        # 成本追蹤
        self._session_cost = 0.0
        self._session_calls = 0

    def _load_config(self, config_path: Optional[str]) -> dict:
        """載入 schedule.json 配置"""
        if config_path is None:
            # 預設: 相對於 scripts/ 的上層 config/
            script_dir = Path(__file__).resolve().parent
            config_path = script_dir.parent / "config" / "schedule.json"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            logger.warning(f"Config 不存在: {config_path}，使用預設值")
            return {}

        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_headers(self) -> dict:
        """建構 API 請求標頭"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/clawclaw",
            "X-Title": "ClawClaw Stock Pipeline"
        }

    def _encode_image(self, image_path: str) -> str:
        """將圖片檔案轉為 base64 data URI"""
        path = Path(image_path)
        if not path.exists():
            raise OpenRouterError(f"圖片不存在: {image_path}")

        suffix = path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp"
        }
        mime_type = mime_map.get(suffix, "image/png")

        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _make_request(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        response_format: Optional[dict] = None
    ) -> dict:
        """
        發送 API 請求（含重試機制）。

        Args:
            messages: OpenAI 格式的 messages 列表
            model: 指定模型（覆蓋全局設定）
            max_tokens: 最大回應 token 數
            temperature: 隨機性
            response_format: 可選的 JSON mode 設定

        Returns:
            API 回應的 JSON dict

        Raises:
            OpenRouterError: 所有重試失敗後拋出
        """
        import requests  # lazy import，避免模組層級依賴問題

        use_model = model or self.model
        headers = self._build_headers()

        body = {
            "model": use_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        if response_format:
            body["response_format"] = response_format

        last_error = None
        for attempt in range(DEFAULT_MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=body,
                    timeout=DEFAULT_TIMEOUT
                )

                if resp.status_code == 200:
                    result = resp.json()
                    # 追蹤成本
                    usage = result.get("usage", {})
                    self._session_calls += 1
                    # OpenRouter 回傳的 cost 欄位（如果有）
                    if "cost" in result:
                        self._session_cost += result["cost"]
                    logger.info(
                        f"OpenRouter 呼叫成功 [{use_model}] "
                        f"(tokens: {usage.get('total_tokens', '?')}, "
                        f"attempt: {attempt + 1})"
                    )
                    return result

                # 可重試的錯誤碼
                if resp.status_code in (429, 500, 502, 503):
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(
                        f"OpenRouter 重試 {attempt + 1}/{DEFAULT_MAX_RETRIES + 1}: "
                        f"{last_error}"
                    )
                    if attempt < DEFAULT_MAX_RETRIES:
                        time.sleep(DEFAULT_RETRY_INTERVAL)
                    continue

                # 不可重試的錯誤
                raise OpenRouterError(
                    f"OpenRouter API 錯誤 (HTTP {resp.status_code}): "
                    f"{resp.text[:500]}"
                )

            except requests.exceptions.Timeout:
                last_error = f"請求超時 ({DEFAULT_TIMEOUT}s)"
                logger.warning(f"OpenRouter 超時 (attempt {attempt + 1})")
                if attempt < DEFAULT_MAX_RETRIES:
                    time.sleep(DEFAULT_RETRY_INTERVAL)

            except requests.exceptions.ConnectionError as e:
                last_error = f"連線失敗: {e}"
                logger.warning(f"OpenRouter 連線失敗 (attempt {attempt + 1})")
                if attempt < DEFAULT_MAX_RETRIES:
                    time.sleep(DEFAULT_RETRY_INTERVAL)

        raise OpenRouterError(
            f"OpenRouter API 呼叫失敗（已重試 {DEFAULT_MAX_RETRIES} 次）: {last_error}"
        )

    # --- 公開 API ---

    def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """
        純文字對話（Stage 0 雙 Agent 對話用）。

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
            model: 指定模型（覆蓋全局設定）
            max_tokens: 最大回應 token
            temperature: 隨機性

        Returns:
            模型回應的文字內容
        """
        result = self._make_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._extract_content(result)

    def chat_with_images(
        self,
        prompt: str,
        image_paths: list,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        多模態對話 — 圖片 + 文字（Stage 3.2/3.4/4/5.1 用）。

        Args:
            prompt: 評分/描述指令文字
            image_paths: 圖片檔案路徑列表
            model: 指定模型
            max_tokens: 最大回應 token
            temperature: 低隨機性適合評分任務
            system_prompt: 可選的系統提示

        Returns:
            模型回應的文字內容
        """
        # 建構多模態 content
        content_parts = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            data_uri = self._encode_image(img_path)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": data_uri}
            })

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content_parts})

        result = self._make_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return self._extract_content(result)

    def chat_json(
        self,
        messages: list,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.3
    ) -> dict:
        """
        請求 JSON 格式回應（評分結果解析用）。

        Returns:
            解析後的 JSON dict。若解析失敗，回傳 {"raw": "原始回應文字"}
        """
        result = self._make_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        text = self._extract_content(result)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 嘗試從回應中提取 JSON 區塊
            return self._try_extract_json(text)

    def chat_with_images_json(
        self,
        prompt: str,
        image_paths: list,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        system_prompt: Optional[str] = None
    ) -> dict:
        """
        多模態 + JSON 回應（Stage 3.2/3.4 評分用）。

        Returns:
            解析後的 JSON dict
        """
        content_parts = [{"type": "text", "text": prompt}]
        for img_path in image_paths:
            data_uri = self._encode_image(img_path)
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": data_uri}
            })

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content_parts})

        result = self._make_request(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        text = self._extract_content(result)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self._try_extract_json(text)

    # --- 輔助方法 ---

    def _extract_content(self, result: dict) -> str:
        """從 API 回應中提取文字內容"""
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise OpenRouterError(f"無法解析 API 回應: {e}\n回應: {json.dumps(result, ensure_ascii=False)[:500]}")

    def _try_extract_json(self, text: str) -> dict:
        """嘗試從文字中提取 JSON 區塊（處理 markdown code block 包裹的情況）"""
        # 嘗試找 ```json ... ``` 區塊
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 嘗試找 { ... } 區塊
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"無法從回應中提取 JSON，回傳原始文字")
        return {"raw": text}

    @property
    def session_stats(self) -> dict:
        """取得本次 session 的呼叫統計"""
        return {
            "total_calls": self._session_calls,
            "estimated_cost": round(self._session_cost, 4),
            "model": self.model
        }

    def reset_stats(self):
        """重置統計（通常在每日批次開始時呼叫）"""
        self._session_cost = 0.0
        self._session_calls = 0
