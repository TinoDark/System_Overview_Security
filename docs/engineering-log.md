# Journal d'ingénierie

Mémoire officielle des travaux, décisions, impacts et actions restantes du projet.
Toute tâche importante doit être consignée ici avant d'être considérée comme terminée.

## 2026-11-05

### Agent

CTO / Coordination projet

### Module

Gouvernance, cadrage et architecture initiale

### Objectif

Lire l'ensemble du dossier `Cadrage/`, vérifier les agents et l'état du workspace, puis mettre en place le journal de projet et le registre des décisions d'architecture.

### Travaux

- Lecture complète des cinq documents de cadrage : exigences fonctionnelles, architecture, base de données, API/connecteurs et backlog.
- Lecture des instructions des agents Architect, Backend, Frontend et Security Integration.
- Vérification du workspace : aucun module applicatif, manifeste de dépendances, code ou tests n'existe à ce stade ; seuls le cadrage et les fichiers d'agents sont présents.
- Création du présent journal et du registre `architecture-decisions.md`.
- Définition du périmètre initial des intégrations comme simulations, conformément à la mission : aucun produit externe Wazuh, Rspamd, ClamAV ou MISP ne doit être installé ou appelé pour le MVP.

### Décisions

- Le cadrage fournit les exigences et la stack de référence ; la présente mission prévaut pour différer tout connecteur réel au profit de mocks.
- Le démarrage se fait en monolithe modulaire ; les modules métier et contrats restent à définir/implémenter au fil des sprints.
- PostgreSQL, FastAPI, Next.js, RabbitMQ, Redis et OIDC/Keycloak constituent la stack de référence du cadrage et des agents, sans présumer que les services sont déjà installés ou configurés.
- Les données, événements et réponses produits par les mocks doivent rester explicitement simulés et ne déclencher aucune action externe réelle.
- Toute modification importante devra être accompagnée d'une mise à jour de ce journal ; les décisions structurantes devront également être enregistrées dans le registre ADR.

### Impact

- Aucune modification du code applicatif ni des dépendances : aucun socle applicatif n'existe encore.
- Ajout du point de référence commun pour coordonner les agents et assurer la traçabilité.
- Le décalage entre les connecteurs réels envisagés dans le cadrage et la contrainte de simulation de la mission est résolu en faveur des mocks jusqu'à validation du MVP.
- Les revues croisées et la checklist de validation restent obligatoires pour les changements de code ; elles ne s'appliquent pas comme validations de compilation à cette tâche documentaire.

### TODO

- Définir les contrats et la structure initiale du backend et du frontend avant leur implémentation.
- Déterminer comment exécuter les mocks et jeux de données dans l'environnement MVP sans dépendre des produits réels.
- Préciser le modèle de stockage des événements et l'usage des services d'infrastructure au moment de concevoir le socle technique.
- Ajouter pour chaque tâche terminée les résultats de tests, la revue croisée, les mises à jour documentaires et les éventuels ADR.

## 2026-11-05 — Définition du prototype vertical MVP

### Agent

CTO / Architecture

### Module

Architecture, contrats API, persistance, identité, intégrations simulées et parcours MVP

### Objectif

À partir des cinq cadrages et des quatre instructions agents, définir des choix implémentables et vérifiables pour un prototype exécutable avec mocks uniquement, sans modifier de code ni prétendre que des composants sont installés/configurés.

### Vérifications et travaux

- Relecture des cadrages `01` à `05`, des décisions ADR existantes, du journal et des instructions Architect, Backend, Frontend et SecurityIntegration.
- Vérification de l'état du workspace : aucun code applicatif, manifeste, test, migration ou configuration d'exécution n'a été créé/validé dans cette tâche.
- Ajout des ADR-004 à ADR-009 : stockage MVP, identité de démonstration, connecteurs/réponse simulés, dépendances et architecture de modules, contrats et parcours, convention d'isolation tenant.
- Définition des DTO/énumérations, enveloppes d'erreurs, routes MVP, limites initiales, flux ingestion-détection-corrélation-incident-réponse et exigences de tests multi-tenant dans `architecture-decisions.md`.
- Aucune installation, configuration ou connexion Wazuh, Rspamd, ClamAV, MISP, Keycloak, RabbitMQ, Redis ou OpenSearch n'a été effectuée. Ces composants ne sont pas déclarés opérationnels.
- Aucune revue de code ni exécution de tests n'est applicable : aucun code n'a été modifié. La revue croisée de l'architecture reste un jalon avant implémentation.

