# 03 - 記憶系統觀測模組

> 模組定位: 研究數據探針（觀測不干預）
> 設計原則: 只記錄，不修改記憶系統本身的行為
> 數據消費者: 05-metrics-data-collection、研究分析
> 技術基礎: YAML frontmatter、keyword_index.json、memory/ 目錄結構

---

## 為什麼需要這個模組

ClawClaw 的記憶系統已經具備完整的架構（YAML frontmatter、insights 層、冷熱分離、keyword_index），但目前缺乏客觀的效能數據。我們需要回答：

- 記憶系統在持續性任務中的實際表現如何？
- 哪些設計決策是有效的，哪些需要修正？
- 隨著記憶量增長，系統是否出現退化？

本模組的任務是在不影響系統正常運作的前提下，持續收集這些數據。

---

## 觀測維度

### 維度 1：記憶存取效率

追蹤每次記憶讀取操作的效能表現。

```
每次記憶讀取時記錄:

{
    "timestamp": "2026-03-27T09:15:32+08:00",
    "session_id": "ws-20260327-001",
    "operation": "memory_read",
    "trigger": "pipeline_stage1_context_load",
    "access_method": "yaml_scan" | "full_read" | "keyword_lookup",

    // 存取路徑
    "target_path": "memory/insights/technical/comfyui-best-practices.md",
    "access_reason": "載入 ComfyUI 相關經驗",

    // 效率指標
    "yaml_only": true,           // 是否只讀了 YAML（未讀全文）
    "full_read_needed": false,   // 最終是否需要讀全文
    "file_size_bytes": 2048,
    "token_estimate": 450,       // 估算消耗的 Token

    // 命中判斷
    "was_useful": true,          // 這次讀取的內容是否實際被使用
    "usage_context": "調整了 CFG 參數基於歷史經驗",

    // 時間
    "read_duration_ms": 120
}
```

#### 衍生指標
```
日度匯總:
- total_reads: 總讀取次數
- yaml_only_ratio: 只讀 YAML 的比例（驗證動態上下文注入效果）
- hit_rate: 有用讀取 / 總讀取（記憶命中率）
- total_tokens_spent: 記憶讀取消耗的總 Token
- avg_read_duration_ms: 平均讀取耗時
```

---

### 維度 2：記憶寫入品質

追蹤每次記憶寫入操作的內容品質。

```
每次記憶寫入時記錄:

{
    "timestamp": "2026-03-27T18:30:00+08:00",
    "session_id": "ws-20260327-001",
    "operation": "memory_write",
    "trigger": "pipeline_batch_complete",

    // 寫入目標
    "target_path": "memory/daily/2026-03-27.md",
    "write_type": "append" | "create" | "update",
    "category": "daily" | "insight" | "topic" | "moment" | "metric",

    // 內容品質
    "has_yaml_frontmatter": true,
    "yaml_fields_present": ["topic", "category", "importance", "tags", "summary", "created"],
    "yaml_fields_missing": [],
    "content_length_chars": 850,
    "importance_score": 6,

    // RICE+S 觸發分類
    "rices_trigger": "E",  // R/I/C/E/S
    "rices_reason": "每日生產批次完成事件",

    // 索引更新
    "keyword_index_updated": true,
    "keywords_added": ["wirestock", "生產批次", "品質通過率"]
}
```

#### 衍生指標
```
日度匯總:
- total_writes: 總寫入次數
- yaml_completeness_rate: YAML 欄位完整度
- category_distribution: 各分類的寫入比例
- rices_distribution: RICE+S 各觸發類型的分佈
- avg_importance_score: 平均重要性評分
```

---

### 維度 3：Keyword Index 效能

追蹤 keyword_index.json 的查詢效能和準確度。

