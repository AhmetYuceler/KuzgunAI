# Kuzgun Faz 5: Motor + İstemci (FastAPI) — Uygulama Planı

**Goal:** Kuzgun'un çekirdeğini bir servise (FastAPI motor) çıkarmak ve ona bağlanan ince bir HTTP istemci eklemek. Böylece motor yerelde veya kiralık sunucuda çalışabilir; istemci sadece adresi değiştirerek bağlanır.

**Architecture:** `engine.py` çekirdeği toplar: `KuzgunEngine` (model + embedder + memory + registry + konuşma durumu) `chat(message, mode)` sunar; ortak yardımcılar (SYSTEM_PROMPT, build_default_registry, build_memory, inject_memory) buraya taşınır (cli.py bunları engine'den içe aktarır — geriye uyumlu). `server.py` FastAPI ile `POST /chat` ve `GET /health` sunar. İnce istemci `remote_chat(message, base_url, mode)` (stdlib urllib) ve `kuzgun-server` giriş noktası (uvicorn).

**Tech Stack:** Python 3.12, FastAPI, uvicorn, httpx (FastAPI TestClient için). pytest.

**Spec:** `docs/2026-09-29-kuzgun-tasarim.md` (§3 motor+istemci)

## Global Constraints
- Yeni bağımlılıklar: `fastapi`, `uvicorn` (motor); `httpx` (dev, TestClient).
- Motor `chat` etkileşimsizdir: `confirm=None` → **normal modda değişiklik yapan araçlar reddedilir** (güvenli). HTTP üzerinden mutasyon için `otonom` mod (bilinçli tercih). Etkileşimli onay yerel `kuzgun` CLI'da kalır. (v1 sınırı.)
- KuzgunEngine bağımlılıkları enjekte edilebilir (test için Fake'ler); birim testler ağa çıkmaz.

## Review Focus
- Motor araçsız mesaja cevap verir (fake model). (Task 1 testi)
- Motor normal modda mutasyonu reddeder (confirm yok). (Task 1 testi)
- `POST /chat` cevabı JSON `{reply}` döndürür; `GET /health` ok. (Task 2 testi)
- remote_chat gövdeyi doğru gönderir/çözer (enjekte edilen poster). (Task 3 testi)

## Görevler
- **Task 1 — engine.py:** yardımcıları taşı + `KuzgunEngine(client,embedder,memory,registry).chat(message,mode)`. cli.py engine'den içe aktarsın (mevcut testler bozulmasın). Test: fake'lerle araçsız cevap + normal-mod mutasyon reddi.
- **Task 2 — deps + server.py:** fastapi/uvicorn/httpx ekle; `POST /chat {message,mode}` → `{reply}`, `GET /health`. Test: FastAPI TestClient.
- **Task 3 — istemci:** `remote_chat(message, base_url, mode, _post=None)` (urllib) + `kuzgun-server` giriş noktası (uvicorn.run). Test: enjekte edilen poster ile gövde/çözme.

## Sonunda
Kuzgun motoru bir servis olarak çalışıyor; ince istemci HTTP ile bağlanıyor. Sunucuya taşımak = motoru orada çalıştırıp istemcinin adresini değiştirmek. Sıradaki Faz 6: taşınabilirlik + cila (config, loglama, data klasörü).
