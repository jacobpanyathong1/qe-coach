"""TF-IDF retrieval over the pre-built book chunk corpus (rag/chunks.json)."""
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CHUNKS_PATH = Path(__file__).parent / "chunks.json"


class Retriever:
    def __init__(self):
        self.chunks = json.loads(CHUNKS_PATH.read_text())
        texts = [c["text"] for c in self.chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", max_df=0.9)
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, k: int = 5):
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix)[0]
        top_idx = sims.argsort()[::-1][:k]
        results = []
        for i in top_idx:
            if sims[i] <= 0:
                continue
            c = self.chunks[i]
            results.append({"book": c["book"], "page": c["page"], "text": c["text"], "score": float(sims[i])})
        return results
