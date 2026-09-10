# Rayonne — plugin Claude Code

Pilote un ou tous les espaces de ton organisation
[Rayonne](https://rayonne.sponge-theory.dev) depuis Claude Code : audit
marketing de ta page produit, analyse produit, génération de contenus et de
vidéos, métriques AARRR.

## Installation

```
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install rayonne
```

Claude Code demande alors ta **clé API** (Rayonne → Réglages → Clés API,
format `rk_…`, plan Business).

## Commandes

- `/rayonne-audit` — audite le message de ta page produit et dit ce qui
  plafonne tes contenus.
- `/rayonne-brief` — ce que Rayonne a compris de ta page produit — et
  corrige-le.
- `/rayonne-content` — génère, relis et approuve un contenu Rayonne.
- `/rayonne-media` — inspecte les médias d'un contenu Rayonne et
  corrige-les.
- `/rayonne-plan` — la stratégie Bullseye de ton workspace — lis-la ou
  crées-en une.
- `/rayonne-publish` — publie un contenu approuvé — ou rends le kit à
  coller.
- `/rayonne-status` — état du workspace Rayonne — contenus, soumissions,
  métriques.
- `/rayonne-video` — lance une vidéo Rayonne et suis-la jusqu'au rendu.
- `/rayonne-workspaces` — les espaces de ton organisation Rayonne —
  liste-les, cible-en un, agis.

## Outils

82 outils, un par verbe de l'API publique — table complète groupée par
module (M1 brief, M2 stratégie, M3 contenu, M3 kit de vente et médias, M4
soumission et pièces jointes du kit, M5 analytics, M9 vidéo et storyboard,
avatars vidéo, galerie produit, audit, espaces de l'organisation,
workspace) dans [`mcp/README.md`](../README.md#outils).

Dix-huit outils sont arrivés en 0.6.0, pour sortir du navigateur le dépôt,
l'atelier vidéo et les pièces jointes d'un kit : la galerie produit devient
inscriptible (`rayonne_upload_product_asset`,
`rayonne_update_product_asset`, `rayonne_suggest_asset_caption`,
`rayonne_delete_product_asset`), l'atelier vidéo s'ouvre en entier (avatars
`rayonne_list_avatars`, `rayonne_generate_avatar`, `rayonne_update_avatar`,
`rayonne_cutout_avatar` ; relecture `rayonne_reopen_storyboard`,
`rayonne_assist_storyboard`, `rayonne_chat_storyboard`,
`rayonne_storyboard_thumbnail`, `rayonne_update_video`,
`rayonne_music_presets`), et un kit Mode C accepte des visuels déposés à la
main (`rayonne_upload_submission_asset`,
`rayonne_generate_submission_assets`, `rayonne_list_submission_assets`,
`rayonne_delete_submission_asset`).

Les deux outils de dépôt prennent un **chemin de fichier local** : le
serveur tourne sur ta machine et lit les octets lui-même — un chemin fautif
est refusé avant tout appel réseau. En revanche il n'y a **aucun outil de
dépôt d'avatar**, et aucune route publique derrière : enregistrer un visage
engage le consentement d'une personne réelle, qu'une clé API ne peut pas
donner à sa place. `rayonne_generate_avatar` compose un portrait de
synthèse ; une vraie photo se dépose dans l'interface, par un humain.

Quatre outils sont arrivés en 0.5.0, pour piloter TOUTE l'organisation
depuis une seule clé : `rayonne_list_workspaces`, `rayonne_create_workspace`,
`rayonne_delete_workspace`, `rayonne_update_workspace`. Les 59 outils
précédents gagnent au passage un `workspace_id` optionnel pour agir sur un
autre espace que celui d'origine — omis, rien ne change ; les 18 outils de
0.6.0 le portent aussi. **Rupture** : le
format rendu par `rayonne_workspace` s'enrichit (`autopilot_enabled` devient
`autopilot`, `locale`/`paused`/`autopublish_live`/`video_music`
apparaissent).

Huit outils sont arrivés en 0.4.0, pour piloter le kit de vente et les
médias d'un post sans quitter Claude : `rayonne_content_media`,
`rayonne_set_content_media`, `rayonne_recompute_content_media`,
`rayonne_brand_card`, `rayonne_regenerate_text`, `rayonne_preview_content`,
`rayonne_workspace`, `rayonne_set_ai_illustrations`.

Chaque outil d'écriture (générer, éditer, publier, planifier…) consomme du
quota du workspace ; la génération vidéo est en plus **facturée**. Coche
**Mode lecture seule** à l'installation pour les désactiver.

Version 0.7.0 : finalisation via `rayonne_onboard_workspace`, sans nouvelle
analyse ; patch du brief par fusion récursive, champs absents conservés.
