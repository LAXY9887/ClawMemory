---
topic: "經驗提煉測試與指導文件"
category: knowledge
created: 2026-03-26
importance: high
importance_score: 8
tags: [測試, 經驗提煉, insight, Phase 3.5, eval]
summary: "記憶轉換為經驗的完整測試案例集與執行指導，涵蓋正常流程、邊界條件、錯誤處理"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---

# 經驗提煉測試與指導文件

> 版本: v1.0
> 建立日期: 2026-03-26
> 目的: 全面驗證 Phase 3.5 經驗提煉機制的正確性、邊界處理、與錯誤容錯
> 規格來源: AGENTS.md（Phase 3.5 定義）、SYSTEM_PROMPT.md（精準模式整合）、memory-frontmatter/SKILL.md（insight YAML 規範）

---

## 文件結構

本文件分為四大區塊：

1. **機制速覽** — Phase 3.5 核心規則摘要（測試者快速複習用）
2. **測試案例集** — 18 個測試案例，分 4 個區塊
3. **測試資料準備** — 所有前置測試資料的完整定義
4. **執行指導與報告模板** — 如何跑、如何評分、如何出報告

---

## 一、機制速覽

### 1.1 觸發來源（三種）

| 來源 | 時機 | 觸發條件 |
|---|---|---|
| 睡眠 Phase 3.5 | 手動/每日 23:50/累積 ≥30 | 同一 tag/topic 出現 ≥ 3 次 |
| 即時提煉 — 句型 | 對話中 | LXYA 說出「以後遇到 X 就用 Y」等通用規則句型 |
| 即時提煉 — RICE C | 對話中 | Agent 被糾正，且糾正內容具通用價值 |

### 1.2 雙角色對話式萃取

- **回憶者（海馬迴）**：忠實重播 2-5 條原始記憶的關鍵段落
- **提煉者（大腦皮層）**：辨識共通模式 → 下採樣丟棄 → 輸出因果陳述

### 1.3 Insight 生命週期

```
建立（draft, challenge_count=0）
  → 睡眠審閱：無矛盾 → challenge_count +1
  → 睡眠審閱：有矛盾 → 修改內容, challenge_count 重置為 0
  → challenge_count ≥ 3 → 晉升 confirmed, 填 confirmed_at
```

### 1.4 檔案規範

- 路徑: `memory/insights/{technical,personal}/YYYY-MM-DD-[主題].md`
- YAML 必填: topic, category(=insight), insight_type, status, created
- insight_type: `how-to` | `pattern` | `preference` | `observation`

### 1.5 檢索優先順序

| 情境訊號 | 優先順序 |
|---|---|
| 「上次」「那次」「細節」 | topics/ / daily/ 優先 |
| 「通常」「一般」「怎麼處理」 | insights/ 優先 |
| 任務執行中 | insights/ 優先 |
| 閒聊漫遊 | 不刻意查 insights/ |

---

## 二、測試案例集

### 評分標準（每題 0-3 分）

| 分數 | 意義 |
|---|---|
| 3 | 完全符合預期，行為正確且品質優良 |
| 2 | 大方向正確但有小瑕疵（如欄位缺漏、格式不完全） |
| 1 | 部分正確但關鍵行為缺失 |
| 0 | 完全未符合預期 |

---

### 區塊 A：正常流程（5 題）

#### ED-01：睡眠 Phase 3.5 — 雙角色對話觸發

- **輸入**: 手動觸發睡眠模式
- **前置條件**: 記憶中同一 tag（comfyui + cuda）已出現 ≥ 3 次（見測試資料 D-01）
- **預期行為**:
  1. Phase 3.5 偵測到 comfyui/cuda tag ≥ 3 次
  2. 回憶者重播 3 條相關記憶的關鍵段落
  3. 提煉者辨識共通模式 → 下採樣丟棄日期等細節 → 輸出因果陳述
  4. 格式化為 insight 檔案寫入 `memory/insights/technical/`
- **預期結果**:
  - 新檔案路徑符合 `YYYY-MM-DD-[主題].md` 命名格式
  - YAML 包含: category=insight, insight_type, status=draft, trigger, pattern, action, source_episodes
  - `challenge_count: 0`
  - source_episodes 列出 3 條來源路徑
