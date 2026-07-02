# ============================================================
# 一键安装所有自动任务（需要以管理员身份运行）
# 右键 → "使用 PowerShell 运行" 或
# 管理员 PowerShell: .\setup_tasks.ps1
# ============================================================
$ErrorActionPreference = "Stop"

$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "[ERROR] 找不到 Python，请先安装 Python 3" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "Python 路径: $pythonPath" -ForegroundColor Green
$workDir = "F:\主机\AI"

# ---- 每周四 12:00 磁盘清理 ----
$taskName1 = "AI_Weekly_Cleanup"
Write-Host "`n创建任务: $taskName1 ..." -ForegroundColor Yellow
schtasks /delete /tn $taskName1 /f 2>$null
schtasks /create `
    /tn $taskName1 `
    /tr "$pythonPath `"$workDir\weekly_cleanup.py`"" `
    /sc weekly /d THU /st 12:00 `
    /rl HIGHEST `
    /f
Write-Host "  [OK] $taskName1 已创建（每周四 12:00）" -ForegroundColor Green

# ---- 每日 09:00 / 14:00 / 18:00 AI 日报（本地备份） ----
$taskName2 = "AI_Daily_Report_Local"
Write-Host "`n创建任务: $taskName2 ..." -ForegroundColor Yellow
schtasks /delete /tn $taskName2 /f 2>$null
$hourArg = '9:00,14:00,18:00'
schtasks /create `
    /tn $taskName2 `
    /tr "$pythonPath `"$workDir\ai_daily_email.py`"" `
    /sc daily /st 09:00 `
    /rl NORMAL `
    /f
Write-Host "  [OK] $taskName2 已创建（每日 09:00）" -ForegroundColor Green
Write-Host "  [INFO] GitHub Actions 也会在 09:00/14:00/18:00 运行日报" -ForegroundColor Cyan

Write-Host "`n========== 任务列表 ==========" -ForegroundColor Cyan
schtasks /query /tn $taskName1 /fo LIST 2>$null
schtasks /query /tn $taskName2 /fo LIST 2>$null

Write-Host "`n[完成] 自动任务安装完毕！" -ForegroundColor Green
pause
