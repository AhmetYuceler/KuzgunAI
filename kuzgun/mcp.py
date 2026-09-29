from __future__ import annotations

import json
import subprocess
from pathlib import Path

_PROTOCOL_VERSION = "2024-11-05"


class StdioTransport:
    """Bir MCP sunucusunu alt süreç olarak başlatır; satır-bazlı JSON-RPC konuşur."""

    def __init__(self, command: list[str]):
        self._command = command
        self._proc: subprocess.Popen | None = None
        self._id = 0

    def start(self) -> None:
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

    def _send(self, obj: dict) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def call(self, method: str, params: dict) -> dict:
        assert self._proc and self._proc.stdout
        self._id += 1
        rid = self._id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP sunucusu kapandı")
            msg = json.loads(line)
            if msg.get("id") == rid:  # bize ait yanıt
                if "error" in msg:
                    raise RuntimeError(str(msg["error"]))
                return msg.get("result", {})
            # değilse: bildirim/log — atla

    def notify(self, method: str, params: dict) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass


class MCPClient:
    """Bir MCP sunucusuyla konuşur: el sıkışma, araç listeleme, araç çağırma."""

    def __init__(self, transport):
        self._t = transport

    def initialize(self) -> None:
        self._t.call(
            "initialize",
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "kuzgun", "version": "0.1"},
            },
        )
        self._t.notify("notifications/initialized", {})

    def list_tools(self) -> list[dict]:
        return self._t.call("tools/list", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self._t.call("tools/call", {"name": name, "arguments": arguments})
        parts = [
            c.get("text", "")
            for c in result.get("content", [])
            if c.get("type") == "text"
        ]
        return "\n".join(parts) if parts else json.dumps(result, ensure_ascii=False)


def _mcp_to_openai_schema(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("inputSchema")
            or {"type": "object", "properties": {}},
        },
    }


def register_mcp_tools(registry, client: MCPClient, read_only=()) -> list[str]:
    """MCP sunucusunun araçlarını ToolRegistry'ye kaydeder. Kaydedilen adları döner.

    GÜVENLİK: MCP araçları varsayılan olarak DEĞİŞİKLİK YAPAN (mutating=True) sayılır
    → mod/onay kapısına tabidir. Yalnızca `read_only` listesindekiler okuyan sayılır.
    Böylece config yazarı unutursa bile yıkıcı bir araç sessizce çalışmaz (fail-safe).
    """
    read_only = set(read_only)
    names = []
    for tool in client.list_tools():
        name = tool["name"]

        def make_fn(tool_name):
            def fn(**kwargs):
                return client.call_tool(tool_name, kwargs)

            return fn

        registry.register(
            _mcp_to_openai_schema(tool),
            make_fn(name),
            mutating=(name not in read_only),
        )
        names.append(name)
    return names


def load_mcp_servers(registry, config_path: str = "mcp_servers.json") -> list[str]:
    """Config dosyasındaki MCP sunucularını başlatıp araçlarını kaydeder.

    Config yoksa sessizce boş döner. Bir sunucu bozuksa Kuzgun bozulmasın diye
    hatalar yutulur. Format: {"servers":[{"name","command":[...],"mutating":[...]}]}.
    """
    p = Path(config_path)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    registered: list[str] = []
    for srv in data.get("servers", []):
        try:
            transport = StdioTransport(srv["command"])
            transport.start()
            client = MCPClient(transport)
            client.initialize()
            registered.extend(
                register_mcp_tools(registry, client, read_only=srv.get("read_only", []))
            )
        except Exception:
            continue  # bir sunucu bozuksa diğerlerine devam et
    return registered
