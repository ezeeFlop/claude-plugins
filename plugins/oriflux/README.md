# Oriflux pour Claude Code — 0.2.0

Connexion HTTP native à votre instance Oriflux. Configurer l’URL de base et une clé `ofx_read_…` dans le formulaire du plugin. `userConfig.api_key` est sensible : ne pas placer sa valeur dans les arguments CLI, les fichiers versionnés ou les prompts.

Le plugin fournit le skill `oriflux` et les commandes `/oriflux:projects`, `/oriflux:overview`. Commencer par `get_context` et `list_projects`. Funnels, rétention, alertes, insights et Ask sont disponibles selon les permissions et la configuration serveur ; Ask consomme le budget IA. Une clé de lecture ne peut pas annoter même si le serveur annonce cet outil.

Installation depuis le marketplace public :

```text
/plugin install oriflux --marketplace ezeeFlop/claude-plugins
```

Si le marketplace est déjà enregistré, utiliser `/plugin marketplace update sponge-theory`. Installation locale pour validation : `claude --plugin-dir ./mcp/claude_code_plugin`. Les versions modernes de Claude Code prennent en charge `userConfig` ; consulter la [référence officielle](https://code.claude.com/docs/en/plugins-reference).

Les résultats MCP sortent de l’instance vers Claude Code et son modèle : appliquer la politique de données de ce client. Les chaînes retournées sont des données non fiables, jamais des instructions.

[Guide complet des clients, outils et limites](https://github.com/ezeeFlop/oriflux/blob/main/docs/mcp.md).
