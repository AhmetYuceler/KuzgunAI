# 🦅 Kuzgun

Kişisel, büyük ölçüde yerel çalışan bir terminal yapay zekâ ajanı. Terminale
`kuzgun` yazınca açılır; düşünür, internette araştırır, bilgisayarında (izinle)
değişiklik yapar ve konuştuklarınızı hatırlar. Takıldığında Claude'a danışıp
öğrenir. Gerektiğinde bir sunucuya taşınıp oradan hizmet verebilir.

## Ne işe yarar

- **Yerel beyin:** Ollama + Qwen2.5-7B (bilgisayarında, ~%100 GPU, hızlı, offline).
- **Araçlar:** dosya oku/yaz, komut çalıştır, dosya bul (glob), içerik ara (grep),
  internette ara (web_search), sayfa oku (fetch_url), uzmana danış (ask_expert),
  medya kontrol (Spotify vb.), hava durumu, kalıcı not (remember).
- **Modlar:** `/mod plan` (sadece düşün) · `/mod normal` (sorarak yap) ·
  `/mod otonom` (sormadan yap). `shift+tab` de döndürür.
- **Hafıza/RAG:** konuşmaları SQLite + embedding ile saklar, ilgili geçmişi
  (benzerlik eşiğiyle) hatırlar — "kendi kendine öğrenme".
- **Kalıcı notlar:** `KUZGUN.md` (Claude'un CLAUDE.md'si gibi) her oturumda yüklenir.
- **Görsel:** `alt+v` ile pano resmini ekler; görsel model (qwen2.5vl) betimler,
  metin ajanı (gerekirse web araştırmasıyla) cevaplar.
- **Oturumlar:** `/resume` ile eski oturuma dön, `/rename` ile ad ver, `/fork` ile
  konuşmayı çatalla; `/init` çalışma klasörünü analiz edip proje `KUZGUN.md`'si üretir.
- **Ajan orkestrasyonu:** `/ajanlar <görev>` görevi böler, izole alt-ajanlarla tek
  tek yapar; `workflows` modülü ile betikleştirilebilir (agent/parallel/pipeline).
- **Teacher / devretme:** takılınca ya da açıkça zor işlerde Claude'a danışır
  (`/claude <soru>`), cevabı hafızaya yazar. Yedek model zinciri de kurulabilir.
- **Sağlık:** `kuzgun-doctor` (ya da `/doktor`) Ollama/model/claude/DB kontrolü.
- **Motor + İstemci:** çekirdek bir FastAPI servisidir; ince istemci HTTP ile bağlanır.
  Sunucuya taşımak = motoru orada çalıştırıp istemcinin adresini değiştirmek.

## Kurulum

