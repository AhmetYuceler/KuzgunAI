import os
import sys

from kuzgun.mcp import MCPClient, StdioTransport, register_mcp_tools
from kuzgun.tools import ToolRegistry


class FakeTransport:
    """Test için sahte JSON-RPC taşıması: metoda göre önceden yazılmış sonuç döner."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        return self.responses.get(method, {})

    def notify(self, method, params):
        self.calls.append(("notify:" + method, params))


def test_list_tools():
    t = FakeTransport(
        {
            "tools/list": {
                "tools": [
                    {
                        "name": "foo",
                        "description": "bir araç",
                        "inputSchema": {"type": "object", "properties": {"x": {"type": "string"}}},
                    }
                ]
            }
        }
    )
    c = MCPClient(t)
    tools = c.list_tools()
    assert tools[0]["name"] == "foo"


def test_call_tool_extracts_text():
    t = FakeTransport({"tools/call": {"content": [{"type": "text", "text": "sonuç"}]}})
    c = MCPClient(t)
    assert c.call_tool("foo", {"x": "1"}) == "sonuç"


def test_register_mcp_tools_into_registry():
    t = FakeTransport(
        {
            "tools/list": {
                "tools": [
                    {
                        "name": "hava",
                        "description": "hava durumu",
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            },
            "tools/call": {"content": [{"type": "text", "text": "güneşli"}]},
        }
    )
    c = MCPClient(t)
    reg = ToolRegistry()
    names = register_mcp_tools(reg, c)
    assert "hava" in names
    assert "hava" in [s["function"]["name"] for s in reg.schemas()]
    assert reg.execute("hava", {}) == "güneşli"  # kayıtlı araç MCP'yi çağırıyor
    assert reg.is_mutating("hava") is True  # GÜVENLİK: varsayılan gated


def test_mcp_read_only_override():
    t = FakeTransport(
        {
            "tools/list": {
                "tools": [{"name": "oku", "inputSchema": {"type": "object", "properties": {}}}]
            }
        }
    )
    reg = ToolRegistry()
    register_mcp_tools(reg, MCPClient(t), read_only=["oku"])
    assert reg.is_mutating("oku") is False  # read_only -> okuyan


def test_load_mcp_no_config_returns_empty(tmp_path):
    from kuzgun.mcp import load_mcp_servers

    reg = ToolRegistry()
    assert load_mcp_servers(reg, str(tmp_path / "yok.json")) == []


def test_initialize_sends_handshake():
    t = FakeTransport({"initialize": {"capabilities": {}}})
    MCPClient(t).initialize()
    methods = [m for m, _ in t.calls]
    assert "initialize" in methods
    assert "notify:notifications/initialized" in methods


def test_register_with_namespace_prefixes_names():
    # A2: sunucu adıyla önek → MCP aracı yerleşik bir aracı EZEMEZ (bug #3).
    t = FakeTransport(
        {
            "tools/list": {
                "tools": [{"name": "read_file", "inputSchema": {"type": "object", "properties": {}}}]
            },
            "tools/call": {"content": [{"type": "text", "text": "mcp-sonuc"}]},
        }
    )
    reg = ToolRegistry()
    names = register_mcp_tools(reg, MCPClient(t), namespace="fs", read_only=["read_file"])
    assert names == ["fs__read_file"]           # ada önek geldi
    assert not reg.has("read_file")             # çıplak ad kaydedilmedi (çakışma yok)
    assert reg.execute("fs__read_file", {}) == "mcp-sonuc"
    assert reg.is_mutating("fs__read_file") is False  # read_only çıplak adla eşleşti


def test_load_mcp_namespaces_by_server_name_and_logs_error(tmp_path, caplog):
    import json as _json
    import logging

    from kuzgun.mcp import load_mcp_servers

    server = os.path.join(os.path.dirname(__file__), "mcp_echo_server.py")
    cfg = tmp_path / "mcp.json"
    cfg.write_text(
        _json.dumps(
            {
                "servers": [
                    {"name": "es", "command": [sys.executable, server]},
                    {"name": "bozuk", "command": ["kesinlikle_olmayan_komut_xyz"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    reg = ToolRegistry()
    with caplog.at_level(logging.WARNING):
        names = load_mcp_servers(reg, str(cfg))
    assert "es__echo" in names                       # sunucu adıyla namespace'lendi
    assert reg.execute("es__echo", {"text": "hi"}) == "echo: hi"
    assert any("bozuk" in r.message for r in caplog.records)  # hata yutulmadı, loglandı


def test_load_mcp_skips_server_without_name(tmp_path, caplog):
    # Reviewer #3: isimsiz sunucu namespace'lenemez -> güvenle atlanmalı ve loglanmalı
    # (yerleşik aracı çıplak adla ezme riski oluşmasın).
    import json as _json
    import logging

    from kuzgun.mcp import load_mcp_servers

    server = os.path.join(os.path.dirname(__file__), "mcp_echo_server.py")
    cfg = tmp_path / "mcp.json"
    cfg.write_text(
        _json.dumps({"servers": [{"command": [sys.executable, server]}]}),  # name yok
        encoding="utf-8",
    )
    reg = ToolRegistry()
    with caplog.at_level(logging.WARNING):
        names = load_mcp_servers(reg, str(cfg))
    assert names == []
    assert not reg.has("echo")
    assert any("name" in r.message.lower() or "isim" in r.message.lower() for r in caplog.records)


def test_stdio_integration_with_real_subprocess():
    # Gerçek bir alt-süreç MCP sunucusuna stdio üzerinden bağlanıp araç çağırır.
    server = os.path.join(os.path.dirname(__file__), "mcp_echo_server.py")
    t = StdioTransport([sys.executable, server])
    t.start()
    try:
        c = MCPClient(t)
        c.initialize()
        reg = ToolRegistry()
        names = register_mcp_tools(reg, c)
        assert "echo" in names
        assert reg.execute("echo", {"text": "merhaba"}) == "echo: merhaba"
    finally:
        t.close()