```
每次 keyword 查詢時記錄:

{
    "timestamp": "2026-03-27T09:16:00+08:00",
    "session_id": "ws-20260327-001",
    "operation": "keyword_lookup",

    // 查詢內容
    "query_keywords": ["wirestock", "品質", "通過率"],
    "query_context": "尋找歷史品質數據",

    // 查詢結果
    "results_count": 4,
    "results_paths": [
        "memory/insights/technical/2026-03-26-ai-defect-resolution-breakthrough.md",
        "memory/topics/business/wirestock-automation-strategy.md",
        "memory/daily/2026-03-26.md",
        "memory/metrics/defect_stats_2026-03-26.json"
    ],

    // 相關性評估
    "relevant_results": 3,          // 實際相關的結果數
    "precision": 0.75,              // 3/4 相關
    "false_positives": 1,           // 不相關的結果數
    "missed_known_relevant": 0,     // 已知相關但未被找到的

    // 索引健康
    "index_total_keywords": 156,
    "index_total_entries": 423,
    "index_file_size_bytes": 18432
}
```

#### 衍生指標
```
週度匯總:
- avg_precision: 平均查詢精確度
- avg_recall: 平均召回率（需要人工標註才能計算，初期可省略）
- index_growth_rate: 索引增長速度（條目/天）
- query_frequency: 每日平均查詢次數
- most_queried_keywords: 最常被查詢的關鍵詞 Top 10
- orphan_entries: 指向不存在檔案的索引條目數
```

---

### 維度 4：Insight 引用追蹤

追蹤 insights/ 目錄下的經驗文件是否真的被後續任務引用。

```
insight 引用事件:

{
    "timestamp": "2026-03-27T09:20:00+08:00",
    "session_id": "ws-20260327-001",
    "operation": "insight_reference",

    // 被引用的 insight
    "insight_path": "memory/insights/technical/comfyui-best-practices.md",
    "insight_created": "2026-03-26",
    "insight_age_days": 1,

    // 引用上下文
    "referenced_by": "pipeline_stage2_prompt_optimization",
    "reference_type": "applied" | "considered_but_skipped" | "contradicted",
    "reference_detail": "使用了 CFG=8 的建議，因為歷史數據顯示科技主題在此設定下品質最穩定",

    // 影響評估
    "impact_on_outcome": "positive" | "neutral" | "negative" | "unknown",
    "impact_detail": "該批次科技主題通過率 100%"
}
```

#### 衍生指標
```
insight 效能報告:
- total_insights: insights/ 目錄下的總檔案數
- referenced_insights: 被引用過的 insight 數量
- reference_rate: 被引用比例（衡量 insight 的實用性）
- avg_reference_age_days: insight 被引用時的平均年齡
- most_referenced_insights: 最常被引用的 insight Top 5
- never_referenced_insights: 從未被引用的 insight 清單
- positive_impact_rate: 引用後產生正面影響的比例
```

---

### 維度 5：記憶系統健康度

定期（每日或每次批次結算後）執行健康度掃描。

```
健康度快照:

{
    "timestamp": "2026-03-27T23:50:00+08:00",
    "snapshot_type": "daily_health_check",

    // 容量指標
    "total_memory_files": 87,
    "total_memory_size_bytes": 245760,
    "files_by_category": {
        "daily": 12,
        "moments": 5,
        "topics/technical": 18,
        "topics/personal": 8,
        "topics/business": 3,
        "insights/technical": 14,
        "insights/personal": 2,
        "metrics": 25
    },

    // YAML 健康度
    "files_with_valid_yaml": 82,
    "files_without_yaml": 5,
    "yaml_completeness_avg": 0.92,

    // 索引健康度
    "keyword_index_entries": 423,
    "orphan_index_entries": 2,        // 指向不存在檔案
    "unindexed_files": 3,             // 存在但未被索引

    // 冷熱分佈
    "hot_memories": 15,               // 7 天內被存取
    "warm_memories": 32,              // 7-30 天內被存取
    "cold_memories": 40,              // 30 天以上未存取
    "access_count_distribution": {
        "0": 25,      // 從未被存取
        "1-3": 30,
        "4-10": 20,
        "10+": 12
    },

    // 增長趨勢
    "files_added_today": 4,
    "files_added_this_week": 18,
    "projected_monthly_growth": 72,

    // 異常偵測
    "anomalies": [
        {
            "type": "rapid_growth",
            "detail": "metrics/ 目錄本週增長 120%，可能需要歸檔策略",
            "severity": "warning"
        }
    ]
}
```

---

## 觀測探針的嵌入方式

### 設計原則：Hook Pattern