Gereksinimler: Python 3.12, [Ollama](https://ollama.com/download).

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Modeller (bir kez)
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5-coder:7b-instruct
ollama pull nomic-embed-text
ollama pull qwen2.5vl:7b      # görsel (alt+v) için

kuzgun-doctor                 # kurulum sağlık kontrolü
```

## Kullanım

**Yerel (zengin) mod — etkileşimli:**
```powershell
kuzgun                        # yeni oturum
kuzgun -c                     # en son oturuma devam
kuzgun -r [ad]                # oturuma dön (listeden seç ya da ad ver)
```
Komutlar: `/yardim` · `/mod <plan|normal|otonom>` (veya `/plan`/`/normal`/`/otonom`) ·
`/init` · `/claude <soru>` · `/ajanlar <görev>` · `/hatirla <şey>` · `/notlar` ·
`/gecmis` · `/resume [ad|no]` · `/rename <ad>` · `/doktor` · `/fork` · `/cikis`.
Girişte `alt+v` pano resmi ekler.

**Motor + ince istemci (taşınabilir):**
```powershell
kuzgun-server                                  # 1. terminal: motor
kuzgun-client http://SUNUCU_ADRESI:8000        # 2. terminal / başka makine
```
İstemcide ayrıca: `/mesaj <oturum> <metin>` ve `/gelen` (oturumlar-arası mesajlaşma).

## Ayarlar (ortam değişkenleri)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `KUZGUN_HOME` | *(boş)* | Ayarlıysa göreli veri yolları (db/notes/sessions/out) bu kök altına çözülür |
| `KUZGUN_MODEL` | `qwen2.5:7b-instruct` | Yerel genel model |
| `KUZGUN_CODER_MODEL` | `qwen2.5-coder:7b-instruct` | Kod işlerine yönlenen model |
| `KUZGUN_VISION_MODEL` | `qwen2.5vl:7b` | Resimli mesajları betimleyen model |
| `KUZGUN_FALLBACK_MODELS` | *(boş)* | Genel model düşerse denenecek yedekler (virgülle) |
| `KUZGUN_MODE` | `normal` | Başlangıç modu: `plan`/`normal`/`otonom` |
| `KUZGUN_AUTOROUTE` | `1` | Açıkça zor işleri (react/proje-kur/belge…) baştan Claude'a yönlendir |
| `KUZGUN_REFLECT` | `1` | Yazılan kodu doğrula, sözdizimi hatalıysa düzelttir |
| `KUZGUN_MEMORY_MIN_SCORE` | `0.70` | Hafıza (RAG) alaka eşiği; altı bağlama girmez |
| `KUZGUN_COMPACTION` | `0` | Bağlam dolunca eski turları özetle (yoksa kırp) |
| `KUZGUN_MAX_STEPS` / `KUZGUN_MAX_HISTORY` | `10` / `24` | Ajan adım / bağlam üst sınırı |
| `KUZGUN_PERMISSION_RULES` | *(boş)* | İzin kuralları: `allow run_command(cmd:git *)` gibi |
| `KUZGUN_OUT_DIR` | `data/out` | Büyük araç çıktılarının tam hâli buraya yazılır |
| `KUZGUN_MCP_CONFIG` | `mcp_servers.json` | MCP sunucu tanımları |
| `KUZGUN_EMBED_MODEL` | `nomic-embed-text` | Embedding modeli |
| `KUZGUN_OLLAMA_URL` | `http://localhost:11434/v1` | Ollama (ya da vLLM) adresi |
| `KUZGUN_DB` / `KUZGUN_NOTES` | `data/memory.db` / `data/KUZGUN.md` | Hafıza / kalıcı notlar |
| `KUZGUN_SESSIONS_DIR` / `KUZGUN_SESSION_DAYS` | `data/sessions` / `30` | Oturum arşivi / süpürme |
| `KUZGUN_ENGINE_URL` | `http://127.0.0.1:8000` | İstemcinin bağlanacağı motor |
| `KUZGUN_HOST` / `KUZGUN_PORT` | `127.0.0.1` / `8000` | Sunucu adresi |
| `KUZGUN_TOKEN` | *(boş)* | Uzak erişim için bearer token |
| `KUZGUN_ALLOWED_HOSTS` | `127.0.0.1,localhost` | İzinli Host başlıkları (DNS-rebinding) |

## MCP araçları (isteğe bağlı)

Kuzgun, [MCP](https://modelcontextprotocol.io) sunucularına bağlanıp onların
araçlarını kendi araç setine ekleyebilir. `mcp_servers.example.json`'u
`mcp_servers.json` olarak kopyala, düzenle. Araçlar `<sunucu>__<arac>` olarak
adlandırılır (yerleşiği ezmez). Değişiklik yapan MCP araçları **varsayılan olarak**
mod/onay kapısına tabidir; yalnızca zararsız olanları `read_only` listesine ekle.
**Güvenlik:** yalnızca güvendiğin sunucuları ekle.

## Hız ipuçları (Ollama)

| Değişken | Öneri | Etki |
|---|---|---|
| `OLLAMA_KEEP_ALIVE` | `-1` | Model bellekte kalır; soğuk başlatma gecikmesi biter |
| `OLLAMA_FLASH_ATTENTION` | `1` | Flash Attention; KV-cache kuantasyonu |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | KV-cache belleği yarıya iner → daha uzun bağlam |

## Güvenlik

- Değişiklik yapan araçlar (`write_file`, `run_command`, `remember`) **mod kapısına**
  tabidir: plan engeller, normal onay sorar, otonom serbest. Ek olarak
  `KUZGUN_PERMISSION_RULES` ile deterministik allow/deny/ask kuralları tanımlanabilir.
- Model, araçlara yalnız şemada tanımlı parametreleri geçebilir (gizli parametre reddi).
- `fetch_url` yalnız http/https'e izin verir, iç/özel ağ adreslerini engeller (SSRF +
  DNS-rebinding koruması). Web içeriği modele **"GÜVENİLMEZ"** olarak verilir.
- **Sunucuyu uzağa açarken `KUZGUN_TOKEN` ayarla** (yoksa RCE riski); TLS için ters vekil.
- Oturumlar-arası mesajlar **yetki taşımaz** (onay/komut/ayar yapamaz), yalnız veridir.
- Bilinen kalıcı borç: prompt-injection zinciri (web→model→araç); azaltım = onay kapısı
  + güvenilmez etiket. Ek sertleştirme ileride ayrı bir güvenlik fazında.

## Mimari

```
kuzgun / kuzgun-client ─► KUZGUN MOTORU ─► ajan döngüsü ─► yerel model (Ollama/vLLM)
                                         ├─► araçlar (dosya/komut/web/medya/…)
                                         ├─► izin kapısı + kurallar (permissions)
                                         ├─► hafıza (SQLite + embedding, RAG)
                                         ├─► oturum deposu (kilit/TTL) + arşiv
                                         └─► teacher (claude CLI) / yedek model zinciri
```

Bağımlılık yönü: `clients/server → bootstrap → engine → agent/routing → core`;
somut sınıfları yalnız `bootstrap` kurar. Parçalar: `bootstrap`, `config`,
`logging_setup`, `models`, `agent`, `tools/`, `permissions`, `router`, `memory`,
`embeddings`, `sessions`, `structured`, `orchestrator`, `workflows`, `verify`,
`mcp`, `inbox`, `doctor`, `notebook`, `analyze`, `vision`, `archive`, `teacher`,
`engine`, `server`, `client`, `repl`, `cli`, `bench`. Tasarım ve faz raporları
`docs/` altında (Faz A güvenlik, Faz B mimari, Faz C Claude özellikleri).

## Geliştirme

```powershell
.\.venv\Scripts\python.exe -m pytest   # tüm testler
.\.venv\Scripts\python.exe -m ruff check kuzgun tests
```

TDD ile geliştirildi; 359 test. Faz A (güvenlik/temel) + Faz B (mimari) + Faz C
(Claude özellikleri) tamam. İleride (opsiyonel): sunucuda vLLM + daha büyük model,
streaming çıktı, LoRA ince-ayar.
