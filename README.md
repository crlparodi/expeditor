# expeditor
#### Script Python permettant de stocker automatiquement dans le cloud les ToDos crées ou mis à jour en local

- Script sous Python 3.7 tournant en background et ce dès le lancement d'XFCE
- Gérer les accès au cloud via un API ou client Linux
- Détecter en temps réel les modifications su un des ToDos (caractérisés par un .todo)
- Comparer les heures de dernière modification, si le document dropbox est plus récent que la dernière modification
    Renvoyer une notification d'alerte et enfin stopper le téléversement
- Dans les cas courants
    - Une version plus à jour est détecté sur le cloud, dans ce cas, le télécharger en local dans le chemin spécifié
    - Une version plus à jour est détecté en Local, dans ce cas, le téléverser sur le cloud
- En cas de perte du fichier en local, ne téléverser AUCUNE modification et proposer à l'utilisateur de faire une récup depuis le cloud
- Anticiper les versions de fichier corrompus et prévoir une récupération de sauvegarde depuis le cloud
- Prévoir une gestion de versions en local (plus d'infos à venir) au cas ou une modification involontaire est produite en local
    - Effectivement, si elle est téléversée automatiquement, la précédente version sera perdue...
- Créer les ToDos sur dropbox lorsqu'ils sont crées en local
- Travailler sur un ou plusieurs clouds pour assurer un backup optimal
- Possibilité d'utiliser ce script en usage bref pour réaliser des sauvegardes sur tous les supports externes locaux

