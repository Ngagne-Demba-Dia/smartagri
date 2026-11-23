"""KnowledgeService — recherche sémantique SmartAgri (multilingual-e5-large + FAISS / repli TF-IDF)."""

import csv
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from runtime.types import ConfidenceLevel, ServiceResponse, confidence_level


RAG_DIR = Path(__file__).resolve().parent
DEFAULT_CHUNKS_PATH = RAG_DIR / "chunks" / "smartagri_knowledge_chunks.csv"
DEFAULT_EMBEDDINGS_DIR = RAG_DIR / "embeddings"
E5_MODEL_NAME = "intfloat/multilingual-e5-large"


class KnowledgeService:
    """
    Moteur RAG local SmartAgri Knowledge.
    Corpus : 527 chunks, 10 domaines.
    Mode dense : intfloat/multilingual-e5-large + FAISS (IndexFlatIP) ou produit scalaire normalisé.
    Mode repli : TF-IDF + cosine (scikit-learn).
    """

    CORPUS_SIZE = 527
    RECALL_5 = 0.75
    MIN_SCORE_TFIDF = 0.08
    MIN_SCORE_DENSE = 0.65

    def __init__(
        self,
        chunks_path: Optional[Path] = None,
        embeddings_dir: Optional[Path] = None,
        mode: str = "auto",
    ):
        self.chunks_path = Path(chunks_path) if chunks_path else DEFAULT_CHUNKS_PATH
        self.embeddings_dir = Path(embeddings_dir) if embeddings_dir else DEFAULT_EMBEDDINGS_DIR
        self.mode = mode  # "auto", "dense", "tfidf"
        self.active_backend: str = "none"
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer = None
        self.matrix = None
        self.st_model = None
        self.faiss_index = None
        self.embeddings: Optional[np.ndarray] = None
        self.load_error: Optional[str] = None
        self.faiss_error: Optional[str] = None
        self._build_index()

    def _load_chunks(self) -> bool:
        chunks_dir = self.chunks_path.parent
        csv_files = sorted(chunks_dir.glob("*.csv")) if chunks_dir.exists() else []
        if not csv_files:
            self.load_error = f"Corpus manquant: {self.chunks_path}"
            return False
        self.chunks = []
        for cf in csv_files:
            with cf.open("r", encoding="utf-8", newline="") as fh:
                self.chunks.extend(list(csv.DictReader(fh)))
        if not self.chunks:
            self.load_error = "Corpus vide"
            return False
        return True

    def _build_dense_index(self) -> bool:
        emb_file = self.embeddings_dir / "e5_large_chunks.npy"
        if self.mode == "tfidf":
            return False
        if self.mode == "auto" and not emb_file.exists():
            return False
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            self.load_error = f"sentence-transformers indisponible: {exc}"
            return False

        self.st_model = SentenceTransformer(E5_MODEL_NAME)
        loaded_emb = np.load(str(emb_file)).astype(np.float32) if emb_file.exists() else None
        if loaded_emb is not None and len(loaded_emb) == len(self.chunks):
            self.embeddings = loaded_emb
        else:
            self.embeddings_dir.mkdir(parents=True, exist_ok=True)
            passages = [
                f"passage: {c.get('domain', '')} | {c.get('doc_source', '')} | {c.get('text_preview', '')}"
                for c in self.chunks
            ]
            self.embeddings = self.st_model.encode(
                passages, normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)
            try:
                np.save(str(emb_file), self.embeddings)
            except OSError:
                pass

        try:
            import faiss

            faiss_file = self.embeddings_dir / "e5_large.faiss"
            if faiss_file.exists():
                idx = faiss.read_index(str(faiss_file))
                if idx.ntotal == len(self.chunks) and idx.d == self.embeddings.shape[1]:
                    self.faiss_index = idx
                    self.active_backend = "e5_large+faiss"
                    return True
            dim = self.embeddings.shape[1]
            idx = faiss.IndexFlatIP(dim)
            idx.add(self.embeddings)
            self.faiss_index = idx
            try:
                faiss.write_index(idx, str(faiss_file))
            except OSError:
                pass
            self.active_backend = "e5_large+faiss"
        except Exception as exc:
            self.faiss_error = str(exc)
            self.faiss_index = None
            self.active_backend = "e5_large+numpy_ip"
        return True

    def _build_tfidf_index(self) -> bool:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError as exc:
            self.load_error = f"scikit-learn manquant: {exc}"
            return False
        texts = [
            f"{c.get('domain', '')} {c.get('doc_source', '')} {c.get('text_preview', '')}"
            for c in self.chunks
        ]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(texts)
        self.active_backend = "tfidf+cosine"
        return True

    def _build_index(self) -> None:
        if not self._load_chunks():
            return
        if self._build_dense_index():
            return
        if self.mode == "dense":
            return
        self._build_tfidf_index()

    @property
    def is_ready(self) -> bool:
        return self.active_backend != "none" and self.load_error is None

    def search(
        self, query: str, top_k: int = 5, domain: Optional[str] = None
    ) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse(
                service="knowledge",
                values={},
                confidence=0.0,
                confidence_level=ConfidenceLevel.UNRELIABLE,
                abstained=True,
                abstention_reason=self.load_error or "Index non chargé",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

        if self.active_backend.startswith("e5_large"):
            q_emb = self.st_model.encode(
                [f"query: {query}"], normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)
            if self.faiss_index is not None and not domain:
                scores_top, idx_top = self.faiss_index.search(q_emb, top_k)
                pairs = [(int(idx_top[0][i]), float(scores_top[0][i])) for i in range(len(idx_top[0]))]
            else:
                scores = (self.embeddings @ q_emb.T).ravel()
                if domain:
                    mask = np.array([c.get("domain", "") == domain for c in self.chunks])
                    scores = np.where(mask, scores, -1.0)
                top_idx = np.argsort(scores)[::-1][:top_k]
                pairs = [(int(i), float(scores[i])) for i in top_idx]
            min_score = self.MIN_SCORE_DENSE
        else:
            from sklearn.metrics.pairwise import cosine_similarity

            q_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self.matrix).ravel()
            if domain:
                mask = np.array([c.get("domain", "") == domain for c in self.chunks])
                scores = np.where(mask, scores, -1.0)
            top_idx = np.argsort(scores)[::-1][:top_k]
            pairs = [(int(i), float(scores[i])) for i in top_idx]
            min_score = self.MIN_SCORE_TFIDF

        results = []
        for idx, sc in pairs:
            if idx < 0 or sc <= 0.0:
                continue
            row = self.chunks[idx]
            results.append({
                "chunk_id": row.get("chunk_id", ""),
                "doc_source": row.get("doc_source", ""),
                "domain": row.get("domain", ""),
                "score": round(sc, 4),
                "text_preview": row.get("text_preview", ""),
            })

        if not results or results[0]["score"] < min_score:
            return ServiceResponse(
                service="knowledge",
                values={"results": results, "backend": self.active_backend},
                confidence=0.10,
                confidence_level=ConfidenceLevel.UNRELIABLE,
                abstained=True,
                abstention_reason="Aucun chunk pertinent au-dessus du seuil",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

        conf = round(min(0.95, 0.50 + results[0]["score"] * 0.5), 4)
        return ServiceResponse(
            service="knowledge",
            values={
                "results": results,
                "top_domain": results[0].get("domain", ""),
                "corpus_size": len(self.chunks),
                "backend": self.active_backend,
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )
