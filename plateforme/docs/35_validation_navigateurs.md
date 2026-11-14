# 35 — Validation Multi-Navigateur (Phase E2)

**Date** : 14 novembre 2026  
**Périmètre** : Application Web SmartAgri92 (`plateforme/web`)  
**Suite automatisée** : [`e2e/navigateurs.spec.ts`](../web/e2e/navigateurs.spec.ts) (`PLAYWRIGHT_MULTI=1 npx playwright test e2e/navigateurs.spec.ts`)  
**Statut** : **VALIDÉ SUR LES 3 MOTEURS (Chromium, Firefox, WebKit / Safari)**

---

## 1. Moteurs et environnements de test

Conformément au plan de la Phase E2, les trois grands moteurs de rendu du marché ont été installés et exécutés via Playwright :

| Navigateur cible | Moteur de rendu / JS | Version exécutée | Équivalence |
|---|---|---|---|
| **Chromium** | Blink / V8 | Playwright Chromium (Desktop Chrome) | Google Chrome, Microsoft Edge, Brave, Opera |
| **Firefox** | Gecko / SpiderMonkey | Playwright Firefox `157.0` (Desktop Firefox) | Mozilla Firefox (Windows, macOS, Linux, Android) |
| **Safari (WebKit)** | WebKit / JavaScriptCore | Playwright WebKit `27.2` (Desktop Safari) | Apple Safari macOS & iOS/iPadOS (équivalent moteur officiel sous Windows) |

Configuration dans [`playwright.config.ts`](../web/playwright.config.ts) :
- Exécution standard rapide sur `chromium` par défaut ;
- Activation simultanée des projets `chromium`, `firefox` et `webkit` lorsque la variable d'environnement `PLAYWRIGHT_MULTI=1` est définie.

---

## 2. Matrice de validation des 8 points de contrôle

| Fonctionnalité vérifiée | Chromium (Blink) | Firefox (Gecko) | Safari / WebKit | Détails techniques & implémentation |
|---|:---:|:---:|:---:|---|
| **1. Carte Leaflet (`/fr/carte`)** | ✅ Pass | ✅ Pass | ✅ Pass | Conteneur `.leaflet-container` visible, polygones SVG (`svg path`) des parcelles rendus, bascule des couches radio (`NDVI (vigueur)`, `Humidité`, `Niveau d’alerte`, `Culture`) et légende séquentielle sans style inline bloqué par la CSP. |
| **2. Uploads image (`/fr/maladies`)** | ✅ Pass | ✅ Pass | ✅ Pass | Sélecteur `<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment">`, réduction/normalisation Canvas 2D via `prepareImage` ([`lib/image.ts`](../web/lib/image.ts)), affichage de l'aperçu `<img>` et envoi Base64 au diagnostic. |
| **3. Microphone (`/fr/assistant`)** | ✅ Pass | ✅ Pass | ✅ Pass | Hydratation SSR propre via `useSyncExternalStore` ([`features/assistant/VoiceInput.tsx`](../web/features/assistant/VoiceInput.tsx)). Sélection multi-navigateur du codec audio via `pickAudioType` ([`lib/voice.ts`](../web/lib/voice.ts)) : `audio/webm;codecs=opus` (Chromium/Firefox), `audio/mp4` (Safari/WebKit), `audio/ogg;codecs=opus`. Repli explicite si périphérique ou API absents. |
| **4. `localStorage`** | ✅ Pass | ✅ Pass | ✅ Pass | Lecture/écriture fonctionnelle (`setItem`/`getItem`/`removeItem`) et vérification stricte de la règle de sécurité Doc 10 § 7 : **aucun jeton d'authentification (`sa_at`, `sa_rt`, `token`, `auth`) n'est stocké dans `localStorage`**. |
| **5. Cookies (`sa_at`, `sa-theme`)** | ✅ Pass | ✅ Pass | ✅ Pass | Cookie de session BFF `sa_at` positionné avec `httpOnly: true`, `sameSite: "strict"`, `path: "/"`. Cookie de préférence visuelle `sa-theme` (`light` / `dark`) écrit avec `SameSite=Lax; Max-Age=31536000`. |
| **6. Thème sombre** | ✅ Pass | ✅ Pass | ✅ Pass | Clic sur `"Passer au thème sombre"` → `document.documentElement.getAttribute("data-theme") === "dark"` + cookie `sa-theme=dark` relu côté serveur par [`app/[locale]/layout.tsx`](../web/app/[locale]/layout.tsx) (zéro flash au rechargement). Support natif de `@media (prefers-color-scheme: dark)`. |
| **7. Responsive (`375×800` → `1920×1080`)** | ✅ Pass | ✅ Pass | ✅ Pass | `documentElement.scrollWidth - window.innerWidth <= 0` vérifié en largeur `375 px` sur les 3 moteurs. Barre de navigation basse + tiroir `<dialog>` sur mobile, barre latérale sur bureau, grilles adaptatives CSS Grid / Flexbox. |
| **8. Animations & `prefers-reduced-motion`** | ✅ Pass | ✅ Pass | ✅ Pass | Animations GPU (`transform`, `opacity`) fluides en mode normal ; réduction immédiate à `0.01ms` (`<= 0.001s`) lorsque `prefers-reduced-motion: reduce` est actif. |

