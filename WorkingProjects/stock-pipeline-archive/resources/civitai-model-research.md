---
topic: "Civitai 模型研究報告"
category: knowledge
created: 2026-03-26
importance: high
importance_score: 9
tags: [civitai, 模型研究, base-model, lora, controlnet]
summary: "為 WireStock 自動化項目研究 Civitai 上的 Base Model、LoRA 和 ControlNet 模型及其配置信息"
last_updated: 2026-03-26
---

# Civitai 模型研究報告
*為 WireStock 自動化項目收集最佳模型組合*

## 🎯 **研究目標**
1. 尋找與現有 rinIllusion 相容的 Base Model
2. 收集適用的 LoRA 模型和觸發關鍵字
3. 記錄 ControlNet 模型和建議參數
4. 建立完整的工作流程配置指南

## 📋 **Base Model 研究**

### 1. Stable Diffusion v1.5 ⭐⭐⭐⭐⭐
**連結**: https://civitai.com/models/155256/stable-diffusion-v15-bf16fp16-no-emaema-only-no-vae-safetensors-checkpoint
**下載URL**: https://civitai.com/api/download/models/[version_id]

**基本信息**:
- **類型**: Base Model (經典 SD1.5)
- **格式**: SafeTensors, bf16/fp16 
- **變體**: no-ema, ema-only, no-vae
- **來源**: CompVis | Stability AI | RunwayML
- **官方**: https://huggingface.co/runwayml/stable-diffusion-v1-5

**技術規格**:
- **解析度**: 512x512 (原生)
- **架構**: Stable Diffusion v1.x
- **VAE**: 需要額外下載 ft-mse-840000-ema-pruned
- **CLIP**: ViT-L/14 text encoder

**優勢分析**:
✅ **經典穩定**: SD1.5 是最成熟穩定的版本
✅ **LoRA 相容性**: 大量 SD1.5 LoRA 可用
✅ **硬體友好**: 相對較小，適合低端硬體
✅ **社群支持**: 最大的社群和資源
⚠️ **解析度限制**: 原生 512x512，需要升頻技術

**建議使用場景**:
- 🖼️ **經典風格**: 寫實、動漫、藝術風格
- 💻 **硬體受限**: 低 VRAM 環境
- 🔧 **快速原型**: 開發和測試工作流

### 2. FLUX.1-Dev ⭐⭐⭐⭐⭐
**連結**: https://civitai.com/models/618692/flux
**下載URL**: https://civitai.com/api/download/models/[version_id]

**基本信息**:
- **類型**: Rectified Flow Transformer 
- **參數**: 12 billion parameters
- **開發**: Black Forest Labs
- **授權**: flux-1-dev-non-commercial-license
- **官方**: https://huggingface.co/black-forest-labs/FLUX.1-dev

**技術規格**:
- **架構**: Rectified Flow Transformer (非 U-Net)
- **解析度**: 最高支援高解析度
- **訓練**: Guidance distillation training
- **品質**: Second only to FLUX.1 [pro]

**優勢分析**:
✅ **最新技術**: 先進的 Transformer 架構
✅ **頂級品質**: 接近商業級 FLUX.1 [pro]
✅ **提示跟隨**: 與閉源模型競爭的提示理解
✅ **開放研究**: 支持科學研究和藝術創新
⚠️ **硬體需求**: 12B 參數需要較多 VRAM
⚠️ **授權限制**: 非商業授權

**建議使用場景**:
- 🎨 **頂級品質**: 需要最高生成品質
- 🔬 **研究用途**: 學術研究和技術實驗
- 🖼️ **個人創作**: 個人藝術創作項目

### 3. Pony Diffusion V6 XL ⭐⭐⭐⭐
**連結**: https://civitai.com/models/257749/pony-diffusion-v6-xl
**下載URL**: https://civitai.com/api/download/models/[version_id]

**基本信息**:
- **類型**: SDXL Finetune
- **基礎**: Stable Diffusion XL 
- **特化**: 擬人化、動物、人形角色
- **評價**: 社群高度評價
- **支持**: SFW/NSFW 內容

**技術規格**:
- **Clip Skip**: 2 (重要！)
- **解析度**: SDXL 標準 (1024x1024+)
- **Sampler**: Euler a, 25 steps 建議
- **模板**: score_9, score_8_up, score_7_up...

**特殊標籤**:
```
品質標籤: score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up
風格標籤: source_pony, source_furry, source_cartoon, source_anime  
評級標籤: rating_safe, rating_questionable, rating_explicit
```