### Décisions

- PostgreSQL constitue la source de vérité du prototype, y compris pour événements et payloads de fixtures ; Indexer, RabbitMQ et Redis sont différés afin de ne pas imposer des composants non requis au flux vertical.
- L'auth simulée est explicitement dev-only, par `PrincipalProvider`, avec utilisateurs de fixtures, jetons opaques volatils et vérification serveur des rôles et appartenances. Elle ne prétend pas remplacer OIDC.
- Les quatre connecteurs ont des fixtures déterministes sans client réseau ni fallback réel. La réponse `simulate_containment` est sans effet externe et reste derrière approbation, autorisation, idempotence et kill switch désactivé par défaut.
- Le premier parcours est : login mock -> choisir organisation autorisée -> collecter une fixture -> normaliser/dédupliquer/persister -> détection/corrélation explicables -> incident -> approbation distincte -> réponse simulée vérifiée -> audit et dashboard.
- Le frontend ne lit que l'API FastAPI. Les métriques proviennent des données du backend ; l'UI montre explicitement le caractère simulé.
- Le contexte tenant authentifié et validé par appartenance est obligatoire dans routes, services et repositories. Un ID tenant du body n'est jamais autoritaire ; les ressources inter-tenant sont masquées en 404.

### Impact

- Cette entrée complète et précise les TODO initiaux concernant stockage, auth, mocks et dépendances ; elle ne constitue pas l'implémentation du prototype.
- La stack de référence reste FastAPI/Next.js/PostgreSQL. RabbitMQ, Redis et Keycloak restent des choix de cible différés, et non des services configurés.
- Les contrats de travail détaillés et le diagramme se trouvent dans ADR-005 à ADR-009 ; le backlog du cadrage reste source des exigences fonctionnelles, avec priorité à la tranche verticale P0.

### Revue croisée requise avant merge MVP

- **Architecte** : frontières des modules, dépendances, cohérence DTO/OpenAPI et absence de couplage direct aux fournisseurs.
- **Backend** : transactions/idempotence PostgreSQL, validation Pydantic, contrats routes-services-repositories et comportement d'erreur.
- **SecurityIntegration** : fixtures synthétiques, absence d'appels réseau/commandes externes, affichage `is_simulated`, réponse sans effet réel.
- **Frontend** : parcours login mock, consommation exclusive de l'API, états d'erreur/loading, indication simulation, aucun contrôle d'autorisation exclusivement UI.
- **Contrôle sécurité tenant (bloquant)** : tests croisés A/B incluant UUID connu, listes, détails, événements liés, approbation, exécution et audit ; contrôle du contexte à chaque couche.
- Une personne différente de l'auteur du changement effectue la revue correspondante ; résultats, correctifs et tests sont ajoutés au journal. Aucun résultat de revue n'est revendiqué ici.

### Tâches restantes — ordre de mise en œuvre

