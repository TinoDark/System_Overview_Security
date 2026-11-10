# Document 2 --- Architecture logicielle détaillée

## Plateforme unifiée de supervision et de réponse aux incidents

**Version :** 1.0 --- **Statut :** architecture de référence initiale

## 1. Principes d'architecture

-   Architecture modulaire orientée événements.
-   Intégration des moteurs existants plutôt que réécriture.
-   Séparation des données métier et des événements volumineux.
-   Sécurité par défaut : authentification, autorisation, isolation et
    audit.
-   Démarrage par un monolithe modulaire ; extraction de services
    uniquement si nécessaire.
-   Découplage des traitements via RabbitMQ.

## 2. Architecture en couches

  -----------------------------------------------------------------------
  Couche                  Responsabilité          Composants
  ----------------------- ----------------------- -----------------------
  Sources                 Produire événements et  Wazuh, Suricata,
                          alertes                 Rspamd, ClamAV, MISP

  Connecteurs             Communiquer avec les    Clients API, lecteurs
                          sources                 de fichiers,
                                                  adaptateurs

  Ingestion               Recevoir et valider les FastAPI, workers
                          données                 

  Messagerie              Découpler les           RabbitMQ
                          traitements             

  Intelligence            Normaliser, détecter,   Modules Python
                          corréler, scorer        

  Données                 Stocker données métier  PostgreSQL, Wazuh
                          et indexer événements   Indexer

  Réponse                 Appliquer politiques et Policies, Approvals,
                          orchestrer les actions  Response Engine

  Présentation            Exposer les fonctions   API REST, React/Next.js

  Identité                Authentifier les        Keycloak/OIDC
                          utilisateurs            
  -----------------------------------------------------------------------

## 3. Architecture logique

``` mermaid
flowchart TB
  subgraph Sources
    W[Wazuh]
    S[Suricata]
    R[Rspamd]
    C[ClamAV]
    M[MISP]
  end
  subgraph Platform
    CON[Connecteurs]
    API[FastAPI]
    MQ[RabbitMQ]
    WK[Workers]
    N[Normalisation]
    D[Détection et corrélation]
    I[Gestion des incidents]
    P[Politiques et approbations]
    RE[Moteur de réponse]
  end
  subgraph Storage
    PG[(PostgreSQL)]
    IDX[(Wazuh Indexer)]
    RD[(Redis)]
  end
  UI[React / Next.js] --> API
  UI --> KC[Keycloak]
  W --> CON
  S --> CON
  R --> CON
  C --> CON
  M --> CON
  CON --> API
  API --> MQ
  MQ --> WK
  WK --> N
  N --> IDX
  N --> D
  D --> I
  I --> PG
  D --> P
  P --> RE
  RE --> CON
  API --> PG
  API --> IDX
  API --> RD
```

## 4. Stack technique

  -----------------------------------------------------------------------
  Technologie             Utilisation             Justification
  ----------------------- ----------------------- -----------------------
  Python                  Backend et traitement   Écosystème
                                                  d'intégration et
                                                  d'analyse

  FastAPI                 API REST                Typage, Pydantic,
                                                  OpenAPI

  PostgreSQL              Données métier          Transactions et
                                                  intégrité relationnelle

  Wazuh Indexer /         Événements et recherche Indexation et recherche
  OpenSearch                                      volumineuse

  RabbitMQ                Messagerie              Découplage, accusés de
                                                  réception et reprise

  Redis                   Cache et données        Accès rapide, sans
                          temporaires             devenir source de
                                                  vérité

  Keycloak                Identité                OIDC et gestion des
                                                  sessions

  React / Next.js         Interface web           Tableau de bord SOC

  Docker                  Conteneurisation        Environnements
                                                  reproductibles

  Ansible                 Déploiement             Configuration
                                                  reproductible
  -----------------------------------------------------------------------

**Décision :** réutiliser le Wazuh Indexer lorsque cela est pertinent.
Ne pas créer un second cluster OpenSearch sans justification de
capacité, sécurité ou cycle de vie.

## 5. Déploiement de référence

``` mermaid
flowchart TB
  B[Navigateur] --> RP[Reverse proxy TLS]
  RP --> FE[Frontend Next.js]
  RP --> API[FastAPI]
  API --> KC[Keycloak]
  API --> PG[(PostgreSQL)]
  API --> MQ[RabbitMQ]
  API --> IDX[(Wazuh Indexer)]
  API --> RD[(Redis)]
  MQ --> WK[Workers Python]
  WK --> IDX
  WK --> PG
  WK --> WZ[Wazuh API]
```

