from sentence_transformers import CrossEncoder
from app.config import settings

class Reranker:
    def __init__(self):
        # Load local cross-encoder model
        self.model = CrossEncoder(settings.RERANKING_MODEL)

    def rerank(self, query: str, chunks: list, top_k: int = 5) -> list:
        """
        chunks: List of dicts, each having 'text' and other metadata.
        Returns: List of top_k chunks sorted by score.
        """
        if not chunks:
            return []
        
        # Create pairs: (query, chunk_text)
        pairs = [(query, chunk["text"]) for chunk in chunks]
        
        # Score the pairs
        scores = self.model.predict(pairs)
        
        # Add scores to chunks
        for i, score in enumerate(scores):
            chunks[i]["score"] = float(score)
            
        # Sort by score descending
        sorted_chunks = sorted(chunks, key=lambda x: x["score"], reverse=True)
        
        return sorted_chunks[:top_k]
