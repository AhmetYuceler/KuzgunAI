# 🦅 Kuzgun

Kişisel, büyük ölçüde yerel çalışan bir terminal yapay zekâ ajanı. Terminale
`kuzgun` yazınca açılır; düşünür, internette araştırır, bilgisayarında (izinle)
değişiklik yapar, ve konuştuklarınızı hatırlar. Takıldığında Claude'a danışıp
öğrenir. Gerektiğinde bir sunucuya taşınıp oradan hizmet verebilir.

## Ne işe yarar

- **Yerel beyin:** Ollama + Qwen2.5-7B (bilgisayarında, ~%100 GPU, hızlı, offline).
- **Araçlar:** dosya oku/yaz, komut çalıştır, dosya bul (glob), içerik ara (grep),
  internette ara (web_search), sayfa oku (fetch_url), uzmana danış (ask_expert).
- **Modlar:** `/mod plan` (sadece düşün) · `/mod normal` (sorarak yap) ·
  `/mod otonom` (sormadan yap).
- **Hafıza/RAG:** konuşmaları SQLite + embedding ile saklar, ilgili geçmişi hatırlar
  ("kendi kendine öğrenme").
- **Teacher:** `/claude <soru>` ile Claude'a danışır, cevabı hafızaya yazar.
- **Motor + İstemci:** çekirdek bir FastAPI servisidir; ince istemci HTTP ile bağlanır.
  Sunucuya taşımak = motoru orada çalıştırıp istemcinin adresini değiştirmek.

## Kurulum

Gereksinimler: Python 3.12, [Ollama](https://ollama.com/download).

```powershell
# Sanal ortam + bağımlılıklar
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Modeller (bir kez)
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
```

## Kullanım

**Yerel (zengin) mod — etkileşimli:**
```powershell
kuzgun
```
Örnekler: `sen> masaüstündeki dosyaları listele` · `sen> /mod plan` ·
`sen> /claude Rust'ta ownership nedir?` · `/yardim` · `/cikis`.

**Motor + ince istemci (taşınabilir):**
```powershell
# 1. terminalde motoru başlat
kuzgun-server
# 2. terminalde (veya başka makinede) istemci
kuzgun-client http://SUNUCU_ADRESI:8000
```

## Ayarlar (ortam değişkenleri)

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `KUZGUN_MODEL` | `qwen2.5:7b-instruct` | Yerel genel model |
| `KUZGUN_CODER_MODEL` | `qwen2.5-coder:7b-instruct` | Kod işlerine yönlenen model |
| `KUZGUN_AUTOROUTE` | `1` | Açıkça zor işleri (react/proje-kur…) baştan Claude'a yönlendir |
| `KUZGUN_REFLECT` | `1` | Yazılan kodu doğrula, sözdizimi hatalıysa modele düzelttir |
| `KUZGUN_EMBED_MODEL` | `nomic-embed-text` | Embedding modeli |
| `KUZGUN_OLLAMA_URL` | `http://localhost:11434/v1` | Ollama adresi |
| `KUZGUN_DB` | `data/memory.db` | Hafıza dosyası (taşınabilir) |
| `KUZGUN_ENGINE_URL` | `http://127.0.0.1:8000` | İstemcinin bağlanacağı motor |
| `KUZGUN_HOST` / `KUZGUN_PORT` | `127.0.0.1` / `8000` | Sunucu adresi |
| `KUZGUN_TOKEN` | *(boş)* | Uzak erişim için bearer token (aşağıya bak) |
| `KUZGUN_ALLOWED_HOSTS` | `127.0.0.1,localhost` | İzinli Host başlıkları |

## MCP araçları (isteğe bağlı)

Kuzgun, [MCP](https://modelcontextprotocol.io) sunucularına bağlanıp onların
araçlarını (GitHub, dosya sistemi, veritabanı…) kendi araç setine ekleyebilir.
`mcp_servers.example.json`'u `mcp_servers.json` olarak kopyala, düzenle; Kuzgun
başlarken oradaki sunucuların araçlarını otomatik yükler. Değişiklik yapan MCP
araçları **varsayılan olarak** mod/onay kapısına tabidir; yalnızca zararsız olanları
`read_only` listesine ekle. **Güvenlik:** `command` gerçek komut çalıştırır ve MCP
sonuçları (web gibi) dış/güvenilmez içeriktir — yalnızca **güvendiğin** sunucuları ekle.

## Hız ipuçları (Ollama)

Ollama'yı başlatmadan önce şu ortam değişkenleriyle belirgin hız kazanılır:

| Değişken | Öneri | Etki |
|---|---|---|
| `OLLAMA_KEEP_ALIVE` | `-1` | Model bellekte kalır; soğuk başlatma gecikmesi (ilk soruda ~1 dk) biter |
| `OLLAMA_FLASH_ATTENTION` | `1` | Flash Attention; KV-cache kuantasyonunu açar |
| `OLLAMA_KV_CACHE_TYPE` | `q8_0` | KV-cache belleği yarıya iner → daha uzun bağlam sığar |

Model Q4_K_M'de kalsın (7B için ~4.7 GB tatlı nokta). Zor kodlama/akıl işleri
zaten otomatik olarak Claude'a devredilir.

## Güvenlik

- Değişiklik yapan araçlar (`write_file`, `run_command`) **mod kapısına** tabidir:
  plan engeller, normal onay sorar, otonom serbest.
- `fetch_url` yalnızca http/https'e izin verir ve iç/özel ağ adreslerini engeller (SSRF).
- Web'den gelen içerik modele **"GÜVENİLMEZ"** olarak verilir.
- **Sunucuyu uzağa açarken (`KUZGUN_HOST` yerel değilse) mutlaka `KUZGUN_TOKEN`
  ayarla.** Token olmadan uzak erişim = araç çalıştırma (RCE) riski. Ayrıca TLS için
  bir ters vekil (nginx vb.) önerilir.
- Bilinen kalıcı borç: prompt-injection zinciri (web→model→araç) ajanların
  doğasındadır; azaltım = onay kapısı + güvenilmez etiket. Ek sertleştirme ilerideki
  bir güvenlik fazına planlıdır.

## Mimari

```
kuzgun (istemci) ──HTTP──► KUZGUN MOTORU ──► ajan döngüsü ──► yerel model (Ollama)
                                          ├─► araçlar (dosya/komut/web/uzman)
                                          ├─► hafıza (SQLite + embedding, RAG)
                                          └─► teacher (claude CLI)
```

Parçalar: `models`, `agent`, `tools/`, `permissions`, `memory`, `embeddings`,
`teacher`, `engine`, `server`, `client`, `config`, `cli`. Tasarım ve faz planları
`docs/` altında.

## Geliştirme

```powershell
.\.venv\Scripts\python.exe -m pytest   # tüm testler
```

TDD ile geliştirildi; 97+ test. İleride (L2): LoRA ince-ayar, alt-ajanlar,
sunucuda vLLM + daha büyük model.