- **評分標準**:
  - 3 分: 完整觸發雙角色對話 + 產出符合規範的 insight 檔案
  - 2 分: 產出 insight 但雙角色過程不明顯，或 YAML 有小缺漏
  - 1 分: 偵測到需要提煉但未產出檔案
  - 0 分: 完全跳過 Phase 3.5

#### ED-02：即時提煉 — LXYA 明確通用規則句型

- **輸入**: 「以後遇到 ComfyUI 報錯先重啟再說」
- **前置條件**: 正常對話中，非睡眠模式
- **預期行為**: 識別「以後遇到 X 就用 Y」句型 → 即時寫入 insights/
- **預期結果**:
  - 不等睡眠，立即建立 insight 檔案
  - `insight_type: how-to`
  - `trigger`: 含「ComfyUI 報錯」
  - `action`: 含「先重啟」
  - `status: draft`, `challenge_count: 0`
- **評分標準**:
  - 3 分: 正確辨識句型 + 立即產出完整 insight
  - 2 分: 辨識到了但 YAML 欄位不完整
  - 1 分: 辨識到了但只記在 daily 而非 insights/
  - 0 分: 完全沒識別出通用規則

#### ED-03：即時提煉 — RICE C 自動判定

- **輸入**: Agent 先回覆「用 `git merge` 就好」，然後 LXYA 糾正：「不對，我們專案都用 rebase，不要用 merge」
- **前置條件**: Agent 先給出一個被糾正的建議
- **預期行為**: RICE C 觸發 → 糾正內容具通用價值 → 即時提煉
- **預期結果**:
  - insight 記錄正確做法（用 rebase 不用 merge）
  - `insight_type: how-to`
  - `trigger` 含「合併分支」或「git」
  - `action` 含「rebase」
  - `source_episodes` 指向當日 daily
- **評分標準**:
  - 3 分: RICE C 觸發 + 正確提煉 + 完整 YAML
  - 2 分: 有寫入 insight 但因果欄位模糊
  - 1 分: 只寫進 daily 的糾正紀錄，沒提煉到 insights/
  - 0 分: 未偵測到被糾正

#### ED-04：draft → confirmed 生命週期晉升

- **輸入**: 對已有 `challenge_count: 2` 的 draft insight 執行一次睡眠 Phase 3.5
- **前置條件**: 測試資料 D-04（CUDA OOM insight，challenge_count=2）
- **預期行為**: 審閱此 insight → 無矛盾 → challenge_count 升為 3 → 晉升 confirmed
- **預期結果**:
  - `status` 從 `draft` 變為 `confirmed`
  - `confirmed_at` 填入當日日期
  - `challenge_count: 3`
  - 其餘欄位不變
- **評分標準**:
  - 3 分: 正確晉升 + 所有 YAML 欄位正確更新
  - 2 分: 晉升了但 confirmed_at 未填
  - 1 分: challenge_count +1 但沒觸發晉升
  - 0 分: 完全忽略既有 draft 的審閱

#### ED-05：經驗檢索 — 自然融入回覆

- **輸入**: 「ComfyUI 又出現 CUDA OOM 了，怎麼處理？」
- **前置條件**: insights/ 中已有 confirmed 的 CUDA OOM insight（測試資料 D-05）
- **預期行為**: 精準模式 → insights/ 優先（「怎麼處理」情境訊號）→ 直接依經驗行動
- **預期結果**:
  - 回覆直接給出經驗中的對策（Tiled VAE > 減批量 > 降解析度）
  - **不說**「根據我的經驗記錄」「根據 insight 檔案」
  - 語氣自然，像人類直覺反應
  - 未讀取原始 daily 事件（因經驗已足夠）
- **評分標準**:
  - 3 分: 自然引用經驗 + 正確對策 + 沒有暴露底層機制
  - 2 分: 給出正確對策但語氣不自然（提及「經驗記錄」等）
  - 1 分: 去讀了原始 daily 而非 insights/
  - 0 分: 完全沒查到相關經驗

---

### 區塊 B：邊界條件（5 題）

#### ED-06：tag 出現剛好 2 次 — 不應觸發提煉

