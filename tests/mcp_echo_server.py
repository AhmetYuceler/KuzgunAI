"""Test için minik bir MCP sunucusu (stdio, satır-bazlı JSON-RPC).

Tek araç: 'echo' — verilen metni 'echo: <metin>' olarak geri döndürür.
"""

import json
import sys


def _reply(mid, result):
    print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}), flush=True)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        mid = msg.get("id")
        method = msg.get("method")
        if method == "initialize":
            _reply(mid, {"protocolVersion": "2024-11-05", "capabilities": {},
                         "serverInfo": {"name": "echo", "version": "1"}})
        elif method == "tools/list":
            _reply(mid, {"tools": [{
                "name": "echo",
                "description": "verilen metni geri dondurur",
                "inputSchema": {"type": "object",
                                "properties": {"text": {"type": "string"}}},
            }]})
        elif method == "tools/call":
            args = msg.get("params", {}).get("arguments", {})
            _reply(mid, {"content": [{"type": "text", "text": "echo: " + args.get("text", "")}]})
        # bildirimler (id yok) -> yanıt yok


if __name__ == "__main__":
    main()
