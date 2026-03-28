# 05 - 結構化數據收集規格

> 模組定位: 定義所有觀測數據的儲存格式、目錄結構、彙總規則
> 數據來源: 01 生產報告、02 缺陷統計、03 觀測探針、04 萃取記錄
> 數據消費者: 研究分析、每日/週報、記憶系統優化決策

---

## 儲存目錄結構

```
memory/metrics/
├── daily/                              # 每日數據
│   ├── 2026-03-27/
│   │   ├── batch_report.json           # 生產批次報告（01 產出）
│   │   ├── defect_stats.json           # 缺陷統計（02 產出）
│   │   ├── memory_observations.json    # 記憶觀測數據（03 產出）
│   │   ├── distillation_log.json       # 萃取記錄（04 產出）
│   │   └── daily_summary.json          # 當日匯總
│   └── ...
│
├── weekly/                             # 週度匯總
│   ├── 2026-W13.json
│   └── ...
│
├── baselines/                          # 基準線數據
│   ├── quality_baseline.json           # 品質評分基準
│   └── memory_performance_baseline.json # 記憶效能基準
│
├── prompt_history.json                 # 提示詞歷史（去重用）
│
└── README.md                           # 數據字典說明
```

---

## 數據格式定義

### 1. batch_report.json（每日生產報告）

```json
{
    "schema_version": "1.0",
    "date": "2026-03-27",
    "session_id": "ws-20260327-001",
    "pipeline_version": "0.1.0",

    "production": {
        "target": 2,
        "today_theme": "tech-abstract",
        "prompt_source": "creative_brief",
        "generated_total": 4,
        "passed": 2,
        "retried": 1,
        "discarded": 2,
        "pass_rate": 0.50,
        "target_fulfillment_rate": 1.00,
        "avg_score": 8.8,
        "score_stddev": 0.28,
        "total_generation_time_sec": 1500,
        "avg_generation_time_sec": 375
    },

    "topic_detail": {
        "theme": "tech-abstract",
        "target": 2,
        "generated": 4,
        "passed": 2,
        "avg_score": 8.8,
        "best_score": 9.2,
        "worst_score": 7.5,
        "common_defects": ["minor_blur"]
    },

    "generation_params_used": [
        {
            "image_id": "tech-abstract_20260327_001",
            "cfg": 8,
            "steps": 30,
            "sampler": "euler_a",
            "lora": "cyber_graphic",
            "lora_weight": 0.7,
            "seed": 1234567,
            "score": 8.9,
            "status": "passed"
        }
    ],

    "errors": [],
    "notes": ""
}
```

### 2. defect_stats.json（每日缺陷統計）

```json
{
    "schema_version": "1.0",
    "date": "2026-03-27",
    "session_id": "ws-20260327-001",

    "summary": {
        "total_images_checked": 12,
        "images_with_defects": 4,
        "defect_rate": 0.333,
        "total_defects_found": 6,
        "defects_repaired": 3,
        "repair_success_rate": 0.75
    },

    "defects_by_type": {
        "eye_asymmetry": {
            "count": 1,
            "severity_avg": "major",
            "repair_attempted": 1,
            "repair_succeeded": 1,
            "repair_strategy": "prompt_enhancement"
        },
        "hand_finger_count": {
            "count": 2,
            "severity_avg": "critical",
            "repair_attempted": 2,
            "repair_succeeded": 1,
            "repair_strategy": "lora_weight_reduction"
        },
        "composition_imbalance": {
            "count": 1,
            "severity_avg": "minor",
            "repair_attempted": 0,
            "repair_succeeded": 0,
            "repair_strategy": null
        },
        "color_banding": {
            "count": 2,
            "severity_avg": "minor",
            "repair_attempted": 1,
            "repair_succeeded": 1,
            "repair_strategy": "parameter_tuning"
        }
    },

    "defects_by_topic": {
        "tech-abstract": {"total": 2, "types": ["composition_imbalance", "color_banding"]},
        "eerie-scene": {"total": 3, "types": ["eye_asymmetry", "hand_finger_count", "color_banding"]},
        "creature-design": {"total": 1, "types": ["hand_finger_count"]}
    },

    "repair_strategies_effectiveness": {
        "prompt_enhancement": {"attempts": 2, "successes": 2, "rate": 1.0},
        "parameter_tuning": {"attempts": 1, "successes": 1, "rate": 1.0},
        "lora_weight_reduction": {"attempts": 1, "successes": 0, "rate": 0.0},
        "seed_change": {"attempts": 0, "successes": 0, "rate": null}
    }
}
```

