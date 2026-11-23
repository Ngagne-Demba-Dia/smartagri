"""Lexique agricole Wolof ↔ Français et normalisation d'intentions pour SmartAgri."""

from typing import Dict, List, Tuple


WOLOF_CROP_MAP: Dict[str, str] = {
    "soble": "oignon",
    "tamaate": "tomate",
    "ceeb": "riz",
    "duggub": "mil",
    "gerte": "arachide",
    "mbaxal": "mais",
    "mboq": "mais",
    "niebe": "niebe",
    "ñebbe": "niebe",
    "bissap": "bissap",
    "mango": "mangue",
    "pomme": "pomme_de_terre",
    "pombiteer": "pomme_de_terre",
}

WOLOF_INTENT_KEYWORDS: List[Tuple[List[str], str]] = [
    (["ndox", "roose", "suuxat", "arros"], "irriguer"),
    (["taw", "mbënn", "asamaan"], "pluie"),
    (["suuf", "tooy", "wow"], "humidite sol"),
    (["feebar", "gàkk", "xob", "garab"], "maladie"),
    (["njëg", "jaay", "marse", "xaalis"], "prix marche"),
    (["ngóob", "meññeef", "bey"], "rendement"),
    (["mbey", "ji", "waxtu"], "calendrier"),
]


def interpret_wolof_text(text: str) -> Dict[str, str]:
    """Détecte la culture et traduit les mots-clés Wolof en requête compréhensible par l'orchestrateur."""
    tl = text.lower()
    detected_crop = "oignon"
    for wo_crop, fr_crop in WOLOF_CROP_MAP.items():
        if wo_crop in tl:
            detected_crop = fr_crop
            break

    matched_intents = []
    for kws, fr_kw in WOLOF_INTENT_KEYWORDS:
        if any(w in tl for w in kws):
            matched_intents.append(fr_kw)

    normalized_fr = " ".join(matched_intents) if matched_intents else text
    if detected_crop not in normalized_fr and matched_intents:
        normalized_fr = f"{normalized_fr} {detected_crop}"

    return {
        "original_wo": text,
        "normalized_fr": normalized_fr.strip(),
        "detected_crop": detected_crop,
    }
