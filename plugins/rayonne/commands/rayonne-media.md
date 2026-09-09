---
description: Inspecte les médias d'un contenu Rayonne et corrige-les.
argument-hint: [id du contenu]
---

Vérifie ce qui accompagnera un post et corrige si besoin.

1. Si $ARGUMENTS n'est pas un id de contenu, demande lequel — ou propose
   `rayonne_list_content` pour le retrouver.
2. `rayonne_content_media` pour voir la sélection résolue : URL publique,
   dimensions, durée.
3. Si une ressource a disparu, la raison de l'abandon est dans la réponse —
   explique-la simplement, sans jargon technique.
4. Selon le cas :
   - un vrai écran du produit manque → `rayonne_list_product_assets` d'abord
     (il y en a peut-être déjà un qui convient), sinon **dépose-le** :
     `rayonne_upload_product_asset` prend un CHEMIN DE FICHIER sur cette
     machine — demande-le à l'utilisateur, ne l'invente pas. Un écran
     derrière un login, aucun crawler ne le verra jamais : c'est le seul
     moyen de le montrer. Écris la légende dans la foulée (ou propose
     `rayonne_suggest_asset_caption`, qui appelle un modèle vision) : sans
     elle, rien ne saura quand piocher cet écran.
   - rien d'utilisable → `rayonne_brand_card` (gratuit, pas d'appel LLM) :
     compose une carte de marque avec la punchline du post, ou une fournie
     par l'utilisateur.
   - la sélection doit juste être rafraîchie depuis le playbook de la venue
     → `rayonne_recompute_content_media` (gratuit) — c'est la seule sortie
     d'un verrouillage manuel.
   - la sélection doit être fixée à la main → `rayonne_set_content_media`,
     en prévenant que ça VERROUILLE la pièce : plus aucune régénération de
     texte ni recalcul automatique n'y touchera tant que
     `rayonne_recompute_content_media` n'est pas rappelé.
5. Termine par `rayonne_preview_content` pour montrer le résultat final,
   texte et médias ensemble, avant publication.

Ne verrouille jamais une sélection sans le dire à l'utilisateur — c'est un
aller simple tant qu'il ne rappelle pas le recalcul.

Une suppression d'écran (`rayonne_delete_product_asset`) est DÉFINITIVE :
le fichier part avec la ligne, et seul un nouveau dépôt le ramène. Demande
avant, toujours.