Séparer les environnements de développement, test et production.
Utiliser des conteneurs non-root lorsque possible. Ne pas exposer
publiquement les ports d'administration.

## 6. Flux principaux

### Collecte Wazuh

1.  Le connecteur s'authentifie auprès de l'API Wazuh.
2.  Il récupère les alertes par fenêtres temporelles ou mécanisme
    adapté.
3.  Il gère pagination, reprise et erreurs temporaires.
4.  Il publie les événements dans RabbitMQ.
5.  Un worker valide et normalise chaque événement.
6.  L'événement est indexé dans Wazuh Indexer.
7.  Les modules de détection et corrélation consomment les événements
    pertinents.

La reprise doit éviter les pertes et limiter les doublons :
curseur/horodatage, fenêtre de recouvrement et déduplication.

### Rspamd

Rspamd s'intègre généralement près du MTA. La plateforme récupère les
résultats et scores via l'interface adaptée à l'installation. Elle ne
remplace ni le MTA ni Rspamd.

### Suricata

Suricata produit notamment des événements EVE JSON. Un lecteur surveille
le flux ou fichier, valide les enregistrements et les envoie au
pipeline. Gérer rotation et offsets.

### Réponse

1.  Une détection satisfait une politique.
2.  Le moteur construit une proposition.
3.  Le niveau de risque détermine l'approbation requise.
4.  Un approbateur autorisé décide.
5.  Le moteur vérifie approbation et autorisation.
6.  L'action est exécutée avec une clé d'idempotence.
7.  Le résultat est vérifié.
8.  Le cycle est audité.

## 7. Arborescence backend proposée

``` text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   └── dependencies.py
│   ├── modules/
│   │   ├── identity/
│   │   ├── organizations/
│   │   ├── assets/
│   │   ├── integrations/
│   │   ├── ingestion/
│   │   ├── events/
│   │   ├── detection/
│   │   ├── correlation/
│   │   ├── incidents/
│   │   ├── policies/
│   │   ├── approvals/
│   │   ├── responses/
│   │   ├── analytics/
│   │   ├── reporting/
│   │   └── audit/
│   ├── connectors/
│   │   ├── base.py
│   │   ├── wazuh/
│   │   ├── suricata/
│   │   ├── rspamd/
│   │   ├── clamav/
│   │   └── misp/
│   ├── workers/
│   └── db/
├── migrations/
├── tests/
├── Dockerfile
└── pyproject.toml
```

Chaque module sépare modèles, schémas, services, dépôts d'accès aux
données et routes. Éviter de placer la logique métier directement dans
les routes.

## 8. Contrat commun des connecteurs

Chaque connecteur expose : - `health_check()` : disponibilité et
authentification. - `collect(cursor, since, limit)` : récupération d'un
lot. - `normalize(raw_event)` : conversion vers le schéma interne. -
`validate(event)` : validation des champs.

Gérer timeouts, erreurs réseau, quotas, pagination, reprises et secrets.
Une source indisponible ne doit pas bloquer les autres.

## 9. Moteur de réponse : garde-fous

-   Catalogue d'actions explicites et limitées.
-   Autorisation vérifiée au moment de l'exécution.
-   Approbation humaine selon la politique.
-   Mode simulation (`dry-run`).
-   Idempotence et protection anti-rejeu.
-   Expiration des demandes.
-   Kill switch global et, si nécessaire, par organisation.
-   Journalisation des décisions et résultats.
-   Vérification post-exécution.
-   Retour arrière lorsque possible.

## 10. Règles de développement

1.  Commencer par un monolithe modulaire.
2.  Définir les contrats entre modules.
3.  Utiliser Pydantic pour valider les entrées/sorties.
4.  Versionner les migrations Alembic.
5.  Écrire tests unitaires, intégration et bout en bout.
6.  Utiliser des logs JSON et identifiants de corrélation.
7.  Verrouiller les dépendances.
8.  Utiliser des images minimales et conteneurs non-root.
9.  Ne jamais committer de secrets.
10. Documenter les décisions d'architecture.

## 11. Points à valider avant production

Version Wazuh et compatibilité API, limites du Wazuh Indexer,
volumétrie, rétention, modèle multi-tenant, SLO, RPO/RTO, certificats,
secrets, restauration et supervision.
