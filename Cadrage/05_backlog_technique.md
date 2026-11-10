# Document 5 --- Backlog technique de développement

## User Stories, tâches, critères d'acceptation et dépendances

**Version :** 1.0 --- **Statut :** backlog initial pour GitHub Projects
ou Jira

## 1. Conventions

-   Epic : domaine fonctionnel ou technique.
-   User Story (US) : besoin utilisateur ou système.
-   Task (T) : travail technique.
-   Critères d'acceptation (CA) : conditions vérifiables.
-   P0 : indispensable au MVP ; P1 : important ; P2 : amélioration.
-   Estimations à ajouter après estimation collective.

## 2. Epics

  ------------------------------------------------------------------------------
  Epic              Domaine                 Résultat           Priorité
  ----------------- ----------------------- ------------------ -----------------
  EPIC-01           Fondations techniques   Environnement      P0
                                            opérationnel       

  EPIC-02           Identité et accès       Authentification   P0
                                            et autorisations   

  EPIC-03           Organisations et actifs Gestion des        P0
                                            organisations et   
                                            équipements        

  EPIC-04           Connecteurs             Connexion aux      P0
                                            outils de sécurité 

  EPIC-05           Ingestion               Collecte et        P0
                                            normalisation      

  EPIC-06           Détection/corrélation   Détection et       P0
                                            regroupement des   
                                            alertes            

  EPIC-07           Incidents               Cycle de vie des   P0
                                            incidents          

  EPIC-08           Réponse                 Actions avec       P0
                                            validation humaine 

  EPIC-09           Interface SOC           Supervision        P0

  EPIC-10           Audit/reporting         Traçabilité et     P1
                                            rapports           

  EPIC-11           Tests/déploiement       Fiabilité et mise  P0
                                            en production      
  ------------------------------------------------------------------------------

## 3. Backlog détaillé

### EPIC-01 --- Fondations techniques

#### US-01 --- Initialiser le backend

En tant que développeur, je veux une structure backend organisée afin de
développer les modules indépendamment.

  -----------------------------------------------------------------------
  ID                      Tâche                   Module
  ----------------------- ----------------------- -----------------------
  T-01                    Créer le dépôt Git et   Git
                          les branches `main`,    
                          `develop`, `feature/*`  

  T-02                    Initialiser FastAPI et  Backend
                          les environnements      

  T-03                    Organiser les modules   Backend
                          métier                  

  T-04                    Configurer Pydantic,    Core
                          variables               
                          d'environnement et      
                          erreurs                 

  T-05                    Configurer Alembic      Database

  T-06                    Ajouter Pytest          Tests

  T-07                    Configurer les logs     Observabilité
                          JSON                    
  -----------------------------------------------------------------------

**CA :** API démarrable et OpenAPI accessible ; secrets hors du code ;
migrations exécutables ; tests lancés ; logs JSON horodatés UTC.\
**Dépendances :** aucune.

#### US-02 --- Déployer l'environnement de développement

En tant que développeur, je veux démarrer les composants avec une
configuration reproductible.

  ID     Tâche                            Module
  ------ -------------------------------- ----------------
  T-08   Créer `docker-compose.yml`       Infrastructure
  T-09   Configurer PostgreSQL            Database
  T-10   Configurer RabbitMQ              Messaging
  T-11   Configurer Redis                 Cache
  T-12   Préparer l'accès Wazuh Indexer   Search
  T-13   Configurer Keycloak              Identity
  T-14   Ajouter les health checks        Infrastructure

**CA :** services démarrables par Docker Compose ; données PostgreSQL
persistées ; secrets externalisés ; backend connecté à PostgreSQL et
RabbitMQ.\
**Dépendances :** US-01.

### EPIC-02 --- Identité et contrôle d'accès

#### US-03 --- Authentifier les utilisateurs

En tant qu'utilisateur, je veux me connecter de manière sécurisée.

  ID     Tâche                                                Module
  ------ ---------------------------------------------------- ----------
  T-15   Configurer realm et clients Keycloak                 Identity
  T-16   Définir les rôles                                    Identity
  T-17   Valider les tokens OIDC/JWT                          Backend
  T-18   Ajouter les dépendances d'authentification FastAPI   API
  T-19   Gérer expiration et renouvellement des sessions      Identity

