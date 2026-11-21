# Gemini 远程工作（gemini-remote-mcp）纯手动配置教程

本教程介绍如何在 Windows 电脑上通过本地 MCP 服务与 Cloudflare 临时隧道，将本机能力安全接入网页端或手机端 Gemini，实现远程执行命令、读取文件与安排定时任务。

---

## 1. 环境要求

- **操作系统**：Windows 10 / Windows 11（64 位）
- **Python**：Python 3.10 及以上版本（安装时建议勾选 `Add Python to PATH`）
- **网络环境**：可正常访问 GitHub、Cloudflare 及 Gemini 网页端

可在终端执行以下命令确认 Python 版本：

```cmd
python --version
```

---

## 2. 下载 `mcp_server.py` 与 `cloudflared`

1. **准备项目目录**  
   在本地创建一个工作目录（例如 `C:\Users\<你的用户名>\gemini-remote-mcp\`），将本仓库中的 `mcp_server.py`（以及 `README.md`、`PROMPT.md`）下载或克隆到该目录。

2. **下载 `cloudflared`**  
   - 前往 [Cloudflare cloudflared Releases](https://github.com/cloudflare/cloudflared/releases/latest) 下载 Windows 64 位版本 `cloudflared-windows-amd64.exe`。
   - 将其重命名为 `cloudflared.exe`，直接放入 `gemini-remote-mcp` 项目根目录（或使用 `winget install Cloudflare.cloudflared` 安装到系统路径）。

3. **检查目录文件**  
   进入项目目录，确认至少包含：
   - `mcp_server.py`
   - `cloudflared.exe`

---

## 3. 启动本地 MCP 服务（附 PIN 来源说明）

在项目目录下打开终端（PowerShell 或 CMD），执行：

```cmd
python mcp_server.py
```

- **PIN 来源说明**：服务启动后会自动生成一次性授权 **PIN**，同时在控制台输出并写入同目录下的 `pin.txt` 文件中。
- 后续在 Gemini 授权页面输入 PIN 时，请直接查看控制台日志或打开 `pin.txt` 获取当前有效的 PIN。
- 保持该终端窗口运行，不要关闭。

---

## 4. 启动 Cloudflare 临时隧道

**另开一个终端窗口**，进入同一项目目录，执行以下命令将本地服务端口（`mcp_server.py` 默认监听 `8787`）映射到公网：

```cmd
cloudflared.exe tunnel --url http://127.0.0.1:8787
```

等待数秒后，终端日志中会出现类似如下格式的临时公网地址：

```text
https://<random-subdomain>.trycloudflare.com
```

> 提示：Quick Tunnel 每次重启都会分配新的随机域名。如需保存日志方便排查，可加上 `--logfile tunnel.log`。

---

## 5. 在 Gemini 网页端关联自定义连接器

按以下顺序在浏览器中完成关联：

1. 打开 Gemini 网页端，进入连接器 / 扩展管理页面，选择 **自定义**。
2. 在 URL 输入框中填入隧道地址并拼接 MCP 路径：
   ```text
   https://<random-subdomain>.trycloudflare.com/mcp
   ```
3. 点击 **下一步**。
4. 在工具/权限列表中 **勾选** 需要开放给 Gemini 的功能。
5. 点击 **关联**。
6. 浏览器跳转到本地服务的授权确认页后，输入 `pin.txt` 中的 **PIN**。
7. 点击 **允许**，等待页面提示关联成功即可返回 Gemini 对话框。

---

## 6. 验收命令

关联完成后，可以在电脑端或手机端 Gemini 对话框发送以下测试指令进行验收：

- **基础连通性验收**：
  > 请通过已关联的远程电脑工具，执行 `python --version` 和 `whoami`，把结果原样返回给我。
- **中文路径与编码验收**：
  > 请查看当前项目目录下有哪些文件，并读取 `README.md` 的前 5 行内容。

如果 Gemini 能准确返回本机的真实输出，说明整条链路已打通。

---

## 7. 「任务 / 已安排」进阶用法

打通远程连接后，你可以结合 Gemini 的 **任务 / 已安排（Scheduled Actions）** 功能，实现自动化远程巡检或定时处理，例如：

- **每日定时巡检**：每天固定时间自动检查本地磁盘空间、服务日志（`server.log`）或指定目录状态，并汇总发送给你。
- **定时文件整理**：定期扫描下载目录或指定工作目录，按规则分类或生成当日工作简报。
- **开发辅助**：在外出时通过手机让 Gemini 定时拉取最新代码、跑一次单元测试并汇报结果。

> 注意：使用定时任务期间，需确保电脑处于开机联网状态，且 `mcp_server.py` 与 `cloudflared` 保持运行。

---

## 8. 常见问题（FAQ）

### Q1：遇到 `401 Unauthorized` 报错怎么办？
**原因**：本地服务重启后生成了新的 PIN，或之前的授权凭证已失效。  
**解决**：在 Gemini 连接器设置中取消当前关联，重新点击 **关联**，并在授权页输入最新的 `pin.txt` 中的 PIN 即可。

### Q2：重启隧道后连不上怎么办（隧道换址重连）？
**原因**：`cloudflared` 的 Quick Tunnel（`trycloudflare.com`）每次关闭重开都会分配全新的随机域名，旧地址立即失效。  
**解决**：从新的 `cloudflared` 输出（或 `tunnel.log`）复制最新公网地址，在 Gemini 自定义连接器中更新 URL 为 `https://<新域名>.trycloudflare.com/mcp` 后重新关联。

### Q3：Windows CMD 输出中文变成乱码怎么办？
**原因**：Windows CMD 默认代码页为 GBK（936），而服务与脚本默认使用 UTF-8。  
**解决**：在执行命令前先运行 `chcp 65001` 将终端切换为 UTF-8 代码页；若由 Gemini 远程下发命令，也可在提示词或命令前缀中加上 `chcp 65001 && ...`。

### Q4：安全边界有哪些注意事项？
- **切勿泄露凭证**：不要将 `pin.txt`、`server.log`、`tunnel.log` 上传到 GitHub 或任何公开平台（`.gitignore` 已默认忽略）。
- **用完即关**：无需远程操控时，及时关闭服务与隧道进程，缩小公网暴露窗口。
- **最小权限原则**：仅在可信的个人账号下关联，对高风险的删除、系统配置修改等操作，建议在系统提示词（`PROMPT.md`）中要求 Gemini 执行前先向你二次确认。

---

## 9. 停止与回滚

### 停止服务
- **手动停止**：分别在运行 `mcp_server.py` 和 `cloudflared.exe` 的两个终端窗口中按 `Ctrl + C` 终止进程。
- **脚本停止**：如果使用了仓库提供的脚本，直接双击或运行 `stop.bat` 即可一键结束两个进程。

### 回滚与清理
如需完全撤回本次配置：
1. 停止本地 MCP 服务与 `cloudflared` 隧道进程。
2. 在 Gemini 网页端设置中删除/取消关联该自定义连接器。
3. 删除本地目录中的临时文件 `pin.txt`、`server.log`、`tunnel.log`（如需彻底移除，删除整个项目文件夹即可）。
