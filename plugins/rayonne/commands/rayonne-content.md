---
description: Génère, relis et approuve un contenu Rayonne.
argument-hint: [canal, ex. linkedin]
---

Aide à produire un contenu pour le canal demandé ($ARGUMENTS si fourni,
sinon demande lequel).

1. `rayonne_list_platforms` pour retrouver le slug de la venue ET son mode
   d'exécution. Dis-le à l'utilisateur : sur une venue `semi_auto` (Reddit,
   Hacker News, Discord…), Rayonne prépare un kit, c'est lui qui poste.
2. `rayonne_generate_content` avec le bon `content_type` pour la venue.
   Cela consomme le quota mensuel — préviens avant, pas après.
3. Attends, puis `rayonne_get_content` pour lire le texte RÉELLEMENT généré
   (la liste ne rend que des métadonnées). Regarde aussi
   `content_jsonb._selling_kit` (les arguments disponibles et celui utilisé),
   `content_jsonb.media` (ce qui accompagnera le post) et
   `quality_jsonb.sells` (verdict, raisons, règles en défaut).
4. Présente le texte tel quel. Puis juge-le honnêtement en une ou deux
   phrases : est-ce qu'il vend le métier ou récite des features ? Avant de
   proposer l'approbation, offre `rayonne_preview_content` : c'est ce qui
   sera réellement publié — texte, découpe en thread, emplacement du lien et
   médias, par venue.
5. Selon la réponse de l'utilisateur : `rayonne_edit_content` pour corriger
   le texte à la main, `rayonne_regenerate_text` avec un autre
   `argument_index` pour changer d'argument de vente sans tout réécrire,
   `rayonne_brand_card` si `content_jsonb.media` est vide (gratuit, pas
   d'appel LLM), `rayonne_approve_content` pour valider, `rayonne_reject_content`
   sinon.

N'approuve jamais de ta propre initiative — c'est la boucle humaine, elle
n'a de valeur que si un humain la ferme.
