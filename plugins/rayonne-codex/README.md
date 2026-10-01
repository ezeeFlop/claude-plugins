# Rayonne pour Codex

Adaptateur Codex du plugin Claude Code Rayonne 0.7.0 : les **82 mêmes
outils**, le même serveur PyPI `rayonne-mcp==0.7.0` et son guide métier.
Aucun code serveur propriétaire n'est embarqué dans cet adaptateur.

## Installation et configuration

Prérequis : Codex avec plugins, `uv`, Python ≥ 3.10 et une clé API Rayonne
`rk_…` (Réglages → Clés API, plan Business). Le formulaire sécurisé utilise
le trousseau macOS. Une première exécution télécharge les dépendances PyPI.

Installation depuis la marketplace publique :

```sh
codex plugin marketplace add https://github.com/ezeeFlop/claude-plugins.git
codex plugin add rayonne-codex@sponge-theory-codex
```

Puis utilise le skill
`rayonne-setup`. Depuis la racine du plugin installé, les commandes équivalentes
sont :

```sh
uv run --locked scripts/configure.py --gui
uv run --locked scripts/check_connection.py
```

Dans ton propre terminal, `--terminal` remplace `--gui` (clé saisie sans écho).
La configuration importe une fois la clé Rayonne choisie vers une entrée Codex
dédiée `ai.sponge-theory.rayonne.codex.v2`, sans modifier Claude. Une clé neuve
peut aussi être saisie dans le champ masqué. L'URL, la référence du credential et le
choix lecture seule sont enregistrés dans `~/.rayonne/codex/connection.json`
(mode 0600) ; ce fichier ne contient pas de clé. La vérification ne publie
rien : elle initialise MCP, contrôle 82 outils et lit l'aperçu de l'espace.
Ouvre ensuite un **nouveau fil Codex** pour charger skills et outils.

Un déploiement sans trousseau peut fournir ensemble `RAYONNE_API_URL` et
`RAYONNE_API_KEY` à l'environnement de Codex via son gestionnaire de secrets.
L'URL est l'origine HTTPS sans `/api/public/v1`. `RAYONNE_READ_ONLY=true`
bloque les écritures côté serveur. Ne stocke pas de clé dans `.mcp.json`.

## Parcours

Les skills `rayonne-audit`, `rayonne-brief`, `rayonne-content`,
`rayonne-media`, `rayonne-plan`, `rayonne-publish`, `rayonne-status`,
`rayonne-video` et `rayonne-workspaces` reprennent les commandes Claude.
Le serveur fournit les descriptions et instructions métier canoniques.
Les actions gardent leurs contraintes : workspace explicite, validation
humaine des contenus, vidéo facturée, publication manuelle en `semi_auto`,
dépôts par chemin local et aucun dépôt de visage par clé API.

## Maintenance

Depuis le dépôt Rayonne :

```sh
python3 mcp/build/sync_codex_skills.py
python3 mcp/build/sync_codex_skills.py --check
python3 mcp/build/build_codex_plugin.py
```

Modifier les parcours dans `mcp/claude_code_plugin/commands/`, puis régénérer.
Le générateur adapte seulement les arguments, les liens entre commandes et
le contexte Codex. Le paquet `mcp/dist/rayonne-codex-0.7.1.tar.gz` contient
uniquement les fichiers nécessaires au plugin, jamais `.venv` ni les caches.
La copie publique est distribuée ici sous `plugins/rayonne-codex`.
Les scripts de maintenance cités ci-dessus vivent dans le dépôt source Rayonne.

## Migration 0.7.1 : fin des demandes répétées du trousseau

Après mise à jour, depuis la copie installée :

```sh
uv run --locked scripts/configure.py --migrate
```

La migration conserve l’URL et le mode lecture seule, vérifie l’accès et importe
la clé existante sans l’afficher. macOS peut demander une autorisation lors de
l’import initial. L’assistant natif partagé est installé à l’emplacement stable
`~/.sponge-theory/codex-keychain/v1/spt-codex-keychain` ; sa signature est locale
(ad-hoc), sans certificat Developer ID. Les lectures normales n’ouvrent aucune
fenêtre : si le trousseau est verrouillé, déverrouille-le puis relance la migration.
Aucune clé Claude n’est modifiée ou supprimée. Les rotations de clé Claude ne
sont plus reprises automatiquement dans la copie Codex. Le serveur PyPI reste
`rayonne-mcp==0.7.0` : cette version corrige uniquement l’adaptateur Codex.
