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


def run_remote_repl(base: str, cfg, input_fn=input, out=print) -> None:
    """HTTP ince istemci REPL'i. Komutlar (mod/yardım/çıkış) ORTAK repl.handle_slash
    ile işlenir (yerel CLI ile aynı komut tablosu — B8); mesajlar remote_chat ile
    uzak motora gider. Not: 'otonom' sunucuda plan/normal'e sıkıştırılır (güvenlik)."""
    import uuid

    from kuzgun.repl import handle_slash

    session = "istemci-" + uuid.uuid4().hex[:8]  # her istemci kendi konuşması
    state = {"mode": "normal", "quit": False}
    out(f"Kuzgun istemcisi -> {base}  (mod: {state['mode']}; /yardim, /cikis)")
    while True:
        try:
            user = input_fn(f"\n[{state['mode']}] sen> ").replace("﻿", "").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user.startswith("/"):
            out(handle_slash(user, state))
            if state.get("quit"):
                break
            continue
        out(
            "\nkuzgun> "
            + remote_chat(user, base_url=base, mode=state["mode"], token=cfg.token, session=session)
        )


def main() -> None:  # kuzgun-client giriş noktası: ince terminal istemcisi
    import sys

    from kuzgun.config import load_config

    cfg = load_config()
    base = sys.argv[1] if len(sys.argv) > 1 else cfg.engine_url
    run_remote_repl(base, cfg)


if __name__ == "__main__":
    main()
