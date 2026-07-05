---
name: audigeo-content-gen
description: Use when the user wants to generate GEO-optimized content via AudiGEO — articles, FAQ, llms.txt, llms-full.txt, robots.txt, Schema.org JSON-LD, Markdown Mirrors. Explains which type to pick, how to write briefs that work, and how IndexNow + A/B testing fit in.
---

# AudiGEO — Génération de contenu GEO

AudiGEO génère 6 types de contenus optimisés pour l'extraction par les IA.
Tous passent par le moteur d'inférence interne (SPT Models, Gemma 4 26B) et
sont contextualisés par le Brand Profile + le secteur.

## Quel type choisir

| Type | Contient | Quand le choisir |
|---|---|---|
| `article` | Article long, structure markdown, dense factuel | Couvrir un sujet avec autorité, gagner des citations |
| `faq` | Q/R avec balisage FAQPage Schema | Capter les requêtes type "comment faire X" |
| `llms_txt` | Résumé machine-readable de l'activité, racine du domaine | Toute marque sérieuse en a un (équivalent du robots.txt pour les IA) |
| `llms_full_txt` | Version exhaustive avec listes de pages | Sites > 50 pages où llms.txt seul ne suffit pas |
| `robots_txt` | robots.txt avec User-agents pour bots IA | Si le site bloque accidentellement GPTBot/Google-Extended |
| `schema_org` | JSON-LD Organization / LocalBusiness / Product | Donne aux IA des faits structurés extractibles |

## Markdown Mirrors

Format à part : `audigeo_generate_markdown_mirror(url)` produit un .md
propre du contenu d'une URL. À déployer en parallèle de l'HTML, servi en
`Content-Type: text/markdown`. Idempotent par URL — relancer ne crée pas
de doublon. Standard GEO, pas une attaque ni un prompt injection.

## Comment écrire un bon brief

- **Article** : indiquer angle, audience, longueur cible (mots), 2-3 mots-clés
  GEO, sources à mentionner. Exemple : "Article 1500 mots pour CMO de PME
  industrielle, sur 'comment l'IA générative impacte la prospection B2B',
  mentionner étude Forrester 2026".
- **FAQ** : lister les 5-10 questions à couvrir. Exemple : "FAQ hôtellerie
  Biarritz : 'meilleure période pour y aller', 'spa avec vue mer',
  'quartier à éviter', 'transport depuis Paris'".
- **llms.txt / Schema.org** : un brief minimal suffit — le générateur tire
  du Brand Profile. Renseigner juste "version courte" ou "inclure tous
  les services".

## A/B testing + IndexNow

Après génération, `audigeo_get_content(content_id)` retourne le contenu et
les flags `ab_test_id` et `index_now_status`. Le A/B testing produit 2
variantes scorées par LLM, l'utilisateur choisit la meilleure. IndexNow
soumet automatiquement les nouvelles URLs aux moteurs (Bing, Yandex).

## Quota

- **Pro** : 30 générations / mois.
- **Agency** : illimité.

Si le quota est atteint, `audigeo_generate_content` retourne un 402 avec
`upgrade_url` — propose à l'utilisateur de passer Agency ou d'attendre le
reset mensuel.
