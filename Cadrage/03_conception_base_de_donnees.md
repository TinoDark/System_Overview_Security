# Document 3 --- Conception de la base de données

## Plateforme unifiée de cybersécurité

**Version :** 1.0 --- **Statut :** modèle initial à valider

## 1. Principes de persistance

-   **PostgreSQL :** organisations, utilisateurs, actifs, intégrations,
    incidents, politiques, approbations, réponses et audit.
-   **Wazuh Indexer/OpenSearch :** événements volumineux, recherches
    temporelles et documents d'alertes.
-   **Redis :** cache et données temporaires.
-   **RabbitMQ :** transport des messages, pas stockage métier
    permanent.

## 2. Principes de modélisation

-   UUID pour les identifiants internes.
-   Horodatages `TIMESTAMPTZ` en UTC.
-   `organization_id` sur les entités métier d'une organisation.
-   Clés étrangères et contraintes d'intégrité.
-   Secrets référencés dans un coffre ou chiffrés ; jamais en clair.
-   Provenance des événements conservée.
-   Idempotence des traitements et réponses.
-   Audit append-only au niveau applicatif.
-   Rétention définie par catégorie de données.

## 3. Modèle conceptuel (MCD)

``` mermaid
erDiagram
  ORGANIZATION ||--o{ USER_ORGANIZATION : associe
  USER ||--o{ USER_ORGANIZATION : appartient
  ORGANIZATION ||--o{ ASSET : possede
  ORGANIZATION ||--o{ INTEGRATION : configure
  ORGANIZATION ||--o{ INCIDENT : suit
  ORGANIZATION ||--o{ SECURITY_POLICY : definit
  ORGANIZATION ||--o{ AUDIT_LOG : produit
  INCIDENT ||--o{ INCIDENT_EVENT : contient
  INCIDENT ||--o{ APPROVAL : demande
  INCIDENT ||--o{ RESPONSE_ACTION : declenche
  SECURITY_POLICY ||--o{ RESPONSE_ACTION : autorise
  USER ||--o{ APPROVAL : decide
```

Les événements volumineux sont principalement conservés dans l'index de
recherche. PostgreSQL peut stocker leurs références et métadonnées
utiles au workflow.

## 4. Modèle logique des tables

### `organizations`

  Champ        Type           Règle
  ------------ -------------- ------------------
  id           UUID           PK
  name         VARCHAR(200)   NOT NULL
  slug         VARCHAR(100)   UNIQUE
  status       VARCHAR(30)    active/suspended
  created_at   TIMESTAMPTZ    NOT NULL
  updated_at   TIMESTAMPTZ    NOT NULL

### `users`

  Champ          Type           Règle
  -------------- -------------- -----------------
  id             UUID           PK
  oidc_issuer    TEXT           NOT NULL
  oidc_subject   TEXT           NOT NULL
  email          VARCHAR(320)   nullable
  display_name   VARCHAR(200)   nullable
  status         VARCHAR(30)    active/disabled
  created_at     TIMESTAMPTZ    NOT NULL

Contrainte : `UNIQUE(oidc_issuer, oidc_subject)`. Ne pas utiliser
l'e-mail comme identifiant fédéré immuable.

### `user_organizations`

  Champ             Type          Règle
  ----------------- ------------- ----------
  organization_id   UUID          FK
  user_id           UUID          FK
  role_id           UUID          FK
  created_at        TIMESTAMPTZ   NOT NULL

Clé primaire composite : `(organization_id, user_id)`.

### `assets`

  Champ                     Type           Règle
  ------------------------- -------------- ----------
  id                        UUID           PK
  organization_id           UUID           FK
  external_id               VARCHAR(255)   nullable
  name                      VARCHAR(255)   NOT NULL
  asset_type                VARCHAR(50)    NOT NULL
  hostname                  VARCHAR(255)   nullable
  ip_address                INET           nullable
  operating_system          VARCHAR(150)   nullable
  status                    VARCHAR(30)    NOT NULL
  last_seen_at              TIMESTAMPTZ    nullable
  created_at / updated_at   TIMESTAMPTZ    NOT NULL

