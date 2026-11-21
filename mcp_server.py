# -*- coding: utf-8 -*-
import base64, hashlib, html as html_mod, json, os, secrets, subprocess, threading, time, urllib.parse


def html_escape(s):
    return html_mod.escape(str(s), quote=True)
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.environ.get("GEMINI_MCP_ROOT") or os.path.join(os.path.expanduser("~"), "gemini-remote-work")
os.makedirs(ROOT, exist_ok=True)
PORT = int(os.environ.get("GEMINI_MCP_PORT", "8787"))
PIN = os.environ.get("GEMINI_MCP_PIN") or "".join(secrets.choice("0123456789") for _ in range(6))

CLIENTS = {}
AUTH_CODES = {}
TOKENS = {}
SESSIONS = set()
LOCK = threading.Lock()

TOOLS = [
    {
        "name": "run_command",
        "description": ("在本机工作目录里执行一条 shell 命令并返回 stdout/stderr。"
                        "读文件用 type 文件名, 写文件用重定向, 列目录用 dir, "
                        "git/npm/python 等任何本机命令均可直接执行。"
                        "命令以当前用户身份运行, 请谨慎。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令行"},
                "timeout": {"type": "integer", "description": "超时秒数, 默认 60, 上限 300"}
            },
            "required": ["command"],
        },
    },
]

def pkce_ok(verifier, challenge):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return secrets.compare_digest(expected, challenge or "")

