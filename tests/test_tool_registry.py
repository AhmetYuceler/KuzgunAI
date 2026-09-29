"""ToolRegistry sözleşme doğrulaması (Faz A1).

Model, araca yalnız şemada TANIMLI parametreleri geçirebilmeli. Şema dışı bir
anahtar (ör. bir aracın gizli `_path` parametresi) reddedilmeli — yoksa model
onay kapısını atlayıp keyfi dosyaya yazabilir (bug #1).
"""

from __future__ import annotations

import pytest

from kuzgun.tools import ToolRegistry


def _schema(name, props):
    return {
        "type": "function",
        "function": {
            "name": name,
            "parameters": {"type": "object", "properties": props},
        },
    }


def test_execute_rejects_unknown_argument():
    reg = ToolRegistry()
    seen = {}
    reg.register(_schema("yaz", {"fact": {"type": "string"}}),
                 lambda **kw: seen.update(kw) or "ok")
    out = reg.execute("yaz", {"fact": "a", "_path": "C:/gizli.txt"})
    assert out.startswith("Error:")           # şema dışı anahtar reddedildi
    assert seen == {}                          # fonksiyon HİÇ çağrılmadı


def test_execute_allows_declared_arguments():
    reg = ToolRegistry()
    reg.register(_schema("yaz", {"fact": {"type": "string"}}),
                 lambda fact: f"kaydedildi:{fact}")
    assert reg.execute("yaz", {"fact": "merhaba"}) == "kaydedildi:merhaba"


def test_execute_allows_empty_args_when_no_properties():
    reg = ToolRegistry()
    reg.register(_schema("ping", {}), lambda: "pong")
    assert reg.execute("ping", {}) == "pong"


def test_duplicate_registration_raises():
    reg = ToolRegistry()
    reg.register(_schema("x", {}), lambda: "1")
    with pytest.raises(ValueError):
        reg.register(_schema("x", {}), lambda: "2")


def test_additional_properties_allows_extra_keys():
    # Reviewer #4: şema additionalProperties:true ise fazladan anahtar reddedilmemeli
    # (serbest şemalı MCP araçları için).
    reg = ToolRegistry()
    seen = {}
    schema = {
        "type": "function",
        "function": {
            "name": "serbest",
            "parameters": {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": True,
            },
        },
    }
    reg.register(schema, lambda **kw: seen.update(kw) or "ok")
    assert reg.execute("serbest", {"a": "1", "b": "2"}) == "ok"
    assert seen == {"a": "1", "b": "2"}


def test_execute_returns_toolresult_with_ok_flag():
    from kuzgun.tools import ToolResult

    reg = ToolRegistry()
    reg.register(_schema("ok", {}), lambda: "sonuc")
    res = reg.execute("ok", {})
    assert isinstance(res, ToolResult)
    assert res == "sonuc"          # str gibi davranır (geriye dönük uyum)
    assert res.ok is True


def test_legit_error_text_is_not_marked_error():
    # B5: çıktısı "Error:" ile başlayan MEŞRU araç sonucu HATA sayılmamalı.
    reg = ToolRegistry()
    reg.register(_schema("api", {}), lambda: "Error: 404 (API'nin gerçek cevabı)")
    res = reg.execute("api", {})
    assert res.ok is True          # istisna yok → başarılı, metni ne olursa olsun


def test_unknown_and_exception_are_not_ok():
    reg = ToolRegistry()
    reg.register(_schema("patlar", {}), lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert reg.execute("yok", {}).ok is False       # bilinmeyen araç
    assert reg.execute("patlar", {}).ok is False     # çalışma hatası


def test_remember_is_mutating_in_default_registry():
    # A6 (bug #2): remember kalıcı nota yazar ve bu not her gelecek sistem promptuna
    # enjekte edilir -> model onaysız yazamamalı (mutating -> izin kapısına tabi).
    from kuzgun.engine import build_default_registry

    reg = build_default_registry()
    assert reg.is_mutating("remember") is True