**CA :** accès authentifié autorisé ; non authentifié = HTTP 401 ; token
expiré/invalide rejeté ; aucun secret dans les réponses.\
**Dépendances :** US-01, US-02.

#### US-04 --- Gérer rôles et permissions

En tant qu'administrateur, je veux attribuer des permissions aux
utilisateurs.

  -----------------------------------------------------------------------
  ID                      Tâche                   Module
  ----------------------- ----------------------- -----------------------
  T-20                    Définir les rôles Super RBAC
                          Administrateur,         
                          Administrateur          
                          sécurité, Analyste SOC, 
                          Opérateur, Auditeur,    
                          Observateur             

  T-21                    Définir permissions par RBAC
                          ressource/action        

  T-22                    Développer les          API
                          vérifications de        
                          permissions             

  T-23                    Tester accès autorisés  Tests
                          et interdits            
  -----------------------------------------------------------------------

**CA :** chaque rôle a des permissions définies ; les actions interdites
sont refusées côté backend ; les refus pertinents sont journalisés.\
**Dépendances :** US-03.

### EPIC-03 --- Organisations et actifs

#### US-05 --- Gérer les organisations

En tant que super administrateur, je veux gérer les organisations pour
isoler leurs environnements.

  ID     Tâche                                         Module
  ------ --------------------------------------------- ---------------
  T-24   Créer `Organization`                          Organizations
  T-25   Créer les endpoints CRUD                      API
  T-26   Associer les utilisateurs aux organisations   Identity
  T-27   Ajouter les contrôles d'isolation             Security
  T-28   Tester l'isolation entre organisations        Tests

**CA :** organisation créable, consultable, modifiable et désactivable ;
données rattachées à une organisation ; aucune consultation croisée non
autorisée.\
**Dépendances :** US-01, US-04.

#### US-06 --- Gérer les actifs

En tant qu'administrateur sécurité, je veux inventorier les équipements
surveillés.

  ID     Tâche                                    Module
  ------ ---------------------------------------- ----------
  T-29   Créer `Asset`                            Assets
  T-30   Définir les types d'actifs               Assets
  T-31   Développer endpoints CRUD                API
  T-32   Associer les actifs à une organisation   Database
  T-33   Gérer l'état de surveillance             Assets
  T-34   Ajouter recherche et filtres             API

**CA :** actif créable, modifiable, consultable et désactivable ;
organisation obligatoire ; champs nom/type/adresse/système/statut ;
filtres disponibles.\
**Dépendances :** US-05.

### EPIC-04 --- Intégrations et connecteurs

#### US-07 --- Enregistrer une source

En tant qu'administrateur sécurité, je veux enregistrer un outil de
sécurité.

  ID     Tâche                                           Module
  ------ ----------------------------------------------- --------------
  T-35   Créer `Integration`                             Integrations
  T-36   Définir les types de sources                    Integrations
  T-37   Développer les endpoints                        API
  T-38   Gérer paramètres et secrets                     Secrets
  T-39   Ajouter état de connexion et dernier contrôle   Monitoring

**CA :** intégration enregistrable/désactivable ; secrets protégés et
jamais renvoyés ; configuration liée à une organisation ; test de
connexion possible.\
**Dépendances :** US-05.

#### US-08 --- Intégrer Wazuh

En tant qu'analyste SOC, je veux récupérer les alertes Wazuh.

  ID     Tâche                                          Module
  ------ ---------------------------------------------- --------------
  T-40   Figer la version Wazuh ciblée                  Architecture
  T-41   Configurer l'accès sécurisé à l'API            Connector
  T-42   Implémenter le client API Wazuh                Connector
  T-43   Récupérer les alertes par fenêtre temporelle   Connector
  T-44   Gérer pagination, erreurs et interruptions     Connector
  T-45   Ajouter reprise sans doublons                  Connector
  T-46   Tester sur instance réelle                     Tests

**CA :** disponibilité vérifiable ; alertes récupérées de façon
authentifiée ; reprise sans perte silencieuse ni doublons fonctionnels ;
erreurs journalisées ; moteur Wazuh non réimplémenté.\
**Dépendances :** US-07, US-02.

#### US-09 --- Préparer les autres connecteurs

