# Utilisation du kit Smart Agri92

Source : documentation interne du kit (firmware v1.1, non encore validé sur le terrain). Fiche à mettre à
jour à chaque version du firmware.

## Seuils d'irrigation automatique

Le kit démarre la pompe quand l'humidité du sol descend sous le seuil de démarrage et l'arrête quand elle
atteint le seuil d'arrêt. Règle des seuils : nombres entiers, démarrage au moins 0, arrêt au moins
démarrage + 5 et au plus 100. Exemple valable : démarrage 30 %, arrêt 60 %.

## Modifier les seuils à distance

Depuis l'application, un changement de seuils est envoyé au kit comme une commande. Le statut passe de
« en attente » à « envoyé » puis « appliqué » quand le kit confirme. Si le kit est hors ligne, la commande
attend sa reconnexion. Si les seuils sont changés directement sur le kit, ce sont eux qui font foi.

## Alertes du kit

Capteur de sol en défaut, défaut de pompe (pompe commandée sans débit ou bloquée), sol sec persistant malgré
l'irrigation, kit silencieux (plus aucune donnée depuis 24 heures) et suspicion de maladie sur les images.
Une alerte se résout automatiquement quand la cause disparaît, sauf la suspicion de maladie qui demande une
vérification humaine.

## Relais par téléphone

Sans réseau sur la parcelle, l'application mobile se connecte au kit, récupère les mesures, les horodate avec
l'heure du téléphone et les envoie à la plateforme dès que le téléphone retrouve une connexion.

## Entretien du kit

Nettoyer le panneau solaire chaque semaine pendant la saison sèche (poussière), vérifier que la sonde
d'humidité reste bien enfoncée dans la zone des racines, protéger les câbles des rongeurs et contrôler le
filtre de la pompe. Noter chaque intervention dans le journal de maintenance de l'équipement.
