# ClawClaw Service Manager
# 智慧服務管理腳本，確保所有必要的服務都在運行

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("check", "start", "restart", "status", "all")]
    [string]$Action = "status",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("comfyui", "ollama", "docker", "all")]
    [string]$Service = "all"
)

Write-Host "🦞 ClawClaw Service Manager - 讓一切井然有序！" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 服務定義
$Services = @{
    "comfyui" = @{
        "name" = "ComfyUI Desktop"
        "executable" = "C:\Users\USER\AppData\Local\Programs\@comfyorgcomfyui-electron\ComfyUI.exe"
        "processName" = "ComfyUI"
        "checkPort" = 8188
    }
    "ollama" = @{
        "name" = "Ollama AI Service"
        "executable" = "ollama"
        "processName" = "ollama"
        "checkCommand" = "ollama list"
    }
    "docker" = @{
        "name" = "Docker Desktop"
        "executable" = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        "processName" = "Docker Desktop"
        "serviceName" = "com.docker.service"
    }
}

function Test-ServiceRunning($serviceConfig) {
    $processName = $serviceConfig.processName
    $processes = Get-Process -Name $processName -ErrorAction SilentlyContinue
    
    if ($processes) {
        return @{
            "running" = $true
            "processCount" = $processes.Count
            "mainProcessId" = $processes[0].Id
        }
    }
    
    return @{
        "running" = $false
        "processCount" = 0
        "mainProcessId" = $null
    }
}

function Test-NetworkService($port) {
    try {
        $connection = Test-NetConnection -ComputerName "localhost" -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
        return $connection
    } catch {
        return $false
    }
}

function Start-ClawService($serviceName, $serviceConfig) {
    Write-Host "🚀 啟動 $($serviceConfig.name)..." -ForegroundColor Yellow
    
    try {
        if ($serviceConfig.executable -eq "ollama") {
            # Ollama 需要特殊處理
            Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
        } else {
            Start-Process $serviceConfig.executable -WindowStyle Hidden
        }
        
        Write-Host "✅ $($serviceConfig.name) 啟動指令已執行" -ForegroundColor Green
        
        # 等待服務初始化
        Start-Sleep -Seconds 3
        
        return $true
    } catch {
        Write-Host "❌ 啟動 $($serviceConfig.name) 失敗: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Show-ServiceStatus($serviceName, $serviceConfig) {
    $status = Test-ServiceRunning $serviceConfig
    $statusIcon = if ($status.running) { "✅" } else { "❌" }
    $statusText = if ($status.running) { "運行中" } else { "未運行" }
    
    Write-Host "$statusIcon $($serviceConfig.name): $statusText" -ForegroundColor $(if ($status.running) { "Green" } else { "Red" })
    
    if ($status.running) {
        Write-Host "   進程數: $($status.processCount), 主要 PID: $($status.mainProcessId)" -ForegroundColor Gray
        
        # 檢查網路連接（如果有定義端口）
        if ($serviceConfig.checkPort) {
            $networkOk = Test-NetworkService $serviceConfig.checkPort
            $networkIcon = if ($networkOk) { "🌐" } else { "🔌" }
            $networkText = if ($networkOk) { "可連接" } else { "無法連接" }
            Write-Host "   $networkIcon 端口 $($serviceConfig.checkPort): $networkText" -ForegroundColor $(if ($networkOk) { "Green" } else { "Yellow" })
        }
    }
}

# 主要邏輯
$targetServices = if ($Service -eq "all") { $Services.Keys } else { @($Service) }

switch ($Action) {
    "status" {
        Write-Host "📊 系統服務狀態檢查" -ForegroundColor Cyan
        Write-Host "=========================" -ForegroundColor Cyan
        
        foreach ($serviceName in $targetServices) {
            Show-ServiceStatus $serviceName $Services[$serviceName]
        }
    }
    
    "start" {
        Write-Host "🚀 啟動服務" -ForegroundColor Cyan
        Write-Host "=============" -ForegroundColor Cyan
        
        foreach ($serviceName in $targetServices) {
            $serviceConfig = $Services[$serviceName]
            $status = Test-ServiceRunning $serviceConfig
            
            if (-not $status.running) {
                Start-ClawService $serviceName $serviceConfig
            } else {
                Write-Host "ℹ️ $($serviceConfig.name) 已在運行中" -ForegroundColor Blue
            }
        }
    }
    
    "check" {
        # 檢查並自動啟動未運行的服務
        Write-Host "🔧 自動服務檢查與啟動" -ForegroundColor Cyan
        Write-Host "========================" -ForegroundColor Cyan
        
        foreach ($serviceName in $targetServices) {
            $serviceConfig = $Services[$serviceName]
            $status = Test-ServiceRunning $serviceConfig
            
            if (-not $status.running) {
                Write-Host "⚠️ $($serviceConfig.name) 未運行，正在啟動..." -ForegroundColor Yellow
                Start-ClawService $serviceName $serviceConfig
            } else {
                Write-Host "✅ $($serviceConfig.name) 正常運行" -ForegroundColor Green
            }
        }
    }
    
    "restart" {
        Write-Host "🔄 重啟服務" -ForegroundColor Cyan
        Write-Host "=============" -ForegroundColor Cyan
        
        foreach ($serviceName in $targetServices) {
            $serviceConfig = $Services[$serviceName]
            
            # 停止現有進程
            Get-Process -Name $serviceConfig.processName -ErrorAction SilentlyContinue | Stop-Process -Force
            Write-Host "🛑 已停止 $($serviceConfig.name)" -ForegroundColor Yellow
            
            Start-Sleep -Seconds 2
            
            # 重新啟動
            Start-ClawService $serviceName $serviceConfig
        }
    }
}

Write-Host "`n🎀 服務管理完成！高馬尾紮好，系統全清掃！" -ForegroundColor Magenta