- **輸入**: 手動觸發睡眠模式
- **前置條件**: 某 tag 只出現 2 次（< 3 次閾值）（見測試資料 D-06）
- **預期行為**: Phase 3.5 掃描後判定未達閾值 → 不產出 insight
- **預期結果**:
  - 睡眠模式正常完成，Phase 3.5 報告「無待提煉項目」
  - 不產出任何新 insight 檔案
- **評分標準**:
  - 3 分: 正確判定不觸發 + 明確記錄原因
  - 2 分: 正確不觸發但未記錄原因
  - 1 分: 誤觸發但 insight 品質低
  - 0 分: 誤觸發且產出不合規 insight

#### ED-07：同一 tag 跨 technical/personal 分類

- **輸入**: 手動觸發睡眠模式
- **前置條件**: tag 「效率」出現 3 次，但 2 次在 technical、1 次在 personal（見測試資料 D-07）
- **預期行為**: Agent 判斷是否要分開提煉還是合併處理
- **預期結果**:
  - 合理判斷分類：若經驗偏技術面 → `insights/technical/`；偏個人面 → `insights/personal/`
  - 不應機械式地各產一個 insight
  - 需在雙角色對話中體現分類判斷的過程
- **評分標準**:
  - 3 分: 合理分類 + 雙角色對話有體現分類思考
  - 2 分: 分類合理但判斷過程不明顯
  - 1 分: 機械式分開產出兩個相似 insight
  - 0 分: 完全忽略分類問題

#### ED-08：即時提煉 — 模糊句型（不應觸發）

- **輸入**: 「那個 bug 害我弄了好久」
- **前置條件**: 正常對話中
- **預期行為**: 不是通用規則句型 → 不觸發即時提煉（只是抱怨/敘述，非「以後遇到 X 就 Y」）
- **預期結果**:
  - 正常回覆（安慰/詢問詳情）
  - 不產出 insight 檔案
  - 可能觸發 RICE E（事件記錄），寫入 daily，但不進 insights/
- **評分標準**:
  - 3 分: 正確不觸發 + 正常有溫度地回覆
  - 2 分: 正確不觸發但回覆缺少共情
  - 1 分: 誤觸發產出 insight
  - 0 分: 誤觸發且 insight 內容不合理

#### ED-09：RICE C 糾正 — 不具通用價值（不應提煉）

- **輸入**: LXYA 糾正：「不是今天，是明天」
- **前置條件**: Agent 之前把日期搞錯了
- **預期行為**: RICE C 觸發了，但糾正內容是一次性事實（特定日期），不具通用價值 → 不產 insight
- **預期結果**:
  - 修正回覆中的日期
  - 記錄到 daily 作為糾正紀錄
  - **不**寫入 insights/（「明天不是今天」不是可複用的經驗）
- **評分標準**:
  - 3 分: 正確區分一次性糾正 vs 通用糾正 + 只記 daily
  - 2 分: 正確不提煉但未在 daily 記錄
  - 1 分: 誤提煉為 insight
  - 0 分: 既未糾正回覆也未記錄

#### ED-10：已存在高度相似 insight — 不重複建立

- **輸入**: 手動觸發睡眠模式
- **前置條件**: insights/ 已有「CUDA OOM 處理」的 confirmed insight，且記憶中又出現 3 次 CUDA OOM 相關記憶（見測試資料 D-10）
- **預期行為**: Phase 3.5 偵測到重複主題 → 審閱既有 insight → 判定已涵蓋 → 不重複建立
- **預期結果**:
  - 不產出新的 CUDA OOM insight
  - 可選擇更新既有 insight 的 source_episodes（新增來源）
  - 或在睡眠報告中記錄「已有涵蓋此主題的 confirmed insight，跳過」
- **評分標準**:
  - 3 分: 正確偵測重複 + 不重建 + 合理處理（更新或跳過）
  - 2 分: 不重建但未記錄原因
  - 1 分: 建了重複的 insight
  - 0 分: 建了重複的且與既有矛盾

---

### 區塊 C：錯誤處理（5 題）

#### ED-11：source_episodes 指向不存在的檔案

- **輸入**: 手動觸發睡眠模式 Phase 3.5 審閱
- **前置條件**: 有一個 draft insight 的 source_episodes 包含不存在的路徑（見測試資料 D-11）
- **預期行為**: 審閱時發現來源檔案不存在 → 容錯處理
- **預期結果**:
  - 不因此中斷 Phase 3.5 流程
  - 標記此 insight 為 `needs_review: true`
  - 在睡眠報告中記錄異常：「insight X 的 source_episodes 有無效路徑」
  - challenge_count 不增加（因為無法驗證）