### `integrations`

  Champ                  Type           Règle
  ---------------------- -------------- ------------------------
  id                     UUID           PK
  organization_id        UUID           FK
  name                   VARCHAR(150)   NOT NULL
  integration_type       VARCHAR(50)    NOT NULL
  endpoint               TEXT           nullable
  secret_reference       TEXT           référence coffre
  configuration          JSONB          paramètres non secrets
  status                 VARCHAR(30)    NOT NULL
  last_health_check_at   TIMESTAMPTZ    nullable
  created_at             TIMESTAMPTZ    NOT NULL

### `incidents`

  Champ                     Type           Règle
  ------------------------- -------------- --------------------
  id                        UUID           PK
  organization_id           UUID           FK
  title                     VARCHAR(300)   NOT NULL
  description               TEXT           nullable
  severity                  VARCHAR(30)    NOT NULL
  status                    VARCHAR(30)    NOT NULL
  risk_score                NUMERIC(6,2)   nullable
  assigned_to               UUID           FK users, nullable
  created_at / updated_at   TIMESTAMPTZ    NOT NULL
  closed_at                 TIMESTAMPTZ    nullable
  closure_reason            TEXT           nullable

### `incident_events`

  Champ               Type          Règle
  ------------------- ------------- --------------------------
  id                  UUID          PK
  organization_id     UUID          NOT NULL
  incident_id         UUID          FK
  event_document_id   TEXT          identifiant dans l'index
  relation_type       VARCHAR(50)   NOT NULL
  created_at          TIMESTAMPTZ   NOT NULL

### `security_policies`

  Champ                     Type           Règle
  ------------------------- -------------- ----------
  id                        UUID           PK
  organization_id           UUID           FK
  name                      VARCHAR(200)   NOT NULL
  description               TEXT           nullable
  conditions                JSONB          NOT NULL
  action_type               VARCHAR(100)   NOT NULL
  approval_required         BOOLEAN        NOT NULL
  enabled                   BOOLEAN        NOT NULL
  created_at / updated_at   TIMESTAMPTZ    NOT NULL

Les politiques sont validées par un schéma strict. Ne jamais exécuter du
code arbitraire contenu dans JSON.

### `approvals`

  Champ             Type          Règle
  ----------------- ------------- -----------------------------------
  id                UUID          PK
  organization_id   UUID          NOT NULL
  incident_id       UUID          FK
  requested_by      UUID          FK users
  decided_by        UUID          FK users, nullable
  status            VARCHAR(30)   pending/approved/rejected/expired
  justification     TEXT          nullable
  requested_at      TIMESTAMPTZ   NOT NULL
  decided_at        TIMESTAMPTZ   nullable
  expires_at        TIMESTAMPTZ   NOT NULL

### `response_actions`

  Champ                       Type           Règle
  --------------------------- -------------- ------------------
  id                          UUID           PK
  organization_id             UUID           NOT NULL
  incident_id                 UUID           FK
  policy_id                   UUID           FK
  approval_id                 UUID           FK nullable
  action_type                 VARCHAR(100)   NOT NULL
  parameters                  JSONB          NOT NULL
  idempotency_key             VARCHAR(255)   UNIQUE
  status                      VARCHAR(30)    NOT NULL
  result                      JSONB          résultat expurgé
  created_at                  TIMESTAMPTZ    NOT NULL
  executed_at / verified_at   TIMESTAMPTZ    nullable

### `audit_logs`

  Champ             Type           Règle
  ----------------- -------------- --------------------------------
  id                UUID           PK
  organization_id   UUID           nullable pour actions globales
  actor_user_id     UUID           FK users, nullable système
  action            VARCHAR(150)   NOT NULL
  resource_type     VARCHAR(100)   NOT NULL
  resource_id       TEXT           nullable
  outcome           VARCHAR(30)    NOT NULL
  metadata          JSONB          données non sensibles
  correlation_id    UUID           nullable
  created_at        TIMESTAMPTZ    NOT NULL

## 5. SQL initial

``` sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  oidc_issuer TEXT NOT NULL,
  oidc_subject TEXT NOT NULL,
  email VARCHAR(320),
  display_name VARCHAR(200),
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (oidc_issuer, oidc_subject)
);

CREATE TABLE roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);

CREATE TABLE user_organizations (
  organization_id UUID NOT NULL REFERENCES organizations(id),
  user_id UUID NOT NULL REFERENCES users(id),
  role_id UUID NOT NULL REFERENCES roles(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  external_id VARCHAR(255),
  name VARCHAR(255) NOT NULL,
  asset_type VARCHAR(50) NOT NULL,
  hostname VARCHAR(255),
  ip_address INET,
  operating_system VARCHAR(150),
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  last_seen_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, external_id)
);

CREATE TABLE integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  name VARCHAR(150) NOT NULL,
  integration_type VARCHAR(50) NOT NULL,
  endpoint TEXT,
  secret_reference TEXT,
  configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  last_health_check_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  title VARCHAR(300) NOT NULL,
  description TEXT,
  severity VARCHAR(30) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'new',
  risk_score NUMERIC(6,2),
  assigned_to UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  closure_reason TEXT
);

CREATE TABLE security_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  name VARCHAR(200) NOT NULL,
  description TEXT,
  conditions JSONB NOT NULL,
  action_type VARCHAR(100) NOT NULL,
  approval_required BOOLEAN NOT NULL DEFAULT true,
  enabled BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE approvals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  incident_id UUID NOT NULL REFERENCES incidents(id),
  requested_by UUID NOT NULL REFERENCES users(id),
  decided_by UUID REFERENCES users(id),
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  justification TEXT,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE response_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  incident_id UUID NOT NULL REFERENCES incidents(id),
  policy_id UUID NOT NULL REFERENCES security_policies(id),
  approval_id UUID REFERENCES approvals(id),
  action_type VARCHAR(100) NOT NULL,
  parameters JSONB NOT NULL,
  idempotency_key VARCHAR(255) NOT NULL UNIQUE,
  status VARCHAR(30) NOT NULL DEFAULT 'proposed',
  result JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  executed_at TIMESTAMPTZ,
  verified_at TIMESTAMPTZ
);

CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES organizations(id),
  actor_user_id UUID REFERENCES users(id),
  action VARCHAR(150) NOT NULL,
  resource_type VARCHAR(100) NOT NULL,
  resource_id TEXT,
  outcome VARCHAR(30) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  correlation_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_assets_org_status ON assets (organization_id, status);
CREATE INDEX idx_integrations_org_type ON integrations (organization_id, integration_type);
CREATE INDEX idx_incidents_org_status_created
  ON incidents (organization_id, status, created_at DESC);
CREATE INDEX idx_approvals_org_status ON approvals (organization_id, status);
CREATE INDEX idx_response_actions_org_status
  ON response_actions (organization_id, status);
CREATE INDEX idx_audit_logs_org_created
  ON audit_logs (organization_id, created_at DESC);
```

Ce SQL est un point de départ, pas un schéma prêt pour la production.
Les migrations doivent ajouter contraintes composites garantissant
l'appartenance à la même organisation, règles de suppression,
contraintes de statut, index adaptés et RLS si retenue.

## 6. Isolation multi-organisation

Une colonne `organization_id` ne suffit pas à elle seule.
Recommandations : - Inclure `organization_id` dans les clés uniques et
index utiles. - Utiliser des clés étrangères composites pour garantir
les relations intra-organisation. - Déterminer l'organisation depuis le
contexte authentifié côté serveur. - Envisager PostgreSQL Row-Level
Security comme défense supplémentaire. - Tester les accès croisés entre
organisations.

## 7. Indexation et rétention

Dans Wazuh Indexer/OpenSearch : - Définir index ou data streams selon
catégorie et volumétrie. - Définir mappings explicites pour les champs
filtrés. - Éviter les champs à forte cardinalité inutiles. - Configurer
rétention, archivage, quotas et snapshots. - Tester la restauration.

## 8. Décisions à finaliser

Stockage exact des événements normalisés, mapping Wazuh/actifs, RLS,
durées de rétention, purge, contraintes composites, coffre de secrets,
chiffrement, RPO/RTO et sauvegardes.
