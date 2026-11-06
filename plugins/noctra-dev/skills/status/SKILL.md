---
name: status
description: Ce skill s’applique quand l’utilisateur demande l’état d’une campagne Noctra, ses constats ou sa consommation mesurée.
argument-hint: "[identifiant de campagne]"
---

Lire [les règles de travail](../../references/workflow.md), puis consulter les campagnes autorisées avec `list_campaigns` et `get_campaign`.

Utiliser `get_campaign_events` avec le dernier numéro de séquence connu, `get_campaign_usage` pour la consommation et `get_findings` pour les constats. Respecter la pagination et le périmètre du projet. Lire `get_finding` pour approfondir un constat demandé.

Présenter les états terminés, en cours, partiels ou indisponibles tels qu’ils sont retournés. Conserver les dénominateurs et la provenance des métriques. Une mesure absente n’est pas zéro ; une campagne sans constat n’établit pas l’absence de vulnérabilité si la couverture est incomplète.

Ne pas lancer de campagne, modifier le triage ni révéler une preuve pour répondre à une demande d’état. Si un triage est explicitement demandé, relire la révision courante puis employer `update_finding` avec le motif et cette révision ; un conflit demande une relecture avant de réappliquer la décision.

Pour une campagne terminée, rappeler que le dossier de correction pour agent de code est accessible avec le parcours `remediate`, sur un rapport terminal figé. Une simple demande d’état ne crée pas ce rapport et ne modifie pas le code.
