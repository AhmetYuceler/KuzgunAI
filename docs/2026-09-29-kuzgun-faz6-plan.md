# Kuzgun Faz 6: Taşınabilirlik + Cila — Uygulama Planı

**Goal:** Kuzgun'u ayarlanabilir (config) ve taşınabilir hale getirmek: model, Ollama adresi, hafıza yolu, motor adresi, sunucu host/port ortam değişkenleriyle ayarlanır. Sunucuya taşımak = ortam değişkenlerini ayarlayıp motoru orada çalıştırmak. Ayrıca sistem promptu cilası ve bir README.

**Architecture:** `config.py` (`Config` + `load_config()` ortam değişkenlerinden okur, varsayılanlarla). `KuzgunEngine` config'ten model/embed/db değerlerini alır. `server.main` config host/port; `client.main` config `KUZGUN_ENGINE_URL`. README.md kullanım + taşınabilirlik anlatır.

**Tech Stack:** Python 3.12 (stdlib os/dataclasses), pytest. Yeni bağımlılık yok.

**Spec:** `docs/2026-09-29-kuzgun-tasarim.md` (§3, §10 taşınabilirlik)

## Global Constraints
- Ortam değişkenleri: `KUZGUN_MODEL`, `KUZGUN_EMBED_MODEL`, `KUZGUN_OLLAMA_URL`, `KUZGUN_DB`, `KUZGUN_ENGINE_URL`, `KUZGUN_HOST`, `KUZGUN_PORT`.
- Tüm ayarların makul varsayılanı var (env yoksa mevcut davranış korunur).
- Geriye uyumluluk: mevcut testler bozulmaz.

## Review Focus
- `load_config` env yokken varsayılanları döner. (Task 1 testi)
- `load_config` env varken onları okur; `KUZGUN_PORT` int'e çevrilir. (Task 1 testi)
- KuzgunEngine config'teki db yolunu kullanır. (Task 2 testi)

## Görevler
- **Task 1 — config.py:** `Config` dataclass + `load_config()`. Test: varsayılanlar; env okuma; port int.
- **Task 2 — wiring + prompt:** KuzgunEngine config'ten model/embed/db; server.main host/port; client.main engine_url; SYSTEM_PROMPT "Adın Kuzgun" olarak cilalanır. Test: engine config db yolu; prompt "Kuzgun" içerir.
- **Task 3 — README.md:** kurulum, `kuzgun`/`kuzgun-server`/`kuzgun-client`, modlar, env ayarları, taşınabilirlik. (Doküman.)

## Sonunda
Kuzgun ayarlanabilir ve taşınabilir; README ile belgeli. v1 tamam. İleride (L2): LoRA, subagent'lar, sunucuda vLLM.