**優勢分析**:
✅ **角色專精**: 擅長角色生成和互動場景
✅ **風格多樣**: 支持多種美術風格
✅ **提示靈活**: 自然語言 + 標籤混合
✅ **無需負面提示**: 設計為不需要 negative prompt
⚠️ **特定領域**: 主要面向特定風格/內容

**建議使用場景**:
- 🐾 **角色設計**: 擬人化角色、動物角色
- 🎭 **故事插圖**: 角色互動場景
- 🎨 **多風格**: 卡通、動漫、毛絨風格

### 4. Illustrious-XL v2.0 ⭐⭐⭐⭐⭐ (最新版本)
**連結**: https://civitai.com/models/1369089/illustrious-xl-20
**官方網站**: https://www.illustrious-xl.ai/
**下載URL**: https://civitai.com/api/download/models/[version_id]

**版本比較**:
- **v0.1**: https://civitai.com/models/795765/illustrious-xl (原始版本)
- **v1.0**: https://civitai.com/models/1232765/illustrious-xl-10 (穩定版)
- **v1.1**: https://civitai.com/models/1252206/illustrious-xl-11 (改進版)  
- **v2.0**: https://civitai.com/models/1369089/illustrious-xl-20 (最新版) ⭐

**v2.0 基本信息**:
- **類型**: Illustrious Base Model (最新一代)
- **基礎**: 與 rinIllusion 同系列，完美相容！
- **數據集**: 大幅擴增，專注動畫和自然語言
- **更新**: 包含 2024-08 最新數據
- **穩定性**: 內部測試最佳微調穩定性

**v2.0 技術規格**:
- **架構**: SDXL-based (Stable Diffusion XL)
- **授權**: Illustrious License (商業友好)
- **作者**: OnomaAI Research Team
- **格式**: SafeTensor format
- **特色**: 自然語言 + 標籤雙模式提示
- **技術博客**: Illustrious XL Tech Blog

**v2.0 核心改進**:
✅ **數據集大幅擴增**: 包含更多動畫內容
✅ **自然語言增強**: 更好的自然語言理解
✅ **微調穩定性**: 內部測試最佳表現
✅ **相容性優化**: 更好的 LoRA 和合併相容性
✅ **去偏化處理**: 減少潛在偏見，更廣泛適用性

**與 rinIllusion 關係**:
✅ **完美相容**: 同 Illustrious 系列，100% 相容
✅ **升級選項**: rinIllusion 用戶的理想升級路徑
✅ **LoRA 通用**: 現有 LoRA 可直接使用
✅ **工作流延續**: 現有工作流可無縫遷移

**建議使用場景**:
- 👩‍🎨 **專業插畫**: 商業級插畫和動畫創作
- 🎨 **藝術創作**: 高品質藝術作品生成
- 🏢 **商業應用**: 完全支持商業用途
- 🔧 **LoRA 訓練**: 最佳的 LoRA 微調基底
- 🌟 **WireStock**: 理想的商業圖像生成基礎

## 🎨 **LoRA 模型研究**

✅ **詳細分析已完成** - 參見 `lora-models-analysis.md`

### 實際下載的 5 個 LoRA
1. **Horror & Creepy** (`Horror.safetensors`) - SD1.5，恐怖氛圍
2. **Creatures Design V1** (`CreaturesDesignV1.safetensors`) - SD1.5，怪物設計
3. **Cyberpunk Style** (`C7b3rp0nkStyle.safetensors`) - 通用，賽博龐克
4. **Abandoned Office DX** (`Abandoned_Office_DX_-_CyberRealistic_PONY.safetensors`) - Pony，場景設計
5. **Eldritch Creatures** (`eldritch_abomination.safetensors`) - Illustrious，Lovecraft 風格

### 三大市場策略匹配
- 🌟 **Horror Market**: Horror + Abandoned Office + Eldritch
- 🌟 **Tech Market**: Cyberpunk Style + SD1.5
- 🌟 **Creature Market**: Creatures Design + Eldritch

## 🎛️ **ControlNet 模型研究**

### 實際下載狀態
**檔案位置**: `C:\Users\USER\Documents\ComfyUI\models\controlnet`
**狀態**: ControlNet 模型已在下載中
**類型**: 預期包含 Canny、Depth、Pose 等基礎 ControlNet

## 📊 **Base Model 優先級排序**

### WireStock 自動化項目建議排序

#### 🥇 **第一優先: Illustrious-XL v2.0**
- **理由**: 與現有 rinIllusion 完美相容，最新技術，商業授權
- **用途**: 主力商業圖像生成
- **檔案**: illustrious-xl-v2.0.safetensors (約 6-7GB)

#### 🥈 **第二優先: SD1.5**  
- **理由**: 最大 LoRA 生態，硬體友好，經典穩定
- **用途**: 低資源環境，快速原型，經典風格
- **檔案**: stable-diffusion-v1-5.safetensors (約 4GB)

