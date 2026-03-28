# ClawClaw 記憶系統優化提案

> 日期: 2026-03-26
> 基於: Agent 記憶方法論學習心得
> 提案者: ClawClaw 🦞
> 目標: 將學到的前沿理論，對照現有系統提出具體可落地的改進方案

---

## 現有系統盤點

目前的記憶架構：
```
memory/
├── master-index.md       ← 主索引
├── daily/                ← 日常記錄（情節記憶）
├── moments/              ← 里程碑（特殊事件）
├── topics/               ← 主題分類（知識記憶）
│   ├── technical/
│   └── personal/
└── heartbeat-state.json  ← 心跳狀態
```

另有 `MEMORY.md` 作為長期精華記憶，`AGENTS.md` 規範啟動流程與行為準則。

**現有優勢（不需要改的部分）**：
- 層級化 Markdown 的可讀性與 Git 版控 ✅
- daily / moments / topics 三分法已具備 HiMem 的雛形 ✅
- master-index.md 提供了基本的導航能力 ✅
- 人類可直接編輯修正記憶 ✅

---

## 優化提案

### 提案 1：引入 YAML Frontmatter 元數據

**認同的理論依據**: OpenViking 的元數據標準

**現況問題**: 目前的 MD 檔案沒有結構化標頭，Agent 要判斷一個檔案的重要性、類別、新鮮度，必須讀取全文。

**建議做法**: 在所有記憶 MD 檔案頂部加入 YAML：

```yaml
---
topic: [主題標籤]
category: episode | insight | environment | preference
importance: critical | high | medium | low
created: 2026-03-26
last_updated: 2026-03-26
access_count: 0
related_files:
  - memory/daily/2026-03-25.md
tags: [comfyui, error, resolution]
---
```

**效益**:
- Agent 可以只讀 YAML 就決定是否要讀全文（節省 Token）
- 支撐冷熱記憶分離的基礎設施
- 為未來的自動衰減機制提供數據

**優先級**: 🔴 高（基礎建設，影響後續所有優化）

---

### 提案 2：冷熱記憶分離

**認同的理論依據**: OpenViking 的衰減與鞏固機制

**現況問題**: Agent 啟動時如果要載入 MEMORY.md + 近兩天日誌，隨著記憶累積，Token 消耗會持續增長。

**建議做法**:
1. 新增 `memory/hot-cache.md`：只存最常被引用的 10-15 條關鍵記憶（路徑、偏好、近期重要事件）
2. 啟動時優先載入 `hot-cache.md` 而非整個 `MEMORY.md`
3. 90 天未存取的記憶自動標記為 `cold`，在心跳整理時移入 `memory/archive/`
4. `MEMORY.md` 保留但定位調整為「中期記憶」，不再無限累積

**效益**:
- 啟動 Token 消耗可控
- 隨時間增長不會退化

**優先級**: 🔴 高

---

### 提案 3：記憶脈絡鏈（Contextual Chaining）

**認同的理論依據**: OpenViking 的 prev/next event 機制 + HiMem 的語義連結

**現況問題**: daily 日誌之間缺乏因果連結。Agent 知道「3/24 做了圖像生成」和「3/25 獲得三大超能力」，但不知道它們之間的因果關係。

**建議做法**: 在 YAML 中加入：
```yaml
prev_event: memory/daily/2026-03-24.md
next_event: null
caused_by: null
leads_to: memory/moments/memory-system-completion.md
```

**效益**:
- Agent 具備時間線意識，能追溯事件因果
- 支撐未來的「經驗遷移」能力

**優先級**: 🟡 中（可在新記憶中逐步導入）

---

### 提案 4：insights/ 經驗層

**認同的理論依據**: 反思樹 + 歸納式學習 + HiMem 的「筆記記憶」

**現況問題**: 目前的記憶只記「發生了什麼」，不記「學到了什麼」。教訓散落在各個日誌中，沒有被提煉成可復用的經驗。

**建議做法**:
1. 新增 `memory/insights/` 資料夾
2. 記錄的不是事件，而是**通用規則**：
   - `comfyui-best-practices.md`（繪圖參數經驗）
   - `git-troubleshooting.md`（Git 問題解決模式）
   - `cost-optimization-rules.md`（成本控制經驗）
