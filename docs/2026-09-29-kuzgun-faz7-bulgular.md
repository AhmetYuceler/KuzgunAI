# Kuzgun Faz 7: Zekâ + Değerlendirme + Gerçek Görev — Bulgular

**Tarih:** 2026-09-29
**Özet:** Kuzgun'a otomatik Claude'a-devretme + bir Kuzgun-vs-Claude benchmark
düzeneği eklendi; yerel 7B modelin gerçek yeteneği dürüstçe ölçüldü.

## Eklenenler
- **Otomatik devretme** (`agent.py` + `engine.py`): model döngüye girer, araçlar
  üst üste hata verir ya da `max_steps` aşılırsa Kuzgun kendiliğinden danışman
  Claude'a devreder ve gelen cevabı hafızaya yazar (öğrenir).
- **Benchmark harness** (`bench.py`): görev takımını hem yerel modele hem Claude'a
  sorar, **Claude'u hakem** yapıp (A/B yer değiştirmeli, konum yanlılığına karşı)
  karşılaştırır, kategori bazında kazanma oranı raporlar. `kuzgun-bench` komutu.
- **Sistem promptu iyileştirme**: rol + planla-yap + araç-sözleşmesi +
  "hata verince tekrarlama" + "çözemezsen uzmana danış/uydurma".
- **Hız hijyeni** (README): `OLLAMA_KEEP_ALIVE=-1`, Flash Attention, KV-cache q8.

## Benchmark sonucu (yerel Qwen2.5-7B vs Claude, hakem: Claude)
**Genel: Kuzgun 0 · Claude 2 · Berabere 4** (6 görev)

| Kategori | Kuzgun | Claude | Berabere |
|---|---|---|---|
| bilgi | 0 | 1 | 1 |
| akıl | 0 | 0 | 2 |
| kod | 0 | 0 | 1 |
| sohbet | 0 | 1 | 0 |

**Yorum:** 7B, basit **akıl yürütme ve kodda Claude'la başa baş** (berabere) — doğru
cevapları verdi (150 km; yaş 15; `liste[::-1]`). Claude, **nüans ve sohbette** önde
(daha temiz/sıcak; 7B "başka soru var mı?" gibi gereksiz ekler yapıyor). Hiçbir
akıl/kod görevinde 7B açıkça kaybetmedi.

## Gerçek görev deneyi (React/web)
- **7B tek başına:** "Tailwind'li bir açılış sayfası yaz (write_file kullan)" görevinde
  model **aracı gerçekten ÇAĞIRMADI** — "şimdi yazacağım" deyip bir kod bloğu yazmaya
  başladı, dosya oluşmadı. Bu, araştırmanın öngördüğü küçük-model hatası: eylemi
  *yapmak* yerine *anlatmak*. (Döngü/hata olmadığı için otomatik devretme tetiklenmedi.)
- **Devretme yolu (tasarımın çözümü):** Aynı görev Kuzgun'un öğretmen-Claude yoluyla
  üretildiğinde **geçerli, şık bir Tailwind sayfası** ortaya çıktı (cam efekti, gradient,
  animasyon). Yani "7B yapamıyorsa Claude'a devret" mimarisi tam da bunun için.

## Dürüst sonuç ve öneriler
- 7B; bilgi, basit akıl ve tek-parça kodda **gerçekten kullanışlı**; nüans ve
  **çok-adımlı ajanik kodlamada** (React kurma gibi) **güvenilmez** (araştırma + deney
  bunu doğruluyor).
- En yüksek kaldıraç: (a) **araç-çağırma güvenilirliği** — few-shot örneklerle prompt'u
  güçlendirmek ya da **Qwen2.5-Coder-7B**'ye geçmek; (b) **karmaşıklık ön-yönlendirmesi**
  — "uygulama kur/çok dosyalı" gibi işleri baştan Claude'a yönlendirmek; (c) donanım
  elverirse **daha büyük MoE model** (Qwen3-Coder-30B-A3B) 24GB+ üzerinde.
- Bu bulgular ileriki fazların (L2) yol haritası: coder-model, ön-yönlendirme,
  doğrulayıcı-yansıtma (build/test geri beslemesi), LoRA.
