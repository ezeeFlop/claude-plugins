# Noctra 0.2.0

Clients publics pour les évaluations AppSec/IA autorisées, les campagnes, rapports et dossiers de correction. Le serveur métier reste distant et aucun moteur n’est exécuté sur le poste.

| Instance | Claude Code | Codex | Claude Desktop |
| --- | --- | --- | --- |
| Bêta .dev | [noctra-dev](plugins/noctra-dev/README.md) | [noctra-dev-codex](plugins/noctra-dev-codex/README.md) | noctra-development-0.2.0.mcpb |
| .ai, service pas encore déployé | [noctra](plugins/noctra/README.md) | [noctra-codex](plugins/noctra-codex/README.md) | noctra-saas-0.2.0.mcpb |

Les bundles Desktop, archives et SHA-256 sont attachés à la [release noctra-mcp-v0.2.0](https://github.com/ezeeFlop/claude-plugins/releases/tag/noctra-mcp-v0.2.0). Choisir la même instance que celle de la clé. Publier un client .ai ne signifie pas que le service .ai est ouvert.

Installer la bêta dans Claude Code :

```text
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install noctra-dev@sponge-theory
```

Installer la bêta dans Codex :

```sh
codex plugin marketplace add https://github.com/ezeeFlop/claude-plugins.git
codex plugin add noctra-dev-codex@sponge-theory-codex
```

Claude Code et Desktop recueillent la clé dans leur champ sensible. Codex propose une saisie masquée avec son skill setup, une entrée trousseau Noctra dédiée par origine sur macOS et un diagnostic sans secret ; le README documente la variable spécifique Linux/Windows. Aucun credential d’un autre plugin n’est importé. Node.js 22+ est requis pour les plugins.

Après un audit terminé, demander le dossier de correction de la campagne : le skill remediate utilise export_remediation_bundle sur un rapport final figé. Le Markdown conserve constats, pistes de correction, vérifications attendues et limites. Les preuves restent masquées par défaut. Prévoir report:read et, pour créer un rapport final manquant, report:write ; les scopes d’organisation/projet/campagne permettent la navigation. Les corrections et réévaluations restent dans le périmètre demandé et le budget autorisé.

Le relais JavaScript autonome et ses licences sont inclus ; aucun npm install au lancement. Les tests du bundle contre une API jetable couvrent protocoles MCP, révocation, scopes, rapport masqué et Markdown. Les manifests MCPB et Claude sont validés par leurs CLI officiels. Cette qualification de protocole ne prétend pas valider tous les dialogues de chaque application ou le trousseau avec un compte réel. Aucune clé de test réelle n’est distribuée. Les bundles n’ont pas de signature éditeur ; le helper macOS est signé ad-hoc et vérifié par SHA-256.