1. **Geler les contrats et critères** : revue croisée des ADR-004..009 par les rôles ci-dessus ; régler les divergences et publier les schémas OpenAPI/DTO/tests de contrat avant d'écrire l'application.
2. **Socle exécutable** : initialiser backend FastAPI et frontend Next.js/TypeScript, PostgreSQL local, migrations, configuration par environnement, health/live et readiness PostgreSQL, enveloppes d'erreur, logs expurgés ; documenter les commandes de démarrage. N'ajouter aucun service différé.
3. **Tenant et identité simulée** : créer les fixtures de deux organisations et les utilisateurs/roles de démo ; provider mock dev-only, login/logout/me, permissions serveur et TenantContext fail-closed. Tester 401/403/404 et tentatives inter-tenant avant de poursuivre.
4. **Données métier minimales** : organisations, appartenances, actifs, intégrations mock, événements JSONB/idempotence, incidents/liens, politiques, approbations, réponses et audit ; migrations et contraintes tenant/FK ; seed synthétique reproductible.
5. **Connecteurs mock et pipeline** : quatre catalogues de fixtures, health/collect/normalize/validate, routes mock et test d'intégration ; collecte idempotente et transactionnelle ; règles, fenêtre de corrélation 15 min, score documenté, création/actualisation d'incidents.
6. **Workflow de réponse contrôlé** : politique whitelist, demande d'approbation, séparation demandeur/décideur, expiration, kill switch off par défaut, dry-run puis exécution mock seulement, vérification, idempotence et audit ; test négatif prouvant qu'aucun système externe n'est modifié/contacté.
7. **API et UI verticales** : recherche événements, incidents/détail/statut/commentaire, approbations/réponses, dashboard agrégé depuis PostgreSQL ; pages Login, Dashboard, Events, Incidents, Assets/Integrations et vues minimales Policies/Approvals/Audit selon priorité ; UI via API seulement.
8. **Validation MVP et revue finale** : tests unitaires, migrations, API/contrats, parcours end-to-end sur deux tenants, doublons, erreurs, permissions, kill switch, absence d'accès réseau tiers ; revue croisée consignée, correction des constats, guide de lancement et limites connues.
9. **Après acceptation seulement** : évaluer séparément le besoin de RabbitMQ/outbox et workers, Redis, Keycloak/OIDC, Indexer/OpenSearch, puis intégrations réelles ; décisions et revues de sécurité distinctes requises avant toute activation.

### Critères d'acceptation du prototype

- Lancement documenté avec l'application et PostgreSQL uniquement ; fixtures locales et aucun service externe nécessaire.
- Le parcours collecte mock -> événement persisté une seule fois -> incident explicable -> approbation -> résultat `simulated` vérifié -> audit/dashboard est répétable.
- Les tentatives inter-tenant échouent aux couches HTTP/service/repository et aucun résultat d'un autre tenant n'est renvoyé.
- Les mocks et états simulés sont identifiables ; aucune clé, URL, socket, installation ou commande des produits réels n'est utilisée.
- Les composants différés sont présentés comme « non configurés/non disponibles », jamais comme sains ou opérationnels.

## 2026-11-05 — Initialisation du prototype

### Agent

CTO / Coordination projet

### Module

Racine du projet, lancement local et tranches backend/frontend

### Objectif

Commencer l'implémentation du prototype sur la base des contrats ADR-004 à ADR-009 et préparer un démarrage local limité à FastAPI, Next.js et PostgreSQL.

### Travaux

- Ajout du README racine avec périmètre, limites de sécurité, prérequis, commandes prévues, validations et liens vers les documents du projet.
- Ajout de `.env.example`, `.gitignore` et d'un `docker-compose.yml` limité à PostgreSQL, publié sur l'interface locale et avec volume persistant/healthcheck.
- Ajout de `.github/copilot-instructions.md` pour rendre les lectures préalables, la journalisation, les contrôles de sécurité et la revue croisée applicables aux agents du workspace.
- Lancement de l'implémentation backend par Backend Agent et du portail par Frontend Agent, dans des dossiers séparés, conformément aux contrats établis.
- Aucun produit de sécurité réel, Keycloak, RabbitMQ, Redis ou indexeur n'a été ajouté à l'environnement.

### Décisions

- Le conteneur PostgreSQL est la seule dépendance d'infrastructure locale ; les identifiants doivent être définis dans un `.env` local ignoré par Git.
- Le backend et le frontend sont des travaux en cours et ne sont pas déclarés intégrés ni validés tant que code, tests et revues croisées ne sont pas vérifiés.
- Au premier constat, Python, Node.js, npm et Docker n'étaient pas disponibles sur le PATH et le raccourci Python du Microsoft Store ne fournissait pas Python ; les binaires Python et Node ont depuis été installés comme indiqué ci-dessous.

