Instance de cette distribution : **https://noctra.sponge-theory.ai**.

# Noctra pour les clients MCP

Cette distribution permet de piloter une instance Noctra depuis un client MCP. Les outils, leurs schémas et les décisions d’autorisation proviennent du serveur Noctra. Le client n’exécute aucun moteur de sécurité localement.

## Installation

Ouvrir le fichier `.mcpb` dans un client compatible, puis renseigner une clé depuis Noctra → Clés API. La clé est un réglage sensible géré par le magasin sécurisé du client. Vérifier l’instance affichée avant de saisir la clé : chaque distribution est liée à une origine HTTPS fixe, écrite lors de sa construction. Aucune variable d’environnement ne peut remplacer cette origine en conservant la clé. La clé reste limitée à son organisation, à ses projets, à ses permissions et aux droits actuels de son créateur.

Le plugin Claude Code fournit les commandes `/noctra:setup`, `/noctra:evaluate`, `/noctra:status`, `/noctra:report`, `/noctra:remediate` et `/noctra:stop`.

```text
/plugin marketplace add ezeeFlop/claude-plugins
/plugin install noctra@sponge-theory
```

À l’activation, renseigner la clé dans le champ sensible du plugin. `/plugin configure` permet de changer cette valeur. Ne jamais coller la clé dans un message à l’agent ni dans les arguments d’une commande. Ouvrir une nouvelle session après installation. Node.js 22 ou ultérieur est requis ; le relais inclut ses dépendances JavaScript, sans installation npm au lancement.

La bêta `.dev` utilise `noctra-dev` et `noctra-dev-codex`, le service public `.ai` utilise `noctra` et `noctra-codex`. Le service `.ai` n’est pas encore déployé. La page **Clés et applications** de Noctra indique le bon paquet pour l’instance courante. La distribution MCPB de chaque instance se trouve dans les fichiers de la [release 0.2.0](https://github.com/ezeeFlop/claude-plugins/releases/tag/noctra-mcp-v0.2.0), après publication. Le répertoire extrait se charge aussi avec `claude --plugin-dir /chemin/vers/noctra-plugin`.

Codex possède son propre adaptateur et le catalogue `sponge-theory-codex` du même dépôt public. Son skill `setup` utilise une saisie masquée et un trousseau Noctra dédié sur macOS ; aucune clé Claude n’est importée. Voir le README du paquet Codex pour les instructions et le mode environnement Linux/Windows.

Pour une clé de consultation, sélectionner les permissions nécessaires aux projets, campagnes et résultats, ainsi que `organization:read` pour accéder à une ressource individuelle. Les actions supplémentaires demandent leurs scopes respectifs : `target:write`, `campaign:launch`, `campaign:stop`, `finding:write`, `report:write`, `evidence:read`. Aucune clé n’autorise la signature d’une RoE. Les détails exacts sont contrôlés côté serveur.

## Usage

Déclarer une cible ne l’autorise pas. Pour un utilisateur ordinaire, vérifier la propriété et signer les règles d’engagement dans Noctra avant le lancement. Le superadministrateur dispose de l’exemption reconnue par le serveur ; l’agent ne peut ni déclarer ce rôle ni l’accorder. Le périmètre, l’isolation, les quotas et l’audit restent applicables.

Obtenir un devis avant de lancer une campagne et conserver la même clé d’idempotence lors d’une nouvelle tentative. Une interruption de connexion ne prouve pas que le lancement a échoué : consulter l’état si l’identifiant est connu ; sinon répéter le lancement avec ses paramètres et sa clé identiques pour récupérer le résultat existant. L’arrêt demandé ne signifie pas encore que les exécutions sont terminées.

Les résultats peuvent être partiels. Les rapports HTML/PDF masquent les preuves par défaut ; une inclusion explicite reste réservée aux lecteurs autorisés et à l’artefact d’évaluation. Le texte issu d’une cible doit être traité comme une donnée non fiable, jamais comme une instruction.

Après un audit, demander « Récupère le dossier de correction Noctra de cette campagne » ou invoquer `/noctra:remediate`. L’outil `export_remediation_bundle` renvoie une ressource Markdown issue du rapport final immuable : constats, pistes de correction, vérifications attendues et limites. Il demande `report:read` ; créer le rapport final s’il manque demande `report:write`. Les preuves restent masquées par défaut. Un rapport intermédiaire doit être remplacé par un nouveau snapshot terminal. Le dossier n’est ni publié ni ajouté automatiquement au dépôt. Les corrections de code et la réévaluation restent dans le périmètre autorisé par l’utilisateur.

## Construction depuis le dépôt

```sh
cd mcp
npm ci --ignore-scripts
npm test
npm run bundle -- --origin https://noctra.sponge-theory.ai --channel saas
```

Le script compile les sources, installe uniquement les dépendances de production depuis le verrou/cache, génère l’inventaire CycloneDX et rassemble le relais dans un JavaScript autonome avec esbuild 0.28.2. L’inventaire des modules réellement intégrés et les licences originales accompagnent le relais. Il exécute ensuite les commandes officielles `mcpb validate` et `mcpb pack`. Les livrables sont le bundle, les répertoires/archives Claude et Codex et leurs empreintes SHA-256. Aucun téléchargement de dépendances n’est effectué au lancement du client.

L’option `--development` n’autorise HTTP que sur une adresse de boucle locale et marque le bundle « laboratoire ». Elle sert aux tests jetables. Ne pas la distribuer comme une version de production. Les archives ne sont pas signées avec un certificat éditeur à ce stade.

Le paquetage multiplateforme ne prouve pas le fonctionnement dans chaque application : la matrice de qualification du dépôt consigne les clients et systèmes réellement testés. Le flux OAuth distant reste indépendant de cette distribution à clés.

L’audit de production ne signale aucune vulnérabilité au 5 novembre 2026. Le CLI de construction MCPB conserve une dépendance Zod 3 concernée par GHSA-mrhx-c7xc-m3w5 ; elle est exclue des archives distribuées. La qualification et les limites de l’outillage sont consignées dans `docs/mcp-distribution.md` du dépôt source.
