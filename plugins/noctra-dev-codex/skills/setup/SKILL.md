---
name: setup
description: Ce skill s’applique quand l’utilisateur demande de connecter Noctra à Codex, configurer sa clé Noctra ou vérifier sa connexion.
disable-model-invocation: true
---

Lire [les règles de travail](../../references/workflow.md). Ce plugin est lié à l’origine HTTPS de son `instance.json` ; aucun paramètre ne la remplace. Ne pas lire de clé existante ni importer un credential Claude.

1. Pour une nouvelle configuration macOS demandée par l’utilisateur, proposer la saisie masquée : `node <racine-du-plugin>/scripts/configure.mjs --gui`. Ce dialogue est visible ; respecter les préférences utilisateur avant de l’ouvrir. En terminal personnel, `--terminal` propose une saisie sans écho. Ne jamais saisir ou demander la clé dans la conversation, les arguments, l’historique shell ou un fichier du dépôt.
2. Le script vérifie le compte en lecture seule et conserve la clé dans une entrée trousseau Noctra Codex dédiée à cette origine. Le helper natif autonome possède sa propre identité et n’accède à aucune autre application. Ne jamais appeler directement `keychain-helper` : sa réponse privée peut contenir la clé.
3. Vérifier avec `node <racine-du-plugin>/scripts/configure.mjs --check`. Ce diagnostic affiche uniquement le succès ou l’échec ; ne pas inspecter les variables ou le trousseau. Ouvrir ensuite un nouveau fil Codex pour charger les outils. Une app déjà ouverte ne reçoit pas de variable exportée dans un autre terminal.
4. Sur Linux/Windows, suivre le README : fournir la variable d’environnement spécifique à cette instance via le gestionnaire de secrets qui lance Codex. Le stockage trousseau macOS n’y est pas disponible. Ne pas prétendre que la clé est persistante sans ce gestionnaire.
5. Découvrir les outils réellement chargés. Appeler `get_account`, `list_organizations` puis `list_projects` selon les permissions. Ne lancer aucune campagne pour vérifier l’installation.

Pour consulter un dossier existant : `organization:read`, `project:read`, `campaign:read`, `report:read`. Ajouter `report:write` pour créer le rapport final s’il manque. Pour préparer et lancer un audit, ajouter les scopes des opérations demandées (`target:write`, `authorization:read` pour un compte ordinaire, `campaign:launch`, puis `campaign:stop` si l’arrêt est nécessaire). Les preuves restent masquées ; `evidence:read` ne s’ajoute qu’en cas de besoin explicite. Les droits du créateur et le périmètre des projets restent contrôlés par Noctra.

Après l’audit, utiliser le parcours `remediate` pour récupérer le Markdown via `export_remediation_bundle`, sur le rapport terminal figé. Respecter les limites d’un audit partiel et ne pas reconstruire le dossier depuis les constats vivants.
