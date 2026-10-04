---
description: La stratégie Bullseye de ton workspace — lis-la ou crées-en une.
---

Montre la stratégie marketing active, ou aide à en créer une — à partir
de la réalité du fondateur.

1. `rayonne_founder_context` : stade, segment (deviné du brief, à
   confirmer), heures par semaine, audience, budget payant. S'il manque le
   stade ou le segment, demande-les et enregistre-les avec
   `rayonne_update_workspace(founder_context=...)` AVANT de créer une
   stratégie : le scoring s'en sert comme a priori.
2. `rayonne_current_strategy`. S'il n'y en a pas, dis-le et propose
   `rayonne_create_strategy` (il faut un brief READY).
3. Présente le scoring Bullseye : les canaux du ring intérieur d'abord,
   avec la raison de leur score. Nomme les garde-fous appliqués
   (`scoring_jsonb.guardrails`, avec leur raison) et les canaux écartés.
4. Résume le plan 90 jours par vagues, pas action par action : ce que
   les premières semaines cherchent à prouver. Distingue ce que Rayonne
   publie (`channel_outlets` : `autopilot`), ce qu'il prépare en kit
   (`launch_kit`) et ce qui revient au fondateur (`founder_task`, dans
   « À faire »). Une action confiée à Rayonne se rédige tout de suite avec
   `rayonne_generate_plan_action`, sur tous les plans, dans le quota.
5. `rayonne_list_experiments` : trois expériences au plus, pré-enregistrées.
   À leur date de fin, présente le rapport (`evidence`) et la
   recommandation garder / couper / prolonger, et laisse le fondateur
   trancher (`rayonne_decide_experiment`).
6. Si une stratégie brouillon existe et convient, propose
   `rayonne_activate_strategy` — sans elle, rien n'est matérialisé.
