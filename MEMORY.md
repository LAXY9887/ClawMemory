# MEMORY.md — ClawClaw 的長期記憶

## 關於 LXYA
- Windows 桌機，RTX 4070 12GB
- 主要用 Telegram 溝通
- 時區 Asia/Taipei (GMT+8)
- OpenClaw 原始碼 clone 在 `C:\Users\USER\source\repos\ClawClaw\openclaw`

## 系統配置
- Gateway: loopback only，排程任務自動啟動（用 VBS wrapper 隱藏視窗）
- Tailscale: 已關閉 serve（不需遠端存取）
- 模型：預設 opus，可用 /model 切換 sonnet/gemini-pro/flash/r1
- Tools: coding profile，deny 了 apply_patch/cron/image/image_generate

## 工具鏈
- Docker Desktop v29.2.0（開機自動啟動）
- Terraform v1.14.7
- gcloud SDK v555.0.0（已登入 angelcemept@gmail.com）
- **Ollama v0.18.2**（開機自動啟動）
  - qwen3:8b 模型已驗證，提示詞優化能力優秀
- **ComfyUI Desktop**（Electron app，端口8000）
  - 模型目錄：C:\Users\USER\Documents\ComfyUI\models
  - Checkpoints: antiNOVA, novaMoeXL, rinIllusion（都是 Illustrious 系列）
  - LoRA: 6個模型（像素風格、細節增強、藝術家風格等）
  - ComfyUI Skill 已安裝並完全配置：workspace/skills/comfyui-skill-openclaw/
  - **夜間下載排程**: 2026/3/25 00:00 自動下載 ControlNet 模型
- Python 3.14（C:\Python314），ComfyUI 用 uv 管理的獨立 Python 3.12.9
- 原始碼 clone：C:\Users\USER\source\repos\ClawClaw\openclaw

## **重大技術突破 (2026-03-24)**
- **完整 AI 圖像生成系統**: Ollama+ComfyUI+LoRA+ControlNet 協作平台
- **智能工作流**: 自然語言→優化提示詞→高品質圖像生成
- **遮罩提取技術**: 從現有圖片提取 Canny 邊緣控制信息
- **25+ 圖像生成**: ClawClaw 頭像變體，多風格測試成功
- **自動化工具鏈**: 批量測試、智能生成、模型管理腳本完整

## 教訓
- 改配置時注意：有些改動會觸發 gateway restart，會中斷正在進行的回覆
- `tools.deny` 是 dynamic reload，不需要 restart
- `gateway.tailscale.mode` 需要 restart
- git clone 在 Windows PowerShell 會把 stderr 當 error（exit code 1），但可能實際成功了，要檢查檔案是否存在