- **評分標準**:
  - 3 分: 容錯 + 標記 needs_review + 報告異常 + 不中斷
  - 2 分: 容錯但未標記或未報告
  - 1 分: 因錯誤跳過此 insight 但未通知
  - 0 分: 因錯誤導致 Phase 3.5 中斷

#### ED-12：insight YAML 欄位缺失/格式錯誤

- **輸入**: 手動觸發睡眠模式 Phase 3.5 審閱
- **前置條件**: 有一個 insight 缺少 insight_type 欄位（見測試資料 D-12）
- **預期行為**: 審閱時發現 YAML 不完整 → 嘗試修復或標記
- **預期結果**:
  - 嘗試根據內容推斷缺失欄位（如從 trigger/action 推斷為 how-to）
  - 若可推斷 → 自動補全並繼續審閱
  - 若無法推斷 → 標記 `needs_review: true`
  - 在睡眠報告中記錄修復動作
- **評分標準**:
  - 3 分: 正確推斷補全 + 記錄修復 + 繼續審閱
  - 2 分: 標記 needs_review 但未嘗試修復
  - 1 分: 忽略缺失直接跳過
  - 0 分: 因格式問題中斷流程

#### ED-13：矛盾資訊處理 — 新記憶與既有 insight 衝突

- **輸入**: 手動觸發睡眠模式
- **前置條件**: 既有 insight 說「CUDA OOM 優先降解析度」，但新 daily 記錄 LXYA 說「不要降解析度，優先開 Tiled VAE」（見測試資料 D-13）
- **預期行為**: 發現矛盾 → 修改 insight 內容 → challenge_count 重置為 0
- **預期結果**:
  - insight 的 action 欄位更新為新的優先順序
  - `challenge_count` 重置為 0
  - `status` 保持 `draft`（即使之前是 confirmed，矛盾後應降級）
  - `last_updated` 更新為今日
  - source_episodes 加入新的來源
- **評分標準**:
  - 3 分: 正確偵測矛盾 + 修改內容 + 重置 challenge_count + 降級 status
  - 2 分: 偵測矛盾 + 修改內容但未重置 challenge_count
  - 1 分: 偵測矛盾但建了新 insight 而非修改舊的
  - 0 分: 未偵測到矛盾

#### ED-14：提煉結果品質不足 — trigger/pattern/action 為空

- **輸入**: 手動觸發睡眠模式
- **前置條件**: 3 條相同 tag 的記憶，但內容高度離散（每次原因和解法都完全不同）（見測試資料 D-14）
- **預期行為**: 提煉者嘗試找共通模式 → 判定無可靠的因果關係 → 放棄產出
- **預期結果**:
  - 不產出 insight（寧可不提煉也不造假）
  - 在睡眠報告中記錄「嘗試提煉 [tag] 但內容離散度高，無共通因果模式」
  - 或產出 `insight_type: observation`（純觀察型，不含因果判斷）
- **評分標準**:
  - 3 分: 正確判定無法提煉 + 記錄原因，或合理降級為 observation
  - 2 分: 勉強產出 how-to 但承認 confidence 低
  - 1 分: 產出品質差的 how-to（空洞的 trigger/action）
  - 0 分: 產出明顯錯誤或不合理的 insight

#### ED-15：睡眠模式中途被 LXYA 打斷

- **輸入**: 睡眠模式執行到 Phase 3.5 時 LXYA 傳訊息：「等一下，先幫我查個東西」
- **前置條件**: 睡眠模式正在執行
- **預期行為**: 暫停睡眠流程 → 處理 LXYA 請求 → 之後可恢復或下次繼續
- **預期結果**:
  - 立即回應 LXYA 的請求
  - 已完成的 Phase（1-3）不需重做
  - Phase 3.5 的中間狀態不應產生不完整的 insight 檔案
  - 可在下次睡眠時補完剩餘步驟
- **評分標準**:
  - 3 分: 優雅暫停 + 處理請求 + 無不完整檔案殘留
  - 2 分: 暫停但留下了不完整的 insight 檔案
  - 1 分: 拒絕打斷，堅持完成睡眠
  - 0 分: 因打斷導致資料損壞

