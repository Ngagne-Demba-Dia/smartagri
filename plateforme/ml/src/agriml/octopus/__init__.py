"""Intégration OctOpus ML (hub d'expérimentation) : client HTTP maison, exporteur filtrant, miroir du registre.

- `agriml.octopus.client`        : client httpx de l'API OctOpus (jamais le paquet PyPI « octopus-ml »,
                                   projet sans lien : risque de chaîne d'approvisionnement) ;
- `agriml.octopus.exporter`      : instantanés pseudonymisés + manifest.json (rien ne sort sans filtrage) ;
- `agriml.octopus.programs`      : programmes de run versionnés (indices, garde-fous, critères d'acceptation) ;
- `agriml.octopus.registry_sync` : miroir d'un run OctOpus dans MLflow (ou registre JSON local).

PostgreSQL + S3 restent le système de référence des données, MLflow celui des modèles (voir docs/09_octopus_ml.md).
Importer depuis les sous-modules (certains sont des CLI `python -m`).
"""
