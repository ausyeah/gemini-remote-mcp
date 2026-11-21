# X（Twitter）发布文案草稿

> 说明：每条推文均已控制在 X 单条字数限制（280 字符权重 / 140 汉字）以内，发布时可直接按顺序发成 Thread。

### 1/6（Hook + 一句话架构）

出门在外突然要查电脑文件、跑脚本，又不想开远控软件？现在可以直接让手机上的 Gemini 远程指挥这台电脑干活。

核心架构一句话：手机/网页 Gemini → Cloudflare 临时隧道 → 本机 `mcp_server.py`（带 PIN 码鉴权），零公网 IP 也能秒连。

### 2/6（步骤 1：准备环境与启动本地服务）

第一步：准备 Windows + Python 3.10+ 环境，下载仓库里的 `mcp_server.py` 和 `cloudflared.exe`。

在项目目录运行 `python mcp_server.py` 启动本地 MCP 服务，同时会在同目录生成 `pin.txt` 保存本次随机授权码，注意别外泄。

### 3/6（步骤 2：启动 Cloudflare 临时隧道）

第二步：另开一个终端，执行 `cloudflared.exe tunnel --url http://127.0.0.1:8787` 拉起隧道。

几秒后控制台会吐出一个 `https://xxx.trycloudflare.com` 临时公网地址，全程不需要买服务器或配置路由器端口转发。

### 4/6（步骤 3：Gemini 网页端关联与 PIN 授权）

第三步：打开 Gemini 网页端连接器设置，依次点击：自定义 → 填入 `https://xxx.trycloudflare.com/mcp` → 下一步 → 勾选工具 → 关联。

在弹出的授权页输入 `pin.txt` 里的 PIN 码并点击允许，手机端 Gemini 就会自动同步该能力。

### 5/6（步骤 4：验收与定时任务玩法）

第四步：直接在手机上对 Gemini 说「帮我查下这台电脑当前目录和 Python 版本」即可验收。

跑通后还能搭配 Gemini 的「已安排任务」，让它每天定时巡检日志、整理桌面或自动跑脚本，用完随时执行 `stop.bat` 一键下线。

### 6/6（开源仓库链接占位）

整套代码、`start.bat` / `stop.bat` 一键脚本和保姆级排错手册（401 重连、`chcp 65001` 防乱码、安全边界）都整理开源了，欢迎 Star 自取：

GitHub 仓库：https://github.com/ausyeah/gemini-remote-mcp