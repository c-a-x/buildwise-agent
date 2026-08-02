from __future__ import annotations


class ChromaRetrievalProvider:
    """Optional vector retrieval adapter placeholder."""

    name = "chroma"

    def search(self, query: str, filters: dict[str, str], top_k: int = 3) -> list[dict[str, object]]:
        raise RuntimeError("Chroma Provider 尚未安装，请使用 RETRIEVAL_PROVIDER=local_keyword")
