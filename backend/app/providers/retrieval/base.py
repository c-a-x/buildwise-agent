from __future__ import annotations

from typing import Protocol


class RetrievalProvider(Protocol):
    def search(self, query: str, filters: dict[str, str], top_k: int = 3) -> list[dict[str, object]]:
        ...
