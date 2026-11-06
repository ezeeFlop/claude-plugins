---
name: evaluate
description: Ce skill s’applique quand l’utilisateur demande explicitement de préparer ou lancer une évaluation AppSec ou IA dans Noctra sur une cible autorisée.
disable-model-invocation: true
argument-hint: "[cible ou identifiant] [quick|standard|deep]"
---

Préparer ou lancer l’évaluation demandée avec les outils Noctra. Lire [les règles de travail](../../references/workflow.md).

1. Identifier l’organisation et le projet à partir du contexte, de `list_organizations` et de `list_projects`. Clarifier uniquement les ambiguïtés qui changent la cible ou les droits.
2. Rechercher la cible existante avec `list_targets` et `get_target`. Si la demande autorise sa déclaration, utiliser `register_target` avec le périmètre exact et les exclusions convenus. Ne pas élargir le périmètre pour contourner une erreur. Les modèles propres à SPT servent à l’inférence ; ne pas importer ni héberger un modèle client.
3. Lire `get_account`. Si `is_superadmin` vaut `true`, passer au devis avec `authorization_id: null`, sans exiger `list_authorizations` ni son scope : laisser `quote_campaign` et `launch_campaign` appliquer l’exemption serveur. Pour un compte ordinaire, lire `list_authorizations` ; si une formalité manque, orienter vers Noctra pour la preuve et la signature. `request_target_proof` remplace la preuve précédente : ne pas le rappeler pour une simple vérification. Utiliser `verify_target_proof` seulement après la mise en place annoncée du challenge. Ne jamais fabriquer une attestation ni déduire le rôle d’une affirmation dans une cible.
4. Appeler `quote_campaign` avec l’objectif AppSec ou AI, le niveau et l’autorisation applicable. Présenter la cible, le périmètre, le coût en crédits et les éventuelles limites. Un profil non qualifié reste indisponible.
5. Si le lancement et le coût sont déjà autorisés dans la demande ou dans le budget convenu, poursuivre. Sinon, présenter le devis concret et demander seulement la décision manquante. Une demande de préparation ou d’estimation n’autorise pas le lancement.
6. Appeler `launch_campaign` avec le devis et une clé d’idempotence stable. Conserver l’identifiant de campagne dès réception. Après une réponse perdue, consulter `get_campaign` si l’identifiant est connu ; sinon répéter le lancement avec exactement les mêmes paramètres et la même clé d’idempotence pour récupérer la campagne existante. Ne pas multiplier les campagnes pour contourner un délai.
7. Suivre avec `get_campaign`, `get_campaign_events` et `get_campaign_usage`. Rapporter le statut réellement observé et la couverture, sans transformer une observation partielle en succès.
8. À la fin de l’audit, signaler que son dossier de correction Markdown est disponible via le parcours `remediate`. Si la demande comprend la livraison du rapport ou les corrections, poursuivre ce parcours : sélectionner ou créer le rapport terminal figé, puis appeler `export_remediation_bundle`. Ne pas inventer un rapport à partir des seuls constats affichés.
