# 04 - 任務後經驗萃取機制

> 模組定位: 將零散事件轉化為可復用經驗
> 觸發時機: 每日批次結算後、異常事件發生後
> 輸出目標: memory/insights/ 目錄
> 設計基礎: RICE+S 觸發器、Phase 3.5 經驗提煉、After Action Review

---

## 核心問題

記憶系統已經能「記住發生了什麼」，但研究的關鍵問題是：**它能從經驗中學到什麼？**

本模組負責在每次任務執行後，自動判斷是否有值得提煉的經驗，並將其寫入 insights/ 目錄。同時追蹤這些 insight 的後續表現——它們是否真的在未來被引用？引用後是否產生了正面效果？

---

## 萃取時機

### 時機 1：每日批次結算後（常規萃取）

每天生產批次完成後，執行一次 mini After Action Review：

```
觸發條件: Stage 5 批次結算完成
輸入: 當天的生產報告 (batch_report.json)
流程:

1. 回顧今日表現
   - 通過率 vs 目標
   - 各主題表現差異
   - 缺陷分佈

2. 與歷史比較
   - 比較近 7 天的趨勢
   - 識別改善或退化的項目

3. 判斷是否產生新 insight
   - 是否出現新的失敗模式？
   - 是否有策略帶來顯著改善？
   - 是否有跨主題的共同現象？

4. 如果有，撰寫 insight 文件
```

### 時機 2：異常事件發生後（即時萃取）

當任務中遇到預期之外的事件時，立即記錄：

```
觸發條件:
- ComfyUI 崩潰或 CUDA OOM
- 某主題通過率驟降 (低於前 7 天平均的 50%)
- 發現新類型的缺陷
- 修復策略意外成功/失敗
- 外部環境變化（WireStock 規則變更等）
```

### 時機 3：睡眠模式中的深度萃取（Phase 3.5）

與現有的智能睡眠模式整合，在每晚 23:50 的 Phase 3.5 中執行更深度的分析：

```
此部分由現有的 intelligent_sleep_mode.py 負責
本模組提供:
- 待萃取的候選事件清單
- 事件之間的關聯建議
- 初步的 insight 草稿

睡眠模式負責:
- 雙角色對話提煉（海馬迴 + 大腦皮層）
- insight 的 draft → confirmed 晉升
- 整合到記憶生命週期管理
```

---

## After Action Review (AAR) 結構

### 每日 AAR 模板

```markdown
# AAR: WireStock 生產 - {date}

## 發生了什麼（事實）
- 目標: {target} 張，實際通過: {passed} 張
- 通過率: {pass_rate}%
- 主要缺陷: {defect_summary}
- 特殊事件: {anomalies}

## 為什麼（分析）
- 通過率 {高於/低於} 目標的原因:
  {analysis}
- 缺陷出現的根本原因:
  {root_cause}

## 學到了什麼（教訓）
- 可重複的成功模式:
  {success_patterns}
- 需要避免的失敗模式:
  {failure_patterns}

## 下次該怎麼做（行動）
- 具體調整:
  {action_items}
- 需要驗證的假設:
  {hypotheses}
```

---

## Insight 分級機制

### 重要性判定

```
判定規則:

Score 1-3 (低): 只記錄在當日日誌中
  例: "今天科技主題的 seed 42 生成了不錯的結果"
  → 寫入 memory/daily/

Score 4-6 (中): 寫入獨立的 insight 文件 (draft 狀態)
  例: "連續 3 天發現 CFG=8 在科技主題下表現最穩定"
  → 寫入 memory/insights/technical/ (status: draft)

Score 7-9 (高): 寫入 insight 文件 (confirmed 狀態)
  例: "Horror LoRA 權重超過 0.7 會導致手部缺陷率翻倍"
  → 寫入 memory/insights/technical/ (status: confirmed)

Score 10 (核心): 更新 MEMORY.md
  例: "發現全新的市場需求"
  → 寫入 insights/ 並同步更新 MEMORY.md
```

### Insight 生命週期

```
draft (草稿)
  ↓ 條件: 該模式連續出現 3 次以上
confirmed (確認)
  ↓ 條件: 90 天內未被引用且未被驗證
deprecated (過時)
  ↓ 條件: 被新 insight 取代或環境變化導致失效
archived (歸檔)
  → 移入 memory/archive/
```

---

## Insight 文件格式

