# Kuzgun — Teknik Tasarım Dokümanı

**Tarih:** 2026-09-29
**Sürüm:** 0.1 (taslak — onay bekliyor)
**Sahip:** Ahmet Yüceler
**Durum:** Tasarım onaylandı; uygulama planı yazılacak.

---

## 1. Amaç ve Vizyon

**Kuzgun**, terminalden `kuzgun` yazınca açılan, kişisel bir yapay zekâ ajanıdır.
Kullanıcı ona ne isterse söyler; Kuzgun arka planda **düşünür, gerekirse internette
araştırır, gerekirse bilgisayarda değişiklik yapar** ve cevabı verir. İnternet yokken
de temel soruları cevaplayabilir ve mantık üretebilir.

**Nihai hedef:** Claude Code'un yaptığı işi, kişiye özel ve büyük ölçüde yerel
(bilgisayarda çalışan) bir modelle yapan; zamanla **kendi kendine öğrenen**; gerektiğinde
kiralık bir sunucuya taşınıp oradan devam edebilen, ama kullanıcının yine kendi
bilgisayarından `kuzgun` ile eriştiği bir sistem.

**Başarı ölçütleri (v1):**
- `kuzgun` komutu terminalde açılıyor ve akıcı çalışıyor (yerel modelle hızlı: hedef ~35-55 kelime/sn).
- Hem soru-cevap/araştırma hem de dosya/komut işlemleri yapabiliyor.
- Kullanıcının seçebildiği **modları** var (plan / normal / otonom).
- Takıldığında Claude'a danışıp öğrendiğini hafızaya yazıyor; benzer soruda artık kendi cevaplıyor.
- Tamamı taşınabilir: bir klasörü kopyalayınca başka makinede/sunucuda kaldığı yerden devam ediyor.

---

## 2. Temel Kavram: Üç Farklı Şeyi Ayırmak

Bu proje sık karıştırılan üç şeyi net ayırır:

1. **Model eğitmek (sıfırdan):** Claude/GPT'nin yaptığı. Binlerce GPU, çok yüksek maliyet.
   **Kapsam dışı** — bu projede yapılmayacak.
2. **Hazır bir modeli yerelde çalıştırmak:** Kullanıcının elindeki GGUF dosyası buydu.
   Kuzgun'un "beyni" bu yolla gelir (Ollama + Qwen).
3. **Bir modelin etrafına ajan kurmak:** Kuzgun'un asıl özü. Model = beyin; ajan = o beynin
   elleri (araçlar), gözleri (araştırma) ve hafızası.

> **Kuzgun = (2) yerel model + (3) ajan katmanı + takılınca danışman olarak Claude.**

**"Kendi kendine öğrenme" ne demek (ve ne değil):** Modelin ağırlıkları (weights) her soruda
değişmez. Bunun yerine Kuzgun, öğrendiklerini bir **hafızaya (RAG)** yazar ve sonraki sorularda
oraya bakar. Sonuç pratikte "öğreniyormuş" gibi olur. (İleri seviye/opsiyonel: biriken bilgiyle
ara ara **LoRA** ince-ayarı yapıp bilgiyi modelin içine de gömmek — bkz. §9.)

---

## 3. Genel Mimari: Motor + İstemci

Kuzgun iki parçadan oluşur. Bu ayrım, "sunucuya taşıma ama yine `kuzgun` ile erişme"
gereksinimini doğrudan çözer.

```
   KULLANICININ BİLGİSAYARI                    (İLERİDE) KİRALIK SUNUCU
 ┌────────────────────────┐                  ┌────────────────────────────┐
 │  kuzgun (İSTEMCİ)      │ ── HTTP/WS ──►    │   KUZGUN MOTORU             │
 │  ince terminal sohbeti │ ◄── cevap ───     │   (aynı kod, büyük GPU)     │
 └────────────────────────┘                  └────────────────────────────┘
        │                                                ▲
        │  ya da motor yerelde çalışır (offline)         │  taşıyınca
        └────────────────────────────────────────────────┘  sadece adres değişir
```

- **Kuzgun Motoru (beyin/servis):** Ajan döngüsü + model bağlantısı + araçlar + hafıza + modlar.
  Bir HTTP/WebSocket servisi olarak çalışır. Bugün yerelde, yarın sunucuda — **aynı kod**.
