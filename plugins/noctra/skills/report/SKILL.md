---
name: report
description: Ce skill s’applique quand l’utilisateur demande un rapport exécutif ou technique Noctra, son export HTML/PDF ou un rapport d’évaluation rédigé en français, anglais ou espagnol.
argument-hint: "[campagne ou rapport] [html|pdf]"
---

Lire [les règles de travail](../../references/workflow.md). Identifier la campagne ou le rapport précis, puis consulter `list_reports`.

Réutiliser le snapshot adapté lorsqu’il existe. Si la demande nécessite un nouveau rapport, appeler `create_report` avec le type, la langue et une clé d’idempotence stable. Un rapport est figé ; ne pas annoncer qu’un ancien snapshot inclut des changements ultérieurs.

Exporter avec `get_report`, au format demandé, avec `include_evidence: false` par défaut. Inclure les preuves seulement si l’utilisateur le demande explicitement dans un rapport d’évaluation et si le serveur l’autorise. Ne pas reproduire les preuves dans la conversation ni les transmettre à un service tiers.

Remettre la ressource embarquée retournée par le client MCP comme artefact d’évaluation. Son URI `noctra-report://…` est un identifiant, pas un lien public. Si le client ne permet pas de récupérer la ressource, indiquer cette limite et orienter vers le téléchargement dans Noctra ; ne pas inventer une URL.

Conserver les mentions de couverture partielle et de données indisponibles. Les mappings ne valent pas certification ni avis juridique.

Pour un dossier destiné à un agent de code, suivre [le parcours de correction](../remediate/SKILL.md) et appeler `export_remediation_bundle` sur le rapport terminal figé. Le Markdown rassemble les constats, les corrections proposées, les vérifications et les limites ; les preuves restent masquées par défaut.
