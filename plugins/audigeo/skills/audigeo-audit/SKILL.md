---
name: audigeo-audit
description: Use when the user asks about an AudiGEO audit — launching one, reading the score, understanding recommendations, the 27 criteria, the 3 pillars (Technique 35%, Contenu 35%, Autorité 30%), action plans, or priority P0-P3. Explains how to interpret an audit and what to do with the recommendations.
---

# AudiGEO — Audit GEO

Un audit AudiGEO mesure la "lisibilité" d'un site par les IA génératives sur
**27 critères** répartis en 3 piliers pondérés :

- **Technique 35%** — `llms.txt`, Schema.org, FAQPage, `robots.txt` (autorisation
  des crawlers IA GPTBot/ClaudeBot/PerplexityBot…), rendu JS, performance
  (LCP/CLS/FCP), HTTPS, sitemap, structure de titres, mobile.
- **Contenu 35%** — densité de mots, cohérence thématique, infos pratiques,
  structure de titres, densité factuelle, citations.
- **Autorité 30%** — Google Business Profile, cohérence NAP, réseaux sociaux,
  mentions presse, Wikipedia/Wikidata, backlinks, annuaires sectoriels.

Chaque check produit un score 0-10, un statut (Pass ≥ 7 / Warn 4-6 / Fail < 4),
et une narrative LLM.

## Flow type d'un audit

1. **Lancer** : `audigeo_launch_audit(site_id)` (5-15 min, async).
2. **Suivre** : `audigeo_get_audit(audit_id)` jusqu'à `status="COMPLETED"`.
3. **Lire le score** : `score_global`, `score_technique`, `score_contenu`,
   `score_autorite`.
4. **Prioriser** : `audigeo_geo_action_plan(audit_id)` retourne les 5 actions
   à plus fort impact / moindre effort en P0/P1.
5. **Régénérer après fix** : `POST /audits/{id}/generate/{check_name}` (pas de
   tool dédié encore — passer par `audigeo_get_audit` après fix manuel).

## Interpréter les priorités

| Priorité | Quand l'attaquer | Effort/Impact typique |
|---|---|---|
| **P0** | Cette semaine | High impact, low/medium effort |
| **P1** | Ce mois | High impact, medium/high effort |
| **P2** | Ce trimestre | Medium impact |
| **P3** | Quand il y a du temps | Nice-to-have |

## Erreurs fréquentes à corriger en priorité

- `llms.txt` absent → P0 quasi-systématique
- Schema.org Organization manquant → P0
- robots.txt bloque GPTBot/Google-Extended → P0 (à débloquer)
- Densité de contenu < 300 mots sur les pages clés → P1
- Google Business Profile incomplet → P1
- Aucune mention presse / Wikipedia → P2-P3 (plus long terme)

## Quand utiliser le briefing exécutif

Si l'utilisateur veut présenter l'audit à un dirigeant non-tech, utilise le
prompt MCP `geo_audit_briefing(audit_id)` — il produit un format
"5 bullets + 1 action de la semaine" prêt à coller dans un email.
