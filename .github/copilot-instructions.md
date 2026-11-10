# Instructions du projet SOC/SIEM

## Avant chaque tâche

- Lire `docs/engineering-log.md` et `docs/architecture-decisions.md` avant de modifier le projet.
- Examiner les modules, contrats API/DTO et dépendances concernés. Respecter les cadrages dans `Cadrage/`.
- Maintenir le périmètre MVP : Wazuh, Rspamd, ClamAV, MISP, identité et réponses restent simulés jusqu'à décision explicite et documentée.

## Architecture et sécurité

- Suivre les ADR : monolithe modulaire, API FastAPI, portail Next.js, PostgreSQL, frontières explicites et logique métier hors routes/UI.
- Toute route métier exige une identité authentifiée et un tenant dont l'appartenance est vérifiée côté serveur. Ne jamais faire confiance au tenant du corps de requête ; les ressources inter-tenant ne doivent pas être révélées.
- Valider les entrées et permissions dans l'API, masquer les secrets, échouer explicitement et ne jamais présenter un échec comme un succès.
- Les intégrations et réponses du prototype n'appellent aucun produit ou service réel et ne produisent aucun effet externe.
- Toute décision d'architecture importante doit être ajoutée à `docs/architecture-decisions.md` avec contexte, solution, alternatives et conséquences.

## Fin de tâche et revue

- Avant de terminer : relire les changements, corriger les incohérences, ajouter/mettre à jour les tests et la documentation directement liée, puis exécuter les validations disponibles.
- Consigner dans `docs/engineering-log.md` la date, l'agent, le module, l'objectif, les travaux, décisions, impact et TODO. Mentionner clairement les validations non exécutées et ne jamais les revendiquer.
- Ne considérer aucune fonctionnalité importante terminée sans revue indépendante par le rôle concerné :
  - Backend et frontend : Architect Agent.
  - Connecteurs/intégrations de sécurité : Backend Agent.
  - Architecture/contrats : Backend, Frontend ou Security Integration selon l'impact.
- La checklist de revue couvre architecture, modules, nommage, DTO, API, base de données, sécurité, compilation, tests, duplication et documentation. Consigner le résultat et les corrections dans le journal ; une revue par l'auteur ne remplace pas la revue croisée.