def run_shell(cmd, timeout):
    # 参数列表形式调起 cmd.exe (无外层 shell 字符串拼接)
    r = subprocess.run(["cmd.exe", "/d", "/s", "/c", cmd],
                       shell=False, cwd=ROOT, capture_output=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (("\n[stderr]\n" + r.stderr) if r.stderr else "")
    if len(out) > 30000:
        out = out[:30000] + "\n...[输出已截断]"
    return "exit_code=" + str(r.returncode) + "\n\n" + (out or "(无输出)")

class Handler(BaseHTTPRequestHandler):
    server_version = "GeminiRemoteMCP/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json", extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ("text" in ctype or "json" in ctype) else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Mcp-Session-Id, Mcp-Protocol-Version")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200, extra=None):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json", extra)

    def _rpc_error(self, id_, code, msg):
        self._json({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}})

    def _host(self):
        return self.headers.get("Host", "127.0.0.1:" + str(PORT))

    def _base_url(self):
        return "https://" + self._host()

    def _form(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(n).decode("utf-8", errors="replace")
        ct = self.headers.get("Content-Type") or ""
        if "json" in ct:
            return json.loads(raw or "{}")
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/.well-known/oauth-protected-resource":
            base = self._base_url()
            self._json({"resource": base + "/mcp", "authorization_servers": [base], "scopes_supported": ["mcp"], "bearer_methods": ["header"]})
        elif path == "/.well-known/oauth-authorization-server":
            base = self._base_url()
            self._json({"issuer": base, "authorization_endpoint": base + "/authorize", "token_endpoint": base + "/token", "registration_endpoint": base + "/register", "response_types_supported": ["code"], "grant_types_supported": ["authorization_code"], "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["none"], "scopes_supported": ["mcp"]})
        elif path == "/authorize":
            self._authorize_page()
        elif path == "/mcp":
            self._send(405, json.dumps({"error": "use POST"}), "application/json")
        elif path == "/healthz":
            self._json({"ok": True, "root": ROOT})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/register":
                self._register()
            elif path == "/approve":
                self._approve()
            elif path == "/token":
                self._token()
            elif path == "/mcp":
                self._mcp()
            else:
                self._json({"error": "not found"}, 404)
        except Exception as e:
            try:
                self._json({"error": "internal", "detail": str(e)[:300]}, 500)
            except Exception:
                pass

    def _register(self):
        body = self._form()
        ruri = body.get("redirect_uris") or body.get("redirect_uri") or []
        if isinstance(ruri, str):
            ruri = [ruri]
        if not ruri:
            self._json({"error": "invalid_client_metadata", "error_description": "redirect_uris required"}, 400)
            return
        client_id = "gc_" + secrets.token_hex(8)
        CLIENTS[client_id] = {"redirect_uris": ruri, "client_name": str(body.get("client_name") or "unknown-client")[:80]}
        self._json({"client_id": client_id, "client_id_issued_at": int(time.time()), "client_name": CLIENTS[client_id]["client_name"], "redirect_uris": ruri, "token_endpoint_auth_method": "none", "grant_types": ["authorization_code"], "response_types": ["code"]}, 201)

    def _authorize_page(self):
        q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
        client_id = q.get("client_id", "")
        redirect_uri = q.get("redirect_uri", "")
        challenge = q.get("code_challenge", "")
        state = q.get("state", "")
        scope = q.get("scope", "mcp")
        resp_type = q.get("response_type", "code")
        cli = CLIENTS.get(client_id)
        if (not cli) or (redirect_uri not in cli["redirect_uris"]) or resp_type != "code" or not challenge:
            self._send(400, "<h2>invalid authorize request</h2>", "text/html")
            return
        hidden = {"client_id": client_id, "redirect_uri": redirect_uri, "code_challenge": challenge, "state": state, "scope": scope}
        fields = "".join('<input type="hidden" name="' + k + '" value="' + html_escape(v) + '"/>' for k, v in hidden.items())
        html = ("<!doctype html><html lang=zh><head><meta charset=utf-8><title>authorize</title>"
                "<style>body{font-family:system-ui;max-width:520px;margin:48px auto;padding:0 20px}"
                ".btn{display:block;width:100%;padding:12px;margin-top:16px;background:#0a7;color:#fff;border:0;border-radius:8px;font-size:16px;cursor:pointer}"
                "input{padding:10px;font-size:16px;width:120px;margin-top:10px}.mut{color:#888;font-size:13px}</style></head><body>"
                "<h2>允许远程工作连接?</h2><p><b>" + cli["client_name"] + "</b> 请求连接这台电脑的 Gemini 远程工作服务。</p>"
                "授权后它将可以: 在工作目录执行命令、读写文件。<br/>"
                "请输入服务启动时生成的授权 PIN: "
                "<form method=POST action=/approve>" + fields +
                "<input name=pin inputmode=numeric autocomplete=off required/>"
                "<button class=btn type=submit>允许 (Approve)</button></form>"
                "<p class=mut>scope: " + scope + "</p>"
                "</body></html>")
        self._send(200, html, "text/html")

    def _approve(self):
        f = self._form()
        pin = str(f.get("pin", "")).strip()
        if not secrets.compare_digest(pin, PIN):
            self._send(403, "<html><body><h2>PIN 错误</h2><p>请使用服务启动时打印的 PIN。</p></body></html>", "text/html")
            return
        client_id = f.get("client_id", "")
        redirect_uri = f.get("redirect_uri", "")
        challenge = f.get("code_challenge", "")
        state = f.get("state", "")
        scope = f.get("scope", "mcp")
        cli = CLIENTS.get(client_id)
        if (not cli) or (redirect_uri not in cli["redirect_uris"]) or not challenge:
            self._send(400, "<h2>authorize failed</h2>", "text/html")
            return
        code = secrets.token_hex(24)
        with LOCK:
            AUTH_CODES[code] = {"client_id": client_id, "redirect_uri": redirect_uri, "challenge": challenge, "scope": scope, "expires": time.time() + 300}
        sep = "&" if "?" in redirect_uri else "?"
        loc = redirect_uri + sep + "code=" + urllib.parse.quote(code) + "&state=" + urllib.parse.quote(state)
        self.send_response(302)
        self.send_header("Location", loc)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _token(self):
        f = self._form()
        if f.get("grant_type") != "authorization_code":
            self._json({"error": "unsupported_grant_type"}, 400)
            return
        code = f.get("code", "")
        rec = AUTH_CODES.get(code)
        if (not rec) or rec["expires"] < time.time():
            self._json({"error": "invalid_grant", "error_description": "code expired or unknown"}, 400)
            return
        if f.get("client_id") != rec["client_id"] or f.get("redirect_uri") != rec["redirect_uri"]:
            self._json({"error": "invalid_grant", "error_description": "client/redirect mismatch"}, 400)
            return
        verifier = f.get("code_verifier", "")
        if (not verifier) or (not pkce_ok(verifier, rec["challenge"])):
            self._json({"error": "invalid_grant", "error_description": "PKCE verification failed"}, 400)
            return
        with LOCK:
            AUTH_CODES.pop(code, None)
            token = "gt_" + secrets.token_hex(24)
            TOKENS[token] = {"client_id": rec["client_id"], "expires": time.time() + 86400 * 7, "scope": rec.get("scope", "mcp")}
        self._json({"access_token": token, "token_type": "Bearer", "expires_in": 86400 * 7, "scope": rec.get("scope", "mcp")})

    def _authed(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Bearer ") and not h.startswith("bearer "):
            base = self._base_url()
            self._json({"error": "unauthorized"}, 401, extra={"WWW-Authenticate": "Bearer resource_metadata=" + chr(34) + base + "/.well-known/oauth-protected-resource" + chr(34)})
            return None
        rec = TOKENS.get(h[7:].strip())
        if (not rec) or rec["expires"] < time.time():
            self._json({"error": "unauthorized", "error_description": "token invalid/expired"}, 401)
            return None
        return rec

    def _mcp(self):
        if self._authed() is None:
            return
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            msg = json.loads(self.rfile.read(n) or b"null")
        except Exception:
            self._json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, 400)
            return
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            self._json({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}, 400)
            return
        method = msg.get("method", "")
        id_ = msg.get("id")
        if method.startswith("notifications/"):
            self._send(202, b"", "text/plain")
            return
        try:
            if method == "initialize":
                sid = self.headers.get("Mcp-Session-Id") or ("s_" + secrets.token_hex(8))
                with LOCK:
                    SESSIONS.add(sid)
                self._json({"jsonrpc": "2.0", "id": id_, "result": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "gemini-remote-work", "version": "1.0.0"}}}, extra={"Mcp-Session-Id": sid})
            elif method == "tools/list":
                self._json({"jsonrpc": "2.0", "id": id_, "result": {"tools": TOOLS}})
            elif method == "tools/call":
                params = msg.get("params") or {}
                name = params.get("name")
                args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
                try:
                    text = self._call_tool(name, args)
                    self._json({"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": text}], "isError": False}})
                except Exception as e:
                    self._json({"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": "工具执行失败: " + str(e)}], "isError": True}})
            elif method == "ping":
                self._json({"jsonrpc": "2.0", "id": id_, "result": {}})
            else:
                self._rpc_error(id_, -32601, "Method not found: " + str(method))
        except Exception as e:
            self._rpc_error(id_, -32603, "Internal error: " + str(e))

    def _call_tool(self, name, a):
        if name == "run_command":
            cmd = str(a.get("command", "")).strip()
            if not cmd:
                raise ValueError("command 不能为空")
            if len(cmd) > 4000:
                raise ValueError("命令过长")
            timeout = min(max(int(a.get("timeout", 60)), 1), 300)
            return run_shell(cmd, timeout)
        raise ValueError("未知工具: " + str(name))

def main():
    pin_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pin.txt")
    with open(pin_file, "w", encoding="utf-8") as f:
        f.write(PIN)
    print("[gemini-mcp] 工作目录 = " + ROOT)
    print("[gemini-mcp] 本轮授权 PIN = " + PIN)
    print("[gemini-mcp] listening on http://127.0.0.1:" + str(PORT))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.serve_forever()

if __name__ == "__main__":
    main()