### Impact

- Les fichiers de lancement documentent les services réellement retenus et ne présentent pas les intégrations différées comme configurées.
- Aucun secret de connexion n'est commis ; le fichier exemple contient une valeur de remplacement non utilisable comme secret de production.
- La documentation de démarrage devra être ajustée à la structure et aux scripts réellement produits par les agents.
- Pour débloquer la validation après le constat d'outils manquants, installation officielle de Python 3.12.10 et Node.js 24.20.0 LTS via WinGet ; les deux binaires sont vérifiés par leurs chemins d'installation. Le shell de la session n'ayant pas rechargé le PATH utilisateur, les validations devront employer le chemin installé ou actualiser PATH explicitement.
- Docker, PostgreSQL local et les dépendances Python/Node du projet ne sont pas encore disponibles ; aucune validation applicative n'est revendiquée à ce stade.

### TODO

- Récupérer et examiner les travaux backend et frontend, corriger les écarts de contrats et actualiser les commandes de démarrage réelles.
- Effectuer les revues croisées Architect / Backend / Frontend / Security Integration selon le périmètre.
- Rendre disponibles les runtimes ou un environnement de validation, puis lancer tests, lint, build et tests d'API requis.
- Fournir PostgreSQL 16 (instance locale ou Docker Compose) pour les validations d'intégration et de démarrage prévues.
- Exécuter le parcours multi-tenant complet avec PostgreSQL, doublons, séparation d'approbation, kill switch et audit.
- Inscrire les constats et résultats de validation dans ce journal ; ne pas déclarer le prototype accepté avant leur résolution.

## 2026-11-05 — Intégration et validation du prototype vertical

### Agent

CTO / Coordination projet

### Module

API FastAPI, portail Next.js, connecteurs mock, contrats et lancement local

### Objectif

Intégrer les modules backend et frontend, corriger les écarts de contrat constatés pendant leur assemblage, valider les parcours couverts par l'environnement et rendre compte des validations croisées.

### Travaux

- Intégration du backend FastAPI et du portail Next.js pour la connexion mock, les tenants, les actifs, intégrations, événements, incidents, politiques, approbations, réponses simulées, audit et dashboard.
- Correction de l'endpoint de synthèse du dashboard, ajout de la timeline tenantée et enrichissement des détails d'incident avec les données de workflow consommées par le portail.
- Alignement des noms DTO, de l'en-tête `Idempotency-Key`, des enveloppes d'erreur, de la gestion des listes et des erreurs de déconnexion ; CORS limité aux origines locales configurées.
- Stabilisation du lint Next.js en utilisant la configuration ESLint classique compatible avec Next.js 15 et ESLint 8 ; mise à jour des commandes de validation documentées.
- Mise à jour des contrats API/dashboard et du comportement CORS dans ADR-007/ADR-008.
- Revue croisée Backend des mocks et du flux ingestion/incident/approbation/réponse : aucun constat actionnable. La revue Architecte du backend/frontend est encore en cours ; aucun résultat n'est anticipé.

### Décisions

- Maintenir les quatre fournisseurs de sécurité et toute réponse comme des simulations ; aucune installation ni connexion de produit réel n'est utilisée.
- Garder PostgreSQL comme base de données runtime, mais ne pas déclarer le parcours accepté sans valider migrations, démarrage et concurrence avec une instance PostgreSQL réelle.
- Le lint est exécuté explicitement par `npm run lint`; Next.js utilise en plus sa vérification de lint/type au build avec la configuration classique.

### Impact

- Backend : 13 tests Pytest réussis ; `ruff check app tests migrations` réussi ; génération SQL hors ligne Alembic réussie.
- Frontend : `npm run lint`, `npm run typecheck`, `npm test` (4 tests), `npm run build` et `npm audit` réussis ; aucune vulnérabilité npm rapportée.
- La compilation de migration ne valide pas son exécution réelle sur PostgreSQL. Docker n'est pas installé et le port local 5432 n'est pas disponible ; le parcours end-to-end avec deux tenants reste donc non vérifié.
- Les données de démonstration et les routes restent réservées au prototype ; ces résultats ne constituent pas une certification de sécurité ou de préparation à la production.

