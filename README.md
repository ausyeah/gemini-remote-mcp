<div align="center">

# 🚀 Gemini Remote Work

**让手机/网页上的 Gemini 远程指挥这台电脑：执行命令、读写文件、定时任务、调研写报告落盘**

[![Platform](https://img.shields.io/badge/platform-Windows-blue)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-green)]()
[![Protocol](https://img.shields.io/badge/protocol-MCP%202025--03--26-purple)]()
[![License](https://img.shields.io/badge/license-MIT-lightgray)]()

*灵感来源：X 上「给 Gemini App 安装正经 GitHub 插件」的社区玩法 —— 既然 Gemini 支持自定义 MCP 连接器，那就把"连接器"指向自己的电脑。*

</div>

---

## 这是什么

一个 300 行纯 Python 标准库实现的 MCP 服务端（零依赖），通过 Cloudflare 隧道暴露为公网 HTTPS，供 Gemini App 作为自定义关联应用连接。**已实测可用：**

| 测试 | 结果 |
| --- | --- |
| 远程执行命令 | ✅ Gemini 真实返回 `Python 3.12.8` / `git 2.52.0` |
| 远程写文件落盘 | ✅ 云端一句话，本机磁盘出现文件，内容分毫不差 |
| 后台调研任务 → 报告落盘 | ✅ Gemini 自主 Google 调研 + 分段写入，10KB 结构化报告自动保存到本机 |

## 架构

```
手机 Gemini → Google 云 → Cloudflare 隧道 (HTTPS)
                                ↓
                  本机 :8787 (仅绑 127.0.0.1)
                  ├─ /mcp            JSON-RPC (initialize/tools/list/tools/call)
                  ├─ /register       OAuth 2.1 动态客户端注册 (RFC7591)
                  ├─ /authorize      同意页 (需 PIN)
                  └─ /token          PKCE(S256) 换 token
```

## 安全模型（为什么公网暴露也不怕）

| 层 | 机制 |
| --- | --- |
| 入口 | 隧道 URL 不公开；泄露也拿不到 token —— 同意页必须输入**启动时随机生成的 6 位 PIN** |
| 传输 | 全程 HTTPS（Cloudflare 边缘 TLS） |
| 服务 | 仅绑定 127.0.0.1，不监听公网 |
| 协议 | OAuth 2.1：动态客户端注册 + PKCE(S256)，token 有效期 7 天 |
| 信任 | Gemini 侧可随时"禁止"/移除连接器；服务端重启即清空全部 token |

## 快速开始（3 条命令 + 1 分钟 Gemini 配置）

> 前置：Windows + Python 3.10+

```bat
:: 1. 下载本仓库到本地
git clone https://github.com/ausyeah/gemini-remote-mcp
cd gemini-remote-mcp

:: 2. 起服务 + 隧道
start.bat

:: 3. 记下窗口里打印的两样东西：授权 PIN（6位数字）+ trycloudflare 公网地址
```

然后打开 `gemini.google.com`（手机也行）→ 关联应用 → **+ 自定义** → 网址填 `<公网地址>/mcp`
→ 下一步 → 勾选风险确认 → 关联 → 浏览器弹出授权页 → **输入 PIN → 允许** → 完成。

## 使用示例

新对话里 `@Gemini Remote Work` 后随便使唤：

```text
@Gemini Remote Work 在这台电脑上运行 python --version 和 git --version
@Gemini Remote Work 在工作目录写个 test.py 跑一下，把输出给我
@Gemini Remote Work 克隆某个仓库、跑通测试、把结果写进 report.md
```

### 嵌入工作流

- **任务（后台）**：新对话右下角切「任务」→「调研 XX 课题，报告存到工作目录 report.md」——Gemini 自主搜索、写文件落盘，完成后通知你
- **已安排（定时）**：「每天早上 9 点检查工作目录新增文件并汇总」——定时任务同样可调用本机工具

## 仓库内容

| 文件 | 说明 |
| --- | ---|
| `mcp_server.py` | 服务端全部实现（MCP + OAuth 2.1 + PIN 同意页） |
| `PROMPT.md` | **一键配置提示词**：整段复制给你本地的 AI 编程助手，它替你跑完全部配置 |
| `TUTORIAL.md` | 纯手动图文教程（无 AI 助手也能照做） |
| `tweet_draft.md` | X 发布文案草稿 |
| `start.bat` / `stop.bat` | 一键启停脚本 |

## 安全须知（务必阅读）

- `run_command` 以**你的用户身份执行任意命令**——这就是本项目的功能本身。授权有三层（隧道不公开、PIN、Gemini 侧随时可禁用），但请务必理解你授予了什么
- **PIN 与隧道地址不要发到任何公开场合**；本仓库文件不含你的任何个人运行时信息
- token 存内存，服务重启即失效；连接器可在 Gemini「关联的应用」随时移除
- 长期使用建议：登录 tailscale 换固定域名（quick tunnel 重启会换地址），或自行加 Named Tunnel

## FAQ

**Q: 关联时浏览器报 authorize failed？**
A: 多为之前版本的 HTML 属性编码 bug，拉取最新代码重启服务后重试。

**Q: 命令输出中文乱码？**
A: cmd 默认 GBK。让 Gemini 执行 `chcp 65001 && 你的命令` 即可。

**Q: 隧道地址变了，Gemini 连接失效？**
A: quick tunnel 重启换地址，重新关联一次即可（30 秒）。要固定地址用 cloudflared Named Tunnel（需 Cloudflare 账号）或 tailscale funnel。

**Q: 可以不用 Cloudflare 吗？**
A: 可以。任何能给你的 :8787 套上 HTTPS 公网入口的方案都行（frp / tailscale funnel / 自有服务器反代），保持「本机只绑 127.0.0.1 + 公网强鉴权」即可。

## Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=ausyeah/gemini-remote-mcp&type=Date)](https://star-history.com/#ausyeah/gemini-remote-mcp)

---

<div align="center">如果这套东西帮到了你，点个 ⭐ 让更多人看到</div>