En tant qu'administrateur sécurité, je veux ajouter plusieurs outils.

  ID     Tâche                                   Module
  ------ --------------------------------------- ---------------------
  T-47   Définir `BaseConnector`                 Connectors
  T-48   Connecteur Suricata via EVE JSON        Connectors
  T-49   Connecteur Rspamd HTTP/JSON ou Milter   Connectors
  T-50   Connecteur ClamAV                       Connectors
  T-51   Étudier MISP                            Threat Intelligence
  T-52   Tester conformité des connecteurs       Tests

**CA :** chaque connecteur expose contrôle, collecte et normalisation ;
panne isolée ; erreurs traçables ; état de santé consultable.\
**Dépendances :** US-07 et conventions de US-08.

### EPIC-05 --- Ingestion et normalisation

#### US-10 --- Collecter les événements

En tant que plateforme, je veux recevoir les événements pour les traiter
de façon asynchrone.

  ID     Tâche                                         Module
  ------ --------------------------------------------- ------------
  T-53   Définir le format d'événement interne         Events
  T-54   Créer files RabbitMQ                          Messaging
  T-55   Développer producteurs                        Ingestion
  T-56   Développer consommateurs                      Workers
  T-57   Gérer files d'échec et nouvelles tentatives   Messaging
  T-58   Surveiller débit et erreurs                   Monitoring

**CA :** événement publié dans RabbitMQ ; consommateur indépendant de
l'API ; message en erreur isolable/rejouable ; traitement idempotent.\
**Dépendances :** US-08, US-01, US-02.

#### US-11 --- Normaliser et stocker les événements

En tant qu'analyste SOC, je veux consulter des événements homogènes.

  ID     Tâche                                   Module
  ------ --------------------------------------- ---------------
  T-59   Créer `NormalizedEvent` avec Pydantic   Events
  T-60   Développer les mappings par source      Normalization
  T-61   Valider les événements                  Validation
  T-62   Calculer une clé de déduplication       Events
  T-63   Indexer dans Wazuh Indexer              Search
  T-64   Ajouter les filtres de recherche        API

**CA :** événement avec identifiant, source, UTC, organisation et type ;
provenance conservée ; invalides rejetés ou mis en quarantaine ;
recherche fonctionnelle ; doublons contrôlés.\
**Dépendances :** US-10, US-05, US-06.

### EPIC-06 --- Détection et corrélation

#### US-12 --- Détecter les événements suspects

En tant qu'analyste SOC, je veux identifier les événements critiques.

  ID     Tâche                            Module
  ------ -------------------------------- -----------
  T-65   Définir niveaux de sévérité      Detection
  T-66   Exploiter les alertes Wazuh      Detection
  T-67   Définir règles complémentaires   Rules
  T-68   Développer moteur d'évaluation   Detection
  T-69   Enregistrer les résultats        Detection

**CA :** alerte Wazuh interprétable ; sévérité harmonisée ; détection
explicable ; règles activables/désactivables ; doublons contrôlés.\
**Dépendances :** US-11.

#### US-13 --- Corréler et calculer le risque

En tant qu'analyste SOC, je veux regrouper les alertes liées.

  -----------------------------------------------------------------------
  ID                      Tâche                   Module
  ----------------------- ----------------------- -----------------------
  T-70                    Définir critères de     Correlation
                          corrélation             

  T-71                    Corrélation temporelle  Correlation

  T-72                    Corrélation par actif,  Correlation
                          utilisateur et          
                          indicateur              

  T-73                    Définir calcul du score Risk
                          de risque               

  T-74                    Enregistrer les liens   Correlation
                          entre événements        

  T-75                    Ajouter les tests       Tests
  -----------------------------------------------------------------------

**CA :** événements liés regroupables ; provenance conservée ; score
documenté et explicable ; facteurs consultables ; aucune corrélation
inter-organisation.\
**Dépendances :** US-11, US-12.

### EPIC-07 --- Incidents

#### US-14 --- Créer et suivre les incidents

En tant qu'analyste SOC, je veux un dossier par incident.

  ID     Tâche                                Module
  ------ ------------------------------------ -----------
  T-76   Définir `Incident`                   Incidents
  T-77   Créer incident depuis corrélation    Incidents
  T-78   Associer les événements              Incidents
  T-79   Définir statuts du workflow          Workflow
  T-80   Développer endpoints                 API
  T-81   Ajouter assignation                  Incidents
  T-82   Ajouter commentaires et historique   Incidents