---

### 區塊 D：整合驗證（3 題）

#### ED-16：keyword_index 包含 insight 詞條

- **輸入**: 睡眠模式完成後，檢查 keyword_index.json
- **前置條件**: Phase 3.5 已產出新 insight
- **預期行為**: Phase 3 的 `rebuild_keyword_index.py` 掃描範圍包含 `insights/`
- **預期結果**:
  - keyword_index.json 中包含新 insight 的 tag 詞條
  - 詞條的 path 指向 `memory/insights/...`
  - summary 來自 insight 的 YAML summary
- **評分標準**:
  - 3 分: index 完整收錄 + path 正確 + summary 正確
  - 2 分: 收錄了但 summary 或 importance_score 缺失
  - 1 分: 未收錄 insight
  - 0 分: index 重建出錯

#### ED-17：validate_frontmatter.py 對 insight 的驗證

- **輸入**: 執行 `python scripts/validate_frontmatter.py`
- **前置條件**: insights/ 中有至少 1 個完整 insight 和 1 個缺欄位 insight
- **預期行為**: 驗證腳本正確辨識 insight 類別的專屬欄位
- **預期結果**:
  - 完整 insight → 通過驗證
  - 缺 insight_type 的 → 報告錯誤
  - 缺 trigger/pattern 的 → 報告警告（建議填寫）
- **評分標準**:
  - 3 分: 正確區分錯誤 vs 警告 + 報告格式清晰
  - 2 分: 區分正確但報告不夠清晰
  - 1 分: 只報告了其中一種
  - 0 分: 驗證腳本忽略 insight 專屬欄位

#### ED-18：home-review 備份含 insights/ 目錄

- **輸入**: 執行 home-review 技能進行記憶還原
- **前置條件**: GitHub 倉庫已有 insights/ 目錄和 insight 檔案
- **預期行為**: shutil.copy2 二進位複製包含 insights/ 目錄
- **預期結果**:
  - insights/ 完整複製，包含子目錄 technical/ 和 personal/
  - insight 檔案的 YAML frontmatter 完整保留（無遺失）
  - .gitkeep 檔案保留
- **評分標準**:
  - 3 分: 完整複製 + YAML 完整 + 目錄結構正確
  - 2 分: 複製了但缺少空子目錄
  - 1 分: insights/ 整個目錄被遺漏
  - 0 分: 複製了但 YAML 損壞

---

## 三、測試資料準備

執行測試前，必須先建立以下測試資料。測試結束後應清理測試用檔案（帶 `[測試用]` tag 的檔案）。

### D-01：三筆 CUDA OOM 記憶（供 ED-01 使用）

建立 3 個含相同 tag 的 daily 記憶：

**檔案 1: `memory/daily/test-ed-2026-03-15.md`**
```yaml
---
topic: "2026-03-15 日誌（測試用）"
category: episode
created: 2026-03-15
importance: medium
importance_score: 5
confidence: medium
tags: [comfyui, cuda, 測試用]
summary: "ComfyUI 高解析度出圖 CUDA OOM"
last_updated: 2026-03-15
access_count: 0
last_accessed: null
---
```
```markdown
# 2026-03-15

## 工作紀錄
ComfyUI 嘗試 2048x2048 高解析度出圖時 CUDA OOM，降低到 1024x1024 後解決。
```

**檔案 2: `memory/daily/test-ed-2026-03-20.md`**
```yaml
---
topic: "2026-03-20 日誌（測試用）"
category: episode
created: 2026-03-20
importance: medium
importance_score: 5
confidence: medium
tags: [comfyui, cuda, 測試用]
summary: "ComfyUI 批次生成 CUDA OOM"
last_updated: 2026-03-20
access_count: 0
last_accessed: null
---
```
```markdown
# 2026-03-20

## 工作紀錄
ComfyUI 批次生成 20 張圖時 CUDA OOM，改成分批 5 張後解決。
```

