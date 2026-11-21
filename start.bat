@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==================================================
echo   Gemini 远程工作 - 一键启动脚本
echo ==================================================

if not exist "mcp_server.py" (
    echo [错误] 当前目录下未找到 mcp_server.py
    pause
    exit /b 1
)

set "CF_CMD=cloudflared"
if exist "cloudflared.exe" (
    set "CF_CMD=%~dp0cloudflared.exe"
) else (
    where cloudflared >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 cloudflared.exe，也未在系统 PATH 中检测到 cloudflared
        pause
        exit /b 1
    )
)

:: 清理旧日志与旧 PIN，避免读取到过期信息
if exist "pin.txt" del /f /q "pin.txt" >nul 2>&1
if exist "server.log" del /f /q "server.log" >nul 2>&1
if exist "tunnel.log" del /f /q "tunnel.log" >nul 2>&1
if exist "server.pid" del /f /q "server.pid" >nul 2>&1
if exist "tunnel.pid" del /f /q "tunnel.pid" >nul 2>&1

echo [1/2] 正在启动本地 MCP 服务...
start "gemini-mcp-server" /b cmd /c "python -u mcp_server.py > server.log 2>&1"
:: 记录本次启动的服务 PID，供 stop.bat 精确停止，避免误伤其它 python 进程
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*mcp_server.py*' } | Sort-Object CreationDate -Descending | Select-Object -First 1; if ($p) { $p.ProcessId | Out-File -FilePath 'server.pid' -Encoding ascii -NoNewline }"

set "PIN_VAL="
for /l %%i in (1,1,15) do (
    if exist "pin.txt" (
        set /p PIN_VAL=<"pin.txt"
        if not "!PIN_VAL!"=="" goto :pin_ready
    )
    timeout /t 1 /nobreak >nul
)

:pin_ready
if "!PIN_VAL!"=="" (
    echo [提示] 暂未从 pin.txt 读取到 PIN，请稍后查看 server.log 或 pin.txt。
) else (
    echo [成功] 当前授权 PIN：!PIN_VAL!
)

echo [2/2] 正在启动 Cloudflare 临时隧道...
:: 隧道端口必须与 mcp_server.py 的监听端口一致；未显式设置时默认 8787
if not defined GEMINI_MCP_PORT set "GEMINI_MCP_PORT=8787"
start "gemini-cloudflared" /b cmd /c ""%CF_CMD%" tunnel --url http://127.0.0.1:%GEMINI_MCP_PORT% --logfile tunnel.log >nul 2>&1"
:: 记录本次启动的隧道 PID
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cloudflared.exe' -and $_.CommandLine -like '*127.0.0.1:%GEMINI_MCP_PORT%*' } | Sort-Object CreationDate -Descending | Select-Object -First 1; if ($p) { $p.ProcessId | Out-File -FilePath 'tunnel.pid' -Encoding ascii -NoNewline }"

set "TUNNEL_URL="
for /l %%i in (1,1,20) do (
    if exist "tunnel.log" (
        for /f "usebackq delims=" %%u in (`powershell -NoProfile -Command "$m = Select-String -Path 'tunnel.log' -Pattern 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' -AllMatches; if ($m) { $m.Matches[-1].Value }"`) do (
            set "TUNNEL_URL=%%u"
        )
        if not "!TUNNEL_URL!"=="" goto :tunnel_ready
    )
    timeout /t 1 /nobreak >nul
)

:tunnel_ready
echo.
echo ==================================================
echo   启动完成！请在 Gemini 网页端填入以下信息：
if not "!TUNNEL_URL!"=="" (
    echo   隧道地址：!TUNNEL_URL!/mcp
) else (
    echo   隧道地址：暂未检测到，请打开 tunnel.log 查看 trycloudflare.com 链接
)
if not "!PIN_VAL!"=="" (
    echo   授权 PIN：!PIN_VAL!
) else (
    echo   授权 PIN：请查看当前目录下的 pin.txt
)
echo ==================================================
echo.
echo 提示：服务已在后台运行，如需关闭请运行 stop.bat。
pause
