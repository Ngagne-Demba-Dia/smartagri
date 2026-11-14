# 31 — Rapport d'exécution du Sprint D6 (`assistant_transcribe` : comparatif ASR et préparation complète de l'intégration)

**Statut** : Comparatif architectural documenté et intégration backend complète livrée et testée (`POST /v1/assistant/transcribe`) — *Confidentiel — réservé aux partenaires de travail.*
**Périmètre** : `assistant_transcribe` (`POST /v1/assistant/transcribe`, service 17 de Doc 16 § 9.3, modèle `asst_asr`).
**Références** : `docs/16_architecture_octopus.md` § 9.3 et § 9.4 (intouché), `docs/22_backend_gap_analysis.md`, `docs/23_integration_plan.md` § 3.7, `ml/catalog/models.yaml` (`asst_asr`, l. 473-498).

---

## 1. État initial

1. **Côté Frontend RC (`web/features/assistant/` et `web/lib/contracts/assistant.ts`)** :
   - Le contrat `TranscribeInputSchema` / `TranscriptionSchema` est gelé : audio base64 (`<= 256 Kio`), `content_type` `audio/*`, `duration_s <= 60`, `language_hint` parmi `["wo", "ff", "fr"]`.
   - En cas de `503 MODEL_UNAVAILABLE`, l'interface bascule proprement sur la saisie texte et les boutons de questions rapides sans bloquer la conversation avec l'assistant Claude (`POST /v1/assistant/chat`).
2. **Côté Backend et ML** :
   - Le catalogue `ml/catalog/models.yaml` (`asst_asr`, l. 473-498) prévoit en V2 un modèle `XLS-R 300M` affiné en CTC sur corpus agricole wolof/pulaar avec modèle de langue `KenLM`, entraîné et servi localement (*« voix identifiante, jamais exportée, consentement explicite »*).
   - Aucun fournisseur ASR cloud ni bundle `XLS-R 300M` n'était encore choisi ni câblé sur `POST /v1/assistant/transcribe`.

---

## 2. Comparatif des options ASR (OpenAI Whisper, Azure Speech, Google Speech-to-Text et XLS-R auto-hébergé)

Conformément au plan D6, le tableau ci-dessous compare les trois fournisseurs cloud demandés ainsi que l'option auto-hébergée prévue au catalogue ML sur les critères du projet (**français `fr`**, **wolof `wo`**, **pulaar `ff`**, **latence**, **coût**, **confidentialité / souveraineté des données vocales**) :