觀測探針不修改主流程邏輯，而是透過 hook/callback 機制掛載：

```python
# 概念示意（非最終實作）

class MemoryObserver:
    """記憶觀測器 - 不干預，只記錄"""

    def __init__(self, session_id: str, metrics_dir: str):
        self.session_id = session_id
        self.metrics_dir = metrics_dir
        self.events = []
        self.enabled = True  # 可隨時關閉觀測

    def on_memory_read(self, path, method, was_useful, **kwargs):
        """掛載於任何記憶讀取操作之後"""
        if not self.enabled:
            return
        self.events.append({
            "timestamp": now(),
            "operation": "memory_read",
            "target_path": path,
            "access_method": method,
            "was_useful": was_useful,
            **kwargs
        })

    def on_memory_write(self, path, write_type, category, **kwargs):
        """掛載於任何記憶寫入操作之後"""
        if not self.enabled:
            return
        self.events.append({
            "timestamp": now(),
            "operation": "memory_write",
            "target_path": path,
            "write_type": write_type,
            "category": category,
            **kwargs
        })

    def on_keyword_lookup(self, keywords, results, relevant_count, **kwargs):
        """掛載於 keyword_index 查詢之後"""
        if not self.enabled:
            return
        self.events.append({
            "timestamp": now(),
            "operation": "keyword_lookup",
            "query_keywords": keywords,
            "results_count": len(results),
            "relevant_results": relevant_count,
            **kwargs
        })

    def flush(self):
        """將累積的觀測數據寫入磁碟"""
        output_path = f"{self.metrics_dir}/observations_{self.session_id}.json"
        # 寫入 JSON ...
        self.events.clear()
```

### 故障隔離
```
觀測模組的任何錯誤都不應中斷主流程:

try:
    observer.on_memory_read(...)
except Exception as e:
    # 靜默記錄錯誤，不中斷生產
    log_observer_error(e)
```

---

## 重要限制與考量

### ClawClaw 是 Agent，不是程式

ClawClaw 在 OpenClaw 上運行時，記憶的讀取和寫入是透過 Agent 的自然行為（讀檔案、寫檔案），而不是透過程式化的 API 呼叫。因此：

1. **觀測需要在 Agent 行為層實作**：在 SKILL.md 的流程指引中，要求 ClawClaw 在每次記憶操作後自行記錄觀測數據
2. **無法做到完全自動的 hook**：需要依賴 ClawClaw 遵循流程指引來記錄
3. **觀測的精確度取決於 Agent 的遵從度**：這本身也是一個有趣的觀測指標

### 實作方案
```
方案 A：流程內嵌記錄（推薦）
- 在 SKILL.md 的每個步驟中明確要求記錄觀測數據
- ClawClaw 在執行每步後，呼叫 metrics_collector 腳本記錄
- 優點：簡單、可靠
- 缺點：增加流程步驟

方案 B：腳本自動攔截
- 用 Python 腳本封裝記憶操作，在腳本層自動記錄
- 所有記憶讀寫都透過這個封裝腳本
- 優點：自動化程度高
- 缺點：需要改變 ClawClaw 的記憶操作方式

方案 C：事後分析
- 不在過程中記錄，而是在每日結算時分析 Git diff
- 根據檔案變更記錄推斷記憶操作
- 優點：零侵入
- 缺點：精度較低，無法知道「讀取但未使用」的情況

建議: 主要採用方案 A，輔以方案 C 作為交叉驗證
```

---

## 待確認事項

1. ~~**觀測精度 vs 流程複雜度的平衡**~~：✅ 採用方案 A「流程內嵌記錄」，每個 Stage 內嵌觀測步驟，不額外增加獨立觀測流程
2. ~~**Token 預算**~~：✅ 觀測記錄使用 JSON 寫入 metrics/，不計入 Agent 上下文。配合 YAML-first 策略，影響可忽略
3. ~~**數據量管理**~~：✅ metrics/ 放於 memory/ 底下，需建立定期歸納機制（每月壓縮歸檔超過 90 天的 daily/ 數據），隨記憶系統統一 Git 備份
4. **Insight 影響評估**：⏳ 初期先記錄 insight 被引用次數和引用後的品質變化，客觀判斷方式待數據累積後再設計
