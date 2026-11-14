# 36 — Audit et Validation Finale d'Accessibilité (Phase E3)

**Date** : 14 novembre 2026  
**Périmètre** : Application Web SmartAgri92 (`plateforme/web` — 24 écrans, thèmes clair et sombre, bureau et mobile)  
**Référentiel** : WCAG 2.1 niveau AA & Doc 10 (`10_interfaces_ux_accessibilite.md`)  
**Statut** : **VALIDÉ (100 % des contrôles automatisés et manuels conformes)**

---

## 1. Outillage et méthodologie de vérification

Trois niveaux complémentaires d'outillage ont été exécutés et intégrés à la suite de validation continue :

1. **Contrôle mathématique des contrastes (`npm run contrast` — [`scripts/contrast.mjs`](../web/scripts/contrast.mjs))** :
   - Analyse statique directe de [`app/globals.css`](../web/app/globals.css) sur les blocs `:root` (thème clair) et `:root[data-theme="dark"]` (thème sombre).
   - Calcul de luminance relative WCAG 2.1 sur **14 paires** de jetons premier plan / arrière-plan (seuil `4,5:1` pour le texte courant et secondaire, `3,0:1` pour l'anneau de focus).
2. **Audit structurel automatisé multi-écrans ([`e2e/accessibilite.spec.ts`](../web/e2e/accessibilite.spec.ts))** :
   - Parcours complet des **23 routes authentifiées** (`/fr/tableau`, `/fr/exploitations`, `/fr/parcelles`, `/fr/carte`, `/fr/meteo`, `/fr/irrigation`, `/fr/fertilisation`, `/fr/risques`, `/fr/recommandations`, `/fr/assistant`, `/fr/maladies`, `/fr/kit`, `/fr/alertes`, `/fr/rapports`, `/fr/equipements`, `/fr/cultures`, `/fr/campagnes`, `/fr/rendement`, `/fr/previsions`, `/fr/planning`, `/fr/pieges`, `/fr/vegetation`, `/fr/marches`) ainsi que `/fr/parcelles/fld-mboro-1` et `/fr/login`.
   - Vérification automatique sur chaque DOM rendu : présence de `<html lang="fr">`, absence d'image sans `alt`, nom accessible non vide sur tout `button`, `a[href]`, `[role=button]`, `[role=tab]`, étiquette explicite sur tout `input`, `select`, `textarea`, unicité de tous les attributs `id`, et hiérarchie stricte des titres `h1 → h2 → h3` sans saut de niveau.
3. **Tests interactifs clavier, tiroir `<dialog>`, formulaires, téléversement et assistant ([`e2e/accessibilite.spec.ts`](../web/e2e/accessibilite.spec.ts))** :
   - Simulation de 25 tabulations successives (`Tab`) avec vérification du style calculé (`outline` ou `box-shadow` non nul).
   - Ouverture et fermeture par `Escape` du tiroir `<dialog>` mobile (`375×800`).
   - Vérification des étiquettes et de la validation du formulaire de seuils d'humidité, de la liaison `aria-describedby` du téléversement photo Maladies, et du pilotage clavier de l'Assistant IA.

---

## 2. Résultats par axe d'audit

### 2.1 Navigation clavier complète

| Point de contrôle | Implémentation | Résultat |
|---|---|---|
| Lien d'évitement (*Skip link*) | Premier élément focusable de [`components/Navigation.tsx`](../web/components/Navigation.tsx) : `<a href="#contenu" className="sr-only focus:not-sr-only ...">Aller au contenu</a>` ciblant `<main id="contenu" tabIndex={-1}>`. | ✅ Conforme |
| Ordre de tabulation | Ordre séquentiel logique : lien d'évitement → barre latérale (bureau) ou barre d'en-tête (mobile) → sélecteur de thème → déconnexion → contrôles de l'écran actif. | ✅ Conforme |
| Onglets Détail Parcelle | Composant Radix UI `@radix-ui/react-tabs` dans [`features/fields/FieldDetailView.tsx`](../web/features/fields/FieldDetailView.tsx) supportant la navigation par flèches gauche/droite, `Home` et `End`. | ✅ Conforme |
| Sélecteur de couche Carte | Groupe `role="radiogroup"` dans [`features/map/ParcelsMap.tsx`](../web/features/map/ParcelsMap.tsx) avec boutons `role="radio"` et `aria-checked`, activables au clavier. | ✅ Conforme |
| Sélecteur de culture Marchés | Boutons de filtre dans [`features/markets/MarketPricesView.tsx`](../web/features/markets/MarketPricesView.tsx) munis de `aria-pressed={crop === c}`. | ✅ Conforme |
| Suggestions rapides Assistant | Boutons `<button type="button">` dans [`features/assistant/AssistantChat.tsx`](../web/features/assistant/AssistantChat.tsx) activables par `Enter` ou `Space`. | ✅ Conforme |

### 2.2 Focus visibles

- **Règle globale ([`app/globals.css`](../web/app/globals.css#L185-L188))** :
  ```css
  :focus-visible {
    outline: 3px solid var(--focus);
    outline-offset: 2px;
  }
  ```
- **Champs de saisie (`.field-input:focus`, [`app/globals.css`](../web/app/globals.css#L631-L634))** :
  ```css
  .field-input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px rgb(58 166 85 / 0.22);
  }
  ```
- **Vérification E2E** : Le test Playwright parcourt 25 éléments interactifs au clavier sur `/fr/tableau` et vérifie via `getComputedStyle(document.activeElement)` que `outlineStyle !== "none" && parseFloat(outlineWidth) > 0` ou `boxShadow !== "none"`. Aucun élément muet (`missing = []`).

### 2.3 Contrastes de couleurs (Thème clair et Thème sombre)

Exécution de `npm run contrast` sur les jetons prudents (`--bg` et `--card` pleins représentant le pire cas sous voile de verre) :

| Couple de jetons | Usage | Seuil WCAG AA | Ratio Thème Clair (`:root`) | Ratio Thème Sombre (`data-theme="dark"`) | Statut |
|---|---|---:|---:|---:|---|
| `ink` sur `bg` | Texte courant sur la page | `4,5:1` | **10,63 : 1** | **9,92 : 1** | ✅ OK |
| `ink` sur `card` | Texte courant sur carte | `4,5:1` | **14,50 : 1** | **13,44 : 1** | ✅ OK |
| `mute` sur `bg` | Texte secondaire sur la page | `4,5:1` | **5,54 : 1** | **5,46 : 1** | ✅ OK |
| `mute` sur `card` | Texte secondaire sur carte | `4,5:1` | **7,55 : 1** | **7,40 : 1** | ✅ OK |
| `g` sur `card` | Texte et lien vert sur carte | `4,5:1` | **7,35 : 1** | **7,71 : 1** | ✅ OK |
| `g` sur `bg` | Texte et lien vert sur la page | `4,5:1` | **5,39 : 1** | **5,69 : 1** | ✅ OK |
| `on-g` sur `g` | Texte de bouton principal | `4,5:1` | **8,39 : 1** | **9,27 : 1** | ✅ OK |
| `ok-ink` sur `ok-bg` | Étiquette « bon » | `4,5:1` | **6,94 : 1** | **7,21 : 1** | ✅ OK |
| `warn-ink` sur `warn-bg` | Étiquette « attention » | `4,5:1` | **6,82 : 1** | **6,99 : 1** | ✅ OK |
| `bad-ink` sur `bad-bg` | Étiquette « critique » | `4,5:1` | **5,56 : 1** | **5,76 : 1** | ✅ OK |
| `bad-ink` sur `card` | Message d'erreur sur carte | `4,5:1` | **5,76 : 1** | **6,69 : 1** | ✅ OK |
| `blue` sur `card` | Lien bleu sur carte | `4,5:1` | **6,21 : 1** | **7,12 : 1** | ✅ OK |
| `focus` sur `bg` | Anneau de focus sur la page | `3,0:1` | **4,55 : 1** | **5,25 : 1** | ✅ OK |
| `focus` sur `card` | Anneau de focus sur carte | `3,0:1` | **6,21 : 1** | **7,12 : 1** | ✅ OK |

### 2.4 Attributs ARIA et structure sémantique

- **Langue du document** : `<html lang={locale}>` (`lang="fr"`) défini dans [`app/[locale]/layout.tsx`](../web/app/[locale]/layout.tsx).
- **Régions landmarks** : `<aside>` (barre latérale bureau), `<header>` (barre mobile), `<nav aria-label="Navigation principale">`, `<main id="contenu">`.
- **États de chargement, d'erreur et de fraîcheur** :
  - [`components/LoadingBlock.tsx`](../web/components/LoadingBlock.tsx) : `role="status" aria-live="polite" aria-busy="true"`.
  - [`components/ErrorBlock.tsx`](../web/components/ErrorBlock.tsx) : `role="alert"` avec bouton `"Réessayer"` explicite.
  - [`components/OfflineBanner.tsx`](../web/components/OfflineBanner.tsx) et [`components/StaleBanner.tsx`](../web/components/StaleBanner.tsx) : `role="status" aria-live="polite"`.
- **Graphiques et jauges SVG** :
  - Tous les graphiques Recharts sont encapsulés dans un conteneur `role="img" aria-label={...}` décrivant la série affichée.
  - [`components/Gauges.tsx`](../web/components/Gauges.tsx) : `GaugeRing` et `StepMeter` exposent `role="img"` et un `aria-label` complet (`"{label} : {value}"`).
  - Les illustrations décoratives ([`components/Illustrations.tsx`](../web/components/Illustrations.tsx)) portent toutes `aria-hidden="true"`.

### 2.5 Formulaires

- **Authentification ([`features/auth/LoginForm.tsx`](../web/features/auth/LoginForm.tsx))** :
  - Champs `<input id="login-username" autoComplete="username" required>` et `<input id="login-password" type="password" autoComplete="current-password" required>` reliés à leurs `<label htmlFor>`.
  - Message d'erreur restitué dans `<p role="alert">`.
- **Création d'exploitation ([`features/farms/FarmsList.tsx`](../web/features/farms/FarmsList.tsx)) et de parcelle ([`features/fields/FieldsList.tsx`](../web/features/fields/FieldsList.tsx))** :
  - Chaque champ (`farm-name`, `farm-region`, `field-name`, `field-farm`, `field-crop`, `field-area`) possède un `<label htmlFor>` explicite et la classe `.field-input` garantissant une hauteur minimale de `44 px` (cible tactile conforme WCAG 2.5.5).
- **Seuils d'humidité ([`features/fields/FieldDetailView.tsx`](../web/features/fields/FieldDetailView.tsx))** :
  - Champs `"Démarrage (%)"` (`id="t-min"`) et `"Arrêt (%)"` (`id="t-max"`) reliés à leurs `<label>`, avec validation côté client (`min < max`) et message d'état annoncé via `role="status"`.
- **Calculateur de fertilisation ([`features/fertilization/FertilizationView.tsx`](../web/features/fertilization/FertilizationView.tsx))** :
  - Sélecteurs de parcelle et de culture + 3 champs numériques (`N`, `P`, `K` en `mg/kg`) étiquetés individuellement.

### 2.6 Téléversement d'image (Diagnostic Maladies)

Dans [`features/diagnosis/DiagnosisView.tsx`](../web/features/diagnosis/DiagnosisView.tsx) :
- Le sélecteur de fichier `<input id="plant-photo" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" aria-describedby="plant-photo-help" />` est relié à son `<label htmlFor="plant-photo">` (`"Photo de la plante"`) et au paragraphe d'aide `id="plant-photo-help"` (`"Formats acceptés : JPEG, PNG ou WebP (10 Mo maximum)..."`).
- Un encadré d'aide à la prise de vue (`"Conseil prise de vue : photographiez une feuille bien éclairée, de près et nette, sur fond simple."`) guide l'utilisateur avant l'envoi.
- L'aperçu après réduction Canvas (`prepareImage`, max `1024 px`) affiche une balise `<img>` dotée d'un attribut `alt="Aperçu de la photo qui sera envoyée"`.
- En cas de format non supporté ou de fichier dépassant `10 Mo`, un message explicite est affiché dans `<p role="alert">`.

### 2.7 Dialogues (Tiroir de navigation mobile)

Dans [`components/Navigation.tsx`](../web/components/Navigation.tsx) :
- Le menu complet sur mobile utilise l'élément HTML5 natif `<dialog ref={drawerRef} aria-label={t("openMenu")}>` ouvert via `drawerRef.current.showModal()`.
- Cela garantit nativement :
  - Le piégeage du focus (*focus trap*) à l'intérieur du tiroir tant qu'il est ouvert ;
  - La fermeture par la touche `Escape` (vérifiée automatiquement dans [`e2e/accessibilite.spec.ts`](../web/e2e/accessibilite.spec.ts#L86-L95)) ;
  - La fermeture par clic sur le bouton `"Fermer le menu"` (`aria-label="Fermer le menu"`) ou sur l'arrière-plan (`::backdrop`) ;
  - La fermeture automatique lors du changement de route (`useEffect` sur `pathname`).

### 2.8 Assistant IA et saisie vocale

Dans [`features/assistant/AssistantChat.tsx`](../web/features/assistant/AssistantChat.tsx) et [`components/VoiceInput.tsx`](../web/components/VoiceInput.tsx) :
- Le fil de conversation est balisé avec `role="log" aria-live="polite" aria-label="Conversation avec l’assistant"`, permettant aux lecteurs d'écran d'annoncer les nouvelles réponses sans interrompre la saisie.
- Lorsque la conversation est vide, **3 boutons de questions rapides** (`"Dois-je arroser demain ?"`, `"Quel est le risque de ravageurs sur mes parcelles ?"`, `"Comment interpréter les niveaux NPK de ma sonde ?"`) sont proposés et activables au clavier (`Tab` + `Enter`).
- Le champ `<textarea id="assistant-question" aria-describedby="assistant-counter" maxLength={2000}>` est relié au compteur de caractères (`"X / 2000 caractères"`).
- Le bouton de dictée vocale (`VoiceInput`) expose `aria-pressed={recording}`, un libellé dynamique (`"Dicter ma question"` / `"Arrêter la dictée"` / `"Transcription en cours…"`), et annonce toute indisponibilité ou erreur microphone dans un conteneur `role="status" aria-live="polite"`.

---

## 3. Respect de `prefers-reduced-motion`

Dans [`app/globals.css`](../web/app/globals.css#L190-L199) :
```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
Cette règle désactive instantanément toutes les animations décoratives (`.reveal`, `.stagger`, `.art-spin`, `.art-drift`, `.art-fall`, `.ai-orb`, `.live-dot`) lorsque l'utilisateur active la réduction des animations dans son système d'exploitation. Ce comportement est vérifié sur Chromium, Firefox et WebKit dans [`e2e/navigateurs.spec.ts`](../web/e2e/navigateurs.spec.ts#L44-L51).
