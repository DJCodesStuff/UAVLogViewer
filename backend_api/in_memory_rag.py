# in_memory_rag.py

from rank_bm25 import BM25Okapi
import re

class BM25RAG:
    def __init__(self):
        self.documents = []
        self.tokenized_docs = []
        self.bm25 = None

    def _tokenize(self, text):
        # Simple whitespace + punctuation split
        return re.findall(r'\b\w+\b', text.lower())

    def add_documents(self, texts):
        self.documents.extend(texts)
        self.tokenized_docs = [self._tokenize(text) for text in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)

    def retrieve(self, query, top_k=3):
        if not self.bm25:
            return []
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.documents[i] for i in ranked_indices[:top_k]]