- **Kuzgun İstemcisi:** Terminale `kuzgun` yazınca açılan ince sohbet arayüzü. Motora bağlanır.
  Motor yereldeyse `localhost`, sunucudaysa sunucu adresi. Kullanıcı için **hep aynı komut**.

**Taşınabilirlik:** Tüm ayarlar ve hafıza tek bir `data/` klasöründe tutulur. Sunucuya geçişte
o klasör kopyalanır, istemcinin baktığı adres değişir; gerisi aynıdır.

---

## 4. Veri Akışı (Ajan Döngüsü)

Kullanıcı bir şey sorduğunda:

```
sen → kuzgun → [1] Hafızaya bak (bunu daha önce öğrendim mi?)
                 [2] Yerel model düşünür (ajan döngüsü başlar)
                 [3] Gerekirse ARAÇ çağırır (web ara / dosya oku-yaz / komut çalıştır)
                     → riskli işlem varsa MODA göre önce kullanıcıya SOR
                 [4] Model/işlem takılırsa → Claude'a DANIŞ (claude CLI, Max ile)
                 [5] Öğrenileni HAFIZAYA YAZ   ← kendi kendine öğrenme
                 [6] Nihai cevabı döndür
```

**Ajan döngüsünün özü (Anthropic mühendisliğinden):** Model ya doğrudan cevap verir ya da bir
"araç çağrısı" (isim + girdi) üretir. Kod aracı çalıştırıp sonucu modele geri besler; model
"başka araç lazım mı, yoksa cevabı yazayım mı?" diye devam eder. Teknik olarak bu, model artık
araç istemeyene kadar dönen bir döngüdür (`tool_use` → ... → `end_turn`).

---

## 5. Bileşenler

Her bileşen tek işi olan, ayrı test edilebilir bir birimdir.

| Bileşen | Görevi | Temel bağımlılık |
|---|---|---|
| `agent` | Ajan döngüsü; modları uygular; araç çağrılarını yönetir | `models`, `tools` |
| `models` | Model soyutlaması. Bugün Ollama (yerel); "zor mod"da Claude; yarın sunucuda vLLM | Ollama API |
| `tools` | Araçlar: web arama+okuma, dosya oku/yaz, glob/grep, komut çalıştır. Her araç izin kapısına tabi | işletim sistemi, web |
| `memory` | Hafıza/RAG deposu + bağlam (context) yönetimi/özetleme | SQLite, embedding modeli |
| `teacher` | Takılınca `claude` CLI'ı çağırır, cevabı alır, hafızaya yazar | claude CLI (Max) |
| `permissions` | İzin kapısı + mod sistemi (plan/normal/otonom) | — |
| `api` | İstemcinin bağlandığı servis (FastAPI/uvicorn) | FastAPI |
| `cli` | `kuzgun` terminal istemcisi; modlar & `/` komutları | rich/textual |
| `config` + `data/` | Taşınabilir ayarlar ve hafıza klasörü | — |

**İyi araç tanımı ilkesi:** Her aracın adı + 3-4 cümlelik net açıklaması + JSON şeması olur.
Açıklama kalitesi, modelin doğru aracı seçmesini doğrudan belirler. Az sayıda ama yetenekli
araç, çok sayıda dar araca tercih edilir.

---

## 6. Teknik Yığın ve Gerekçeler

| Program/Kütüphane | Rol | Neden |
|---|---|---|
| **Ollama** | Yerel model motoru | Windows'ta tek tık kurulum; RTX 5060'ı otomatik bulur; OpenAI-uyumlu API (`localhost:11434/v1`); model değiştirmek tek komut; **her modelin araç-çağırma şablonunu otomatik uygular** (flaky tool-call sorununu kökten çözer). |
| **Qwen2.5-7B-Instruct (Q4_K_M)** | Yerel beyin | 8 GB VRAM'e tam sığar (~5 GB); bu boyutta araç-çağırmada en iyilerden; ~35-55 kelime/sn. Kod ağırlıklıysa **Qwen2.5-Coder-7B**. |
| **Python 3.12 (ayrı sanal ortam)** | Motor/araç/hafıza kodları | Sistemdeki 3.14 çok yeni; bazı ML kütüphaneleri henüz uyumsuz. 3.12 venv güvenli seçim. |
| **FastAPI + uvicorn** | Motor↔istemci servisi | Motor+istemci ayrımını (taşınabilirlik) sağlar. |
| **rich / textual** | `kuzgun` terminal arayüzü | Akıcı, okunabilir sohbet ekranı. |
| **nomic-embed-text (Ollama) + SQLite** | Hafıza/RAG | Embedding'i Ollama verir; SQLite taşınabilir tek dosya = "kopyala-taşı". |
| **httpx + trafilatura** | Web araştırma | Arama + sayfa metni çıkarma. Arama için ücretsiz seçenek (DuckDuckGo/SearxNG). |
| **claude CLI (mevcut)** | Öğretmen / "zor mod" | Max üyeliğiyle bedava danışman. Ayrı API anahtarı gerekmez. |
| **Docker (mevcut)** | İleride sunucu servisleri | Şimdilik opsiyonel. |
| *(sunucu, ileride)* **vLLM** | Sunucuda büyük model motoru | Yüksek eşzamanlılık/verim. Laptop=Ollama, sunucu=vLLM. |

