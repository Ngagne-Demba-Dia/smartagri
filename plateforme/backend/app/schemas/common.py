"""Bases communes des schémas d'entrée (pydantic v2).

Toute clé inconnue est refusée (422) : une faute de frappe côté client ne doit pas passer inaperçue.
Les mises à jour partielles (PATCH) ne transmettent que les clés fournies (`changes()`) et refusent
`null` sur une colonne obligatoire.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, model_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    def values(self) -> dict[str, Any]:
        """Valeurs à transmettre au service (toutes les clés, y compris les valeurs par défaut)."""
        return self.model_dump()


class PatchModel(InputModel):
    NON_NULLABLE: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _no_null_on_required(self) -> PatchModel:
        nulls = sorted(key for key in self.model_fields_set & self.NON_NULLABLE if getattr(self, key) is None)
        if nulls:
            raise ValueError(f"Valeur obligatoire, null interdit : {', '.join(nulls)}.")
        if not self.model_fields_set:
            raise ValueError("Aucune modification fournie.")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)
