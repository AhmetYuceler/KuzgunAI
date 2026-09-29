from __future__ import annotations

import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Metni sayısal bir vektöre (embedding) çeviren istemcinin sözleşmesi."""

    def embed(self, text: str) -> list[float]: ...


def cosine(a: list[float], b: list[float]) -> float:
    """İki vektör arasındaki kosinüs benzerliği (0..1). Boş/sıfır vektörde 0."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class FakeEmbedder:
    """Test için deterministik embedding: a-z harf frekansına dayalı 26 boyut."""

    def embed(self, text: str) -> list[float]:
        v = [0.0] * 26
        for ch in text.lower():
            if "a" <= ch <= "z":
                v[ord(ch) - 97] += 1.0
        return v


class OllamaEmbedder:
    """Ollama'nın embedding modeliyle (varsayılan nomic-embed-text) vektör üretir."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434/v1",
        timeout: float = 30,
    ):
        from openai import OpenAI

        # Kısa zaman aşımı: hafıza yalnız yardımcı bağlamdır; embedding takılırsa
        # (ekran görüntüsündeki Ctrl+C durumu) sohbet engellenmesin.
        self.client_timeout = timeout
        self._client = OpenAI(base_url=base_url, api_key="ollama", timeout=timeout, max_retries=1)
        self._model = model

    def embed(self, text: str) -> list[float]:
        resp = self._client.embeddings.create(model=self._model, input=text)
        return list(resp.data[0].embedding)
