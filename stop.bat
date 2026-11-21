@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==================================================
echo   Gemini 远程工作 - 一键停止脚本
echo ==================================================

echo [1/2] 正在停止 cloudflared 隧道进程...
taskkill /f /im cloudflared.exe >nul 2>&1
if %errorlevel%==0 (
    echo [成功] 已结束 cloudflared.exe
) else (
    echo [提示] 未发现运行中的 cloudflared.exe
)

echo [2/2] 正在停止 mcp_server.py 服务进程...
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*mcp_server.py*' }; if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host '[成功] 已结束 mcp_server.py 相关进程' } else { Write-Host '[提示] 未发现运行中的 mcp_server.py 进程' }"

echo.
echo 全部停止操作已完成。
pause
