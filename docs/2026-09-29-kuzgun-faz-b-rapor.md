# Faz B — Mimari temel (rapor)

Tarih: 2026-09-29. Dal: `faz-b` (izole worktree `LLM-fazA`; ana checkout'ta eş
zamanlı "vision" oturumu çalıştı, koordineli ilerlendi). Faz B, vision main'e
(`2afe968`) alındıktan sonra onun üstüne rebase edilerek yapıldı.

## Yapılanlar

| Adım | İş | Commit |
|---|---|---|
| B7 | Hafıza: `MemoryStore` protokolü; her kayıt embedding model+boyut saklar, aramada boyut-uyumsuz kayıtlar atlanır (model değişince sessiz bozulma önlendi); `min_score` benzerlik eşiği | e4456d8 |
| B1 | Loglama: `kuzgun` logger, `setup_logging` (idempotent), `timed` (ms); `run_turn`'e tur kimliği + model/araç süreli loglar; sessiz `except` yerine log | 3c6f35f |
| B6 | Araç çıktısı kırpma (`MAX_TOOL_CHARS`): büyük çıktı 7B bağlamını doldurmasın | fc46efb |
| B2 | `Config` frozen + doğrulama; yeni alanlar (api_key, temperature, max_steps, max_history, request_timeout, mcp_config_path, memory_min_score); `KUZGUN_HOME` altına göreli yol çözümü | 3b2666f |
| B3/B4 | `bootstrap.py` fabrika katmanı (make_client/embedder/memory, build_default_registry, build_engine); `OpenAICompatBackend` (OllamaClient takma ad, vLLM'e taşımaya hazır); `remember` config'den koparıldı (partial ile bağlanır = ToolContext); engine kurulumu bootstrap'e devretti | 5216853 |
| B5 | `ToolResult` (str alt sınıfı + `ok`): hata artık metin-sniffing ile değil bayrakla anlaşılır; meşru "Error: 404" çıktısı yanlış devretme tetiklemez; izin reddi de hata değil | c82ef4e |

**276 test, ruff temiz.** Bağımlılık yönü hedeflendi: `clients/server → bootstrap
→ engine → agent/routing → core`; somut sınıfları yalnız `bootstrap` kurar; araçlar
`config`/`engine` import etmez.

## Ertelenenler

- **B8 (tek REPL):** `cli.py` eş zamanlı oturumca (vision/resume/sekme başlığı) aktif
  düzenlendiği için ertelendi; çakışmayı önlemek üzere o oturum bitince yapılacak.
- **B4 tam boru-hattı nesnesi:** engine'in kurulum sorumluluğu bootstrap'e taşındı
  (asıl kazanım); `chat()`'in ayrı bir pipeline sınıfına çıkarılması kozmetik olduğu
  için yapılmadı.
- **B6 token-duyarlı kırpma:** karakter tabanlı kırpma/trim yeterli çalışıyor; gerçek
  token sayımı ileride.

## Doğrulama

`.venv\Scripts\python.exe -m pytest -q` → 276 passed. Her yeni yetenek için test.
Geriye dönük uyum korundu: `KuzgunEngine.chat()`, `build_default_registry`,
`OllamaClient`, tüm `KUZGUN_*` ortam değişkenleri, `_sessions` erişimi aynı çalışır.
