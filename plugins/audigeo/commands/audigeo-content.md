---
description: Génère un contenu GEO optimisé (article / FAQ / llms.txt / Schema.org / etc.) pour un site.
argument-hint: "<type> <brief>"
---

Tu vas générer un contenu GEO. L'utilisateur a passé : $ARGUMENTS.

Le format attendu est `<type> <brief en texte libre>` où `<type>` est l'un de :
- `article` — article long, markdown
- `faq` — FAQ avec balisage FAQPage Schema
- `llms_txt` — fichier llms.txt racine
- `llms_full_txt` — version exhaustive
- `robots_txt` — robots.txt avec User-agents IA
- `schema_org` — JSON-LD Organization / LocalBusiness / Product

Procédure :

1. Parse `$ARGUMENTS` : premier token = `<type>`, reste = `<brief>`.
2. Valide que le type est dans la liste autorisée. Sinon, demande à l'utilisateur de préciser.
3. Récupère le `site_id` : si l'utilisateur n'a pas précisé via `AUDIGEO_DEFAULT_SITE_ID`, appelle `audigeo_list_sites` et utilise le premier (ou demande).
4. Appelle `audigeo_generate_content(content_type=<type>, brief=<brief>, site_id=<site_id>)`.
5. La génération est async — tu reçois un `content_id` avec `generation_status="generating"`.
6. Poll `audigeo_get_content(content_id)` toutes les 15s jusqu'à `generation_status="generated"` (max 8 tentatives = 2 min).
7. Présente le contenu généré à l'utilisateur, formaté pour qu'il puisse le copier directement.

Si quota atteint (HTTP 402) : propose l'upgrade Agency. Si génération échoue (HTTP 500 / status `failed`) : montrer le `generation_error` et proposer de relancer.
