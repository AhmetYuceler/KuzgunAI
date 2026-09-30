# Faz D — Sunucuya taşıma (kılavuz)

Kullanıcı kararı: "önce PC'de olgunlaşsın." Bu yüzden Faz D opsiyoneldir ve
**kod gerektirmez** — altyapı (Faz B, `OpenAICompatBackend`) buna hazır bırakıldı.

## Önerilen: Option A — yalnız çıkarımı taşı

Motor (ajan döngüsü, araçlar, izin kapısı, hafıza) **PC'de kalır**; yalnız model
çıkarımı GPU'lu bir sunucudaki vLLM'e (ya da başka bir OpenAI-uyumlu API'ye) gider.
Tüm araçlar, onay, hafıza ve `/resume` PC'de çalışmaya devam eder.

### Adımlar
1. Sunucuda vLLM'i OpenAI-uyumlu modda başlat (örnek):
   ```bash
   vllm serve Qwen/Qwen2.5-7B-Instruct --host 0.0.0.0 --port 8000 --api-key GIZLI
   ```
2. PC'de yalnız iki ayarı değiştir:
   ```powershell
   $env:KUZGUN_OLLAMA_URL = "http://SUNUCU_IP:8000/v1"
   $env:KUZGUN_API_KEY    = "GIZLI"
   # (gerekirse) $env:KUZGUN_MODEL = "Qwen/Qwen2.5-7B-Instruct"
   kuzgun
   ```
3. Bitti. `kuzgun-doctor` ile bağlantıyı doğrula.

`OpenAICompatBackend` zaten `base_url`/`api_key`/`model` parametrelerini config'ten
alır; başka kod değişikliği yoktur. Ağı güvene almak için sunucuda TLS + firewall.

## Alternatif: Option B — motoru da taşı (daha büyük iş)

Motorun tamamı sunucuda çalışır; PC'de yalnız ince istemci (`kuzgun-client`) kalır.
Bu durumda araçlar sunucuda çalışır (PC dosyalarına erişmek istersen istemci-taraflı
araç köprüsü + akış üzerinden onay gerekir). Çok cihazdan erişim istenirse yapılır;
şimdilik gerek yok. Güvenlik: `KUZGUN_TOKEN` + `KUZGUN_ALLOWED_HOSTS` + TLS zorunlu
(bkz. README Güvenlik).

## Faz A+B+C'nin bu taşımaya kazandırdıkları
- **B3** tek arka uç soyutlaması (`OpenAICompatBackend`) → adres/anahtar değişimi yeter.
- **B2** `KUZGUN_HOME` + mutlak yollar → sunucuda veri tek kök altında.
- **A** oturum kilidi/izolasyonu + sunucu bearer-token/Host doğrulama → çok-oturum güvenli.
- **C4** yedek model zinciri → sunucu yoğunsa yerel/başka modele düşme.
