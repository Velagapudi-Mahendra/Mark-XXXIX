import math
import re
from collections import Counter
from typing import List, Dict, Any, Tuple

class SimpleRetriever:
    """
    A simple TF-IDF based retriever for local memory search.
    """
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def add_documents(self, docs: List[Dict[str, Any]], text_field: str = "value"):
        """
        Docs should be a list of dicts with at least a text field.
        """
        self.documents = docs
        all_tokens = []
        doc_counts = Counter()
        
        for doc in docs:
            tokens = self._tokenize(doc.get(text_field, ""))
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_counts[token] += 1
            all_tokens.extend(tokens)

        num_docs = len(docs)
        self.vocab = {token: i for i, token in enumerate(set(all_tokens))}
        self.idf = {token: math.log(num_docs / (count + 1)) + 1 for token, count in doc_counts.items()}

    def _get_tf_idf_vector(self, text: str) -> Dict[int, float]:
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        vector = {}
        for token, count in tf.items():
            if token in self.vocab:
                vector[self.vocab[token]] = count * self.idf.get(token, 0)
        return vector

    def _cosine_similarity(self, v1: Dict[int, float], v2: Dict[int, float]) -> float:
        intersection = set(v1.keys()) & set(v2.keys())
        numerator = sum(v1[x] * v2[x] for x in intersection)

        sum1 = sum(v1[x]**2 for x in v1.keys())
        sum2 = sum(v2[x]**2 for x in v2.keys())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        return numerator / denominator

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if not self.documents:
            return []
            
        query_vec = self._get_tf_idf_vector(query)
        scores = []
        
        for i, doc in enumerate(self.documents):
            doc_text = f"{doc.get('category', '')} {doc.get('key', '')} {doc.get('value', '')}"
            doc_vec = self._get_tf_idf_vector(doc_text)
            score = self._cosine_similarity(query_vec, doc_vec)
            scores.append((score, doc))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scores[:top_k] if score > 0]

def get_relevant_memories(query: str, memory_data: dict, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Flattens the memory dict and retrieves top-k relevant items.
    """
    flattened = []
    for cat, items in memory_data.items():
        if not isinstance(items, dict): continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                flattened.append({
                    "category": cat,
                    "key": key,
                    "value": entry["value"]
                })
            elif isinstance(entry, str):
                flattened.append({
                    "category": cat,
                    "key": key,
                    "value": entry
                })
    
    retriever = SimpleRetriever()
    retriever.add_documents(flattened)
    return retriever.retrieve(query, top_k)
