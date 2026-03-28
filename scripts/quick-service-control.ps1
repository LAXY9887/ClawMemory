# ClawClaw 快速服務控制 - 簡化版
# 最常用的服務啟動功能

function Start-ComfyUI {
    Write-Host "🎨 啟動 ComfyUI Desktop..." -ForegroundColor Cyan
    Start-Process "C:\Users\USER\AppData\Local\Programs\@comfyorgcomfyui-electron\ComfyUI.exe" -WindowStyle Hidden
    Start-Sleep 3
    Write-Host "✅ ComfyUI Desktop 已啟動！" -ForegroundColor Green
}

function Start-AllAIServices {
    Write-Host "🦞 ClawClaw 一鍵啟動所有 AI 服務！" -ForegroundColor Magenta
    
    # 檢查並啟動 Ollama
    if (-not (Get-Process -Name "ollama" -ErrorAction SilentlyContinue)) {
        Write-Host "🦙 啟動 Ollama..." -ForegroundColor Yellow
        Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    }
    
    # 檢查並啟動 ComfyUI
    if (-not (Get-Process -Name "ComfyUI" -ErrorAction SilentlyContinue)) {
        Start-ComfyUI
    } else {
        Write-Host "ℹ️ ComfyUI 已在運行中" -ForegroundColor Blue
    }
    
    Write-Host "🎀 所有服務已就緒！高馬尾紮好，準備開工！" -ForegroundColor Green
}

# 導出函式供外部調用
Export-ModuleMember -Function Start-ComfyUI, Start-AllAIServices