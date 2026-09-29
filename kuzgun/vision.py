"""Görsel desteği: pano/dosya resmini alma ve modele (OpenAI-uyumlu) verme."""

from __future__ import annotations

import base64
import mimetypes
import os
import time

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def default_images_base() -> str:
    """Oturumluk resim klasörlerinin kökü: %TEMP%/kuzgun/images."""
    import tempfile

    return os.path.join(tempfile.gettempdir(), "kuzgun", "images")


def new_session_dir(base: str | None = None) -> str:
    """Bu oturuma özel benzersiz resim klasörü oluşturur (Claude Code'un
    Temp\\claude\\<oturum>\\images düzeni gibi). Çıkışta cleanup_session_dir ile silinir."""
    import tempfile

    base = base or default_images_base()
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-"), dir=base)


def cleanup_session_dir(path: str) -> None:
    """Oturum klasörünü içindekilerle siler; yoksa/silinemezse sessiz geçer."""
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def sweep_stale(base: str | None = None, max_age: float = 86400) -> None:
    """Çökme vb. yüzünden kalmış eski (max_age sn'den yaşlı) oturum klasörlerini siler."""
    base = base or default_images_base()
    if not os.path.isdir(base):
        return
    now = time.time()
    for name in os.listdir(base):
        p = os.path.join(base, name)
        try:
            if os.path.isdir(p) and now - os.path.getmtime(p) > max_age:
                cleanup_session_dir(p)
        except OSError:
            pass


def image_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def build_user_content(text: str, image_paths: list[str]) -> list[dict]:
    """Metin + resimleri OpenAI 'content parçaları' biçimine çevirir."""
    parts: list[dict] = [{"type": "text", "text": text}]
    for p in image_paths:
        parts.append({"type": "image_url", "image_url": {"url": image_to_data_url(p)}})
    return parts


def _pil_grab():
    from PIL import ImageGrab  # Pillow: pano görüntüsü (Windows/mac)

    return ImageGrab.grabclipboard()


def grab_clipboard_image(images_dir: str, _grab=None) -> str | None:
    """Panodaki resmi PNG olarak images_dir'e kaydeder ve yolunu döndürür.

    Panoda kopyalanmış bir resim DOSYASI varsa doğrudan onun yolunu verir.
    Resim yoksa None.
    """
    grab = _grab or _pil_grab
    try:
        data = grab()
    except Exception:  # noqa: BLE001 — Pillow yok / pano erişilemedi
        return None
    if data is None or isinstance(data, str):
        return None
    if isinstance(data, list):  # kopyalanmış dosya(lar)
        for p in data:
            if str(p).lower().endswith(IMAGE_EXTS) and os.path.exists(p):
                return str(p)
        return None
    os.makedirs(images_dir, exist_ok=True)
    path = os.path.join(images_dir, time.strftime("%Y%m%d-%H%M%S") + ".png")
    data.save(path, "PNG")
    return path
