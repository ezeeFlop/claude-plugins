---
description: Publie un contenu approuvé — ou rends le kit à coller.
---

Accompagne la publication d'un contenu approuvé.

1. `rayonne_list_content` filtré sur `approved`. S'il n'y a rien, dis-le et
   arrête-toi là.
2. `rayonne_list_platforms` : choisis la venue avec l'utilisateur, et
   annonce son mode AVANT de promettre quoi que ce soit.
   - `api` → Rayonne poste seul.
   - `browser_local` → il faut l'extension navigateur, dans l'onglet où
     l'utilisateur est déjà connecté.
   - `semi_auto` → Rayonne prépare, l'humain poste. Les ToS de ces
     plateformes l'exigent ; ne propose jamais de contourner ça.
3. `rayonne_create_submission`, en proposant une date si utile.
4. En mode `semi_auto`, enchaîne sur `rayonne_submission_kit` et rends le
   deep-link, les blocs à coller et la checklist, prêts à l'emploi. Une fois
   posté, `rayonne_confirm_submission` avec l'URL publique — elle est exigée,
   c'est la preuve.
5. Propose `rayonne_create_tracking_link` : une URL nue ne mesure rien, le
   redirect est ce qui écrit la métrique d'acquisition.
