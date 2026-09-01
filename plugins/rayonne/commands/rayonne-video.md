---
description: Lance une vidéo Rayonne et suis-la jusqu'au rendu.
argument-hint: [format, ex. 9x16]
---

Génère une vidéo produit et rends compte du résultat.

1. AVERTIS d'abord : la génération vidéo est FACTURÉE et consomme le quota.
   Attends un accord explicite avant d'appeler quoi que ce soit.
2. `rayonne_create_video` (format $ARGUMENTS si fourni, sinon 9x16).
3. Le rendu est long. Suis-le avec `rayonne_get_video` : `stage` dit où en
   est le pipeline (plan → capture → avatar → voice → music → compose →
   render), `degradations` ce qui a été dégradé en route.
4. Quand c'est fini, donne l'URL de rendu et le score de couverture
   commerciale. Si le storyboard est disponible, montre le hook et le CTA.
5. Si le résultat est faible, ne relance pas tout : `rayonne_regenerate_video`
   reprend à une étape précise. Un storyboard à réécrire, c'est `plan` ; un
   montage à refaire, c'est `compose`.

Si la vidéo vend l'architecture plutôt que le métier, le défaut n'est pas
dans la vidéo : lance `/rayonne-brief`, la cause est en amont.
