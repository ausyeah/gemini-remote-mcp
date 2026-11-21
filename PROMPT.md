# 一键配置提示词（PROMPT.md）

> 使用方法：先把本仓库推上 GitHub，然后把下面整段提示词复制给你电脑上的本地 AI 编程助手（ZCode / Claude Code / Cursor / Codex 等均可）。它会替你完成全部配置。

---

## 提示词（整段复制）

```text
目标：在这台 Windows 电脑上部署「Gemini 远程工作」MCP 服务，让手机/网页的
Gemini App 能远程指挥这台电脑执行命令、读写文件，并完成 Gemini 侧关联和端到端验收。

材料（不要自己从零写服务端，直接用现成的）：
- 服务端代码：https://raw.githubusercontent.com/ausyeah/gemini-remote-mcp/main/mcp_server.py
- cloudflared：https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

背景知识：
- 服务端是纯 Python 标准库单文件，监听 127.0.0.1:8787（仅本机），实现：
  MCP streamable HTTP(/mcp) + OAuth 2.1(RFC8414 元数据/RFC7591 动态客户端注册/
  PKCE S256/PIN 同意页)。启动时会生成 6 位授权 PIN 并打印、写入同目录 pin.txt。
- 公网入口用 cloudflared quick tunnel（免账号），域名形如 xxx.trycloudflare.com。
  隧道进程重启会换域名；Gemini 侧重新关联一次即可。
- /mcp 未带 Bearer token 时返回 401 并附带 RFC9728 资源元数据，Gemini 会自动
  发现 OAuth 元数据并动态注册，无需手填任何 client id/secret。

请按顺序执行，每步都验证后再进下一步；同一报错不要重复超过两次，先读完整报错：

1. 环境：确认 python 3.10+ 可用；建目录 ~/gemini-mcp；下载上面两个文件到该目录。
2. 起服务：后台运行 `python mcp_server.py`，日志写 server.log。
   验证：curl http://127.0.0.1:8787/healthz 返回 ok；记录 pin.txt 里的 6 位 PIN 并告诉我。
3. 起隧道：后台运行 `cloudflared.exe tunnel --url http://127.0.0.1:8787`，日志写
   tunnel.log；从日志提取 https://xxx.trycloudflare.com 地址并告诉我。
4. 公网自测（curl 走隧道域名）：
   a) /healthz 返回 ok
   b) POST /mcp 无 token 返回 401
   c) 完整 OAuth 流程自测：POST /register 拿 client_id → GET /authorize 拿到同意页
      → POST /approve(带 PIN 与页面隐藏字段) 拿 302 里的 code → POST /token(带
      code_verifier) 拿 access_token → POST /mcp(带 Bearer) 调 run_command 执行
      echo REMOTE-OK，把真实输出给我看。
5. 全部通过后，引导我手动完成 Gemini 关联（这步必须真人操作）：
   在任意设备打开 gemini.google.com → 关联应用 → 「+ 自定义」→ 网址填
   <隧道地址>/mcp → 下一步 → 勾选风险确认 → 关联 → 浏览器弹出「允许远程工作连接?」
   授权页 → 输入上面给我的 PIN → 点「允许 (Approve)」→ 页面跳回 Gemini 即成功。
6. 端到端验收：Gemini 新对话 @该连接器，让它远程执行 python --version 与
   git --version，把 Gemini 返回的真实输出发给我对照。

约束与底线：
- 服务只绑 127.0.0.1；公网只经 HTTPS 隧道；PIN 与隧道地址不要外传。
- 不改全局配置、不写系统目录、不装全局依赖；所有文件放 ~/gemini-mcp。
- 完成后输出三样东西：启停方法、隧道地址变更后的重关联步骤、彻底回滚步骤。
```

---

## 没有本地 AI 助手？

看 [TUTORIAL.md](TUTORIAL.md)，纯手动 10 分钟照做。

## 提示词设计说明（为什么这么写）

1. **不让 agent 从零写服务端** —— MCP+OAuth 服务端实现细节多（streamable HTTP 会话头、
   RFC8414/7591/9728、PKCE），直接下发仓库里已验证的实现，成功率天差地别。
2. **强制分步自测** —— register→authorize→approve→token→call 每步 curl 可验，
   agent 能自纠错。
3. **真人步骤显式标注** —— Gemini 关联页 + PIN 输入必须本人操作，提示词里写明，
   避免 agent 在 UI 上空转。
4. **约束段** —— 限定文件位置、禁止全局改动，对应原推文"改全局配置前先确认"的底线。