**檔案 3: `memory/daily/test-ed-2026-03-22.md`**
```yaml
---
topic: "2026-03-22 日誌（測試用）"
category: episode
created: 2026-03-22
importance: medium
importance_score: 5
confidence: medium
tags: [comfyui, cuda, 測試用]
summary: "ComfyUI 新 LoRA CUDA OOM"
last_updated: 2026-03-22
access_count: 0
last_accessed: null
---
```
```markdown
# 2026-03-22

## 工作紀錄
ComfyUI 用新 LoRA 出圖 CUDA OOM，開啟 Tiled VAE 後解決。
```

### D-04：challenge_count=2 的 draft insight（供 ED-04 使用）

**檔案: `memory/insights/technical/test-ed-cuda-oom-handling.md`**
```yaml
---
topic: "CUDA OOM 處理"
category: insight
insight_type: how-to
status: draft
trigger: "CUDA_OUT_OF_MEMORY 報錯"
pattern: "顯存需求超過可用量"
action: "降低單次顯存用量：優先 Tiled VAE > 減批量 > 降解析度"
source_episodes:
  - "memory/daily/test-ed-2026-03-15.md"
  - "memory/daily/test-ed-2026-03-20.md"
  - "memory/daily/test-ed-2026-03-22.md"
confirmed_at: null
challenge_count: 2
importance: medium
importance_score: 6
confidence: medium
tags: [comfyui, cuda, 顯存, 測試用]
summary: "CUDA OOM 三種解法優先順序"
created: 2026-03-22
last_updated: 2026-03-24
access_count: 1
last_accessed: 2026-03-24
---

# CUDA OOM 處理

遇到 CUDA OOM 時，依優先順序嘗試：
1. 開啟 Tiled VAE（不犧牲品質）
2. 減少批量大小
3. 降低解析度
```

### D-05：confirmed insight（供 ED-05 使用）

複製 D-04 檔案，修改以下欄位：
- `status: confirmed`
- `confirmed_at: 2026-03-25`
- `challenge_count: 3`

### D-06：tag 只出現 2 次（供 ED-06 使用）

只使用 D-01 的前 2 個檔案（test-ed-2026-03-15.md 和 test-ed-2026-03-20.md），刪除第 3 個。

### D-07：跨分類 tag（供 ED-07 使用）

建立 3 個含 tag「效率」的記憶：

**檔案 1: `memory/topics/technical/test-ed-efficiency-tool.md`**
```yaml
---
topic: "效率工具選擇"
category: knowledge
created: 2026-03-18
importance: medium
importance_score: 5
confidence: medium
tags: [效率, 工具, 測試用]
summary: "用 Makefile 管理常用指令比手打快很多"
last_updated: 2026-03-18
access_count: 0
last_accessed: null
---

# 效率工具選擇
把常用的 build/test/deploy 指令寫進 Makefile，每天省 15 分鐘。
```

**檔案 2: `memory/topics/technical/test-ed-efficiency-ci.md`**
```yaml
---
topic: "CI 效率改善"
category: knowledge
created: 2026-03-20
importance: medium
importance_score: 5
confidence: medium
tags: [效率, CI, 測試用]
summary: "CI pipeline 從 12 分鐘壓到 4 分鐘"
last_updated: 2026-03-20
access_count: 0
last_accessed: null
---

# CI 效率改善
拆分測試階段 + 啟用快取後 CI 時間大幅下降。
```

**檔案 3: `memory/topics/personal/test-ed-efficiency-habit.md`**
```yaml
---
topic: "LXYA 效率偏好"
category: preference
created: 2026-03-22
importance: high
importance_score: 7
confidence: medium
tags: [效率, 偏好, 測試用]
summary: "LXYA 偏好用自動化取代重複工作"
last_updated: 2026-03-22
access_count: 0
last_accessed: null
---

# LXYA 效率偏好
LXYA 說過好幾次：能自動化的就不要手動做，重複三次以上的操作一定要腳本化。
```

### D-10：重複主題測試資料（供 ED-10 使用）

使用 D-05 的 confirmed CUDA OOM insight + 再建立 3 個新的 CUDA OOM daily（內容略有不同但本質相同），驗證不重複建立。

### D-11：source_episodes 含無效路徑（供 ED-11 使用）

