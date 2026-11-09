"""Base de connaissances agronomique locale (fiches Markdown) et recherche BM25.

Chaque section `## ` d'une fiche de `knowledge/` est un passage indexé. La recherche est lexicale (BM25,
accents ignorés, mots vides retirés) : simple, déterministe, sans service externe. Les fiches doivent être
validées par l'ISRA, l'ANCAR et la DPV avant tout usage en production.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).with_name("knowledge")
BM25_K1 = 1.5
BM25_B = 0.75
DEFAULT_TOP_K = 3
MAX_PASSAGE_CHARS = 1200

STOPWORDS = frozenset(
    "a au aux avec ce ces dans de des du elle en est et il ils je la le les leur mais me mon ne nos notre "
    "nous on ou par pas plus pour qu que qui sa se ses son sont sur ta te tes ton tu un une vos votre vous "
    "y comment quel quelle quels quelles quoi faut faire peut dois doit est-ce".split()
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Passage:
    source: str
    title: str
    section: str
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class SearchHit:
    source: str
    title: str
    section: str
    excerpt: str
    score: float

    def as_dict(self) -> dict[str, object]:
        return {"citation": f"{self.title} — {self.section} ({self.source})", "source": self.source,
                "section": self.section, "excerpt": self.excerpt, "score": round(self.score, 3)}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(tok for tok in _TOKEN_RE.findall(normalize(text)) if tok not in STOPWORDS and len(tok) > 1)


def parse_markdown(source: str, content: str) -> list[Passage]:
    """Découpe une fiche en passages (un par section `## `)."""
    title_match = re.search(r"^# (.+)$", content, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source
    passages = []
    for chunk in re.split(r"^## ", content, flags=re.MULTILINE)[1:]:
        heading, _, body = chunk.partition("\n")
        body_text = " ".join(body.split())
        if body_text:
            passages.append(Passage(source, title, heading.strip(), body_text,
                                    tokenize(f"{heading} {heading} {body_text}")))
    return passages


class KnowledgeIndex:
    def __init__(self, passages: Sequence[Passage]) -> None:
        self._passages = tuple(passages)
        self._avg_len = sum(len(p.tokens) for p in passages) / max(1, len(passages))
        doc_freq: Counter[str] = Counter()
        for passage in passages:
            doc_freq.update(set(passage.tokens))
        total = len(passages)
        self._idf = {term: math.log(1 + (total - df + 0.5) / (df + 0.5)) for term, df in doc_freq.items()}

    def __len__(self) -> int:
        return len(self._passages)

    def _score(self, passage: Passage, query: Sequence[str]) -> float:
        counts = Counter(passage.tokens)
        norm = BM25_K1 * (1 - BM25_B + BM25_B * len(passage.tokens) / max(self._avg_len, 1e-9))
        score = 0.0
        for term in query:
            tf = counts.get(term, 0)
            if tf:
                score += self._idf.get(term, 0.0) * tf * (BM25_K1 + 1) / (tf + norm)
        return score

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
        terms = tokenize(query)
        if not terms:
            return []
        scored = [(self._score(p, terms), p) for p in self._passages]
        ranked = sorted((item for item in scored if item[0] > 0), key=lambda item: item[0], reverse=True)
        return [SearchHit(p.source, p.title, p.section, p.text[:MAX_PASSAGE_CHARS], score)
                for score, p in ranked[:top_k]]


def load_index(directory: Path = KNOWLEDGE_DIR) -> KnowledgeIndex:
    passages: list[Passage] = []
    for path in sorted(directory.glob("*.md")):
        passages.extend(parse_markdown(path.name, path.read_text(encoding="utf-8")))
    return KnowledgeIndex(passages)


@lru_cache(maxsize=1)
def default_index() -> KnowledgeIndex:
    return load_index()
