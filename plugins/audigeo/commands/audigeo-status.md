---
description: Affiche l'état du compte AudiGEO (org, plan, sites configurés, derniers audits).
---

Tu vas exécuter une vérification rapide de l'état du compte AudiGEO de l'utilisateur. Procède dans cet ordre :

1. Appelle `audigeo_list_sites` pour voir les sites configurés.
2. Pour chaque site (limite-toi aux 3 premiers si plus), appelle `audigeo_list_audits(site_id, limit=1)` pour récupérer le dernier audit.
3. Appelle `audigeo_get_monitoring_kpis(site_id)` sur le site principal pour les KPIs récents.
4. Appelle `audigeo_brand_safety_check(days=7)` pour le statut hallucinations.

Présente un résumé synthétique en français, format markdown :

- **Compte** : nombre de sites, plan détecté implicitement par les limites observées (Pro/Agency).
- **Sites** : liste avec URL + dernier score d'audit + date.
- **Monitoring** : mention rate / citation rate / Share of Voice sur le site principal.
- **Sécurité** : statut hallucinations (safe/elevated/high).

Termine par UN seul prochain pas recommandé.

Si une erreur d'authentification survient, indique à l'utilisateur de vérifier `AUDIGEO_API_KEY` et de générer une clé sur https://audigeo.ai → Settings → API Keys (plan Pro ou Agency requis).
