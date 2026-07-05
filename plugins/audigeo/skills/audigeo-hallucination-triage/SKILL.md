---
name: audigeo-hallucination-triage
description: Use when an AI hallucination is detected on the user's brand — wrong address, wrong pricing, fake service, confusion with a competitor. Explains severity levels, correction workflow, and how to draft a customer-facing response.
---

# AudiGEO — Triage des hallucinations IA

AudiGEO compare automatiquement chaque affirmation factuelle émise par une
IA à propos de la marque avec le **Brand Profile vérifié**. Quand un écart
est détecté, un `HallucinationAlert` est créé.

## Sévérités

| Niveau | Exemples | Action attendue |
|---|---|---|
| **critical** | Mauvaise adresse postale, faux prix présenté comme actuel, dirigeant fictif | Correction sous 24h, possible communication publique |
| **high** | Service inexistant attribué, mauvais slogan, confusion avec concurrent | Correction sous 7j |
| **medium** | Date d'événement passée mais encore citée, ancien fait obsolète | Correction sous 30j |
| **low** | Détail mineur incorrect (couleur du logo, anecdote) | Optionnel |

## Catégories

- `incorrect` — fait faux contredit par le Brand Profile (le pire cas)
- `obsolete` — fait qui était vrai mais ne l'est plus
- `unverifiable` — claim qu'on ne peut ni confirmer ni infirmer (signaler
  prudemment)

## Flow de triage

1. **Aperçu** : `audigeo_brand_safety_check(days=7)` retourne un statut
   `safe` / `elevated` / `high` et la liste des critical récents.
2. **Détail** : `audigeo_list_hallucinations(severity="critical")` pour
   inspecter chaque alerte (claim, fact, plateforme, monitoring_result_id).
3. **Correction du site** : si la cause est un fait manquant ou mal
   structuré sur le site (Schema.org, page À propos), corriger là d'abord.
4. **Brand Profile** : `audigeo_update_brand_profile()` pour enrichir/
   préciser les `key_facts` qui ont permis la détection — ça aide les
   prochaines détections automatiques.
5. **Réponse client** : utilise le prompt MCP `hallucination_response_draft(
   hallucination_id)` pour générer un texte de support standard.

## Quand sortir de l'outil

Une hallucination ne se corrige pas DANS AudiGEO — AudiGEO la détecte. Les
corrections vont :

1. Sur le **site** (contenu, Schema.org, llms.txt) pour empêcher la
   réapparition.
2. Vers les **plateformes IA elles-mêmes** quand elles permettent un
   feedback (ex: bouton 👎 dans ChatGPT, signalement Perplexity).
3. Dans une **stratégie de relations presse / Wikipédia** si le sujet
   touche à l'identité de la marque (peu d'autres signaux dépassent ces
   deux sources auprès des LLM).

L'agent peut aider à prioriser, rédiger, planifier — pas à modifier
l'IA cible elle-même.