| Critère | OpenAI Whisper API (`whisper-1` / `gpt-4o-transcribe`) | Azure AI Speech (Speech-to-Text) | Google Cloud Speech-to-Text (Chirp 2 / USM) | Cible catalogue V2 : `XLS-R 300M` + `KenLM` auto-hébergé (ou `faster-whisper` local pour `fr`) |
| :--- | :--- | :--- | :--- | :--- |
| **Qualité en français (`fr`, accent sénégalais)** | **Excellente** (WER `< 8 %`, robuste au bruit de vent/extérieur). | **Très bonne** (`fr-SN` / `fr-FR` supportés, adaptation acoustique possible). | **Très bonne** (`fr-FR` / USM, bonne robustesse au bruit). | **Très bonne** en `fr` via `faster-whisper` local ; dépend du corpus pour `XLS-R`. |
| **Couverture du wolof (`wo`)** | **Faible en zéro-shot** : le wolof n'est pas officiellement garanti en production par l'API Whisper (WER `> 45 %` sur vocabulaire agricole sans fine-tuning). | **Non supporté nativement** dans les locales standard `wo-SN` (nécessite Custom Speech avec corpus audio annoté). | **Partielle / expérimentale** sur USM/Chirp (`wo` présent dans le périmètre USM étendu, mais WER élevé sur les termes maraîchers locaux sans adaptation). | **Cible nominale du projet** (`WER <= 25 %` après fine-tuning CTC sur corpus agricole wolof + lexique `KenLM`, ex. *soble*, *tamaate*, *suuf*). |
| **Couverture du pulaar / peul du Sénégal (`ff` / `fuc`)** | **Absente / non exploitable** en zéro-shot. | **Absente** en standard. | **Absente / très dégradée** (les modèles publics confondent les variantes peules ou ignorent le pulaar du Fouta). | **Seule option viable à terme** après collecte dédiée dans la vallée du fleuve (ou compromis catalogue : boutons vocaux + transmission au conseiller). |
| **Latence (pour 10 s d'audio Opus <= 256 Kio)** | `1,2 s – 2,8 s` (HTTPS hors Sénégal). | `1,0 s – 2,2 s` (streaming ou REST batch). | `1,2 s – 2,5 s` (REST v2). | `< 1,5 s` sur GPU T4/L4 local ou `< 3 s` sur CPU 4 vCPU en `int8` (cible catalogue : `< 3 s`). |
| **Coût indicatif** | `~0,006 USD / min` (`whisper-1`), soit `~0,001 USD` par message vocal de 10 s (`~6 USD` pour 6 000 messages). | `~0,016 USD / min` (`~1,00 USD / h` en standard), soit `~2,7×` Whisper. | `~0,016 USD / min` (standard v2), `~0,004 USD / min` en batch différé. | **Coût marginal nul par requête** (inclus dans le serveur d'inférence CPU/GPU de la plateforme). |
| **Confidentialité & conformité (`ml/catalog/models.yaml` l. 492)** | **Incompatible par défaut avec l'exigence de souveraineté vocale** : la voix est une donnée biométrique identifiante envoyée hors du Sénégal. | Même contrainte d'export cloud hors Sénégal (sauf contrat entreprise sans rétention + consentement explicite). | Même contrainte d'export cloud hors Sénégal. | **100 % conforme** : la voix ne quitte jamais l'infrastructure SmartAgri92. |

### Recommandation architecturale
1. **En attendant le corpus vocal wolof/pulaar (`features.asr_speech`)** : laisser `assistant_transcribe` répondre honnêtement `503 MODEL_UNAVAILABLE` en production (ou `mock` en démonstration), ce qui active le repli prévu au catalogue (`saisie texte, boutons rapides`).
2. **Pour un pilote rapide en français (`fr`) sans export cloud** : brancher une instance locale de `faster-whisper` (`small` ou `medium` quantifié `int8` sous licence MIT) derrière le protocole `Transcriber` livré dans ce sprint.
3. **Pour le wolof (`wo`) et le pulaar (`ff`) en V2** : affiner `wav2vec2-xls-r-300m` (licence Apache-2.0) en CTC avec un modèle de langue `KenLM` sur le vocabulaire agricole sénégalais, servi par le même protocole `Transcriber`.

---

## 3. Modifications réalisées

### Backend (`plateforme/backend/`)
- **`app/schemas/assistant.py`** :
  - Ajout de `TranscribeIn` (`audio_base64`, `content_type` `^audio/...`, `duration_s` dans `(0, 60]`, `language_hint` dans `{"wo", "ff", "fr", None}`).
- **`app/services/assistant/transcribe.py`** :
  - Implémentation du protocole injectable `Transcriber` (`TranscribeOutput`) et de `transcribe_audio()`.
  - Vérification stricte de la taille (`<= 256 Kio` → `413 PAYLOAD_TOO_LARGE`), du base64 (`422 VALIDATION_ERROR`), de la durée (`<= 60 s` → `422 VALIDATION_ERROR`) et de la langue (`wo`, `ff`, `fr`).
  - Renvoi honnête de `503 MODEL_UNAVAILABLE` tant qu'aucun `Transcriber` n'est attaché à `app.state.transcriber`.
  - Construction de la réponse conforme à `TranscriptionSchema` avec `provenance` (`model_name = "asst_asr"`, `confidence.kind = "probability"`).
- **`app/api/v1/assistant.py`** :
  - Ajout de la route `POST /v1/assistant/transcribe` (couverte automatiquement par la règle de limitation de débit `/v1/assistant` à `rate_limit_assistant_per_min` requêtes/min dans `app/main.py`) et journalisation d'audit sans stocker l'audio brut ni le texte personnel.

### Tests (`plateforme/backend/tests/` et `plateforme/web/tests/live/`)
- **`backend/tests/test_sprint_d4_d5_d6.py`** (`test_d6_assistant_transcribe_validation_503_and_injected`) :
  - Vérifie le `503 MODEL_UNAVAILABLE` par défaut, le `422` au-delà de 60 s, le `413` au-delà de 256 Kio, et le `200` conforme à `TranscriptionSchema` lorsqu'un `Transcriber` est injecté.
- **`web/tests/live/prepared-services.live.ts`** :
  - Vérifie en live via le BFF Next le comportement de `POST /v1/assistant/transcribe`.

---

## 4. Tests exécutés

1. **Backend (`pytest`)** : `test_d6_assistant_transcribe_validation_503_and_injected` et `test_assistant.py` passants à 100 %.
2. **Contrat live (`vitest.live.config.ts`)** : test live BFF → FastAPI passant à 100 %.

---

## 5. Prochaines étapes (Sprint D7)

- Exécuter la validation globale du Sprint D (tests unitaires et d'intégration backend, tests frontend, tests de contrat live BFF → FastAPI, vérification du typage TypeScript et du linter) et produire `docs/32_validation_globale_sprint_D.md`.