### TODO

- Recevoir et traiter la revue Architecte, puis consigner ses constats et validations.
- Démarrer PostgreSQL 16 dans un environnement disponible, exécuter Alembic et vérifier le démarrage/readiness.
- Parcourir le flux complet avec deux tenants : collecte répétée/idempotence, accès par UUID connu, création d'incident, approbateur distinct, kill switch désactivé puis réponse simulée autorisée, audit et dashboard.
- Ne pas déclarer le MVP accepté tant que ces vérifications d'intégration et la revue croisée finale ne sont pas terminées.

## 2026-11-05 — Correctifs après revue Architecte

### Agent

CTO / Coordination projet

### Module

Isolation tenant en base, workflow d'approbation et architecture des services backend

### Objectif

Traiter les constats de la revue croisée Architecte sur les liens relationnels inter-tenant, les décisions concurrentes et l'écart entre les frontières ADR et l'organisation actuelle des cas d'usage.

### Travaux

- Ajout de clés étrangères composites pour contraindre au même tenant les références événement/intégration, incident/événement, incident/commentaire, incident/réponse/approbation et réponse/politique.
- Ajout de contraintes de membre organisationnel pour demandeurs, décideurs et auteurs de commentaires.
- Ajout du tenant à la clé primaire de `incident_events` et mise à jour des lectures/écritures correspondantes.
- Remplacement de la décision d'approbation « lire puis modifier » par une mise à jour conditionnelle atomique qui n'accepte qu'une approbation pending non expirée. Un test confirme aussi qu'une deuxième décision est refusée.
- Activation des clés étrangères SQLite dans les tests et ajout d'un test prouvant qu'un lien incident A / événement B est rejeté par la base.
- Exécution de la migration Alembic contre SQLite temporaire et vérification `PRAGMA foreign_key_check` sans violation.
- Revue Architecte : trois constats moyens. Les invariants tenant et la course d'approbation sont corrigés. Le service d'application demeure centralisé ; l'écart avec ADR-007 est maintenant explicite dans ADR-010 comme dette d'architecture à résoudre avant extension importante ou usage de production, plutôt que présenté comme une frontière déjà effective.

### Décisions

- Conserver les vérifications tenant dans les services et y ajouter les contraintes relationnelles comme défense en profondeur.
- Enregistrer atomiquement les décisions d'approbation dans la base plutôt que d'utiliser un verrou applicatif ou mémoire.
- Ne pas entreprendre une extraction mécanique de `services.py` au milieu de la stabilisation fonctionnelle ; aucune nouvelle fonctionnalité majeure ne doit s'appuyer sur cette organisation centrale avant une décomposition en services/domaines avec revue dédiée.

### Impact

- Backend : 14 tests Pytest réussis, `ruff check app tests migrations` réussi, compilation SQL Alembic réussie, migration initiale SQLite exécutée et clés étrangères vérifiées.
- Le test initial avec clés étrangères activées a révélé que le seed supposait un autoflush ; l'ordre de flush des organisations, utilisateurs et intégrations est maintenant explicite.
- Le test SQLite valide les contraintes relationnelles et le parcours applicatif, mais ne remplace pas PostgreSQL : les migrations et la course concurrente doivent encore être exercées avec PostgreSQL.
- Le constat de modularité demeure ouvert et documenté ; la revue ne recommande pas de déclarer l'architecture complète ou le prototype accepté avant la suite des validations.

### TODO

- Décomposer `backend/app/services.py` en services de domaine effectifs selon les frontières ADR-007, en préservant les transactions inter-domaines et en ajoutant des tests de contrats.
- Valider la migration et l'approbation concurrente sur PostgreSQL, puis exécuter le parcours multi-tenant complet.
- Obtenir et consigner la revue finale des frontières de modules après leur matérialisation.
