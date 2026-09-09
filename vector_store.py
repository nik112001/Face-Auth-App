"""Vector storage for face embeddings, behind one interface with two backends.

- LocalStore: brute-force cosine over an in-memory dict, persisted to a
  git-ignored JSON file. Zero external services — this is the default so
  the app runs with no setup.
- OpenSearchStore: indexes vectors into an OpenSearch `knn_vector` field
  and does approximate nearest-neighbor search (HNSW) for identify().
  verify() is a single get-by-id + local dot product — a 1:1 check never
  needs an index, only 1:N search does.

Select via VECTOR_BACKEND=opensearch|local (default: local).
"""

import json
import os
import numpy as np

EMBEDDING_DIM = 512


def cosine_similarity(a, b):
    """Dot product of two L2-normalized vectors == their cosine similarity."""
    return float(np.dot(np.asarray(a), np.asarray(b)))


class LocalStore:
    def __init__(self, path="vectors_local.json"):
        self.path = path
        self._vectors = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                raw = json.load(f)
            return {user_id: np.array(vec) for user_id, vec in raw.items()}
        return {}

    def _persist(self):
        with open(self.path, "w") as f:
            json.dump({uid: vec.tolist() for uid, vec in self._vectors.items()}, f)

    def enroll(self, user_id, vector):
        self._vectors[user_id] = np.asarray(vector)
        self._persist()

    def identify(self, vector):
        if not self._vectors:
            return None, 0.0
        best_id, best_score = None, -1.0
        for user_id, enrolled in self._vectors.items():
            score = cosine_similarity(enrolled, vector)
            if score > best_score:
                best_id, best_score = user_id, score
        return best_id, best_score

    def verify(self, user_id, vector):
        enrolled = self._vectors.get(user_id)
        if enrolled is None:
            return 0.0
        return cosine_similarity(enrolled, vector)


class OpenSearchStore:
    INDEX = "faces"

    def __init__(self, url=None):
        from opensearchpy import OpenSearch

        url = url or os.environ.get("OPENSEARCH_URL", "http://localhost:9200")
        self.client = OpenSearch(hosts=[url])
        self._ensure_index()

    def _ensure_index(self):
        if self.client.indices.exists(index=self.INDEX):
            return
        self.client.indices.create(
            index=self.INDEX,
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "user_id": {"type": "keyword"},
                        "vector": {
                            "type": "knn_vector",
                            "dimension": EMBEDDING_DIM,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib",
                            },
                        },
                    }
                },
            },
        )

    def enroll(self, user_id, vector):
        self.client.index(
            index=self.INDEX,
            id=user_id,
            body={"user_id": user_id, "vector": list(vector)},
            refresh=True,
        )

    def identify(self, vector):
        resp = self.client.search(
            index=self.INDEX,
            body={"size": 1, "query": {"knn": {"vector": {"vector": list(vector), "k": 1}}}},
        )
        hits = resp["hits"]["hits"]
        if not hits:
            return None, 0.0
        top = hits[0]
        # OpenSearch's cosinesimil space reports score = 1 + cosine_similarity
        # (unlike l2/l1, which use 1 / (1 + distance)) -- subtract 1 to get
        # back a plain cosine value comparable to LocalStore's.
        return top["_source"]["user_id"], float(top["_score"]) - 1.0

    def verify(self, user_id, vector):
        doc = self.client.get(index=self.INDEX, id=user_id, ignore=[404])
        if not doc.get("found"):
            return 0.0
        enrolled = doc["_source"]["vector"]
        return cosine_similarity(enrolled, vector)


def get_store():
    backend = os.environ.get("VECTOR_BACKEND", "local")
    if backend == "opensearch":
        return OpenSearchStore()
    return LocalStore()
