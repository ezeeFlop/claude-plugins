# Rayonne — plugin Claude Code

Pilote un ou tous les espaces de ton organisation
[Rayonne](https://rayonne.sponge-theory.dev) depuis Claude Code : audit
marketing de ta page produit, analyse produit, génération de contenus et de
vidéos, métriques AARRR.

## Manuel d'utilisation

Le plugin laisse Claude piloter Rayonne à ta place. Il sert à deux choses :
**configurer un produit depuis son code** (une fois par produit) et **le
travail courant** (contenus, vidéos, publication, suivi).

Dans Claude Code, chaque commande prend le préfixe du plugin :
`/rayonne:rayonne-from-code`, `/rayonne:rayonne-status`…

### 1. Installer — une seule fois, pour ton compte et tous tes dépôts

1. **Le plugin** :
   ```
   /plugin marketplace add ezeeFlop/claude-plugins
   /plugin install rayonne@sponge-theory
   ```
   Portée « user », celle par défaut. Prérequis :
   [`uv`](https://docs.astral.sh/uv/). Claude Code propose de saisir la clé
   tout de suite : tu peux laisser vide et passer par l'étape 3.
2. **La clé** : Rayonne → Réglages → « Clés d'API (extension, API,
   Claude) ».
   - Coche **« Piloter toute l'organisation »**, clique « Générer une
     clé », puis copie-la : elle ne s'affiche qu'une fois.
   - Dans la liste, la portée doit indiquer « organisation +
     administration ». Il faut être propriétaire de l'organisation, sur le
     plan Business.
   - Une clé existante ne se promeut pas : crée-en une nouvelle, puis
     révoque l'ancienne.
3. **L'installer**, sans jamais la coller dans une conversation :
   ```
   ! pbpaste | uvx rayonne-mcp login
   /reload-plugins
   ```
   - La clé est vérifiée auprès de Rayonne, puis rangée dans
     `~/.config/rayonne/credentials.json`, lisible par toi seul.
   - Sous Linux, remplace `pbpaste` par `wl-paste`. Dans un terminal,
     `uvx rayonne-mcp login` la demande en saisie masquée.
   - `uvx rayonne-mcp logout` la retire.
4. **Vérifier** : `/rayonne:rayonne-setup`. La commande contrôle que la clé
   est chargée et qu'elle porte l'administration.

**Mettre à jour** :
```
/plugin marketplace update
/plugin update rayonne
/reload-plugins
```

### 2. Configurer un produit — une fois par produit

Ouvre Claude Code **dans le dépôt du produit**, puis tape :
```
/rayonne:rayonne-from-code https://url-du-produit
```
L'URL est facultative si le produit n'a pas encore de page publique.
L'agent fait le travail ; toi, tu valides aux moments clés :

| L'agent | Toi |
|---|---|
| Trouve l'espace du produit, ou le crée (il ne supprime jamais rien, et reprend un espace existant tel quel) | — |
| Lit le code et rédige un dossier produit, chaque ligne avec sa source | **relis le dossier et dis OK** |
| Lance l'analyse, puis vérifie le brief et les faits contre le code | **acceptes ou refuses ses corrections** |
| Fait l'inventaire de la galerie et ne capture que les écrans qui manquent | **dis OK** s'il faut capturer |
| Te pose quelques questions : stade, heures par semaine, audience, budget, objectif à 90 jours | **réponds** |
| Branche dans ton code les événements mesurés (inscription, activation, revenu) | **relis le diff** et mets le secret dans ta prod |
| Propose la stratégie et la vérifie | **l'actives**, si elle te va |
| Liste les comptes à connecter | **les connectes dans l'application** |
| Génère les premiers contenus et les vérifie | **les approuves** |

Il termine par un tableau : ce qu'il a vérifié, ce qu'il a corrigé, ce
qui reste à ta charge.

### 3. Au quotidien

| Commande | Quand |
|---|---|
| `/rayonne:rayonne-status` | Où on en est : contenus, publications, chiffres. |
| `/rayonne:rayonne-verify` | À chaque version de ton produit, ou avant d'approuver : revérifie contre le code les faits, la stratégie, les contenus, les scénarios vidéo, la galerie et les questions GEO, puis améliore ce qui peut l'être. |
| `/rayonne:rayonne-content linkedin` | Générer, relire, approuver un contenu. |
| `/rayonne:rayonne-video` | Lancer une vidéo et la suivre jusqu'au rendu. Elle est facturée : il demande avant. |
| `/rayonne:rayonne-publish` | Publier un contenu approuvé, ou récupérer le kit à coller. |
| `/rayonne:rayonne-plan` | Lire la stratégie, ou en créer une. |
| `/rayonne:rayonne-brief` | Ce que Rayonne a compris du produit, et le corriger. |
| `/rayonne:rayonne-audit` | Ce qui plafonne le message de ta page produit. |
| `/rayonne:rayonne-media` | Les images ou la vidéo d'un contenu. |
| `/rayonne:rayonne-workspaces` | Les espaces de l'organisation : en cibler un. |
| `/rayonne:rayonne-setup` | Installer ou remplacer la clé. |

Le rythme simple : `/rayonne:rayonne-verify` à chaque version du produit,
et une passe sur « À valider » dans l'application chaque semaine.

### Ce que le plugin ne fait jamais

- Te demander ta clé dans la conversation.
- Approuver, publier ou lancer une vidéo facturée sans ton accord.
- Valider un post LinkedIn ou Hashnode, ni poster sur Reddit, Hacker News
  ou Product Hunt : c'est toi, dans l'application ou avec le kit.
- Supprimer un espace, ni régénérer le secret de mesure d'un produit déjà
  branché.

### Le serveur ne démarre pas ?

- `/mcp` → `rayonne` → **Reconnect**.
- Si le premier démarrage est lent (réseau, antivirus), allonge le délai
  des serveurs MCP dans `~/.claude/settings.json`
  (`"env": {"MCP_TIMEOUT": "120000"}`), puis relance Claude Code.
- `uv --version` doit répondre : sans `uv`, le serveur ne peut pas partir.
- Le serveur démarre par `uv run --locked` sur le verrou livré avec le
  plugin (`uv.lock`) : rien n'est résolu sur PyPI au lancement.

## Outils

168 outils — ceux du serveur publié qu'épingle le verrou (`rayonne-mcp==0.13.1`),
un par verbe de l'API publique — table complète groupée par
module (M1 brief, M2 stratégie, M3 contenu, M3 kit de vente et médias, M4
soumission et pièces jointes du kit, M5 analytics, M9 vidéo et storyboard,
avatars vidéo, galerie produit, audit, espaces de l'organisation,
workspace) dans [`mcp/README.md`](../README.md#outils).

Dix-huit outils sont arrivés en 0.6.0, pour sortir du navigateur le dépôt,
l'atelier vidéo et les pièces jointes d'un kit : la galerie produit devient
inscriptible (`rayonne_upload_product_asset`,
`rayonne_update_product_asset`, `rayonne_suggest_asset_caption`,
`rayonne_delete_product_asset`), l'atelier vidéo s'ouvre en entier (avatars
`rayonne_list_avatars`, `rayonne_generate_avatar`, `rayonne_update_avatar`,
`rayonne_cutout_avatar` ; relecture `rayonne_reopen_storyboard`, `rayonne_cancel_reopen_storyboard`,
`rayonne_assist_storyboard`, `rayonne_chat_storyboard`,
`rayonne_storyboard_thumbnail`, `rayonne_update_video`,
`rayonne_music_presets`), et un kit Mode C accepte des visuels déposés à la
main (`rayonne_upload_submission_asset`,
`rayonne_generate_submission_assets`, `rayonne_list_submission_assets`,
`rayonne_delete_submission_asset`).

Une vidéo livrée avant le bandeau produit de la première image le reçoit
en deux outils : `rayonne_suggest_video_cover` propose le texte (chiffres
vérifiés sur les faits produit), `rayonne_set_video_cover` le pose et refait
la vidéo à partir du montage — offert, rien n'est facturé.

TikTok ne rend aucun lien cliquable dans une légende : le seul est le champ
« Site web » du profil. `rayonne_list_accounts` rend ce lien (`bio_link`, la
page du compte TikTok qui mène à chacun de ses produits) et
`rayonne_confirm_bio_link` coche « Mon lien est dans ma bio TikTok » quand
l'utilisateur dit l'avoir collé. Même chose pour YouTube : aucun lien de la
description d'un Short n'est cliquable, seuls ceux de la chaîne le sont ; un
compte YouTube connecté rend son `bio_link` (la page YouTube de l'espace,
qui mène à son produit) et `rayonne_confirm_bio_link(platform_slug="youtube")` coche
« Mon lien est sur ma chaîne YouTube ».

Les deux outils de dépôt prennent un **chemin de fichier local** : le
serveur tourne sur ta machine et lit les octets lui-même — un chemin fautif
est refusé avant tout appel réseau. En revanche il n'y a **aucun outil de
dépôt d'avatar**, et aucune route publique derrière : enregistrer un visage
engage le consentement d'une personne réelle, qu'une clé API ne peut pas
donner à sa place. `rayonne_generate_avatar` compose un portrait de
synthèse ; une vraie photo se dépose dans l'interface, par un humain.

Quatre outils sont arrivés en 0.5.0, pour piloter TOUTE l'organisation
depuis une seule clé : `rayonne_list_workspaces`, `rayonne_create_workspace`,
`rayonne_delete_workspace`, `rayonne_update_workspace`. Les 59 outils
précédents gagnent au passage un `workspace_id` optionnel pour agir sur un
autre espace que celui d'origine — omis, rien ne change ; les 18 outils de
0.6.0 le portent aussi. **Rupture** : le
format rendu par `rayonne_workspace` s'enrichit (`autopilot_enabled` devient
`autopilot`, `locale`/`paused`/`autopublish_live`/`video_music`
apparaissent).

Huit outils sont arrivés en 0.4.0, pour piloter le kit de vente et les
médias d'un post sans quitter Claude : `rayonne_content_media`,
`rayonne_set_content_media`, `rayonne_recompute_content_media`,
`rayonne_brand_card`, `rayonne_regenerate_text`, `rayonne_preview_content`,
`rayonne_workspace`, `rayonne_set_ai_illustrations`.

Chaque outil d'écriture (générer, éditer, publier, planifier…) consomme du
quota du workspace ; la génération vidéo est en plus **facturée**. Coche
**Mode lecture seule** à l'installation pour les désactiver.

Version 0.9.0 : `rayonne_reset_content` remet en relecture sans rien
réécrire — la réécriture depuis le brief corrigé est
`rayonne_regenerate_content` ; les comptes connectés (lecture,
déconnexion), le badge « attention requise », la revue hebdo lue en entier,
la page GEO en lecture et la couverture vendeuse arrivent (10 outils
ajoutés, détail dans [`mcp/README.md`](../README.md#090)).

Version 0.8.0 : la réalité du fondateur, le plan modifiable et ses
expériences, la liste « À faire », le plan de lancement et ses gardes, les
pages de comparaison sourcées, le rapport par canal et le registre des
faits du produit (36 outils ajoutés, détail dans
[`mcp/README.md`](../README.md#080)) ; un refus de l'API arrive entier.

Version 0.7.0 : finalisation via `rayonne_onboard_workspace`, sans nouvelle
analyse ; patch du brief par fusion récursive, champs absents conservés.
