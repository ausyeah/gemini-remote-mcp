# 一键配置提示词（PROMPT.md）

> 使用方法：复制下面「提示词」框里的全部内容，发给电脑上的本地 AI 编程助手（ZCode / Claude Code / Cursor / Codex 等）。它会替你完成所有技术步骤，只在必须用真人操作的那一步，用大白话告诉你点哪里。

---

## 提示词（整段复制）

```text
目标：在这台 Windows 电脑上部署「Gemini 远程工作」MCP 服务，让手机/网页上的
Gemini 能远程指挥这台电脑执行命令、读写文件，并完成关联和端到端验收。

服务面向的是不懂技术的普通用户，所以：所有技术步骤由你（AI）执行并验证；
只有「在 Gemini 网页里点关联、输入 PIN」这一步必须真人操作，届时请用
大白话逐步告诉用户点哪里，不要甩术语、不要让用户敲命令。

材料（直接用现成的，不要从零写服务端）：
- 仓库：https://github.com/ausyeah/gemini-remote-mcp
  （git clone 或下载 ZIP 到 ~/gemini-mcp；仓库里已包含 start.bat / stop.bat / mcp_server.py）
- cloudflared：https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

背景知识：
- 服务端是纯 Python 标准库单文件，监听 127.0.0.1:8787（仅本机），实现
  MCP streamable HTTP(/mcp) + OAuth 2.1（RFC8414/7591/9728 元数据、动态客户端注册、
  PKCE S256、PIN 同意页）。启动生成 6 位 PIN，打印并写入同目录 pin.txt。
- 安全加固已内置：PIN 连错 5 次锁 5 分钟；自动 chcp 65001 防中文乱码；
  审计日志 audit.log（超 1MB 轮转为 audit.log.1）；/authorize 带 X-Frame-Options
  和 CSP 防点击劫持；redirect_uri 只接受 https 与回环 http；无 CORS 通配符。
- start.bat 会在启动后把服务与隧道的 PID 写入 server.pid / tunnel.pid，
  stop.bat 只终止本次启动的进程，不会误杀机器上其它 cloudflared。
- 公网入口用 cloudflared quick tunnel（免账号），域名形如 xxx.trycloudflare.com，
  每次重启都会换；用户只需在 Gemini 里重新关联一次。
- /mcp 未带 Bearer token 时返回 401 并附带 RFC9728 资源元数据，Gemini 会自动
  发现 OAuth 元数据并动态注册，无需手填 client id/secret。

请按顺序执行，每步都验证后再进下一步；同一报错不要重复超过两次，先读完整报错：

1. 环境：确认 python 3.10+ 可用（python --version）。向用户确认是否已装 Python，
   没有就给出安装链接并提示勾选 Add Python to PATH，等用户装完再继续。
2. 部署：把仓库放到 ~/gemini-mcp；下载 cloudflared-windows-amd64.exe，
   重命名为 cloudflared.exe 放入该目录（与 start.bat 同级）。
3. 启动：运行 start.bat（双击或命令行均可）。它会自动起服务与隧道，并把
   PIN 和隧道地址打印在窗口里，同时写 server.pid / tunnel.pid。
   验证：curl http://127.0.0.1:8787/healthz 返回 ok；
   从窗口输出或 server.log / tunnel.log 里提取 6 位 PIN 和
   https://xxx.trycloudflare.com 地址，告诉用户「窗口不要关」。
4. 公网自测（curl 走隧道域名）：
   a) /healthz 返回 ok
   b) POST /mcp 无 token 返回 401
   c) GET /.well-known/oauth-authorization-server 返回 OAuth 元数据；
      GET /.well-known/oauth-protected-resource/mcp 返回资源元数据
   d) /authorize 响应头含 X-Frame-Options: DENY（防点击劫持）
   e) 完整 OAuth 流程自测：POST /register 拿 client_id → GET /authorize 拿同意页
      → POST /approve（带 PIN 与页面隐藏字段）拿 302 里的 code → POST /token
      （带 43～128 位 code_verifier）拿 access_token → POST /mcp（带 Bearer）
      调 run_command 执行 echo REMOTE-OK，把真实输出给我看。
5. 引导真人完成 Gemini 关联（这步必须本人操作，用大白话逐条告诉用户）：
   在任意设备打开 gemini.google.com → 左下角「关联应用」→「+ 自定义」→
   网址栏粘贴上一步的隧道地址并确保以 /mcp 结尾 → 下一步 → 勾选风险确认 →
   关联 → 浏览器弹出「允许远程工作连接?」授权页 → 在上一步记下的 PIN 输入框里
   填 6 位数字 → 点绿色「允许 (Approve)」→ 跳回 Gemini 即成功。
   提醒用户：PIN 和网址不要发给任何人；PIN 连错 5 次会锁 5 分钟。
6. 端到端验收：让用户新开对话 @该连接器，发送：
   「请在这台电脑上运行 python --version 和 whoami，把真实输出原样返回给我」
   把 Gemini 返回的真实输出拿来对照，确认链路打通。
7. 收尾：用面向小白的大白话，给用户三样东西：
   ① 以后怎么开（双击 start.bat）、怎么关（双击 stop.bat），窗口别关；
   ② 隧道网址变了怎么办（用新窗口里的网址在 Gemini 里重新关联一次）；
   ③ 怎么彻底删除（stop.bat → Gemini 里取消关联 → 删项目文件夹）。
   同时提醒：用完记得 stop.bat；pin.txt / server.log / tunnel.log / audit.log
   不要上传或公开。

约束与底线：
- 服务只绑 127.0.0.1；公网只经 HTTPS 隧道；PIN 与隧道地址不要外传。
- 不改全局配置、不写系统目录、不装全局依赖；所有文件放 ~/gemini-mcp。
- 不要把任何凭证写进 git 提交。
- 对用户始终用大白话：每个技术动作说一句「这一步在干嘛」，术语出现时顺手解释。
```

---

## 没有本地 AI 助手？

看 [TUTORIAL.md](TUTORIAL.md)，纯手动、小白也能照着做。

## 提示词设计说明（为什么这么写）

1. **不让 agent 从零写服务端** —— MCP+OAuth 服务端实现细节多（streamable HTTP 会话头、RFC8414/7591/9728、PKCE），直接下发仓库里已验证的实现，成功率天差地别。
2. **技术步骤全自动、真人步骤大白话** —— 面向小白用户，agent 负责下载/启动/验证/排错，只在必须本人点按钮的 Gemini 关联步骤用普通话逐步引导。
3. **强制分步自测** —— register→authorize→approve→token→call 每步 curl 可验，agent 能自纠错；额外验证防点击劫持头和资源元数据路径。
4. **收尾交付三件套** —— 开/关方法、换址重关联、彻底删除，用大白话写，避免用户以后迷路。
5. **约束段** —— 限定文件位置、禁止全局改动、禁止泄露 PIN/隧道地址，对应「改全局配置前先确认」的底线。
