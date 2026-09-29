import os
import base64

from kuzgun.vision import build_user_content, grab_clipboard_image, image_to_data_url


def test_image_to_data_url_encodes_png(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"\x89PNG\r\n")
    url = image_to_data_url(str(p))
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == b"\x89PNG\r\n"


def test_image_to_data_url_jpeg_mime(tmp_path):
    p = tmp_path / "b.jpg"
    p.write_bytes(b"\xff\xd8")
    assert image_to_data_url(str(p)).startswith("data:image/jpeg;base64,")


def test_build_user_content_has_text_and_images(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"x")
    parts = build_user_content("bu ne?", [str(p)])
    assert parts[0] == {"type": "text", "text": "bu ne?"}
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


class _FakeImg:
    def save(self, path, fmt=None):
        with open(path, "wb") as f:
            f.write(b"png")


def test_grab_clipboard_image_saves_png(tmp_path):
    out = grab_clipboard_image(str(tmp_path), _grab=lambda: _FakeImg())
    assert out and out.endswith(".png")
    assert (tmp_path / out.split("\\")[-1].split("/")[-1]).read_bytes() == b"png"


def test_grab_clipboard_image_accepts_copied_file(tmp_path):
    f = tmp_path / "foto.jpg"
    f.write_bytes(b"x")
    out = grab_clipboard_image(str(tmp_path), _grab=lambda: [str(f)])
    assert out == str(f)


def test_grab_clipboard_image_none_when_empty(tmp_path):
    assert grab_clipboard_image(str(tmp_path), _grab=lambda: None) is None
    assert grab_clipboard_image(str(tmp_path), _grab=lambda: "metin") is None


def test_new_session_dir_is_unique_under_base(tmp_path):
    from kuzgun.vision import new_session_dir

    a = new_session_dir(str(tmp_path))
    b = new_session_dir(str(tmp_path))
    assert a != b and os.path.isdir(a) and os.path.isdir(b)
    assert os.path.dirname(a) == str(tmp_path)


def test_cleanup_session_dir_removes_files(tmp_path):
    from kuzgun.vision import cleanup_session_dir, new_session_dir

    d = new_session_dir(str(tmp_path))
    open(os.path.join(d, "x.png"), "wb").write(b"x")
    cleanup_session_dir(d)
    assert not os.path.exists(d)
    cleanup_session_dir(d)  # ikinci çağrı hata vermez


def test_sweep_stale_removes_only_old_dirs(tmp_path):
    import time

    from kuzgun.vision import sweep_stale

    old = tmp_path / "eski"
    new = tmp_path / "yeni"
    old.mkdir()
    new.mkdir()
    eski_zaman = time.time() - 3 * 86400
    os.utime(old, (eski_zaman, eski_zaman))
    sweep_stale(str(tmp_path), max_age=86400)
    assert not old.exists() and new.exists()
