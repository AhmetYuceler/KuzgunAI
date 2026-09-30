# Kuzgun Kendi Modeli — İlk Kilometre Taşı (politikasız) Tasarımı

Tarih: 2026-09-30
Durum: Onay bekliyor (spec incelemesi)

## Amaç ve kapsam

Kuzgun için **kendi modelimizi** üretmenin ilk kilometre taşı. Bu turda
**hiçbir politika/ret davranışı** eğitilmez; tek hedef **eğitim boru hattını
uçtan uca kanıtlamak**: Qwen2.5'i taban alıp küçük bir ince-ayar (LoRA) yapmak,
sonucu GGUF'a çevirip Ollama'ya `kuzgun` adıyla yüklemek ve Kuzgun CLI'da
çalıştırmak. Politika/izin-ret eğitimi **sonraki ayrı bir turda** aynı boru
hattına eklenecek.

### Kritik çerçeve (beklenti netliği)
Sıfırdan "Qwen2.5 seviyesinde" bir model eğitmek bu donanımda (ve genel olarak
kişisel donanımda) mümkün değildir; bu binlerce GPU / trilyonlarca token / aylar
gerektirir. Bu yüzden **Qwen2.5'i taban (base) alırız** ve üstüne ince-ayar
yaparız. "Kendi Kuzgun modelimiz" = **Qwen2.5 tabanı + bizim fine-tune'umuz +
kendi kimliği (`kuzgun`)**. Bu, kullanıcının istediği tam kontrolü verir; fark
yalnızca "sıfırdan" değil "üstüne" inşa etmektir.

## Kararlar (onaylı)

- **İlk hedef model:** Qwen2.5-**3B**-Instruct. 8GB VRAM'de rahat eğitilir;
  boru hattı düşük riskle kanıtlanır. Çalışınca **birebir aynı boru hattı 7B**'ye
  uygulanacak (sonraki tur).
- **Araç zinciri:** **Unsloth** (birincil). Takılırsa **LLaMA-Factory** yedek.
- **İnce-ayar yükü:** yalnız **kimlik/üslup** (politika yok). Model kendine
  "Kuzgun" desin, geliştiricisinin Ahmet Yüceler olduğunu bilsin, Türkçe üslubu
  korunsun. Genel yetenek (Qwen2.5 kalitesi) bozulmasın.

## Donanım / ortam (tespit edildi)

- GPU: **RTX 5060 Laptop, 8 GB VRAM** (Blackwell / sm_120 — çok yeni;
  bitsandbytes/PyTorch güncel/nightly sürüm gerekebilir).
- RAM: 31.7 GB. Boş disk (C:): ~57 GB (7B fp16 ~15GB + GGUF ~15GB → sıkı ama
  yeterli; 3B için rahat).
- WSL: yalnız `docker-desktop` dağıtımı var → **Ubuntu dağıtımı kurulacak**.
- Sistem Python 3.14 (ML için fazla yeni) → eğitim için **ayrı Python 3.11
  ortamı** (WSL içinde). Ana proje `.venv` (3.12) **DEĞİŞTİRİLMEZ**.
- Ollama 0.34.4 kurulu (Windows). GGUF modeli Windows Ollama'ya yüklenecek.

## Mimari — üç aşama

### Aşama 0 — Ortam + duman testi (fizibilite kapısı)
En büyük risk burada: Blackwell GPU'nun eğitim araç zinciriyle çalışıp
çalışmadığı. Erken görülür.
- WSL2 + Ubuntu kurulumu; NVIDIA CUDA (WSL passthrough) doğrulanır (`nvidia-smi`).
- Python 3.11 sanal ortamı; Unsloth + uyumlu PyTorch/CUDA + bitsandbytes kurulur.
- Qwen2.5-3B-Instruct indirilir; **10 adımlık** minik bir QLoRA koşusu yapılır.
- **Kabul ölçütü:** 10 adım OOM/çökme olmadan tamamlanır; loss sayısı üretilir.
- **Başarısızlık planı:** Unsloth Blackwell'de kurulmazsa/çökerse → LLaMA-Factory
  denenir; o da olmazsa toolchain sürümleri (PyTorch nightly/CUDA) ayarlanır ve
  bulgu kullanıcıya raporlanır (bu aşama, ilerlemeden önce yeşil olmalı).

### Aşama 1 — Kimlik ince-ayarı (asıl kilometre taşı)
- **Veri seti:** `training/dataset/kimlik.jsonl` — sohbet formatında ~50–150
  örnek. İçerik: "Adın ne? / Kimsin? / Seni kim yaptı?" gibi sorulara Kuzgun
  kimlikli yanıtlar + birkaç genel Türkçe üslup örneği. **Politika/ret YOK.**
  Aşırı-uyum (overfit) ve genel yetenek kaybını önlemek için küçük ve dengeli.