#### 🥉 **第三優先: Pony V6 XL**
- **理由**: 特定風格專精，角色生成優秀
- **用途**: 角色設計，動物/擬人化內容
- **檔案**: pony-diffusion-v6-xl.safetensors (約 6GB)

#### 🏅 **第四優先: FLUX.1-Dev**
- **理由**: 最新技術，頂級品質，但授權限制
- **用途**: 非商業研究，個人創作
- **檔案**: flux.1-dev.safetensors (約 12-15GB)

### 📝 **工作流程配置指南**

#### Illustrious-XL v2.0 配置
```yaml
模型設定:
  檔案: illustrious-xl-v2.0.safetensors
  VAE: Illustrious-XL v2.0 VAE (官方)
  路徑: /models/checkpoints/

生成參數:
  Steps: 25-35
  CFG Scale: 7-9  
  Sampler: DPM++ 2M Karras 或 Euler a
  Resolution: 1024x1024, 832x1216, 1216x832
  
提示格式:
  自然語言: "a beautiful landscape painting"
  標籤混合: "landscape, painting, masterpiece"
  品質提升: "high quality, detailed, professional"
```

#### SD1.5 配置
```yaml
模型設定:
  檔案: stable-diffusion-v1-5.safetensors
  VAE: vae-ft-mse-840000-ema-pruned.ckpt
  
生成參數:
  Steps: 20-30
  CFG Scale: 7-12
  Sampler: DPM++ 2M Karras
  Resolution: 512x512 (原生), 768x768 (升頻)
  
升頻建議:
  方法: Real-ESRGAN, SwinIR, Latent upscale
  倍率: 1.5x 到 2x
```

#### Pony V6 XL 配置
```yaml
重要設定:
  Clip Skip: 2 (必須！)
  
生成參數:
  Steps: 25
  CFG Scale: 7-9
  Sampler: Euler a
  Resolution: 1024x1024+
  
提示模板:
  品質: "score_9, score_8_up, score_7_up, score_6_up"
  風格: "source_anime" 或 "source_cartoon"
  評級: "rating_safe" (商業用途)
```

## 🔗 **下載連結整理**

### 立即下載建議 (LXYA)

```bash
# 第一優先 - Illustrious-XL v2.0
https://civitai.com/models/1369089/illustrious-xl-20
檔名: illustrious-xl-v2.0.safetensors

# 第二優先 - SD1.5 
https://civitai.com/models/155256/stable-diffusion-v15-bf16fp16-no-emaema-only-no-vae-safetensors-checkpoint
檔名: stable-diffusion-v1-5.safetensors

# 第三優先 - Pony V6 XL
https://civitai.com/models/257749/pony-diffusion-v6-xl
檔名: pony-diffusion-v6-xl.safetensors

# 第四優先 - FLUX.1-Dev (非商業)
https://civitai.com/models/618692/flux
檔名: flux.1-dev.safetensors
```

## 🎯 **行動建議**
1. ✅ **Base Model 研究** - 4個核心模型已完成
2. ✅ **優先級排序** - 基於 WireStock 需求完成
3. ✅ **配置指南** - 每個模型的最佳參數
4. ⏳ **立即下載** - 建議 LXYA 優先下載 Illustrious-XL v2.0
5. ⏳ **工作流整合** - 下載完成後整合到 ComfyUI

## 💡 **核心發現總結**

### 🌟 **最重要發現: Illustrious-XL v2.0**
- **完美升級路徑**: 從 rinIllusion 升級的理想選擇
- **商業就緒**: 完全支持 WireStock 商業化需求
- **技術領先**: 2024最新技術，自然語言+標籤雙模式
- **生態相容**: 現有 LoRA 和工作流可直接使用

### 🔧 **技術棧建議**
```
主力: Illustrious-XL v2.0 (商業生產)
備用: SD1.5 (經典穩定，大量 LoRA)
特化: Pony V6 XL (角色專精)
實驗: FLUX.1-Dev (最新技術研究)
```

### 🏢 **WireStock 策略**
1. **立即採用**: Illustrious-XL v2.0 作為主要生產模型
2. **品質保證**: 配合現有品質檢測系統
3. **多樣化**: SD1.5 + Pony 提供風格多樣性
4. **未來準備**: FLUX 技術路線跟蹤

---

**✅ 研究狀態**: Base Model 研究 100% 完成
**🎯 建議**: 立即開始 Illustrious-XL v2.0 下載和測試
**⏭️ 下一階段**: LoRA 和 ControlNet 模型已在下載，等待整合測試