**CA :** corrélation pertinente créant un incident ;
sévérité/statut/organisation/date présents ; événements associés
consultables ; assignation autorisée ; statuts historisés ; clôture
justifiée.\
**Dépendances :** US-13, US-04, US-06.

### EPIC-08 --- Réponse et orchestration

#### US-15 --- Définir les politiques

En tant qu'administrateur sécurité, je veux définir les actions
autorisées selon le risque.

  ID     Tâche                                 Module
  ------ ------------------------------------- -----------
  T-83   Définir `SecurityPolicy`              Policies
  T-84   Définir conditions de déclenchement   Policies
  T-85   Définir actions autorisées            Responses
  T-86   Ajouter niveaux d'approbation         Approvals
  T-87   Tester les politiques                 Tests

**CA :** politique créable/modifiable/activable/désactivable ;
conditions/actions explicites ; approbation humaine pour actions
sensibles ; modifications auditées ; politique désactivée sans effet.\
**Dépendances :** US-14.

#### US-16 --- Soumettre à approbation humaine

En tant qu'analyste SOC, je veux valider ou refuser une action proposée.

  ID     Tâche                                   Module
  ------ --------------------------------------- -----------
  T-88   Créer `Approval`                        Approvals
  T-89   Générer demande d'approbation           Workflow
  T-90   Développer endpoints approve/reject     API
  T-91   Vérifier permissions de l'approbateur   Security
  T-92   Gérer expiration                        Workflow
  T-93   Journaliser décisions                   Audit

**CA :** aucune exécution avant approbation requise ; approbateur
autorisé ; demande expirée inexécutable ; acteur/date/justification
enregistrés ; traitement unique.\
**Dépendances :** US-15, US-04.

#### US-17 --- Exécuter et vérifier les réponses

En tant qu'opérateur SOC, je veux exécuter une action autorisée et
vérifier son résultat.

  ID      Tâche                                      Module
  ------- ------------------------------------------ --------------
  T-94    Définir contrat des actions                Responses
  T-95    Implémenter moteur d'orchestration         Orchestrator
  T-96    Ajouter mode `dry-run`                     Responses
  T-97    Implémenter premières actions autorisées   Connectors
  T-98    Ajouter idempotence et anti-rejeu          Security
  T-99    Ajouter `kill switch`                      Security
  T-100   Vérifier résultat post-exécution           Verification
  T-101   Enregistrer résultats et erreurs           Audit

**CA :** action non autorisée bloquée ; approbation valide exigée si
nécessaire ; simulation sans modification réelle ; répétition sans
exécution multiple non désirée ; résultat vérifié et audité ; kill
switch opérationnel ; échec jamais présenté comme succès.\
**Dépendances :** US-16, US-15, US-08.

Commencer par des actions réversibles et testées en environnement isolé.
Les actions à fort impact exigent analyse de risque, validation
explicite et retour arrière.

### EPIC-09 --- Interface web SOC

#### US-18 --- Authentifier depuis l'interface

En tant qu'utilisateur, je veux me connecter depuis l'interface web.

  ID      Tâche                                 Module
  ------- ------------------------------------- ----------
  T-102   Initialiser React/Next.js             Frontend
  T-103   Configurer client OIDC/Keycloak       Frontend
  T-104   Créer connexion et déconnexion        Frontend
  T-105   Gérer sessions et routes protégées    Frontend
  T-106   Adapter l'affichage aux permissions   Frontend

**CA :** connexion/déconnexion fonctionnelles ; pages protégées
inaccessibles sans authentification ; affichage selon permissions ;
backend reste l'autorité d'accès.\
**Dépendances :** US-03, US-01.

#### US-19 --- Consulter le tableau de bord

En tant qu'analyste SOC, je veux visualiser les indicateurs de sécurité.

  ID      Tâche                                    Module
  ------- ---------------------------------------- -----------
  T-107   Définir KPI                              Analytics
  T-108   Développer agrégations API               API
  T-109   Créer cartes KPI                         Frontend
  T-110   Créer graphiques temporels               Frontend
  T-111   Afficher incidents par sévérité/statut   Frontend
  T-112   Ajouter filtres période/actif            Frontend
  T-113   Ajouter rafraîchissement                 Frontend

KPI : événements collectés, alertes, incidents
ouverts/critiques/résolus, actions en attente, état des connecteurs,
temps moyen de traitement.