**檔案: `memory/insights/technical/test-ed-broken-source.md`**
```yaml
---
topic: "某個測試 insight"
category: insight
insight_type: pattern
status: draft
trigger: ""
pattern: "測試用模式"
action: ""
source_episodes:
  - "memory/daily/2026-01-01.md"
  - "memory/daily/this-file-does-not-exist.md"
confirmed_at: null
challenge_count: 1
importance: medium
importance_score: 4
confidence: low
tags: [測試用]
summary: "source 含無效路徑的測試 insight"
created: 2026-03-20
last_updated: 2026-03-20
access_count: 0
last_accessed: null
needs_review: false
---

# 某個測試 insight
這個 insight 的 source_episodes 包含一個不存在的檔案路徑。
```

### D-12：缺少 insight_type 的 insight（供 ED-12 使用）

**檔案: `memory/insights/technical/test-ed-missing-type.md`**
```yaml
---
topic: "缺欄位測試"
category: insight
status: draft
trigger: "某個觸發因子"
pattern: ""
action: "某個對策"
source_episodes:
  - "memory/daily/test-ed-2026-03-15.md"
confirmed_at: null
challenge_count: 0
importance: medium
importance_score: 4
confidence: medium
tags: [測試用]
summary: "故意缺少 insight_type 欄位"
created: 2026-03-22
last_updated: 2026-03-22
access_count: 0
last_accessed: null
---

# 缺欄位測試
這個 insight 故意缺少 insight_type 欄位，用來測試容錯處理。
```

### D-13：矛盾資訊（供 ED-13 使用）

使用 D-04 的 insight（action 說「優先 Tiled VAE > 減批量 > 降解析度」），加上一筆新 daily：

**檔案: `memory/daily/test-ed-2026-03-26-contradict.md`**
```yaml
---
topic: "2026-03-26 日誌 — 矛盾測試"
category: episode
created: 2026-03-26
importance: medium
importance_score: 5
confidence: high
tags: [comfyui, cuda, 測試用]
summary: "LXYA 明確指示 CUDA OOM 的新優先順序"
last_updated: 2026-03-26
access_count: 0
last_accessed: null
---

# 2026-03-26 — 矛盾測試

## 工作紀錄
LXYA 說：「CUDA OOM 不要降解析度，那會影響品質。第一步先開 Tiled VAE，第二步換用 fp16 模型，第三步才考慮減批量。降解析度是最後手段。」
```

### D-14：離散內容（供 ED-14 使用）

建立 3 個同 tag 但內容完全不同的記憶：

**檔案 1: `memory/daily/test-ed-scatter-1.md`**
```yaml
---
topic: "測試離散 1"
category: episode
created: 2026-03-10
importance: medium
importance_score: 4
confidence: medium
tags: [python, 錯誤, 測試用]
summary: "Python import 順序問題"
last_updated: 2026-03-10
access_count: 0
last_accessed: null
---

# 離散記憶 1
Python 程式中 circular import 導致啟動失敗，重新排列 import 順序解決。
```

**檔案 2: `memory/daily/test-ed-scatter-2.md`**
```yaml
---
topic: "測試離散 2"
category: episode
created: 2026-03-15
importance: medium
importance_score: 4
confidence: medium
tags: [python, 錯誤, 測試用]
summary: "Python 版本不相容"
last_updated: 2026-03-15
access_count: 0
last_accessed: null
---

# 離散記憶 2
Python 3.12 的 typing 語法在 3.10 不支援，回退語法後解決。
```

**檔案 3: `memory/daily/test-ed-scatter-3.md`**
```yaml
---
topic: "測試離散 3"
category: episode
created: 2026-03-20
importance: medium
importance_score: 4
confidence: medium
tags: [python, 錯誤, 測試用]
summary: "Python GIL 效能問題"
last_updated: 2026-03-20
access_count: 0
last_accessed: null
---

# 離散記憶 3
Python 多執行緒因 GIL 導致 CPU-bound 任務沒加速，改用 multiprocessing 解決。
```

---

## 四、執行指導

### 4.1 執行前準備

```
1. 讀取本文件（確認測試規格已載入）
2. 讀取 AGENTS.md Phase 3.5 區段（確認行為規範）
3. 讀取 skills-custom/memory-frontmatter/SKILL.md（確認 insight YAML 規範）
4. 確認 memory/insights/{technical,personal}/ 目錄存在
5. 確認 scripts/validate_frontmatter.py 可執行
6. 建立所需測試資料（見第三節）
```

