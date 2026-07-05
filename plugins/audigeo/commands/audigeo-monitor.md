---
description: Présente l'état du monitoring IA pour un site (KPIs, concurrence, opportunités).
argument-hint: "[site_id]"
---

Tu vas produire un rapport monitoring synthétique. Argument optionnel : $ARGUMENTS (site_id, vide = site par défaut).

1. Si pas d'argument, `audigeo_list_sites` et prendre le premier (ou demander à l'utilisateur de préciser si plusieurs).
2. `audigeo_get_monitoring_kpis(site_id, days=30)` — KPIs + historique.
3. `audigeo_competitive_analysis(site_id, days=30)` — comparaison concurrents.
4. `audigeo_get_citations_gap(site_id)` — top 5 des prompts où on perd.
5. `audigeo_brand_safety_check(days=7)` — statut hallucinations.

Présente un rapport en français, format markdown avec sections :

- **KPIs** : tableau avec mention_rate, citation_rate, Share of Voice + delta vs il y a 30 jours.
- **Plateformes** : laquelle est la plus forte / la plus faible (en mention).
- **Concurrence** : top 3 concurrents + leur SoV vs le client.
- **Opportunités citations-gap** : top 5 des prompts où des concurrents sont cités et pas le client (= où concentrer le contenu).
- **Sécurité de marque** : `safe` / `elevated` / `high` + nombre d'hallucinations critiques.

Termine par UN focus concret pour cette semaine (action contenu ou monitoring).
