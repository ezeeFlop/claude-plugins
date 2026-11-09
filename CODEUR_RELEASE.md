# Codeur MCP 0.1.0

Codeur Automation expose 163 opérations métier et diagnostic via sept outils MCP,
avec la même implémentation pour Codex, Claude Code et Claude Desktop.

## Installation

- Codex : `codex plugin add codeur-codex@sponge-theory-codex` après ajout ou mise à jour de cette marketplace.
- Claude Code : `/plugin install codeur@sponge-theory` après `/plugin marketplace add ezeeFlop/claude-plugins`.
- Claude Desktop : télécharger [le MCPB et son SHA-256](https://github.com/ezeeFlop/claude-plugins/releases/tag/codeur-mcp-v0.1.0).

Créer une clé par installation dans Codeur → Paramètres → Accès MCP.
Le MCPB présente un champ obligatoire et sensible « Clé API Codeur ».
Pour Codex sur macOS, depuis le dossier installé du plugin :
`node server.cjs --setup --gui --client codex`. La saisie est masquée ; la clé
est conservée dans une entrée dédiée du trousseau. Claude Code peut utiliser
son champ sensible ou le même assistant avec `--client claude-code`.

Le backend doit inclure la gestion des clés API (commit application `31eca7fbbeb6d4b2e33423d7be5dfb5e2660132d`).
Une clé permet la lecture seule ou la lecture et l'écriture ; elle expire par
défaut au bout de 90 jours et se révoque immédiatement dans l'application.
Elle ne permet pas d'administrer d'autres clés ni les services Docker/Portainer.

## Construction et vérification

La source reproductible est dans [shared/codeur](shared/codeur/README.md).
Les plugins prêts à installer sont dans `plugins/codeur` et `plugins/codeur-codex`.
Le MCPB est construit avec la CLI officielle MCPB, à partir des seuls fichiers
connus ; son manifest est validé. Le bundle n'est pas signé ni soumis à un annuaire.

Validation : 48 tests backend ciblés, 15 tests MCP dont une API FastAPI isolée,
démarrage des trois paquets, création/révocation par l'interface web, build React,
et test de lecture native non interactive du trousseau avec des clés factices.

- Serveur commun SHA-256 : `f8beca6eb4ac7ce22e797025ac857a339ee260e1a3666a6861cfffa8f71761fd`.
- Helper natif universel macOS SHA-256 : `0327d50f3011e905e899383fe285265247e35b77bdfdcb5f54bdd4d84d5eb60b`.
- Emplacement stable : `~/.sponge-theory/codeur-keychain/v1/spt-codeur-keychain`.

Ce helper est propre à Codeur : la publication ne modifie pas celui des autres
plugins. Son binaire versionné et son empreinte sont conservés à l'identique entre
les releases ordinaires, conformément à [la règle du trousseau Codex](CODEX_KEYCHAIN_RELEASE.md).
Une nouvelle identité exige une version distincte et une migration préparée.
