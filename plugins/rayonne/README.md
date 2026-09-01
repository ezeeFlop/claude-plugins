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
  plafonne tout ce que Rayonne génère pour toi.
- `/rayonne-status` — état du workspace en quelques lignes.

## Outils

Lecture : `rayonne_overview`, `rayonne_list_content`,
`rayonne_list_submissions`, `rayonne_metrics_aarrr`, `rayonne_list_audits`.

Écriture : `rayonne_analyze_product`, `rayonne_marketing_audit`,
`rayonne_create_video`. Chacun consomme du quota ; la génération vidéo est
facturée. Coche **Mode lecture seule** à l'installation pour les désactiver.
