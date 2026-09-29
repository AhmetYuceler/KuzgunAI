# Faz C — Claude özelliklerinin uyarlanması (rapor)

Tarih: 2026-09-29. Dal: `faz-c` (izole worktree; ana checkout'ta eş zamanlı vision/UI
oturumu sürdü, iş bölümü: o cli/ui, ben engine/models/agent/yeni modüller). 342 test.

## Yapılanlar

| Madde | İş | Commit |
|---|---|---|
| C1 | **Yapılandırılmış çıktı** (`structured.py`): `complete_json` JSON'a zorlar + yeniden dener; orkestratör planı serbest-metin ayrıştırmaz | af95480 |
| C2 | **Bütçe + zarif kapanış**: `run_turn(wrapup=True)` max_steps dolunca çökmez/Claude'a gitmez, modelden "yaptıklarını özetle" turu ister | 8f2f32a |
| C3 | **Büyük araç çıktısı dosyaya**: limit üstü çıktı `out_dir`'e tam yazılır, bağlama önizleme + yol (7B read_file ile okur) | 897df6d |
| C4 | **Yedek model zinciri** (`FallbackClient`): model düşerse sıradakine geçer; `KUZGUN_FALLBACK_MODELS` | b3afef0 |
| C5 | **`Tool(param:value)` izin kuralları**: deterministik allow/deny/ask (fnmatch); `KUZGUN_PERMISSION_RULES` | 67c1f14 |
| C6 | **Compaction**: bağlam dolunca eski turları özetle, sonu koru; olgular zaten SQLite'ta; `KUZGUN_COMPACTION` | 7d232d9 |
| C7 | **Tura-bağlı hatırlatma**: `chat(reminder=)` model o turda görür, geçmişe girmez | 0cacabc |
| C8 | **Betik workflow'ları** (`workflows.py`): agent/parallel/pipeline, izole, yalnız son değer | d5edd3a |
| C9 | **`/doktor`** (`doctor.py`, `kuzgun-doctor`): Ollama/model/claude/DB/MCP kontrolleri | 8b81376 |
| C10 | **`/fork`**: `engine.fork_session` oturum geçmişini derin kopyalar | 0cacabc |
| C11 | **Oturumlar-arası mesajlaşma** (`inbox.py` + `/inbox/send,poll`): yetki taşımaz, hız sınırı + kopya düşürme + kuyruk sınırı | 3381456 |
| C12 | **Eval A/B** (`bench.run_ab`): özellik açık/kapalı hakemle karşılaştırma | d7ed87e |

## Kapsam / bilinçli kararlar

- **7B'ye uygunluk süzgeci uygulandı:** güvenlik kararı (auto mode sınıflandırıcısı),
  computer/browser use, /design, Projects — 7B'ye aktarılmadı (öncü model + uzun ufuk
  gerektirir). İzin kuralları deterministik (model zekâsına dayanmaz).
- **C11 `/mesaj` CLI komutu** ve **C9/C10 slash komutları**: `cli.py` eş zamanlı
  oturumun (peer) alanında; çekirdek mantık + HTTP/entry-point tarafım bitti, kullanıcıya
  dönük slash komutları peer ile koordineli eklenecek (`kuzgun-doctor` ayrı script hazır).
- Tüm yeni ayarlar `Config`'e eklendi (frozen), `KUZGUN_*` ile açılır; varsayılanlar
  eski davranışı korur (fallback boş, compaction kapalı, kurallar boş).

## Doğrulama

`.venv\Scripts\python.exe -m pytest -q` → 342 passed. Her madde için test. Geriye
dönük uyum korundu (public API, ortam değişkenleri, mevcut testler).