**Alternatifler:** Ollama yerine **LM Studio** (görsel arayüz, aynı GGUF dosyaları) veya
maksimum güvenilirlik için **llama.cpp** (`--jinja` + grammar-constrained çıktı). Üçü de aynı
model dosyalarını kullanır, geçiş ucuzdur.

**Neden Grok/xAI değil:** Açık Grok modelleri (Grok-1 314B, Grok-2 ~270B) veri-merkezi
boyutundadır (8 GB VRAM'de çalışmaz), Grok-2 lisansı başka model eğitmeyi yasaklar ve xAI
işe yarar teknik doküman yayımlamaz. Açık ekosistemde en uygun aile **Qwen** (Apache 2.0,
güçlü araç-çağırma, iyi dokümanlar).

---

## 7. Model Seçimi ve Araç-Çağırma Notları

- **Birincil:** Qwen2.5-7B-Instruct — Q4_K_M. Genel amaçlı ajan için "sorunsuz çalışan" seçenek.
- **Kod ağırlıklıysa:** Qwen2.5-Coder-7B-Instruct.
- **Alternatif:** Qwen3-8B (daha yeni, agentic). **Uyarı:** "thinking mode" açıkken `<think>`
  belirteçleri araç şablonunu bozabilir → **Hermes araç formatı** kullan veya `/no_think`
  ile çalıştır.
- **En katı JSON uyumu:** Llama-3.1-8B-Instruct (yedek).
- **Kaçınılacaklar (ajan için güvenilmez):** 4B altı modeller (ör. Llama-3.2-3B düşük geçerli-JSON
  oranı), gevşek araç-çağıran modeller.
- **Güvenilirlik ipuçları:** Şablonu runtime'a bırak (Ollama otomatik yapar); düşük sıcaklık;
  KV-cache'i aşırı kuantalama; gerektiğinde grammar/JSON-şema ile kısıtlı çıktı.
- **Ollama kısıtı:** `tool_choice: required` desteklemez (aracı zorla çağırtamazsın). Ajan
  döngüsü `auto` ile tasarlanır; "zorunlu araç" gerekirse llama.cpp/vLLM'e geçilir.

---

## 8. Modlar ve Güvenlik

Kullanıcı, tıpkı Claude Code'daki gibi anlık mod değiştirir:

- `/mod plan` — sadece düşünür/araştırır, planı sunar, hiçbir şeye dokunmaz.
- `/mod normal` — zararsız işleri (okuma, arama, listeleme) yapar; kalıcı/riskli işlemlerden
  (dosya yazma/silme, komut, program kurma) önce **sorar**. (varsayılan)
- `/mod otonom` — sormadan yapar (kullanıcının sorumluluğunda).
- `/model yerel | zor` — "zor" = Claude'a daha çok danış.
- `/effort dusuk | orta | yuksek` — düşünme derinliği.

**İzin kapısı (permissions):** Her araç çağrısı, çalışmadan önce moda ve basit kurallara
(izinli/yasaklı yollar) göre denetlenir. Başta ML sınıflandırıcı yerine **kural tabanlı**
(yalın) bir kapı kullanılır. İleride araç öncesi/sonrası **hooks** eklenebilir.

---

## 9. Öğrenme Mekanizması

**Seviye 1 (v1 — hafıza/RAG):**
1. Kuzgun takılırsa → `teacher` üzerinden Claude'a danışır.
2. Claude'un cevabı (+ kullanıcı onayı) hafızaya (SQLite + embedding) yazılır.
3. Sonraki benzer soruda → önce hafızaya bakılır; cevap oradaysa Claude'a gidilmez.
4. Zamanla Claude'a danışma azalır. Ağırlıklar değişmez, sonuç "öğrenmiş" gibi olur.

**Seviye 2 (ileride — LoRA ince-ayar, opsiyonel):** Biriken soru→cevap verisiyle yerel modele
ara ara küçük bir LoRA eğitimi yapılıp bilgi modelin içine kalıcı gömülür. Bu, "sınırsız büyüme"nin
bir kolu; başta gerekli değildir.

---

## 10. Taşınabilirlik ve "Sınırsız Büyüme"

Bir modelin parametre sayısı sabittir (7B model öğrenerek 70B olmaz). Ama **sistem** sınırsız büyür:

- **(a) Hafıza** sonsuza dek birikir (SQLite → sunucuda pgvector/Qdrant).
- **(b) Model** daha iyi donanıma geçince büyür (Ollama → sunucuda vLLM + büyük model; tek ayar).
- **(c) LoRA** ile öğrenilen bilgi modele gömülür (Seviye 2).

Motor kodu hep aynı kalır; arkasındaki model ve hafıza büyür. Tavanı donanım belirler, kod değil.

---

## 11. Yol Haritası

| Hafta | İş | Çıktı |
|---|---|---|
| **0** | Ollama kur, Qwen2.5-7B indir, gerçek hızı ölç, Python 3.12 venv, proje iskeleti | Hızlı yerel model + boş proje |
| **1** | `agent` ajan döngüsü + ilk 2 araç (dosya oku, komut) | Araç çağırıp cevap veren Kuzgun |
| **2** | Araçları genişlet (dosya yaz, glob/grep, web arama+okuma) + izin kapısı + modlar | Güvenli, moddan moda geçen Kuzgun |
| **3** | `memory` (SQLite+embedding, KUZGUN.md, context özetleme) | Hatırlayan, ilgili bilgiyi çeken Kuzgun |
| **4** | `teacher` (claude escalation) + router (basit→yerel, zor→Claude) | Kendi kendine öğrenme döngüsü |
| **5** | FastAPI motoru + ince `kuzgun` istemcisi (yerel/sunucu adresi) | Terminalden `kuzgun` açılıyor |
| **6** | Loglama, hata yönetimi, taşınabilir config/data, MCP (ops.), taşıma provası | **v1 hazır**, sunucuya uygun |
| **L2** | LoRA ince-ayar, subagent'lar, sunucuda vLLM+büyük model | Sınırsız büyüme yolu |

*Tempo esnek; "hafta" sadece sıralamadır.*

---

## 12. Riskler ve Açık Sorular

- **Küçük model kalitesi:** 7B model bazı zor işlerde zorlanır → `teacher` (Claude) devreye girer.
- **Araç-çağırma kararlılığı:** Model/şablon seçimi kritik; §7'deki önlemler alınır.
- **Python 3.14 uyumu:** 3.12 venv ile aşılır.
- **Ollama `tool_choice` kısıtı:** `auto` ile tasarlanır; gerekirse llama.cpp/vLLM.
- **Web arama sağlayıcısı:** Ücretsiz (DuckDuckGo/SearxNG) ile başla; gerekirse ücretli API.
- **Güvenlik:** Otonom mod ve komut çalıştırma dikkatli test edilmeli; yasaklı yol listesi.
- **Açık soru:** Sunucu ne zaman/hangi sağlayıcıdan kiralanacak? (v1 sonrası.)

---

## 13. Kaynaklar

- Anthropic — Building Effective Agents: https://www.anthropic.com/research/building-effective-agents
- Anthropic — Tool use (how it works, define tools): https://platform.claude.com/docs/en/agents-and-tools/tool-use/
- Ollama — OpenAI uyumluluğu / araç desteği / Windows: https://docs.ollama.com/api/openai-compatibility · https://ollama.com/blog/tool-support · https://docs.ollama.com/windows
- llama.cpp — function calling: https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md
- vLLM — tool calling: https://docs.vllm.ai/en/latest/features/tool_calling/
- Qwen3 — function calling / thinking mode: https://qwen.readthedocs.io/en/latest/framework/function_call.html
- Grok-1 açık kaynak: https://x.ai/news/grok-os · https://github.com/xai-org/grok-1
