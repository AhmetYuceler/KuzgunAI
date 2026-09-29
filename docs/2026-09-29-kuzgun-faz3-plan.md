# Kuzgun Faz 3: Hafıza + RAG — Uygulama Planı

**Goal:** Kuzgun'un konuşmaları bir hafızaya (SQLite + embedding) yazması ve yeni soruda ilgili geçmişi geri çağırıp bağlama katması — "kendi kendine öğrenme"nin temeli.

**Architecture:** `embeddings.py` (cosine benzerliği + `Embedder` Protocol + `FakeEmbedder` test için + `OllamaEmbedder` gerçek, nomic-embed-text). `memory.py` (`Memory`: SQLite'ta konuşmaları embedding ile saklar, benzerlikle arar) + `recall_context` yardımcısı. CLI her turda: ilgili geçmişi çağır → bağlama kat → cevapla → konuşmayı kaydet. Embedding çağrısı enjekte edilebilir; birim testler gerçek modele çıkmaz.

**Tech Stack:** Python 3.12, SQLite (stdlib), Ollama `nomic-embed-text` (embedding), pytest. Yeni pip bağımlılığı yok.

**Spec:** `docs/2026-09-29-kuzgun-tasarim.md` (§9 öğrenme)

## Global Constraints
- Hafıza taşınabilir tek dosya: `data/memory.db` (data/ zaten .gitignore'da).
- Embedding testte `FakeEmbedder` (deterministik, harf-frekansı) ile; gerçekte `OllamaEmbedder`.
- Hafıza sınırsız büyür (spec: sınır yok).

## Review Focus
- Boş hafızada arama → çökmez, boş liste/mesaj. (Task 2 testi)
- Benzer soru → en ilgili geçmiş kaydı ilk sırada döner. (Task 2 testi)
- cosine: aynı vektör=1, dik=0, boş=0. (Task 1 testi)
- recall_context boş hafızada boş string döner. (Task 3 testi)

## Görevler
- **Task 1 — embeddings.py:** `cosine(a,b)`, `Embedder` Protocol, `FakeEmbedder`, `OllamaEmbedder`. Test: cosine değerleri + FakeEmbedder benzer metinde yüksek skor.
- **Task 2 — memory.py:** `Memory(db_path)` → `add(user,assistant,embedder)`, `search(query,embedder,k)`, `count()`. Test: ekle+ara (fake embedder ile ilgili kayıt ilk), boş hafıza.
- **Task 3 — recall_context:** `recall_context(memory,query,embedder,k)` → biçimli string ya da boş. Test: dolu/boş.
- **Task 4 — CLI wiring + e2e:** main() Memory+OllamaEmbedder kurar; her turda recall→inject→run_turn→add. `nomic-embed-text` ile gerçek e2e (hatırlama).

## Sonunda
Kuzgun geçmişi hatırlıyor; ilgili notları bağlama katıyor. Sıradaki Faz 4: teacher (Claude'a danışma) — takılınca sorar, cevabı bu hafızaya yazar.
