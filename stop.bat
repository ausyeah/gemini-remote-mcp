@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==================================================
echo   Gemini 远程工作 - 一键停止脚本
echo ==================================================

echo [1/2] 正在停止本次启动的 cloudflared 隧道进程...
if exist "tunnel.pid" (
    set "TPID="
    set /p TPID=<"tunnel.pid"
    if defined TPID (
        powershell -NoProfile -Command "$id = [int]'!TPID!'; $p = Get-CimInstance Win32_Process -Filter \"ProcessId=$id\"; if ($p -and $p.Name -eq 'cloudflared.exe' -and $p.CommandLine -like '*127.0.0.1:*') { Stop-Process -Id $id -Force; Write-Host ('[成功] 已结束隧道进程 PID ' + $id) } else { Write-Host '[提示] PID 已失效或不是本次启动的隧道，未终止' }"
    ) else (
        echo [提示] tunnel.pid 为空
    )
    del /f /q "tunnel.pid" >nul 2>&1
) else (
    echo [提示] 未找到 tunnel.pid；如需强制清理，请手动结束 cloudflared.exe
)

echo [2/2] 正在停止本次启动的 mcp_server.py 服务进程...
if exist "server.pid" (
    set "SPID="
    set /p SPID=<"server.pid"
    if defined SPID (
        powershell -NoProfile -Command "$id = [int]'!SPID!'; $p = Get-CimInstance Win32_Process -Filter \"ProcessId=$id\"; if ($p -and $p.Name -eq 'python.exe' -and $p.CommandLine -like '*mcp_server.py*') { Stop-Process -Id $id -Force; Write-Host ('[成功] 已结束服务进程 PID ' + $id) } else { Write-Host '[提示] PID 已失效或不是本次启动的服务，未终止' }"
    ) else (
        echo [提示] server.pid 为空
    )
    del /f /q "server.pid" >nul 2>&1
) else (
    echo [提示] 未找到 server.pid；如需强制清理，请手动结束对应 python 进程
)

echo.
echo 全部停止操作已完成。
pause
