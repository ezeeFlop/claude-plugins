---
name: audigeo-monitoring
description: Use when the user wants to understand or improve their brand visibility on AI platforms (ChatGPT, Claude, Gemini, Mistral, Perplexity, Groq). Covers KPIs (mention rate, citation rate, Share of Voice), competitive analysis, citations gap, and the daily monitoring cron.
---

# AudiGEO — Monitoring IA

AudiGEO interroge chaque jour à 06:00 UTC les 6 plateformes IA actives avec
les prompts configurés pour le site, mesure si la marque y est citée, à
quelle position dans une liste, avec quel sentiment, et avec ou sans
citation d'URL.

## KPIs de base

| KPI | Définition |
|---|---|
| **Mention rate** | % de réponses où la marque est mentionnée |
| **Citation rate** | % de réponses où l'IA renvoie vers l'URL du site |
| **Share of Voice** | Part des mentions de la marque vs concurrents |

## Plateformes monitorées (v0.3.43)

- ChatGPT (`gpt-4o-mini`) — modèle free-tier dominant
- Claude (`claude-haiku-4-5`) — free-tier de Claude.ai
- Gemini (`gemini-2.0-flash-lite`) — free-tier Google
- Mistral (`mistral-small-latest`) — free-tier Mistral Chat
- Perplexity (`sonar`) — tier par défaut
- Groq (`llama-3.1-8b-instant`) — modèle rapide

Stratégie MVP : on monitor avec le modèle que voit la majorité des
utilisateurs (free tier). À l'avenir, le plan Agency basculera sur les
modèles premium pour mesurer aussi le payant.

## Flow de diagnostic typique

1. **Vue d'ensemble** : `audigeo_get_monitoring_kpis(site_id, days=30)`.
2. **Plateforme spécifique faible** : `audigeo_get_monitoring_results(
   site_id, platform="X", brand_mentioned=False, limit=20)` pour voir les
   prompts ratés.
3. **Concurrence** : `audigeo_competitive_analysis(site_id, days=30)`.
4. **Quick wins** : `audigeo_get_citations_gap(site_id)` — prompts où les
   concurrents sont cités mais pas la marque (= où concentrer les efforts
   contenu).

## Recap hebdomadaire

Utilise le prompt MCP `monitoring_weekly_recap(site_id, days=7)` pour
produire un livrable client prêt à envoyer (highlight, comparatif s-1, top
3 opportunités, sécurité de marque).

## Quand déclencher un run manuel

`audigeo_run_monitoring_now(site_id)` ne remplace pas le run quotidien. À
utiliser uniquement :

- Juste après avoir publié un fix majeur (nouveau llms.txt, nouvelle FAQ,
  nouveau contenu) pour mesurer l'impact rapidement.
- Avant une revue de pilotage client à 14h alors que le run quotidien
  date de 06:00.

Sinon, attendre le run du lendemain matin — il consomme du quota d'appels
sur les API vendor (chaque plateforme a son rate limit).
