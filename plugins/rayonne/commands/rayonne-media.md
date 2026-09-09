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
