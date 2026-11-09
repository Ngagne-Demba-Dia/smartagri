# Broker MQTT local (Mosquitto)

Configuration du broker utilisé par `docker-compose.yml`. Aucun mot de passe n'est versionné :
le fichier `secrets/passwd` est généré localement et ignoré par git.

## Fichiers

| Fichier | Rôle |
|---|---|
| `mosquitto.conf` | Accès anonyme interdit, fichier de mots de passe, ACL, persistance, limites de taille |
| `acl` | Droits par compte : `ingestor` (lecture), `api` (commandes), `healthcheck`, et un motif par kit (`%u` = `device_id`) |
| `secrets/passwd` | Mots de passe hachés (PBKDF2-SHA512), **généré**, jamais commité |

## Générer le fichier de mots de passe

Prérequis : `.env` rempli (voir `.env.example`), Docker démarré.

```bash
make mqtt-passwd
```

La cible lance un conteneur Mosquitto jetable qui exécute `mosquitto_passwd` pour les comptes
`ingestor`, `api` et `healthcheck`, avec les mots de passe lus dans `.env`. Le résultat (haché) est écrit
dans `infra/mosquitto/secrets/passwd`.

Ajouter un kit de test (identifiant = `device_id`, mot de passe saisi au clavier, jamais en argument) :

```bash
docker run --rm -it -v "$PWD/infra/mosquitto/secrets:/work" eclipse-mosquitto:2.0.20 \
  mosquitto_passwd /work/passwd SA92-000123
docker compose restart mqtt
```

Remarques :

- `mosquitto_passwd -b` (utilisé par `make mqtt-passwd`) place le mot de passe dans la ligne de commande du
  conteneur jetable ; acceptable en local, pas en production.
- Mosquitto 2.0.x avertit si `passwd` est lisible par tous ; une version future le refusera. Sous Linux :
  `chmod 0700 secrets && chmod 0600 secrets/passwd` (propriétaire UID 1883 dans l'image).
- Après toute modification de `passwd` ou `acl` : `docker compose restart mqtt`.

## Production

- TLS 8883 uniquement (bloc commenté dans `mosquitto.conf`), certificats hors dépôt.
- Le fichier statique ne passe pas à l'échelle de milliers de kits : utiliser le plugin
  `dynamic-security` de Mosquitto ou un broker managé (AWS IoT Core, EMQX) avec authentification
  adossée à la table `devices` (secret du kit haché côté serveur, cf. CONVENTIONS.md §4).
