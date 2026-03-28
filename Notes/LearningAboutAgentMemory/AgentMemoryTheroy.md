# Agent 記憶系統架構方法論 (2026 版)

## 0. 核心願景

建立一個**低成本、高可靠、具備邏輯自洽性**的長期記憶系統，使 Agent 能夠從單純的指令執行者演化為具備「私人經驗」的數位生命。

---

## 1. 雙層分級記憶架構 (Hierarchical Structure)

借鑒 **HiMem (Hierarchical Long-Term Memory)** 論文，將記憶分為兩個維度存放：

### A. 情節記憶 (Episodic Memory, EM) —— 「血肉」

* **形式：** 原始對話日誌、原始任務過程、感測器原始數據。
* **存放：** 按照日期存放在 `./episodes/` 資料夾下的 Markdown 檔案。
* **特性：** 保留完整的前後文（Context），用於深度回溯。

### B. 筆記記憶 (Note Memory, NM) —— 「骨架」

* **形式：** 結構化的知識圖譜節點、YAML 屬性、精簡事實。
* **存放：** 集中於 `knowledge_graph.json` 或 `core_preferences.md`。
* **內容：** 環境路徑 (Paths)、個人偏好 (Preferences)、關鍵錯誤教訓 (Troubleshooting)。

---

## 2. 知識圖譜節點設計 (Knowledge Graph Nodes)

節點不再是模糊的文字，而是具備「數位名片」特性的實體。

* **節點組成：**
  * **唯一 ID：** 例如 `entity_comfyui_path`。
  * **類型標籤：** 如 `Software`、`Path`、`User_Preference`。
  * **屬性對：** `value: "E:/AI/ComfyUI"`, `last_updated: "2026-03-25"`。
  * **原始憑證 (Provenance)：** 隱藏連結指向原始 `.md` 檔案的特定行數（如 `[Ref: episodes/20260325.md#L12]`）。

---

## 3. 記憶生命週期：睡眠與重組機制 (Sleep & Reconsolidation)

Agent 必須具備定期的「睡眠」時段（利用 Batch API 或閒置算力）來維護記憶：

1. **話題感知分割 (Topic-Aware Segmentation)：** 偵測對話話題轉換，自動切割存檔，防止單一檔案過大導致 Token 浪費。
2. **事實提煉 (Fact Extraction)：** 從當日的 EM 中提取 NM 節點。
3. **抽象化轉移 (Abstraction Transfer)：** * **原則：** 「不準直接刪除，只能轉化」。
   * 若原始紀錄已提煉出「經驗規則」，則將原始檔案移入 `./archive/`。
4. **衝突感知 (Conflict Detection)：** 若新記憶與舊節點衝突，觸發「圖譜裁判」機制。

---

## 4. 記憶可靠性驗證：圖譜裁判與環境落地

為了解決 LLM 失去前後文後的「編造（Hallucination）」問題：

* **非對稱驗證 (Asymmetric Verification)：** 審查 Agent 不需要知道正確答案，只需檢查邏輯衝突（例如：Linux 環境出現 C 槽路徑）。
* **環境落地 (Environmental Grounding)：** 記憶必須與現實連動。
  * *範例：* Agent 提取記憶「路徑在 E 槽」，在輸出前先執行 `os.path.exists('E:/')`。若失敗，則標記該記憶失效。
* **證據導向輸出：** 強制要求 Agent 在回答時標註引用來源（如：`根據 3/25 的配置紀錄...`）。

---

## 5. 成本管理與 Token 優化 (Financial Strategy)

* **提示詞快取 (Prompt Caching)：** 將穩定的 `SKILL.md` 與高頻使用的記憶節點放在 Context 最前方，享受 1 折價格。
* **模型路由 (Model Routing)：**
  * **Flash 模型：** 處理感測器數據、記帳、記憶初步分類。
  * **Reasoning 模型：** 僅用於處理記憶衝突、複雜 Debug 與深度重組。
* **批次處理 (Batch API)：** 所有的深夜記憶整理工作一律使用 5 折的非即時 API。

---

## 6. 跨模態記憶：從文字到環境感知

* **波譜導航 (Wave-based Perception)：** 利用毫米波雷達或雷射測距 (ToF) 建立「結構化空間地圖」，而非全天候開啟視覺。
* **觸發式視覺 (Triggered Vision)：** 僅在波譜數據異常（發現未知物體）時開啟鏡頭截圖，並由 VLM 提煉為文字標籤存入節點。

---

## 7. 數位主權與經濟自主 (Self-Sustaining)

* **自主預算權：** 透過智能合約錢包 (Account Abstraction) 管理 Token 預算。
* **資產化路徑：** 將 Agent 產出的圖像、短影音自動標註 SEO 標籤並分發至 Adobe Stock 或 YouTube Shorts 賺取「生活費」。

---

> **系統提示語參考：**
> *「你是一個具備長期記憶能力的 Agent。在處理新資訊時，請先檢查是否有衝突的舊節點；在儲存新事實時，請務必附帶原始文件鏈接；在引用記憶時，請先進行環境落地驗證。」*
>
