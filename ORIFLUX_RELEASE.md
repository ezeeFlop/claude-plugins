# Oriflux 0.2.0

Oriflux réunit les analytics web, produit et API. Cette livraison publie le plugin Claude Code, l’extension Claude Desktop et les SDK d’instrumentation Python et Node dans le catalogue public Sponge Theory.

## Claude Code

```text
/plugin install oriflux --marketplace ezeeFlop/claude-plugins
```

Pour une installation existante : `/plugin marketplace update sponge-theory`, puis mettre à jour le plugin. Renseigner l’URL de l’instance et une clé de lecture dans sa configuration sensible. Le plugin commence par découvrir le périmètre et les outils disponibles. Projet, opérations et expiration restent contrôlés côté serveur.

## Claude Desktop

Télécharger [oriflux-0.2.0.mcpb](https://github.com/ezeeFlop/claude-plugins/releases/download/oriflux-v0.2.0/oriflux-0.2.0.mcpb) et son [checksum](https://github.com/ezeeFlop/claude-plugins/releases/download/oriflux-v0.2.0/oriflux-0.2.0.mcpb.sha256), puis installer l’archive dans les extensions locales de Claude Desktop. Node 22.13 ou ultérieur est requis. Configurer l’URL de base sans `/mcp` et une clé `ofx_read_…`.

Le pont utilise le SDK MCP officiel, refuse les redirections et les destinations non HTTPS hors boucle locale, et expose onze outils de lecture. Le paquet contient ses dépendances de production et un SBOM. Les mises à jour nécessitent de réinstaller l’archive.

## SDK Python

```sh
pip install 'oriflux-sdk==0.2.0'
```

[PyPI](https://pypi.org/project/oriflux-sdk/0.2.0/) · [Guide](https://github.com/ezeeFlop/oriflux/blob/main/sdk/python/README.md) · [Wheel](https://github.com/ezeeFlop/claude-plugins/releases/download/oriflux-v0.2.0/oriflux_sdk-0.2.0-py3-none-any.whl) · [Sources](https://github.com/ezeeFlop/claude-plugins/releases/download/oriflux-v0.2.0/oriflux_sdk-0.2.0.tar.gz).

## SDK Node

Installation depuis la distribution publique du marketplace :

```sh
npm install https://github.com/ezeeFlop/claude-plugins/releases/download/oriflux-v0.2.0/oriflux-node-0.2.0.tgz
```

Le paquet exporte `oriflux-node`, ses types TypeScript et sa licence MIT. [Guide Node/Express](https://github.com/ezeeFlop/oriflux/blob/main/sdk/node/README.md). La disponibilité sur le registre npm est distincte de ce téléchargement GitHub.

Les deux SDK bornent la cardinalité, préservent les totaux dans des buckets de débordement et ne bloquent pas le produit instrumenté en cas d’échec réseau. La livraison reste best effort. Utiliser une clé d’ingestion de source API, distincte de la clé de lecture des agents.

## Codex et autres clients MCP

L’instance expose directement un serveur MCP HTTP ; le [guide de connexion](https://github.com/ezeeFlop/oriflux/blob/main/docs/mcp.md) couvre Codex et VS Code. Pour Codex, le secret est lu depuis `ORIFLUX_READ_KEY` via `bearer_token_env_var`. Cette livraison ne crée pas un adaptateur Codex distinct : la connexion native documentée utilise les mêmes contrôles serveur.

## Données et validation

Les résultats MCP sont transmis au client agent et à son modèle. Les chaînes retournées sont des données non fiables, jamais des instructions. Ne pas insérer de clé dans un prompt ou une commande contenant sa valeur.

Validation : manifeste Claude Code, schéma MCPB, checksum du bundle, construction reproductible, tests du pont stdio/HTTP, 16 tests Python, sept tests Node, contrôle des métadonnées PyPI et du contenu des archives. Le serveur 0.2.0 est déployé ; l’audit complet est disponible dans le [dépôt Oriflux](https://github.com/ezeeFlop/oriflux/blob/main/docs/audit-2026-10-15.md).
