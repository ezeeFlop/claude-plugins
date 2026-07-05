---
name: audigeo-brand-profile
description: Use whenever the user asks to view, fix, or generate their AudiGEO Brand Profile — the ground truth that drives hallucination detection, prompt discovery, and content generation. Explains the schema, common pitfalls, and how to maintain it.
---

# AudiGEO — Brand Profile

Le Brand Profile est **la source de vérité** sur la marque dans AudiGEO. Sa
qualité conditionne :

- La **détection d'hallucinations** (chaque claim IA est comparé à
  `key_facts`).
- La **génération de prompts de monitoring** (les prompts sont contextualisés
  par le profil).
- La **génération de contenu** (le moteur tire de `key_facts` et `competitors`).
- La **recherche concurrence** via Serper (les `competitors` sont la cible).

Un Brand Profile pauvre = des hallucinations non détectées + des contenus
génériques + des prompts inutiles.

## Schéma

```yaml
brand_name: "Acme Corp"                  # nom canonique
business_type: "agence de développement web"  # PRÉCIS, pas "tech"
sector: "Agence digitale spécialisée IA, Paris"  # spécialité + positionnement
target_size: "PME / TPE"                 # freelance / TPE / PME / ETI / grand
key_facts:
  Description: "..."
  Localisation: "Paris 9ème + télétravail"
  Services: ["développement web", "automatisation IA", "audit GEO"]
  Fondateurs: ["Jean Dupont"]
  Année de création: 2023
  Téléphone: "+33 1 23 45 67 89"
  Email: "contact@acme.corp"
  Adresse: "10 rue Lafayette, 75009 Paris"
  Horaires: "Lun-Ven 9h-18h"
  URL: "https://acme.corp"
competitors: ["Studio X", "Agence Y", "Boîte Z"]
aliases: ["Acme", "ACME"]
```

## Génération automatique

`POST /brand-profile/generate` (pas exposé en tool écriture en v0.1 —
disponible via UI) crawle le site + 4 recherches Serper et propose un
profil pré-rempli à valider. **Toujours faire valider par l'humain** avant
de s'en servir comme ground truth.

## Erreurs à corriger en priorité

1. **`competitors` vide** → la mesure de Share of Voice ne marche pas. Lister
   3-5 vrais concurrents minimum.
2. **`key_facts.Description` générique** → les hallucinations passent. Doit
   être un paragraphe précis qui distingue la marque.
3. **`brand_name` trop ambigu** ("ACME" matche tout) → utiliser `aliases`
   pour les variantes mais garder le canonique strict.
4. **`business_type` flou** ("conseil", "tech") → impossible de filtrer
   contre les bonnes requêtes IA. Préciser le métier.

## Édition

`audigeo_update_brand_profile(brand_name=..., key_facts={...}, ...)` — patch
partiel, seuls les champs fournis sont mis à jour. Idempotent.