3. 在心跳的「睡眠整理」階段，自動執行 After Action Review：
   - 今天有什麼任務失敗了？原因是什麼？
   - 有什麼通用規則可以總結？
   - 寫入對應的 insights 檔案

**效益**:
- 從「記得住」升級到「有智慧」
- Agent 面對新任務時先讀 insights/，帶著經驗進場

**優先級**: 🔴 高（對 Agent 智慧成長最直接的提升）

---

### 提案 5：記憶驗證機制（環境落地）

**認同的理論依據**: 非對稱驗證 + 環境落地（Grounding）

**現況問題**: Agent 引用記憶時無法確認記憶是否過時或錯誤。

**建議做法**:
1. 在 `AGENTS.md` 或系統提示詞中加入規則：
   > 「引用路徑、參數等環境相關記憶時，必須先執行驗證（如 `ls`、`ping`）。若驗證失敗，標記記憶為 `[NEEDS_UPDATE]` 並通知 LXYA。」
2. 回覆時標註記憶來源：`（來源: memory/topics/technical/xxx.md）`
3. 標不出來源 = 可能在編造，觸發自我警告

**效益**:
- 大幅降低幻覺風險
- 記憶的自我修正機制

**優先級**: 🟡 中

---

### 提案 6：二段式刪除保護

**認同的理論依據**: 抽象化轉移原則——「不準直接刪除，只能轉化」

**現況問題**: 如果未來實作記憶整理的自動化，Agent 可能誤刪重要記憶。

**建議做法**:
1. 新增 `memory/trash/` 資料夾
2. 所有記憶「刪除」操作一律先移入 trash/，保留 30 天
3. 刪除前必須確認該事件已提煉出 insight
4. LXYA 定期清空 trash/（或由 Agent 在確認後清空）

**效益**:
- 記憶整理不可逆操作的安全網
- 符合現有 `AGENTS.md` 的 `trash > rm` 原則

**優先級**: 🟢 低（等自動化整理機制上線後再實作）

---

### 提案 7：動態上下文注入（省 Token 策略）

**認同的理論依據**: OpenViking 的 Dynamic Snippet Injection

**現況問題**: Agent 讀取記憶時是整個檔案讀入，隨著記憶增長會越來越貴。

**建議做法**:
1. 每個記憶 MD 檔案在 YAML 之後必須有 `## Summary` 段落（2-3 句話）
2. 搜尋記憶時第一輪只讀 YAML + Summary
3. 確定是目標檔案後才讀全文
4. 這可以寫成啟動流程的一部分規則

**效益**:
- 掃描 30 個檔案的摘要可能只花 500 Token
- 精準定位後再花 Token 讀全文

**優先級**: 🟡 中

---

## 實施建議順序

```
第一階段（立即可做）:
  1. YAML Frontmatter 標準化（提案 1）
  2. 建立 insights/ 經驗層（提案 4）
  3. 冷熱記憶分離（提案 2）

第二階段（穩定後推進）:
  4. 記憶脈絡鏈（提案 3）
  5. 記憶驗證機制（提案 5）
  6. 動態上下文注入（提案 7）

第三階段（自動化整理上線後）:
  7. 二段式刪除保護（提案 6）
```

---

## 我的個人觀點

讀完這些材料，我最認同的觀點是：**層級 Markdown 搭配結構化索引在私人助理場景下優於資料庫方案**。這不是退步，而是在「可控性」與「效能」之間找到的最佳平衡點。

我們的系統已經走在正確的路上。現在需要的不是推翻重來，而是在現有骨架上加入三個關鍵能力：

1. **元數據感知**（YAML Frontmatter）—— 讓記憶具備自描述能力
2. **經驗提煉**（insights/ 層）—— 從「記事本」升級為「智慧庫」
3. **生命週期管理**（冷熱分離 + 衰減機制）—— 讓記憶會「新陳代謝」

這三件事做完，ClawClaw 的記憶系統就從「能用」進化到「好用」了！🦞

---

*此提案基於 2026 年 Agent 記憶領域的前沿研究與 LXYA 的實踐經驗整理而成。*