- **Eğitim:** QLoRA (4-bit), batch=1 + gradient accumulation, kısa seq_len,
  gradient checkpointing (8GB'ye sığsın). Birkaç epoch.
- **Kabul ölçütü:** eğitim hatasız biter, loss düşer, LoRA adapter dosyaları
  (`training/output/kuzgun-3b-lora/`) oluşur.

### Aşama 2 — Paketle + doğrula
- LoRA adapter taban modele **merge** edilir → fp16 model.
- llama.cpp `convert_hf_to_gguf.py` ile **GGUF**'a çevrilir; q4_k_m (ve/veya q8)
  nicemleme.
- `training/Modelfile` (`FROM ./kuzgun-3b.gguf` + kimlik SYSTEM'i opsiyonel) ile
  `ollama create kuzgun-3b`.
- **Kabul ölçütü:**
  - `ollama run kuzgun-3b "adın ne?"` → kendine "Kuzgun" der.
  - Genel sorularda (matematik, kısa sohbet) Qwen2.5-3B kalitesi korunur
    (bariz bozulma yok).
  - Kuzgun CLI'da `KUZGUN_MODEL=kuzgun-3b` ile uçtan uca çalışır.

## Dosya yapısı (yeni `training/` klasörü)

```
training/
  README.md              # WSL kurulum + çalıştırma adımları
  requirements.txt       # eğitim ortamı (WSL 3.11) — ana .venv'den AYRI
  dataset/
    kimlik.jsonl         # ~50-150 kimlik/üslup örneği (politika yok)
  train_lora.py          # Unsloth QLoRA eğitim betiği (parametrik: model, veri)
  merge_and_export.py    # LoRA merge + GGUF'a çevirme sarmalayıcı
  Modelfile              # ollama create için
  output/                # ağırlıklar/GGUF — .gitignore'da (repoya girmez)
```

- `.gitignore`'a: `training/output/`, `*.gguf`, `*.safetensors` (büyük ikili
  dosyalar repoya girmez).
- **Ana kod tabanına (kuzgun/ paketi) dokunulmaz.** Sadece `KUZGUN_MODEL` ortam
  değişkeniyle yeni model seçilir (kod zaten bunu destekliyor).

## Bileşenler (izole birimler)

- **Veri seti (`kimlik.jsonl`):** girdi = tek dosya; sözleşme = Unsloth'un
  beklediği sohbet şeması (`messages` / role-content). Bağımsız değiştirilebilir.
- **Eğitim betiği (`train_lora.py`):** girdi = model adı + veri yolu + hiper-
  parametreler; çıktı = LoRA adapter. Unsloth'a bağımlı.
- **Export (`merge_and_export.py` + `to_gguf`):** girdi = adapter + taban;
  çıktı = GGUF. llama.cpp'ye bağımlı.
- **Paketleme (`Modelfile` + ollama):** girdi = GGUF; çıktı = `kuzgun-3b` Ollama
  modeli. Ollama'ya bağımlı.

Her birim tek işe sahip, ayrı test edilir; biri değişince diğeri bozulmaz.

## Riskler

1. **Blackwell (sm_120) toolchain** — en yüksek risk; Aşama 0 kapısı bunu erken
   yakalar.
2. **8GB VRAM** — 3B için rahat; 7B'de (sonraki tur) sıkışık olacak.
3. **Disk** — 3B için sorun yok; 7B turunda yer izlenecek.
4. **Overfit / yetenek kaybı** — küçük, dengeli veri seti + az epoch ile azaltılır;
   Aşama 2 doğrulaması genel kaliteyi kontrol eder.

## Kapsam dışı (bu tur)

- Politika / izin-ret / güvenlik eğitimi (sonraki ayrı tur).
- Qwen2.5-7B (boru hattı kanıtlandıktan sonra).
- Veri seti büyütme, DPO/tercih eğitimi, guard modeli.
- Ana `kuzgun/` paketinde kod değişikliği.

## Başarı tanımı (bu turun sonu)

WSL'de Qwen2.5-3B üzerinde kimlik LoRA'sı eğitilmiş, GGUF'a çevrilmiş,
`ollama create kuzgun-3b` ile paketlenmiş ve Kuzgun CLI'da `KUZGUN_MODEL=kuzgun-3b`
ile çalışır durumda; model kendine "Kuzgun" diyor ve genel kalite korunuyor.
Böylece eğit→çevir→çalıştır döngüsü kanıtlanmış olur; sonraki tur yalnızca
veri setini (politika) ve model boyutunu (7B) değiştirmek olur.
