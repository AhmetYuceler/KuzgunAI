from __future__ import annotations

import json
import urllib.request


def _build_request(url: str, payload: dict, token: str = "") -> urllib.request.Request:
    headers = {"Content-Type": "application/json"}
    if token:  # sunucuda KUZGUN_TOKEN ayarlıysa bearer token zorunlu
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(url, data=data, headers=headers)


def _http_post(url: str, payload: dict, token: str = "") -> dict:
    req = _build_request(url, payload, token)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def remote_chat(
    message: str,
    base_url: str = "http://127.0.0.1:8000",
    mode: str = "normal",
    _post=None,
    token: str = "",
    session: str = "default",
) -> str:
    """Uzak (veya yerel) Kuzgun motoruna HTTP ile mesaj gönderir, cevabı döndürür."""
    url = base_url.rstrip("/") + "/chat"
    payload = {"message": message, "mode": mode, "session": session}
    try:
        if _post is not None:
            result = _post(url, payload)
        else:
            result = _http_post(url, payload, token)
    except Exception as exc:
        return f"Error: {exc}"
    return result.get("reply", "")


def main() -> None:  # kuzgun-client giriş noktası: ince terminal istemcisi
    import sys
    import uuid

    from kuzgun.config import load_config

    cfg = load_config()
    base = sys.argv[1] if len(sys.argv) > 1 else cfg.engine_url
    session = "istemci-" + uuid.uuid4().hex[:8]  # her istemci kendi konuşması
    mode = "normal"
    # Not: HTTP üzerinden yalnız plan/normal geçerli; 'otonom' (onaysız mutasyon)
    # güvenlik nedeniyle sunucuda yasak, yerel `kuzgun` CLI'da yapılır.
    print(f"Kuzgun istemcisi -> {base}  (mod: {mode}; /mod <plan|normal>, /cikis)")
    while True:
        try:
            user = input(f"\n[{mode}] sen> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user in ("/cikis", "/exit"):
            break
        if not user:
            continue
        if user.startswith("/mod"):
            parts = user.split()
            if len(parts) > 1 and parts[1] in ("plan", "normal"):
                mode = parts[1]
                print(f"Mod değişti: {mode}")
            else:
                print("Kullanım: /mod <plan|normal>  (otonom yalnız yerel CLI'da)")
            continue
        print(
            "\nkuzgun>",
            remote_chat(user, base_url=base, mode=mode, token=cfg.token, session=session),
        )


if __name__ == "__main__":
    main()
