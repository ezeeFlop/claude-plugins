---
name: audigeo-overview
description: Use whenever the user mentions AudiGEO, GEO audits, AI-visibility monitoring, brand hallucinations, llms.txt, AI crawler tracking, or asks "what should I do about ChatGPT/Claude/Gemini answers about my brand". Activates the AudiGEO toolkit and outlines which tool to start with.
---

# AudiGEO — quand et comment intervenir

L'utilisateur travaille avec **AudiGEO.ai**, plateforme de Generative Engine
Optimization éditée par Sponge Theory. Si la question touche à : audits de
sites pour visibilité IA, monitoring sur ChatGPT/Claude/Gemini/Mistral/
Perplexity/Groq, détection d'hallucinations IA sur une marque, génération
de contenus optimisés GEO (articles, FAQ, llms.txt, Schema.org), Markdown
Mirrors, AI crawlers (GPTBot, ClaudeBot, PerplexityBot), ou comparaison
concurrence dans les réponses IA — utilise le MCP `audigeo`.

## Quel outil pour quelle question

| Question utilisateur | Outil à appeler en premier |
|---|---|
| "Quels sites j'ai dans AudiGEO ?" | `audigeo_list_sites` |
| "Donne-moi le dernier audit de X" | `audigeo_list_audits` puis `audigeo_get_audit(id)` |
| "Que dois-je corriger en priorité ?" | `audigeo_geo_action_plan(audit_id)` |
| "Comment est ma marque sur les IA ?" | `audigeo_get_monitoring_kpis()` |
| "Suis-je mentionné sur ChatGPT ?" | `audigeo_get_monitoring_results(platform="chatgpt")` |
| "Mes concurrents me dépassent où ?" | `audigeo_competitive_analysis()` puis `audigeo_get_citations_gap()` |
| "Y a-t-il des hallucinations ?" | `audigeo_brand_safety_check(days=7)` |
| "Génère-moi un llms.txt" | `audigeo_generate_content(content_type="llms_txt", ...)` |
| "Briefing exécutif d'un audit" | prompt MCP `geo_audit_briefing` |
| "Recap monitoring de la semaine" | prompt MCP `monitoring_weekly_recap` |

## Configuration

- L'utilisateur a une API key AudiGEO (env `AUDIGEO_API_KEY`).
- Plan requis : **Pro** ou **Agency**. Si le MCP refuse au démarrage, c'est
  que le plan est Free — propose l'upgrade sur https://audigeo.ai/pricing.
- En mode `AUDIGEO_READ_ONLY=true`, les outils d'écriture (`launch_audit`,
  `generate_content`, `run_monitoring_now`, etc.) sont désactivés. Adapte
  ta réponse si un outil refuse pour cette raison.

## Anti-patterns

- **Ne pas** appeler tous les outils en parallèle "au cas où" — ça consomme
  des appels API quota-limités. Pose UNE question, appelle UN outil, lis
  le résultat avant d'enchaîner.
- **Ne pas** inventer un `audit_id` ou `site_id` — toujours partir de
  `audigeo_list_sites` / `audigeo_list_audits` pour récupérer les vrais.
- **Ne pas** confondre le **monitoring** (mesure ce que disent les vraies
  IA publiques sur la marque du client) avec **l'inférence interne**
  d'AudiGEO (génération de contenu, audit). Les modèles sont différents,
  les tarifications aussi.
