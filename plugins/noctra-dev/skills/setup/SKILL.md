---
name: setup
description: Ce skill s’applique quand l’utilisateur demande de connecter Noctra à Claude Code, vérifier sa connexion Noctra ou résoudre un refus de clé API.
disable-model-invocation: true
---

Vérifier la connexion Noctra avec les outils du serveur fourni par ce plugin.

1. Repérer les outils Noctra réellement disponibles. Appeler `get_account`, puis `list_organizations` et les projets utiles avec `list_projects`.
2. Si la connexion est absente ou refusée, orienter vers la configuration du plugin et la page **Clés API** de Noctra. Vérifier l’instance affichée, l’expiration, la révocation et les permissions. Ne pas demander de coller une clé dans la conversation ; ne pas lire le trousseau, les fichiers de configuration sensibles ou les variables contenant le secret.
3. Indiquer l’organisation et les projets accessibles, sans exposer de secret. Une réponse correcte de lecture ne qualifie pas une campagne ni un moteur.
4. Ne lancer aucune campagne pour tester la connexion.

Consulter [les règles de travail](../../references/workflow.md) avant toute action métier.
