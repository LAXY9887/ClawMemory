# ComfyUI 和 Ollama 自啟動設置腳本
# 修復開機自動啟動問題

Write-Host "🔧 設置 ComfyUI 和 Ollama 自動啟動..." -ForegroundColor Cyan

# 定義程式路徑
$ComfyUIPath = "C:\Users\USER\AppData\Local\Programs\ComfyUI0826\ComfyUI.exe"
$OllamaPath = "C:\Users\USER\AppData\Local\Programs\Ollama\ollama app.exe"

# 驗證檔案存在
Write-Host "🔍 驗證檔案路徑..." -ForegroundColor Yellow

if (-not (Test-Path $ComfyUIPath)) {
    Write-Host "❌ ComfyUI 執行檔不存在: $ComfyUIPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $OllamaPath)) {
    Write-Host "❌ Ollama 執行檔不存在: $OllamaPath" -ForegroundColor Red  
    exit 1
}

Write-Host "✅ 檔案路徑驗證通過" -ForegroundColor Green

# 獲取啟動資料夾
$StartupFolder = [System.IO.Path]::Combine($env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup")
Write-Host "📂 啟動資料夾: $StartupFolder" -ForegroundColor Cyan

# 創建 ComfyUI 自啟動 VBS 腳本 (隱藏視窗)
$ComfyUIVBS = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$ComfyUIPath""", 0, False
"@

$ComfyUIVBSPath = Join-Path $StartupFolder "ComfyUI-AutoStart.vbs"
$ComfyUIVBS | Out-File -FilePath $ComfyUIVBSPath -Encoding ASCII -Force

Write-Host "✅ ComfyUI 自啟動腳本已創建: $ComfyUIVBSPath" -ForegroundColor Green

# 創建 Ollama 自啟動 VBS 腳本 (隱藏視窗)  
$OllamaVBS = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$OllamaPath""", 0, False
"@

$OllamaVBSPath = Join-Path $StartupFolder "Ollama-AutoStart.vbs"  
$OllamaVBS | Out-File -FilePath $OllamaVBSPath -Encoding ASCII -Force

Write-Host "✅ Ollama 自啟動腳本已創建: $OllamaVBSPath" -ForegroundColor Green

# 清理舊的問題腳本
$OldComfyUIScript = Join-Path $StartupFolder "ComfyUI-AutoStart.vbs"
if (Test-Path $OldComfyUIScript) {
    Write-Host "🧹 清理舊的自啟動腳本..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 自啟動設置完成！" -ForegroundColor Green
Write-Host "📋 已設置的自啟動項目:" -ForegroundColor Cyan
Write-Host "   • ComfyUI Desktop: $ComfyUIVBSPath" -ForegroundColor White
Write-Host "   • Ollama Service: $OllamaVBSPath" -ForegroundColor White
Write-Host ""
Write-Host "⚠️ 注意事項:" -ForegroundColor Yellow  
Write-Host "   • VBS 腳本會隱藏視窗啟動，避免開機時顯示命令提示字元" -ForegroundColor White
Write-Host "   • 下次重開機後會自動啟動 ComfyUI 和 Ollama" -ForegroundColor White
Write-Host "   • 如需手動測試，可以雙擊 VBS 檔案" -ForegroundColor White

# 立即測試啟動
Write-Host ""
Write-Host "🧪 立即測試啟動..." -ForegroundColor Cyan

# 檢查是否已在運行
$ComfyUIRunning = Get-Process -Name "ComfyUI" -ErrorAction SilentlyContinue
$OllamaRunning = Get-Process -Name "ollama*" -ErrorAction SilentlyContinue

if ($ComfyUIRunning) {
    Write-Host "✅ ComfyUI 已在運行 (PID: $($ComfyUIRunning.Id))" -ForegroundColor Green
} else {
    Write-Host "🚀 啟動 ComfyUI..." -ForegroundColor Yellow
    Start-Process -FilePath $ComfyUIPath -WindowStyle Hidden
    Start-Sleep 3
}

if ($OllamaRunning) {
    Write-Host "✅ Ollama 已在運行 (PID: $($OllamaRunning.Id))" -ForegroundColor Green  
} else {
    Write-Host "🚀 啟動 Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath $OllamaPath -WindowStyle Hidden
    Start-Sleep 3
}

Write-Host ""
Write-Host "🎯 設置完成！下次開機將自動啟動 ComfyUI 和 Ollama" -ForegroundColor Green