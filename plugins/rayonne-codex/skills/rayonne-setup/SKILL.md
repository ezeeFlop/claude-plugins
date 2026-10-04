---
name: rayonne-setup
description: Configure ou vérifie le plugin Rayonne pour Codex, avec clé API dans le trousseau macOS et saisie masquée.
---

# Configurer Rayonne

Depuis la racine installée de ce plugin, lance :

```sh
uv run --locked scripts/configure.py --gui
```

Le formulaire demande l'URL HTTPS de Rayonne, propose la clé existante du
trousseau si elle correspond à cette instance, sinon demande une clé `rk_…`
dans un champ masqué. Il vérifie l'espace en lecture avant d'enregistrer.
Il propose aussi le mode lecture seule. Une clé se crée dans Rayonne →
Réglages → Clés API (plan Business).

Ne demande jamais la clé dans la conversation, ne lis pas les secrets,
n'affiche pas les variables d'environnement et ne lance pas les helpers
Keychain isolément. Le script seul manipule le credential. Une clé Claude est importée une fois dans une entrée dédiée Codex ;
la configuration et la clé Claude restent intactes.

Pour migrer une configuration existante, lance
`uv run --locked scripts/configure.py --migrate` depuis la copie installée.
L’URL et le mode lecture seule sont conservés, la connexion est vérifiée.
macOS peut demander un accès lors de cet import initial ; les lectures normales
sont non interactives et passent par un assistant natif à signature locale,
installé à un emplacement stable. Ne lance jamais cet assistant directement.
Une rotation de la clé Claude doit désormais être reportée dans Codex.
Respecte les autorisations Codex pour le formulaire et le trousseau.

Après configuration, vérifie depuis la même copie installée :

```sh
uv run --locked scripts/check_connection.py
```

Ce contrôle initialise MCP, vérifie les 118 outils puis appelle uniquement
`rayonne_overview`. Il affiche un statut, aucun contenu de l'espace ni secret.
Indique le résultat réel, puis demande d'ouvrir un nouveau fil Codex pour
charger les outils. Ne présente pas la connexion comme validée en cas d'échec.

L'assistant graphique et le trousseau ciblent macOS. Sur les autres systèmes,
l'utilisateur peut fournir `RAYONNE_API_URL` et `RAYONNE_API_KEY` via son propre
gestionnaire de secrets dans l'environnement du processus Codex ;
`RAYONNE_READ_ONLY=true` désactive les écritures. Ne mets jamais ces valeurs
dans un manifeste, une commande visible ou un fichier versionné.
