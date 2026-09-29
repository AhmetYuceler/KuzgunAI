"""Betik workflow'ları (Faz C8).

`/ajanlar` orkestrasyonunun büyümüş hâli: bir workflow, Python'da `agent()`,
`parallel()`, `pipeline()` ilkelleriyle yazılır. Ara sonuçlar betik değişkenlerinde
kalır (ana konuşma bağlamını KİRLETMEZ); yalnız son değer döner. Her `agent()` izole
bir oturumda koşar. Betiği güçlü bir model (Claude/teacher) yazmalı — 7B doğru
orkestrasyon kodu üretmez.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from kuzgun.logging_setup import get_logger

log = get_logger("workflows")


class Workflow:
    def __init__(self, engine, mode: str = "normal", confirm=None, max_workers: int = 4):
        self.engine = engine
        self.mode = mode
        self.confirm = confirm
        self.max_workers = max_workers

    def agent(self, prompt: str, schema: bool = False):
        """Bir alt görevi İZOLE bir oturumda çalıştırır, sonucu döndürür. schema=True
        ise çıktı JSON'a zorlanır (yapılandırılmış alt-ajan; C1)."""
        sid = "wf-" + uuid.uuid4().hex[:8]
        try:
            if schema:
                from kuzgun.structured import complete_json

                # İzole oturumun sistem bağlamıyla birlikte JSON iste.
                msgs = [*self.engine.history(sid), {"role": "user", "content": prompt}]
                return complete_json(self.engine.client, msgs, retries=2)
            return self.engine.chat(prompt, mode=self.mode, confirm=self.confirm, session_id=sid)
        finally:
            self.engine._store.drop(sid)  # geçici oturum birikmesin

    def parallel(self, fns: list[Callable[[], object]]) -> list:
        """Bağımsız işleri eşzamanlı çalıştırır; sonuçları GİRDİ SIRASINDA döndürür."""
        if not fns:
            return []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(fns))) as ex:
            return list(ex.map(lambda f: f(), fns))

    def pipeline(self, items: list, stage_fn: Callable[[object], object]) -> list:
        """Bir aşamayı her öğeye sırayla uygular (çıktı yine liste)."""
        return [stage_fn(it) for it in items]


def run_workflow(engine, script: Callable[[Workflow], object], **kwargs):
    """Bir workflow betiğini çalıştırır ve YALNIZ son değerini döndürür (ara sonuçlar
    ana konuşmaya girmez). script(wf) -> son değer."""
    wf = Workflow(engine, **kwargs)
    log.info("workflow başladı")
    result = script(wf)
    log.info("workflow bitti")
    return result
