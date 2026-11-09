"""Catalogue data/IA de SmartAgri92 : sources → jeux de données → modèles, validé par code.

Source de vérité de la cartographie IA (docs 13 à 16) ; les annexes A1–A4 en sont générées.
Usage : `python -m agriml.catalog check | render | lineage <modèle>` (voir ml/catalog/README.md).
"""

from agriml.catalog.rules import (
    Issue,
    Lineage,
    ProgramRef,
    computed_personal,
    lineage,
    load_program_refs,
    validate,
)
from agriml.catalog.schema import Catalog, CatalogError, Dataset, Model, Source, load_catalog

__all__ = [
    "Catalog",
    "CatalogError",
    "Dataset",
    "Issue",
    "Lineage",
    "Model",
    "ProgramRef",
    "Source",
    "computed_personal",
    "lineage",
    "load_catalog",
    "load_program_refs",
    "validate",
]
