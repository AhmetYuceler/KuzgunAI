from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from kuzgun.config import Config, load_config
from kuzgun.engine import KuzgunEngine


class ChatRequest(BaseModel):
    message: str
    mode: str = "normal"


def create_app(engine: KuzgunEngine | None = None, config: Config | None = None) -> FastAPI:
    engine = engine if engine is not None else KuzgunEngine()
    cfg = config if config is not None else load_config()
    app = FastAPI(title="Kuzgun Motoru")

    # DNS-rebinding koruması: yalnızca izinli Host başlıklarına yanıt ver.
    allowed = [h.strip() for h in cfg.allowed_hosts.split(",") if h.strip()] or ["*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        # Token ayarlıysa bearer token zorunlu (uzak erişim için). Boşsa yalnız yerel.
        if cfg.token and authorization != f"Bearer {cfg.token}":
            raise HTTPException(status_code=401, detail="yetkisiz")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(req: ChatRequest, _: None = Depends(require_auth)) -> dict:
        return {"reply": engine.chat(req.message, mode=req.mode)}

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