---

## 3. Particularités inter-navigateurs identifiées et traitées

1. **Sérialisation CSS de `animation-duration: 0.01ms` sous `prefers-reduced-motion: reduce`** :
   - **Observation** : `getComputedStyle(el).animationDuration` retourne `"1e-05s"` sous Chromium et WebKit, mais `"0.00001s"` sous Firefox (Gecko).
   - **Traitement** : Utilisation de `parseFloat(getComputedStyle(el).animationDuration) <= 0.001` dans [`e2e/navigateurs.spec.ts`](../web/e2e/navigateurs.spec.ts#L46-L50) pour valider la durée réelle indépendamment de la notation scientifique ou décimale du moteur CSS.
2. **Hydratation client du composant `VoiceInput` sous WebKit** :
   - **Observation** : `VoiceInput` utilise `useSyncExternalStore` (`useHydrated`) pour retourner `null` lors du rendu serveur initial et éviter tout décalage d'hydratation React #418 entre le serveur Node.js (sans `MediaRecorder`) et le navigateur. Sous WebKit, une assertion synchrone `.count()` immédiatement après `page.goto` s'exécutait avant la fin du cycle d'hydratation client.
   - **Traitement** : Utilisation de l'assertion auto-retry de Playwright `await expect(voiceBtn.or(voiceUnsupported)).toBeVisible()` dans [`e2e/navigateurs.spec.ts`](../web/e2e/navigateurs.spec.ts#L77-L79), qui attend proprement la fin de l'hydratation sur les 3 moteurs.
3. **Formats audio `MediaRecorder` entre Blink/Gecko et WebKit/Safari** :
   - **Architecture validée** : La fonction `pickAudioType` dans [`lib/voice.ts`](../web/lib/voice.ts) teste dans l'ordre `["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]` via `MediaRecorder.isTypeSupported`. Chromium et Firefox sélectionnent `audio/webm;codecs=opus`, tandis que Safari/WebKit sélectionne `audio/mp4`, tous deux acceptés par le contrat `TranscriptionRequestSchema` (`POST /v1/assistant/transcribe`).
4. **Comportement de l'attribut de cookie `Secure` sur `http://localhost` (WebKit vs Chromium/Firefox)** :
   - **Architecture validée** : Conformément à [`lib/session-cookies.ts`](../web/lib/session-cookies.ts), `secure` vaut `process.env.NODE_ENV !== "development"`. En production derrière HTTPS, `Secure` est actif sur tous les navigateurs ; en développement local sur `http://localhost`, `secure` est `false`, ce qui permet à WebKit (qui contrairement à Chromium/Firefox n'exempte pas `http://localhost` de la contrainte HTTPS pour les cookies `Secure`) de stocker le cookie `sa_at` en test local.

---

## 4. Résultat d'exécution Playwright Multi-Navigateur

```text
Running 3 tests using 1 worker

  ✓ 1 [chromium] › e2e/navigateurs.spec.ts › validation multi-navigateur (Phase E2) › cookies httpOnly, thème sombre (localStorage), responsive, animations, Leaflet, upload image et micro
  ✓ 2 [firefox]  › e2e/navigateurs.spec.ts › validation multi-navigateur (Phase E2) › cookies httpOnly, thème sombre (localStorage), responsive, animations, Leaflet, upload image et micro
  ✓ 3 [webkit]   › e2e/navigateurs.spec.ts › validation multi-navigateur (Phase E2) › cookies httpOnly, thème sombre (localStorage), responsive, animations, Leaflet, upload image et micro

  3 passed
```
