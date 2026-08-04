from __future__ import annotations


class ChromaRetrievalProvider:
    """Optional persistent Chroma adapter loaded only when selected."""

    name = "chroma"

    def __init__(self, directory) -> None:
        self.directory = directory

    def search(self, query: str, filters: dict[str, str], top_k: int = 3) -> list[dict[str, object]]:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("Chroma Provider 未安装，请使用 RETRIEVAL_PROVIDER=local_keyword") from exc
        client = chromadb.PersistentClient(path=str(self.directory))
        collection = client.get_or_create_collection("buildwise-standards")
        result = collection.query(query_texts=[query], n_results=top_k, where={"hazard_type": filters["hazard_type"]} if filters.get("hazard_type") else None)
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [{"source": str(metadata.get("source", "")), "article": str(metadata.get("article", "")), "content": str(document), "score": float(1 - distance) if distance is not None else None, "metadata": metadata} for document, metadata, distance in zip(documents, metadatas, distances)]
