"""Données de démonstration : coopérative, administrateur, exploitation des Niayes, kit SA92-000001.

Usage (depuis plateforme/backend) : `python -m app.seed [--create-schema]`.
Idempotent : si l'organisation de démonstration existe déjà, rien n'est créé ni affiché.
Les secrets (mot de passe administrateur, clé du kit) sont affichés UNE seule fois : les noter aussitôt.
Interdit en production.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Campaign, CropCycle, Equipment, Farm, Field, Membership, Organization, User
from app.db.session import build_engine, build_session_factory, set_tenant_scope
from app.services import devices, farms

DEMO_ORG = "Coopérative démo des Niayes"
DEMO_ADMIN_EMAIL = "admin@demo.smartagri92.invalid"
DEMO_SERIAL = "SA92-000001"
# Parcelle d'environ 0,5 ha près de Mboro (zone des Niayes) ; anneau fermé, [longitude, latitude].
DEMO_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-16.8800, 15.1500], [-16.8793, 15.1500], [-16.8793, 15.1506], [-16.8800, 15.1506],
                     [-16.8800, 15.1500]]],
}
DEMO_FARM = {"name": "Exploitation démo de Mboro", "region": "Thiès", "commune": "Mboro",
             "latitude": 15.1503, "longitude": -16.8797, "area_ha": 2.0}
DEMO_FIELD = {"name": "Parcelle oignon 1", "area_ha": 0.5, "soil_type": "sableux", "irrigation_type": "drip",
              "geometry": DEMO_POLYGON}


@dataclass(frozen=True)
class SeedSecrets:
    admin_login: str
    admin_password: str
    device_serial: str
    device_key: str


def _org_and_admin(session: Session) -> tuple[Organization, User, str]:
    org = Organization(name=DEMO_ORG, kind="cooperative", region="Thiès")
    password = secrets.token_urlsafe(18)
    admin = User(email=DEMO_ADMIN_EMAIL, full_name="Administrateur démo", password_hash=hash_password(password),
                 locale="fr")
    session.add_all([org, admin])
    session.flush()
    # Sous un rôle soumis à la RLS (agri_app), les insertions suivantes doivent passer WITH CHECK.
    set_tenant_scope(session, [org.id])
    session.add(Membership(user_id=admin.id, organization_id=org.id, role="admin"))
    return org, admin, password


def _farm_and_cycle(session: Session, org: Organization) -> tuple[Farm, Field]:
    farm = farms.create_farm(session, org.id, dict(DEMO_FARM))
    field = farms.create_field(session, farm, dict(DEMO_FIELD))
    campaign = Campaign(organization_id=org.id, name="Saison sèche 2026-2027", season="dry",
                        start_date=date(2026, 10, 1), end_date=date(2027, 3, 31), status="active")
    session.add(campaign)
    session.flush()
    session.add(CropCycle(organization_id=org.id, field_id=field.id, campaign_id=campaign.id, crop="onion",
                          variety="Violet de Galmi", planted_on=date(2026, 10, 15),
                          expected_harvest_on=date(2027, 2, 15), status="active"))
    return farm, field


def seed(session: Session, settings: Settings) -> SeedSecrets | None:
    """Crée le jeu de démonstration ; renvoie None s'il existe déjà. L'appelant valide la transaction."""
    if session.scalars(select(Organization.id).where(Organization.name == DEMO_ORG)).first() is not None:
        return None
    org, _admin, password = _org_and_admin(session)
    farm, field = _farm_and_cycle(session, org)
    device, key = devices.register_device(session, settings, org.id, DEMO_SERIAL, "Kit démo", field.id)
    session.add(Equipment(organization_id=org.id, farm_id=farm.id, kind="pump", label="Pompe solaire de surface",
                          installed_at=date(2026, 10, 10), status="ok", device_id=device.id, flow_m3h=3.0))
    session.flush()
    return SeedSecrets(DEMO_ADMIN_EMAIL, password, DEMO_SERIAL, key)


def _print_secrets(created: SeedSecrets) -> None:
    print("Jeu de démonstration créé. Secrets affichés une seule fois :")
    print(f"  Administrateur : {created.admin_login}")
    print(f"  Mot de passe   : {created.admin_password}")
    print(f"  Kit            : {created.device_serial}")
    print(f"  Clé du kit     : {created.device_key}  (en-tête X-Device-Key)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crée les données de démonstration SmartAgri92.")
    parser.add_argument("--create-schema", action="store_true",
                        help="crée les tables via l'ORM (SQLite local ; sur PostgreSQL utiliser db/migrations)")
    args = parser.parse_args(argv)
    settings = get_settings()
    if settings.app_env == "prod":
        print("Refusé : pas de données de démonstration en production.", file=sys.stderr)
        return 2
    engine = build_engine(settings.database_url)
    if args.create_schema:
        Base.metadata.create_all(engine)
    with build_session_factory(engine)() as session:
        created = seed(session, settings)
        session.commit()
    if created is None:
        print(f"Organisation « {DEMO_ORG} » déjà présente : rien à faire.")
        return 0
    _print_secrets(created)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
