---
description: Installe ou remplace la clé API Rayonne du plugin, sans jamais la coller dans la conversation, puis vérifie ce qu'elle permet.
---

Guide l'utilisateur pour installer la clé API du plugin. Le plugin et sa
clé valent pour l'UTILISATEUR, sur tous ses dépôts : rien ne s'installe ni
ne s'écrit dans un projet. Le plugin s'installe en portée utilisateur
(`/plugin install rayonne@sponge-theory`, portée « user », celle par
défaut). La clé va dans son dossier personnel (`~/.config/rayonne/`), jamais
dans un dépôt, un `.env` ou un fichier versionné. Ne demande JAMAIS la
clé dans la conversation, ne la lis pas, ne l'écris dans aucun fichier toi-même,
n'explore pas le trousseau. Si l'utilisateur la colle quand même dans le chat :
ne la recopie nulle part, et conseille-lui de la révoquer puis d'en créer une
nouvelle (elle reste dans la transcription).

## 1. Ce que la clé permet aujourd'hui

`rayonne_workspace_access` :
- `key_source` dit quelle clé le serveur a chargée :
  - `file` : posée par `rayonne-mcp login` ;
  - `plugin` : saisie à l'installation du plugin ;
  - `env` : la variable `RAYONNE_API_KEY`.
- `org_admin: true` : rien à faire, la clé crée, configure et initialise les
  espaces. Arrête-toi là.
- Sinon, `next_step` dit quoi faire : suis les étapes ci-dessous.

## 2. Créer la bonne clé (l'utilisateur, dans l'application)

Rayonne → **Réglages** → **« Clés d'API (extension, API, Claude) »** :
1. Un nom, par exemple « Claude Code — <sa machine> ».
2. Coche **« Piloter toute l'organisation »**.
3. **« Générer une clé »** : la clé ne s'affiche qu'une fois, il la copie.
4. Dans la liste, la portée doit dire **« organisation + administration »**.
   Si elle dit seulement « toute l'organisation », l'administration a été
   refusée. Il faut être **propriétaire** de l'organisation, sur un plan avec
   accès API (Business).

Une clé existante ne se promeut pas : on en crée une nouvelle, puis on
révoque l'ancienne dans la même liste.

## 3. L'installer (l'utilisateur, lui-même)

La clé copiée dans le presse-papiers, il tape dans Claude Code :

```
! pbpaste | uvx rayonne-mcp login
```

- macOS : `pbpaste` lit le presse-papiers.
- Linux : remplace `pbpaste` par `wl-paste` ou `xclip -o -selection clipboard`.
- Dans un terminal ordinaire, `uvx rayonne-mcp login` demande la clé en
  saisie masquée.
- Sous macOS, sans tube, une fenêtre masquée s'ouvre.

La commande vérifie la clé auprès de Rayonne avant de l'enregistrer, dans
`~/.config/rayonne/credentials.json`, lisible par lui seul. Elle affiche la
portée et l'administration, jamais la clé. Une instance auto-hébergée ajoute
`--api-url https://<son-instance>`.

Ce fichier l'emporte sur la clé saisie à l'installation du plugin. Seule une
variable `RAYONNE_API_KEY` définie explicitement passerait devant.
`uvx rayonne-mcp logout` le retire.

## 4. Recharger, puis vérifier

1. L'utilisateur tape `/reload-plugins`.
2. Relance `rayonne_workspace_access`. Attendu : `key_source: "file"` et
   `org_admin: true`.
3. Si ce n'est pas le cas, dis exactement ce qui manque, sans deviner.
4. Si c'était bien la bonne clé, reprends la tâche interrompue (par exemple
   `/rayonne-from-code`).
