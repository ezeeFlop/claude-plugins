---
name: audigeo-bot-analytics
description: Use when the user asks which AI crawlers visit their site, whether their robots.txt is blocking AI bots, or wants to set up bot tracking. Covers the JS snippet, server log import, and the 8+ tracked bots.
---

# AudiGEO — Bot Analytics

Mesure le trafic des crawlers IA sur le site du client. Réponse à la
question : "qui crawle vraiment mon site, à quelle fréquence, et est-ce
que mon `robots.txt` les bloque ?".

## Bots détectés

- **GPTBot** (OpenAI) — la principale cible
- **Google-Extended** (Google AI / Gemini training)
- **ClaudeBot** (Anthropic)
- **PerplexityBot** (Perplexity)
- **Bytespider** (ByteDance / Doubao)
- **CCBot** (Common Crawl — alimente plusieurs IA)
- **AppleBot-Extended** (Apple Intelligence)
- **OAI-SearchBot** (ChatGPT Search)

## Deux méthodes d'ingestion

### Snippet JS

`audigeo_get_bot_snippet()` retourne un `<script>` à coller en head/footer.
Capte les visites côté front, envoie un beacon à AudiGEO. Pas exposé
comme tool écriture en v0.1 — l'utilisateur récupère le snippet via UI.

**Limitation** : les bots qui ne rendent pas le JS (la plupart) ne sont
pas vus. Le snippet est utile pour les bots qui rendent JS (rare) + les
utilisateurs IA qui scrappent côté client (encore plus rare).

### Import de logs serveur (préférable)

`POST /bots/import-logs` ingère un fichier de logs Nginx/Apache et
détecte les User-Agents IA. **C'est la méthode qui voit vraiment tout.**
Pas exposé comme tool en v0.1 — usage UI ou cron côté client.

## Interpréter les visites

- **GPTBot peu présent + ChatGPT ne mentionne pas la marque** → vérifier
  `robots.txt` (blocage involontaire ?) et la fraîcheur du site.
- **GPTBot très présent + ChatGPT ne mentionne pas** → problème de contenu
  (lisibilité, structure, faits extractibles). Relancer un audit.
- **Pic de Bytespider** → audience asiatique potentielle (Doubao). Adapter
  contenu localisé si pertinent.
- **CCBot fréquent** → indexation Common Crawl en cours. Va alimenter les
  prochains entraînements de tous les LLM.

## En lien avec robots.txt

Si l'audit signale "robots.txt bloque GPTBot", c'est ici qu'on vérifie le
résultat de la correction : faire un patch robots.txt, attendre 24-48h,
puis regarder si GPTBot revient dans les Bot Analytics.