```yaml
---
topic: "科技主題最佳 CFG 參數"
category: insight
created: 2026-03-27
last_updated: 2026-03-27
importance: high
importance_score: 7
confidence: medium
status: draft
source: realtime_aar              # 來源標記: realtime_aar（即時萃取）或 sleep_deep（睡眠模式深度萃取）
tags: [wirestock, comfyui, cfg, 科技抽象, 參數優化]
summary: "科技抽象主題使用 CFG=8 配合 euler_a 採樣器，品質穩定性最高"
evidence_count: 3
last_validated: 2026-03-27
contradiction_count: 0
application_count: 0
positive_outcome_count: 0
source_events:
  - memory/metrics/batch_report_2026-03-25.json
  - memory/metrics/batch_report_2026-03-26.json
  - memory/metrics/batch_report_2026-03-27.json
---

# 科技主題最佳 CFG 參數

## 規則
科技抽象主題使用以下參數組合時，品質穩定性最高：
- CFG Scale: 8
- 採樣器: euler_a
- 步數: 30
- Cyber Graphic LoRA 權重: 0.7

## 證據
- 2026-03-25: CFG=8 通過率 100%，CFG=10 通過率 60%
- 2026-03-26: CFG=8 平均分 8.9，CFG=7 平均分 8.2
- 2026-03-27: CFG=8 連續第 3 天保持 90%+ 通過率

## 適用範圍
- 主題: 科技抽象
- 模型: rinIllusion + Cyber Graphic LoRA
- 精煉解析度: 1280x1280 (方形) / 900x1400 (人像)
- 最終解析度: 4x Upscale

## 已知限制
- 尚未測試不同畫布類型下是否仍然成立
- LoRA 權重變化時 CFG 最佳值可能需要連動調整

## 變更歷史
- 2026-03-27: 初始建立 (draft)
```

---

## 自動萃取邏輯

### 模式偵測規則

```
規則 1: 重複模式偵測
  條件: 同一個 tag 在近 7 天的日誌/報告中出現 >= 3 次
  動作: 提取為 draft insight
  範例: "comfyui" + "hand_defect" 連續出現 → 提煉手部缺陷模式

規則 2: 顯著偏差偵測
  條件: 當日某指標偏離 7 天移動平均值 > 2 個標準差
  動作: 立即記錄為候選 insight，標記待分析
  範例: 科技主題通過率從 90% 驟降到 50%

規則 3: 成功策略偵測
  條件: 某個參數調整後，連續 3 張通過率提升
  動作: 提煉為參數優化 insight
  範例: 降低 LoRA 權重 0.1 後手部缺陷消失

規則 4: 跨主題相關性
  條件: 不同主題出現相同的缺陷模式或成功模式
  動作: 提煉為通用 insight（而非主題特定）
  範例: 所有主題在步數 < 25 時都出現品質下降

規則 5: 外部事件觸發
  條件: WireStock 審核回饋、市場數據變化
  動作: 記錄為環境變化 insight
  範例: WireStock 開始拒絕某類風格的圖片
```

### 自我矛盾偵測

```
當新 insight 與現有 insight 矛盾時:

1. 標記矛盾:
   - 在兩個 insight 的 YAML 中互相引用
   - contradiction_count += 1

2. 優先保留證據更多的:
   - 比較 evidence_count
   - 比較 positive_outcome_count

3. 如果無法判斷:
   - 兩者都保留但降低 confidence
   - 標記為 needs_review: true
   - 通知 LXYA 人工判斷
```

---

## 與記憶觀測模組（03）的聯動

### 觀測 → 萃取的數據流

```
03-memory-observation 記錄的 insight_reference 事件
  ↓
本模組在 AAR 中讀取這些事件
  ↓
更新被引用 insight 的 application_count 和 positive_outcome_count
  ↓
據此判斷 insight 的實際效用
  ↓
效用低的 insight 降級，效用高的升級
```

### 循環改進

```
記憶 → 引用 → 效果追蹤 → 品質評估 → 改進萃取邏輯

這個循環本身就是記憶系統研究的核心觀測對象:
- insight 的「存活率」: 多少 draft 能晉升為 confirmed？
- insight 的「實用率」: 被引用且產生正面效果的比例？
- insight 的「保鮮期」: 從建立到過時的平均天數？
```

---

## 待確認事項

1. ~~**萃取頻率**~~：✅ 每日 AAR 足夠，未來再視需求優化
2. ~~**自動化 vs 人工**~~：✅ 全部自動化，這是 Agent 自主進化的考驗。不需要 LXYA 手動介入萃取判斷
3. ~~**Insight 數量控制**~~：✅ 初期不限制數量，但在週報中加入 insight 健康指標（總數、本週新增、draft/confirmed 比例），有數據依據後再決定是否需要控制
4. ~~**與 Phase 3.5 的分工**~~：✅ 允許重複。即時萃取產出的 insight 標記 `source: realtime_aar`，睡眠模式深度萃取標記 `source: sleep_deep`，未來可按標記篩選去重
5. ~~**矛盾處理策略**~~：✅ 自動降級，不需要人為判斷參與。矛盾 insight 自動降級為 draft 狀態，由後續 AAR 自行驗證和解決
