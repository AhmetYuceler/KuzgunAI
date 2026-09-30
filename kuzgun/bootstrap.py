"""Kurulum/fabrika katmanı (Faz B3).

Somut sınıfların (model arka ucu, embedder, hafıza, araç kataloğu) NASIL kurulacağı
tek yerde burada bilinir. Motor ve istemciler buradan kurar; araçlar config/engine
import etmez (bağımlılık yönü: clients/server → bootstrap → engine → agent → core).
"""

from __future__ import annotations

import functools

from kuzgun.config import Config, load_config
from kuzgun.embeddings import OllamaEmbedder
from kuzgun.logging_setup import get_logger
from kuzgun.mcp import load_mcp_servers
from kuzgun.memory import Memory
from kuzgun.models import FallbackClient, OpenAICompatBackend
from kuzgun.tools import ToolRegistry
from kuzgun.tools.ask_expert import ASK_EXPERT_SCHEMA, ask_expert
from kuzgun.tools.fetch_url import FETCH_URL_SCHEMA, fetch_url
from kuzgun.tools.glob_search import GLOB_SCHEMA, glob_search
from kuzgun.tools.grep_search import GREP_SCHEMA, grep_search
from kuzgun.tools.media_control import MEDIA_SCHEMA, media_control
from kuzgun.tools.read_file import READ_FILE_SCHEMA, read_file
from kuzgun.tools.remember import REMEMBER_SCHEMA, remember
from kuzgun.tools.run_command import RUN_COMMAND_SCHEMA, run_command
from kuzgun.tools.security_scan import SECURITY_SCAN_SCHEMA, security_scan
from kuzgun.tools.weather import WEATHER_SCHEMA, weather
from kuzgun.tools.web_recon import WEB_RECON_SCHEMA, web_recon
from kuzgun.tools.web_search import WEB_SEARCH_SCHEMA, web_search
from kuzgun.tools.write_file import WRITE_FILE_SCHEMA, write_file

log = get_logger("bootstrap")


def make_client(config: Config, model: str | None = None) -> OpenAICompatBackend:
    """Genel/kod/görsel modeller için OpenAI-uyumlu arka uç kurar (config'ten)."""
    return OpenAICompatBackend(
        model=model or config.model,
        base_url=config.ollama_url,
        api_key=config.api_key,
        timeout=config.request_timeout,
        temperature=config.temperature,
    )


def make_general_client(config: Config):
    """Genel sohbet istemcisi. config.fallback_models doluysa birincil + yedekleri
    kapsayan bir FallbackClient döner (C4); yoksa tek arka uç."""
    if config.fallback_models:
        names = [config.model] + [
            m.strip() for m in config.fallback_models.split(",") if m.strip()
        ]
        return FallbackClient([make_client(config, m) for m in names])
    return make_client(config, config.model)


def make_embedder(config: Config) -> OllamaEmbedder:
    return OllamaEmbedder(model=config.embed_model, base_url=config.ollama_url)


def make_memory(config: Config) -> Memory:
    return Memory(config.db_path)


def build_default_registry(config: Config | None = None) -> ToolRegistry:
    """Yerleşik araçları kaydeder. `remember`, config'in notes_path'ine `partial`
    ile bağlanır (ToolContext) — böylece araç modülü config import etmez."""
    cfg = config if config is not None else load_config()
    reg = ToolRegistry()
    reg.register(READ_FILE_SCHEMA, read_file)
    reg.register(GLOB_SCHEMA, glob_search)
    reg.register(GREP_SCHEMA, grep_search)
    reg.register(WEB_SEARCH_SCHEMA, web_search)
    reg.register(FETCH_URL_SCHEMA, fetch_url)
    reg.register(ASK_EXPERT_SCHEMA, ask_expert)
    # A6 (bug #2): remember mutating (model onaysız yazamasın). Yol partial ile bağlı.
    reg.register(
        REMEMBER_SCHEMA,
        functools.partial(remember, _path=cfg.notes_path),
        mutating=True,
    )
    reg.register(MEDIA_SCHEMA, media_control)  # zararsız medya/müzik kontrolü
    reg.register(WEATHER_SCHEMA, weather)  # hava durumu (konumdan)
    reg.register(WEB_RECON_SCHEMA, web_recon)  # yetkili güvenlik keşfi (GET, okuyan)
    reg.register(SECURITY_SCAN_SCHEMA, security_scan, mutating=True)  # aktif zafiyet taraması
    reg.register(WRITE_FILE_SCHEMA, write_file, mutating=True)
    reg.register(RUN_COMMAND_SCHEMA, run_command, mutating=True)
    return reg


def build_registry_with_mcp(config: Config) -> ToolRegistry:
    """Yerleşik araçlar + (varsa) MCP sunucu araçları."""
    reg = build_default_registry(config)
    try:
        load_mcp_servers(reg, config.mcp_config_path)
    except Exception as exc:  # noqa: BLE001 — MCP bozuksa Kuzgun ayakta kalsın
        log.warning("MCP yüklenemedi: %s", exc)
    return reg


def build_engine(config: Config | None = None, **overrides):
    """KuzgunEngine'i kurar. `overrides` ile bağımlılıklar (client, embedder, memory,
    registry, confirm, escalate, coder_client, vision_client) enjekte edilebilir
    (test/sunucu için). Verilmeyenler config'ten kurulur."""
    from kuzgun.engine import KuzgunEngine  # geç import: döngüsel bağımlılığı önler

    cfg = config if config is not None else load_config()
    return KuzgunEngine(config=cfg, **overrides)
