"""AssistantService — Assistant Parcellaire v2 (prompt 93 + RAG + SoilNowcast + Irrigation)."""

from typing import Any, Dict


SYSTEM_PROMPT = (
    "Tu es l'assistant agricole SmartAgri. Tu utilises les données de "
    "SoilNowcast, Rain Intelligence, ET0 Forecast et la base de "
    "connaissances agricoles pour répondre aux questions des agriculteurs "
    "sénégalais. Réponds en français, avec des recommandations concrètes. "
    "Cite tes sources (modèle, confiance, données)."
)


class AssistantService:
    """Assemble le contexte local RAG + prédictions pour répondre en français."""

    def __init__(self, knowledge, soil=None, irrigation=None):
        self.knowledge = knowledge
        self.soil = soil
        self.irrigation = irrigation

    def ask(self, question: str, features: Dict[str, Any] = None, crop: str = "oignon") -> Dict[str, Any]:
        k_resp = self.knowledge.search(question, top_k=3)
        sources = [
            {"doc_source": r["doc_source"], "domain": r["domain"], "score": r["score"]}
            for r in k_resp.values.get("results", [])
        ]
        parts = []
        if self.soil is not None and features:
            sr = self.soil.predict(features)
            if not sr.abstained:
                parts.append(
                    f"SoilNowcast (confiance {sr.confidence:.2f}): "
                    f"J+1={sr.values['y_plus_1d']:.1f}%, J+2={sr.values['y_plus_2d']:.1f}%, J+3={sr.values['y_plus_3d']:.1f}%."
                )
        if self.irrigation is not None and features:
            rec = self.irrigation.recommend(features, crop=crop)
            parts.append(f"Irrigation ({crop}): {rec.decision.value} (dose {rec.dose_mm} mm).")
        if sources:
            top = k_resp.values["results"][0]
            parts.append(f"Connaissances ({top['doc_source']}, score={top['score']}): {top['text_preview'][:240]}")

        return {
            "system_prompt": SYSTEM_PROMPT,
            "question": question,
            "answer": " ".join(parts) if parts else "Données insuffisantes — consulter un conseiller agricole.",
            "sources": sources,
            "confidence": k_resp.confidence,
        }
