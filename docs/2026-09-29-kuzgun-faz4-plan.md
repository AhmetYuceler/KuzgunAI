# Kuzgun Faz 4: Teacher (Claude'a danışma) — Uygulama Planı

**Goal:** Kuzgun takıldığında / kullanıcı istediğinde arka planda `claude` CLI'ı (Max üyeliği) çağırıp danışması, cevabı gösterip **hafızaya yazması** — böylece bir dahaki sefere aynı soruyu kendi cevaplayabilmesi.

**Architecture:** `teacher.py` (`ask_claude(question)` → `claude --print` alt sürecini çalıştırır, cevabı döndürür; çalıştırıcı test için enjekte edilebilir). Bir `ask_expert` aracı (okuyan) yerel modelin emin olmadığında uzmana danışmasını sağlar. CLI'de ayrıca `/claude <soru>` komutu: doğrudan Claude'a sorar, cevabı yazdırır ve `(soru, cevap)` çiftini hafızaya kaydeder (öğrenme döngüsü).

**Tech Stack:** Python 3.12, `claude` CLI (Max, ayrı API anahtarı yok), pytest. Yeni pip bağımlılığı yok.

**Spec:** `docs/2026-09-29-kuzgun-tasarim.md` (§9 teacher)

## Global Constraints
- `claude` çağrısı `subprocess` ile, `--print` (etkileşimsiz) modda; çalıştırıcı test için enjekte edilir (birim testler gerçek claude'a çıkmaz).
- `ask_expert` okuyan (mutating=False) araçtır.
- Hata (claude yok/zaman aşımı) → `Error: ...`, çökme yok.
- Öğrenme: `/claude` cevabı doğrudan hafızaya (soru→cevap) yazılır.

## Review Focus
- `claude` bulunamaz / hata verir → `Error: ...`, çökmez. (Task 1 testi)
- Boş soru → `Error:`. (Task 1 testi)
- `ask_expert` boş soruda `Error:`; şema adı doğru. (Task 2 testi)
- Registry `ask_expert`'i okuyan olarak içerir. (Task 3 testi)

## Görevler
- **Task 1 — teacher.py:** `ask_claude(question, _runner=None) -> str`. Test: runner cevabı döndürür; hata yakalanır; boş soru reddedilir.
- **Task 2 — tools/ask_expert.py:** `ask_expert(question)` + `ASK_EXPERT_SCHEMA` (ask_claude'a sarar). Test: boş soru Error; şema adı.
- **Task 3 — CLI:** `ask_expert` kaydı (okuyan) + `/claude <soru>` komutu (sorar→yazar→hafızaya kaydeder) + `/yardim` güncelle. Test: registry ask_expert okuyan; /yardim claude içerir. E2e: gerçek `claude --print`.

## Sonunda
Kuzgun zor sorularda Claude'a danışıp öğreniyor; öğrendiği hafızaya yazılıyor. Sıradaki Faz 5: FastAPI motor + ince istemci (taşınabilirlik).