**CA :** KPI issus de données réelles ; filtres fonctionnels ; isolation
par organisation ; indisponibilité de source signalée.\
**Dépendances :** US-06, US-11, US-14, US-08.

#### US-20 --- Consulter et traiter les incidents dans l'interface

En tant qu'analyste SOC, je veux suivre un incident depuis une interface
unique.

  ID      Tâche                                          Module
  ------- ---------------------------------------------- ----------
  T-114   Créer liste des incidents                      Frontend
  T-115   Créer détail d'incident                        Frontend
  T-116   Afficher événements associés                   Frontend
  T-117   Ajouter assignation et changements de statut   Frontend
  T-118   Créer interface d'approbation                  Frontend
  T-119   Afficher historique des actions                Frontend

**CA :** incidents autorisés consultables ; événements associés visibles
; actions selon rôle ; demande d'approbation détaillée ; résultats de
réponse visibles.\
**Dépendances :** US-14, US-16, US-17, US-18.

### EPIC-10 --- Audit et reporting

#### US-21 --- Tracer les actions

En tant qu'auditeur, je veux consulter les opérations réalisées.

  ID      Tâche                                                 Module
  ------- ----------------------------------------------------- ----------
  T-120   Définir `AuditLog`                                    Audit
  T-121   Tracer connexions/déconnexions                        Audit
  T-122   Tracer modifications actifs/politiques/intégrations   Audit
  T-123   Tracer approbations et exécutions                     Audit
  T-124   Développer endpoints de consultation                  API
  T-125   Protéger les journaux contre modification             Security

**CA :** actions sensibles journalisées ;
acteur/action/date/ressource/résultat présents ; consultation autorisée
; journaux append-only côté application ; utilisateurs standards sans
droit de modification.\
**Dépendances :** US-04, US-05, US-14, US-15, US-17.

#### US-22 --- Générer des rapports

En tant qu'administrateur sécurité, je veux produire des rapports
périodiques.

  ID      Tâche                                  Module
  ------- -------------------------------------- -----------
  T-126   Définir modèles de rapport             Reporting
  T-127   Créer agrégations statistiques         Analytics
  T-128   Générer PDF ou CSV                     Reporting
  T-129   Ajouter filtres période/organisation   Reporting
  T-130   Historiser les rapports                Reporting

**CA :** rapport par période ; indicateurs cohérents avec tableau de
bord ; isolation organisationnelle ; période et date de génération
visibles.\
**Dépendances :** US-19, US-21.

### EPIC-11 --- Tests, sécurité et déploiement

#### US-23 --- Tester les fonctionnalités et intégrations

En tant que responsable technique, je veux vérifier les fonctionnalités
afin de réduire les régressions.

  ID      Tâche                                            Module
  ------- ------------------------------------------------ -------------
  T-131   Tests unitaires des services métier              Backend
  T-132   Tests PostgreSQL/RabbitMQ                        Backend
  T-133   Tests connecteurs avec données représentatives   Connectors
  T-134   Tests bout en bout détection → réponse           E2E
  T-135   Tests permissions et isolation                   Security
  T-136   Tests de reprise après interruption              Reliability

**CA :** fonctions critiques couvertes ; interactions intermodules
testées ; parcours MVP testé ; refus et échecs vérifiés ; pas de données
de production dans les tests.

#### US-24 --- Sécuriser et préparer le déploiement

En tant qu'administrateur système, je veux déployer la plateforme de
manière reproductible.

  ID      Tâche                                          Module
  ------- ---------------------------------------------- ----------------
  T-137   Configurer CI/CD                               DevOps
  T-138   Contrôles qualité et analyse des dépendances   DevSecOps
  T-139   Configurer TLS et certificats                  Infrastructure
  T-140   Gérer les secrets                              Security
  T-141   Configurer sauvegardes PostgreSQL              Database
  T-142   Définir rétention des événements               Data
  T-143   Documenter restauration                        Operations
  T-144   Définir RPO/RTO                                Operations
  T-145   Préparer déploiement Ansible                   Deployment

**CA :** déploiement reproductible ; communications chiffrées ; secrets
absents des images/dépôts ; restauration testée ; procédures documentées
; RPO/RTO validés.

## 4. Dépendances entre Epics