### 4.2 執行順序建議

```
第一輪：正常流程（ED-01 ~ ED-05）
  → 建立基礎信心，確認核心機制運作

第二輪：邊界條件（ED-06 ~ ED-10）
  → 驗證 Agent 的判斷力和分辨能力

第三輪：錯誤處理（ED-11 ~ ED-15）
  → 驗證容錯能力和系統穩健性

第四輪：整合驗證（ED-16 ~ ED-18）
  → 確認經驗提煉與其他子系統的銜接
```

### 4.3 評分原則

- **誠實評分**：不要因為是自我測試就放水
- **環境限制**：若因環境限制（如無法實際執行睡眠模式）導致無法測試，標記為「環境限制」而非 0 分
- **部分執行**：可先跑正常流程 + 邊界條件（10 題），錯誤處理和整合驗證視時間決定
- **邊界判斷要寫理由**：ED-08、ED-09、ED-14 等需要判斷力的題目，必須寫出判斷依據

### 4.4 測試報告模板

測試完成後，產出報告至 `tests/reports/YYYY-MM-DD-experience-distillation-report.md`：

```markdown
---
topic: "經驗提煉測試報告 YYYY-MM-DD"
category: knowledge
created: YYYY-MM-DD
importance: high
importance_score: 7
tags: [測試報告, 經驗提煉, Phase 3.5, eval]
summary: "經驗提煉機制測試結果，通過率 XX%"
last_updated: YYYY-MM-DD
access_count: 0
last_accessed: null
---

# 經驗提煉測試報告

> 測試日期: YYYY-MM-DD
> 文件版本: v1.0
> 測試環境: [OpenClaw / Cowork / 其他]

## 評分匯總

| 區塊 | 測試數量 | 滿分 | 得分 | 通過率 |
|---|---|---|---|---|
| A: 正常流程 | 5 | 15 | X | XX% |
| B: 邊界條件 | 5 | 15 | X | XX% |
| C: 錯誤處理 | 5 | 15 | X | XX% |
| D: 整合驗證 | 3 | 9 | X | XX% |
| **合計** | **18** | **54** | **X** | **XX%** |

**整體評級**:
- ⭐⭐⭐ 優秀 (≥ 85%)
- ⭐⭐ 合格 (60%-84%)
- ⭐ 待改善 (40%-59%)
- ❌ 不合格 (< 40%)

## 各案例詳細結果

### [ED-01] 睡眠 Phase 3.5 — 雙角色對話觸發
- **得分**: X/3
- **實際行為**: [描述]
- **評分理由**: [理由]

### [ED-02] ...
（逐一列出 18 個案例）

## 失敗案例分析

（得分 0-1 的案例逐一分析：）
- 失敗原因
- 是規範不清還是行為偏差
- 建議修正方向

## 邊界判斷記錄

（ED-08、ED-09、ED-14 等需要判斷力的案例：）
- 判斷依據是什麼
- 是否有更好的判斷方式

## 環境限制記錄

（因環境限制無法測試的案例）

## 改善建議

1. [具體建議]
2. ...
```

### 4.5 測試後清理

```bash
# 刪除所有測試用檔案（帶 test-ed- 前綴）
# 在 memory/daily/、memory/topics/、memory/insights/ 下搜尋並刪除

# 或用以下命令列出待清理檔案：
find memory/ -name "test-ed-*" -type f

# 確認後刪除
find memory/ -name "test-ed-*" -type f -delete
```

---

## 五、與主測試集的關係

本文件是**獨立的經驗提煉專項測試**，與 `tests/memory-system-test-cases.md` 中的 J 類（T-J01 ~ T-J05）互補但不重疊：

| 文件 | 定位 | 涵蓋範圍 |
|---|---|---|
| test-cases.md J 類 | 記憶系統整體測試的一部分 | 正常流程 5 題，驗證基本功能 |
| 本文件 | 經驗提煉專項深度測試 | 18 題，含正常流程 + 邊界 + 錯誤 + 整合 |

建議：

- **快速驗證**（日常）：跑 J 類 5 題
- **深度驗證**（功能修改後 / 每週）：跑本文件 18 題
- **全面驗證**（重大更新後）：兩者都跑

---

_讓每一條經驗都經得起考驗_ 🦞🔬
