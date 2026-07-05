---
description: Lance un audit GEO sur un site et présente le résultat dès qu'il est prêt.
argument-hint: "<site_id ou URL>"
---

Tu vas lancer un audit GEO et restituer le résultat. L'utilisateur t'a passé un identifiant de site ou une URL en argument : $ARGUMENTS.

1. Si l'argument ressemble à une URL (commence par `http`), commence par `audigeo_list_sites` et trouve le site correspondant. Si aucun ne match, propose à l'utilisateur de créer le site d'abord (`audigeo_create_site` — demande confirmation avant).
2. Sinon, traite l'argument comme un `site_id` UUID.
3. Lance l'audit : `audigeo_launch_audit(site_id)`. Récupère l'`audit_id` retourné.
4. Indique à l'utilisateur que l'audit est en cours (durée typique 5-15 min).
5. **Poll** `audigeo_get_audit(audit_id)` toutes les 60s jusqu'à ce que `status` soit `COMPLETED` ou `FAILED` (max 20 tentatives = 20 min).
6. Une fois `COMPLETED` :
   - Présente les 4 scores (global, technique, contenu, autorité) en français.
   - Appelle `audigeo_geo_action_plan(audit_id, max_actions=3)` pour le top 3 des priorités.
   - Présente chaque priorité avec son `title`, `priority`, `impact`, `effort`.
   - Termine par UNE recommandation concrète à attaquer cette semaine.

Si le quota plan est atteint (HTTP 402), indique-le et propose l'upgrade Pro/Agency.
