---
description: Enregistre ta clé API AudiGEO pour le plugin (une seule fois, pour toutes les sessions).
argument-hint: "<agk_...>"
---

L'utilisateur te fournit sa clé API AudiGEO en argument : `$ARGUMENTS`.

Ton rôle : enregistrer cette clé dans le fichier de credentials que le serveur
MCP AudiGEO lit automatiquement, pour que tous les outils `audigeo_*`
fonctionnent — sans variable d'environnement ni édition de config.

1. Récupère la clé depuis `$ARGUMENTS` (ignore les espaces autour). Si elle est
   vide ou ne commence pas par `agk_`, arrête-toi et demande à l'utilisateur sa
   clé AudiGEO (format `agk_...`, générée sur https://audigeo.ai → Settings →
   API Keys, plan Pro ou Agency).
2. Écris **uniquement la clé** (sans saut de ligne superflu) dans
   `~/.config/audigeo/api_key` : crée le dossier `~/.config/audigeo` s'il
   n'existe pas, puis fixe les permissions du fichier à `600`.
   Par exemple : `mkdir -p ~/.config/audigeo && printf '%s' 'agk_...' > ~/.config/audigeo/api_key && chmod 600 ~/.config/audigeo/api_key`
3. Vérifie que le fichier contient bien la clé, puis confirme à l'utilisateur
   que c'est enregistré et que les outils AudiGEO sont **immédiatement
   utilisables (aucun redémarrage nécessaire)**. Propose un test rapide comme
   `/audigeo-status`.

IMPORTANT : ne réaffiche JAMAIS la clé en clair dans ta réponse — montre
seulement son préfixe tronqué (ex : `agk_C5DO…`). La clé est un secret.