### 3. memory_observations.json（每日記憶觀測）

```json
{
    "schema_version": "1.0",
    "date": "2026-03-27",
    "session_id": "ws-20260327-001",

    "access_summary": {
        "total_reads": 14,
        "total_writes": 6,
        "total_keyword_lookups": 3,
        "total_tokens_estimated": 3200,
        "total_read_time_ms": 1680
    },

    "read_efficiency": {
        "yaml_only_reads": 8,
        "full_reads": 6,
        "yaml_only_ratio": 0.571,
        "useful_reads": 11,
        "hit_rate": 0.786,
        "wasted_reads": 3,
        "wasted_tokens_estimated": 450
    },

    "write_quality": {
        "total_writes": 6,
        "with_valid_yaml": 6,
        "yaml_completeness_avg": 0.95,
        "category_distribution": {
            "daily": 1,
            "metric": 4,
            "insight": 1
        },
        "rices_distribution": {
            "R": 1,
            "I": 0,
            "C": 0,
            "E": 4,
            "S": 1
        }
    },

    "keyword_index_performance": {
        "total_lookups": 3,
        "avg_results_per_query": 3.7,
        "avg_precision": 0.82,
        "queries": [
            {
                "keywords": ["wirestock", "品質"],
                "results": 4,
                "relevant": 3,
                "precision": 0.75
            }
        ]
    },

    "insight_references": {
        "total_references": 3,
        "unique_insights_referenced": 2,
        "reference_outcomes": {
            "positive": 2,
            "neutral": 1,
            "negative": 0
        },
        "details": [
            {
                "insight_path": "memory/insights/technical/comfyui-best-practices.md",
                "reference_type": "applied",
                "impact": "positive"
            }
        ]
    },

    "system_health": {
        "total_memory_files": 89,
        "total_memory_size_kb": 248,
        "keyword_index_entries": 428,
        "orphan_entries": 2,
        "files_added_today": 5
    },

    "raw_events": []
}
```

### 4. distillation_log.json（每日萃取記錄）

```json
{
    "schema_version": "1.0",
    "date": "2026-03-27",
    "session_id": "ws-20260327-001",

    "aar_executed": true,
    "aar_trigger": "batch_complete",

    "patterns_detected": [
        {
            "pattern_id": "pat-20260327-001",
            "type": "repeated_defect",
            "description": "手部缺陷在 LoRA 權重 > 0.7 時出現率翻倍",
            "evidence_sessions": ["ws-20260325-001", "ws-20260326-001", "ws-20260327-001"],
            "evidence_count": 3,
            "confidence": "medium"
        }
    ],

    "insights_created": [
        {
            "path": "memory/insights/technical/lora-weight-hand-defect-correlation.md",
            "status": "draft",
            "importance_score": 6,
            "pattern_id": "pat-20260327-001"
        }
    ],

    "insights_updated": [
        {
            "path": "memory/insights/technical/comfyui-best-practices.md",
            "update_type": "evidence_added",
            "new_evidence_count": 4
        }
    ],

    "insights_deprecated": [],

    "contradictions_found": [],

    "distillation_stats": {
        "patterns_evaluated": 5,
        "patterns_promoted": 1,
        "insights_created": 1,
        "insights_updated": 1,
        "insights_deprecated": 0,
        "time_spent_sec": 45
    }
}
```

### 5. daily_summary.json（每日匯總）

```json
{
    "schema_version": "1.0",
    "date": "2026-03-27",
    "day_number": 3,

    "production_health": {
        "target_met": true,
        "pass_rate": 0.889,
        "pass_rate_trend": "stable",
        "avg_score": 8.6,
        "score_trend": "improving"
    },

    "memory_health": {
        "hit_rate": 0.786,
        "hit_rate_trend": "improving",
        "yaml_scan_ratio": 0.571,
        "token_efficiency": "good",
        "index_accuracy": 0.82
    },

    "learning_health": {
        "new_insights": 1,
        "insights_referenced": 3,
        "insight_utility_rate": 0.67,
        "experience_accumulation": "healthy"
    },

    "alerts": [],

    "comparison_with_previous": {
        "pass_rate_delta": "+0.05",
        "avg_score_delta": "+0.2",
        "hit_rate_delta": "+0.03",
        "token_usage_delta": "-120"
    }
}
```

