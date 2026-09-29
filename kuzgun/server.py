from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from kuzgun.config import Config, load_config
from kuzgun.engine import KuzgunEngine
from kuzgun.inbox import Inbox


class ChatRequest(BaseModel):
    message: str
    mode: str = "normal"
    session: str = "default"


class InboxSend(BaseModel):
    to: str
    text: str
    sender: str = Field(default="anon", alias="from")

    model_config = {"populate_by_name": True}


class InboxPoll(BaseModel):
    session: str


def create_app(engine: KuzgunEngine | None = None, config: Config | None = None) -> FastAPI:
    engine = engine if engine is not None else KuzgunEngine()
    cfg = config if config is not None else load_config()
    app = FastAPI(title="Kuzgun Motoru")
    inbox = Inbox()  # C11: oturumlar-arası mesaj kutusu (yetki taşımaz, sadece veri)

    # DNS-rebinding koruması: yalnızca izinli Host başlıklarına yanıt ver.
    # Boşsa güvenli varsayılana dön (asla '*'a düşme).
    allowed = [h.strip() for h in cfg.allowed_hosts.split(",") if h.strip()]
    if not allowed:
        allowed = ["127.0.0.1", "localhost"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        # Token ayarlıysa bearer token zorunlu (uzak erişim için). Boşsa yalnız yerel.
        if cfg.token:
            expected = f"Bearer {cfg.token}"
            if not authorization or not secrets.compare_digest(authorization, expected):
                raise HTTPException(status_code=401, detail="yetkisiz")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(req: ChatRequest, _: None = Depends(require_auth)) -> dict:
        # GÜVENLİK: istemciden gelen mod yalnız plan/normal olabilir. 'otonom'
        # (onaysız mutasyon = uzaktan kod çalıştırma riski) HTTP üzerinden yasak;
        # gerçek mutasyon yerel etkileşimli CLI'da yapılır.
        safe_mode = req.mode if req.mode in ("plan", "normal") else "normal"
        return {
            "reply": engine.chat(req.message, mode=safe_mode, session_id=req.session)
        }

    @app.post("/inbox/send")
    def inbox_send(req: InboxSend, _: None = Depends(require_auth)) -> dict:
        # GÜVENLİK: gelen mesaj yalnız veridir; onay/mod/komut yetkisi taşımaz.
        accepted = inbox.send(req.to, req.sender, req.text)
        return {"accepted": accepted}

    @app.post("/inbox/poll")
    def inbox_poll(req: InboxPoll, _: None = Depends(require_auth)) -> dict:
        return {"messages": inbox.poll(req.session)}

    return app


def main() -> None:  # kuzgun-server giriş noktası
    import uvicorn

    cfg = load_config()
    if cfg.host not in ("127.0.0.1", "localhost") and not cfg.token:
        print(
            "UYARI: Sunucu yerel olmayan bir adrese açılıyor ama KUZGUN_TOKEN ayarlı "
            "değil! Uzak erişimde araç çalıştırma (RCE) riski için mutlaka token ayarla."
        )
    uvicorn.run(create_app(), host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
