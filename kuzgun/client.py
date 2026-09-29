from __future__ import annotations

import json
import urllib.request


def _http_post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def remote_chat(
    message: str,
    base_url: str = "http://127.0.0.1:8000",
    mode: str = "normal",
    _post=None,
) -> str:
    """Uzak (veya yerel) Kuzgun motoruna HTTP ile mesaj gönderir, cevabı döndürür."""
    post = _post or _http_post
    url = base_url.rstrip("/") + "/chat"
    try:
        result = post(url, {"message": message, "mode": mode})
    except Exception as exc:
        return f"Error: {exc}"
    return result.get("reply", "")


def main() -> None:  # kuzgun-client giriş noktası: ince terminal istemcisi
    import sys

    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    print(f"Kuzgun istemcisi -> {base}  (/cikis ile çık)")
    while True:
        try:
            user = input("\nsen> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user in ("/cikis", "/exit"):
            break
        if not user:
            continue
        print("\nkuzgun>", remote_chat(user, base_url=base))


if __name__ == "__main__":
    main()
