# Rayonne — plugin Claude Code

Pilote ton workspace [Rayonne](https://rayonne.sponge-theory.dev) depuis Claude Code :
audit marketing de ta page produit, analyse produit, génération de contenus
et de vidéos, métriques AARRR.

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

## Outils

59 outils, un par verbe de l'API publique — table complète groupée par
module (M1 brief, M2 stratégie, M3 contenu, M3 kit de vente et médias, M4
soumission, M5 analytics, M9 vidéo et storyboard, galerie produit, audit,
workspace) dans [`mcp/README.md`](../README.md#outils).

Huit outils sont arrivés en 0.4.0, pour piloter le kit de vente et les
médias d'un post sans quitter Claude : `rayonne_content_media`,
`rayonne_set_content_media`, `rayonne_recompute_content_media`,
`rayonne_brand_card`, `rayonne_regenerate_text`, `rayonne_preview_content`,
`rayonne_workspace`, `rayonne_set_ai_illustrations`.

Chaque outil d'écriture (générer, éditer, publier, planifier…) consomme du
quota du workspace ; la génération vidéo est en plus **facturée**. Coche
**Mode lecture seule** à l'installation pour les désactiver.