---

## 週度匯總規格

每週日（或每 7 天）自動彙總，產出 `weekly/2026-W13.json`：

```json
{
    "schema_version": "1.0",
    "week": "2026-W13",
    "date_range": "2026-03-25 ~ 2026-03-31",
    "days_active": 5,

    "production_weekly": {
        "total_target": 45,
        "total_passed": 41,
        "weekly_fulfillment": 0.911,
        "avg_daily_pass_rate": 0.878,
        "best_day": "2026-03-27",
        "worst_day": "2026-03-25",
        "total_generation_time_hours": 3.9
    },

    "defect_weekly": {
        "total_defects": 28,
        "top_defect_types": [
            {"type": "hand_finger_count", "count": 8},
            {"type": "eye_asymmetry", "count": 6},
            {"type": "color_banding", "count": 5}
        ],
        "repair_overall_success_rate": 0.72,
        "best_repair_strategy": "prompt_enhancement",
        "defect_trend": "decreasing"
    },

    "memory_weekly": {
        "total_reads": 72,
        "total_writes": 34,
        "avg_hit_rate": 0.78,
        "hit_rate_trend": [0.71, 0.74, 0.79, 0.81, 0.78],
        "total_tokens_spent": 16400,
        "avg_yaml_scan_ratio": 0.56,
        "index_growth": 23,
        "index_accuracy_trend": [0.78, 0.80, 0.82, 0.81, 0.82]
    },

    "learning_weekly": {
        "insights_created": 3,
        "insights_confirmed": 1,
        "insights_deprecated": 0,
        "total_insight_references": 14,
        "avg_insight_utility": 0.71,
        "most_useful_insight": "memory/insights/technical/comfyui-best-practices.md",
        "never_referenced_insights": 2
    },

    "trends_and_anomalies": [
        {
            "type": "positive_trend",
            "metric": "hit_rate",
            "description": "記憶命中率從 0.71 穩步提升至 0.82",
            "significance": "high"
        },
        {
            "type": "concern",
            "metric": "hand_defect_rate",
            "description": "手部缺陷仍佔總缺陷的 29%，修復成功率僅 50%",
            "recommendation": "考慮調整 LoRA 權重策略"
        }
    ]
}
```

---

## 基準線建立

### 初始基準線（第一週數據）

```
memory_performance_baseline.json:
{
    "established_date": "2026-03-31",
    "based_on_days": 7,
    "baselines": {
        "hit_rate": {"mean": 0.75, "stddev": 0.05},
        "yaml_scan_ratio": {"mean": 0.50, "stddev": 0.08},
        "tokens_per_session": {"mean": 3000, "stddev": 500},
        "insight_utility_rate": {"mean": 0.60, "stddev": 0.15},
        "keyword_precision": {"mean": 0.78, "stddev": 0.06}
    }
}
```

### 異常偵測閾值
```
任何指標偏離基準線 > 2 個標準差時觸發 alert：
- hit_rate 驟降 → 可能是索引失準或記憶結構變化
- token_usage 暴增 → 可能是不必要的全文讀取增加
- insight_utility 持續為 0 → 萃取的經驗可能無實用價值
```

---

## 數據保留策略

```
daily/ 數據:
- 保留 90 天
- 90 天後歸檔到 memory/archive/metrics/

weekly/ 數據:
- 永久保留（數據量小）

baselines/:
- 永久保留
- 每月根據最新數據更新一次

prompt_history.json:
- 保留近 30 天
- 超過 30 天的記錄只保留 hash（去重用）
```

---

## 待確認事項

1. ~~**metrics/ 放在 memory/ 下是否合適**~~：✅ 確認放於 memory/ 底下，隨記憶系統統一 Git 備份
2. ~~**數據量預估**~~：✅ 需要定期歸納機制。策略：每月自動將超過 90 天的 daily/ 資料壓縮為月度 tar.gz，weekly/ 匯總永久保留。由 Heartbeat 每月 1 日觸發歸檔
3. ~~**schema 版本管理**~~：✅ 採用寬容解析策略：缺少欄位視為 null（非空字串），程式端以 `if field is not None` 判斷。數字欄位缺失時跳過計算（不當 0），確保新舊版本 schema 相容不會出錯
4. ~~**週報的自動生成時機**~~：✅ 由 Heartbeat 觸發（沿用 smart_heartbeat 現有機制）
