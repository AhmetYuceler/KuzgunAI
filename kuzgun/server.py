from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from kuzgun.engine import KuzgunEngine


class ChatRequest(BaseModel):
    message: str
    mode: str = "normal"


def create_app(engine: KuzgunEngine | None = None) -> FastAPI:
    engine = engine if engine is not None else KuzgunEngine()
    app = FastAPI(title="Kuzgun Motoru")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/chat")
    def chat(req: ChatRequest) -> dict:
        return {"reply": engine.chat(req.message, mode=req.mode)}

    return app


def main() -> None:  # kuzgun-server giriş noktası
    import uvicorn

    from kuzgun.config import load_config

    cfg = load_config()
    uvicorn.run(create_app(), host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
