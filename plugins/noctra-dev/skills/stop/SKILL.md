---
name: stop
description: Ce skill s’applique quand l’utilisateur demande explicitement d’arrêter une campagne Noctra en cours.
disable-model-invocation: true
argument-hint: "[identifiant de campagne]"
---

Lire [les règles de travail](../../references/workflow.md). Identifier la campagne demandée et son organisation, puis consulter `get_campaign`.

Appeler `stop_campaign` pour cette campagne lorsque la demande d’arrêt est explicite. Ne pas demander une nouvelle autorisation pour répéter la même demande idempotente après une réponse perdue. Ne pas arrêter d’autres campagnes par déduction.

Relire l’état et les événements. Distinguer **arrêt demandé** et **exécution effectivement terminée**. Préserver les constats partiels et rapporter le règlement des crédits tel que le serveur le fournit ; ne pas promettre un remboursement non observé.