``` mermaid
flowchart TD
  A["EPIC 01 — Fondations"] --> B["EPIC 02 — Identité"]
  A --> C["EPIC 03 — Organisations et actifs"]
  B --> C
  A --> D["EPIC 04 — Connecteurs"]
  C --> D
  D --> E["EPIC 05 — Ingestion"]
  E --> F["EPIC 06 — Détection et corrélation"]
  F --> G["EPIC 07 — Incidents"]
  G --> H["EPIC 08 — Réponse"]
  B --> H
  G --> I["EPIC 09 — Interface SOC"]
  H --> I
  I --> J["EPIC 10 — Audit et reporting"]
  A --> K["EPIC 11 — Tests et déploiement"]
  E --> K
  H --> K
```

Les tests, la sécurité et la documentation accompagnent chaque Epic ;
l'EPIC-11 regroupe les validations transversales et la préparation de la
mise en production.

## 5. Phases de réalisation

  -----------------------------------------------------------------------
  Phase                   Contenu                 Livrable
  ----------------------- ----------------------- -----------------------
  0\. Cadrage             Version Wazuh, schémas, Socle validé
                          environnements,         
                          conventions             

  1\. Infrastructure      EPIC-01 et début        Backend et services
                          EPIC-02                 démarrables

  2\. Accès et inventaire EPIC-02 et EPIC-03      Utilisateurs,
                                                  organisations, actifs

  3\. Première            EPIC-04, connecteur     Alertes récupérées
  intégration             Wazuh                   

  4\. Pipeline            EPIC-05                 Événements
                                                  normalisés/indexés

  5\. Intelligence        EPIC-06 et EPIC-07      Détections,
                                                  corrélations, incidents

  6\. Réponse contrôlée   EPIC-08                 Approbation et action
                                                  vérifiée

  7\. Interface           EPIC-09                 Tableau de bord SOC

  8\. Finalisation        EPIC-10 et EPIC-11      Audit, reporting,
                                                  déploiement
  -----------------------------------------------------------------------

## 6. Définition du MVP

Le MVP doit démontrer : alerte Wazuh → collecte →
normalisation/indexation → détection/corrélation → incident →
proposition de politique → approbation/refus → exécution contrôlée →
vérification et audit.

Le MVP est validé lorsque ce parcours fonctionne de bout en bout, y
compris les scénarios d'échec, de reprise et de refus d'approbation.

## 7. Definition of Done

-   [ ] Besoin fonctionnel satisfait.
-   [ ] Critères d'acceptation vérifiés.
-   [ ] Tests unitaires et d'intégration réussis.
-   [ ] Permissions et isolation vérifiées.
-   [ ] Erreurs correctement gérées.
-   [ ] Logs disponibles.
-   [ ] Documentation mise à jour.
-   [ ] Code relu et validé.
-   [ ] Migrations testées si nécessaire.
-   [ ] Aucun secret exposé.

## 8. Dix premières tâches

  ------------------------------------------------------------------------
                         Ordre Tâche                 Résultat
  ---------------------------- --------------------- ---------------------
                             1 T-01 --- Initialiser  Dépôt disponible
                               Git                   

                             2 T-02 --- Initialiser  API fonctionnelle
                               FastAPI               

                             3 T-03 --- Organiser    Architecture backend
                               les modules           

                             4 T-08 --- Configurer   Environnement
                               Docker Compose        démarrable

                             5 T-09 --- Configurer   Base accessible
                               PostgreSQL            

                             6 T-10 --- Configurer   Messagerie
                               RabbitMQ              opérationnelle

                             7 T-40 --- Figer        Cible d'intégration
                               version Wazuh         définie

                             8 T-41 --- Configurer   Authentification
                               accès API Wazuh       fonctionnelle

                             9 T-42 --- Développer   Communication
                               client Wazuh          possible

                            10 T-43 --- Récupérer    Premières données
                               les alertes           disponibles
  ------------------------------------------------------------------------

Premier jalon technique : récupérer une alerte Wazuh depuis FastAPI, la
convertir en JSON normalisé et l'indexer. Cela valide la chaîne
d'intégration avant de construire les autres modules.

## 9. Organisation GitHub Projects

Colonnes : Product Backlog, Ready, In Progress, Code Review, Testing,
Done.

Champs recommandés : identifiant, Epic, User Story, description,
priorité, estimation, responsable, dépendances, critères d'acceptation
et statut.
