# Document 4 --- Spécification des API et connecteurs

## Plateforme unifiée de cybersécurité

**Version :** 1.0 --- **Statut :** contrat initial à implémenter

## 1. Conventions générales

-   Préfixe : `/api/v1`.
-   Format : JSON.
-   Transport : HTTPS hors environnement local isolé.
-   Dates : ISO 8601 en UTC.
-   Identifiants : UUID.
-   Documentation : OpenAPI/FastAPI.
-   Authentification : OIDC/OAuth2 avec Keycloak.
-   Autorisation : RBAC côté backend.
-   Isolation : requêtes limitées aux organisations autorisées.

## 2. Authentification et autorisation

Le frontend utilise un flux OIDC adapté, de préférence Authorization
Code avec PKCE pour une application navigateur. L'API valide signature,
émetteur, audience, expiration et claims requis.

Ne pas faire confiance à un `organization_id` fourni par le client sans
le comparer au contexte d'autorisation. Les permissions sont contrôlées
sur chaque endpoint sensible.

Codes HTTP : - `401` : authentification absente ou invalide. - `403` :
authentifié mais non autorisé. - `404` : ressource absente ou masquée
selon la politique d'isolation. - `409` : conflit d'état ou doublon
métier. - `422` : données invalides. - `429` : limite de débit
atteinte. - `500` / `503` : erreur interne ou dépendance indisponible.

## 3. Ressources et endpoints

### Organisations

  Méthode   Endpoint                        Fonction
  --------- ------------------------------- -------------------------------------
  GET       `/organizations`                Lister les organisations autorisées
  POST      `/organizations`                Créer une organisation
  GET       `/organizations/{id}`           Consulter une organisation
  PATCH     `/organizations/{id}`           Modifier une organisation
  POST      `/organizations/{id}/suspend`   Suspendre une organisation

### Utilisateurs et rôles

  -----------------------------------------------------------------------------
  Méthode                 Endpoint                      Fonction
  ----------------------- ----------------------------- -----------------------
  GET                     `/users`                      Lister les utilisateurs
                                                        autorisés

  GET                     `/users/{id}`                 Consulter un
                                                        utilisateur

  POST                    `/users/{id}/organizations`   Associer un utilisateur
                                                        à une organisation

  GET                     `/roles`                      Lister les rôles

  PUT                     `/users/{id}/role`            Attribuer un rôle si
                                                        autorisé
  -----------------------------------------------------------------------------

### Actifs

  Méthode   Endpoint                    Fonction
  --------- --------------------------- -------------------
  GET       `/assets`                   Lister et filtrer
  POST      `/assets`                   Créer
  GET       `/assets/{id}`              Consulter
  PATCH     `/assets/{id}`              Modifier
  POST      `/assets/{id}/deactivate`   Désactiver

### Intégrations

  Méthode   Endpoint                       Fonction
  --------- ------------------------------ ------------------------
  GET       `/integrations`                Lister
  POST      `/integrations`                Enregistrer
  GET       `/integrations/{id}`           Consulter sans secrets
  PATCH     `/integrations/{id}`           Modifier
  POST      `/integrations/{id}/test`      Tester la connexion
  POST      `/integrations/{id}/disable`   Désactiver

### Événements

  -----------------------------------------------------------------------
  Méthode                 Endpoint                Fonction
  ----------------------- ----------------------- -----------------------
  GET                     `/events`               Rechercher

  GET                     `/events/{id}`          Consulter

  POST                    `/events/ingest`        Recevoir un événement
                                                  si ingestion HTTP
                                                  activée
  -----------------------------------------------------------------------

Filtres : `from`, `to`, `source`, `asset_id`, `severity`, `event_type`,
`cursor`, `limit`.

### Incidents

  Méthode   Endpoint                     Fonction
  --------- ---------------------------- --------------------------------------
  GET       `/incidents`                 Lister et filtrer
  POST      `/incidents`                 Créer un incident manuel si autorisé
  GET       `/incidents/{id}`            Consulter
  PATCH     `/incidents/{id}`            Modifier les champs autorisés
  POST      `/incidents/{id}/assign`     Assigner
  POST      `/incidents/{id}/status`     Changer le statut
  POST      `/incidents/{id}/comments`   Ajouter un commentaire

### Politiques et réponses

  Méthode   Endpoint                    Fonction
  --------- --------------------------- -----------------------
  GET       `/policies`                 Lister
  POST      `/policies`                 Créer
  PATCH     `/policies/{id}`            Modifier
  POST      `/policies/{id}/enable`     Activer
  POST      `/policies/{id}/disable`    Désactiver
  GET       `/approvals`                Lister les demandes
  POST      `/approvals/{id}/approve`   Approuver
  POST      `/approvals/{id}/reject`    Refuser
  POST      `/responses/{id}/dry-run`   Simuler
  POST      `/responses/{id}/execute`   Exécuter si autorisé
  GET       `/responses/{id}`           Consulter le résultat

### Tableau de bord, audit et santé

  Méthode   Endpoint                Fonction
  --------- ----------------------- ---------------------------------------
  GET       `/dashboard/summary`    KPI de synthèse
  GET       `/dashboard/timeline`   Évolution temporelle
  GET       `/audit-logs`           Rechercher l'audit
  GET       `/health/live`          Vérifier l'application
  GET       `/health/ready`         Vérifier les dépendances essentielles

Les endpoints de santé ne divulguent aucun secret ni détail
d'infrastructure sensible.

## 4. Contrat d'événement normalisé

``` json
{
  "event_id": "9d9f6b8b-85cc-4c31-9e5d-8b70a9f2b60d",
  "organization_id": "a24e5d3d-b5db-4f6f-a3a8-0b91c1c6b8e2",
  "source": {
    "product": "wazuh",
    "integration_id": "f02a5b0f-19b0-4a5d-bd25-3d7e7b8f1b8f"
  },
  "event_type": "authentication_failure",
  "occurred_at": "2026-11-05T10:15:30Z",
  "observed_at": "2026-11-05T10:15:33Z",
  "severity": "high",
  "asset": {
    "asset_id": null,
    "hostname": "server-01",
    "ip_address": "192.0.2.10"
  },
  "actor": {
    "user_id": null,
    "username": "unknown"
  },
  "message": "Multiple authentication failures detected",
  "indicators": [],
  "raw_event": {},
  "schema_version": "1.0"
}
```

Les valeurs sont fictives. Le contrat réel doit préciser champs
obligatoires, énumérations, limites de taille, validation et traitement
des champs inconnus. Le contenu brut peut être stocké séparément si sa
taille ou sa sensibilité le justifie.

## 5. Contrat Python des connecteurs

``` python
from abc import ABC, abstractmethod
from typing import Any

class BaseConnector(ABC):
    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        # Retourne l'état de disponibilité du système source.
        ...

    @abstractmethod
    async def collect(self, cursor: str | None = None,
                      since: str | None = None,
                      limit: int = 500) -> dict[str, Any]:
        # Retourne un lot de données et le curseur suivant.
        ...

    @abstractmethod
    def normalize(self, raw_event: dict[str, Any]) -> dict[str, Any]:
        # Convertit l'événement source vers le schéma commun.
        ...

    @abstractmethod
    def validate(self, event: dict[str, Any]) -> None:
        # Valide l'événement ou lève une erreur explicite.
        ...
```

Préciser également timeouts, exceptions, tailles maximales, pagination,
curseur de reprise et métriques.

## 6. Contrats spécifiques

### Wazuh

Authentification API, récupération paginée des alertes, gestion des
jetons selon la version, fenêtre de recouvrement temporel, déduplication
et tests avec la version réellement déployée.

### Suricata

Lecture EVE JSON, gestion rotation/reprise, normalisation des catégories
et métadonnées réseau, validation des enregistrements.

### Rspamd

Récupération des résultats par l'interface activée, conservation des
scores/symboles/décisions utiles, respect de l'architecture MTA et de la
confidentialité des courriels.

### ClamAV

Intégration via l'interface de service retenue, collecte du résultat,
identifiant de fichier et menace détectée. Ne pas transférer le contenu
des fichiers sans nécessité et autorisation.

### MISP

Récupération d'indicateurs et métadonnées, conservation
provenance/confiance/validité/contexte. Ne pas considérer
automatiquement tout indicateur comme malveillant.

## 7. Formats de réponse API

Succès :

``` json
{
  "data": {
    "id": "9d9f6b8b-85cc-4c31-9e5d-8b70a9f2b60d",
    "status": "created"
  },
  "meta": {
    "request_id": "f4d7b8c2-0b24-4d50-8f7a-3f9d3c7c9e11"
  }
}
```

Erreur :

``` json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted data is invalid",
    "details": []
  },
  "meta": {
    "request_id": "f4d7b8c2-0b24-4d50-8f7a-3f9d3c7c9e11"
  }
}
```

Ne jamais inclure secrets, jetons, chaînes de connexion ou détails
internes exploitables.

## 8. Traitements asynchrones

Les opérations longues (collecte, enrichissement, indexation, rapport,
réponse) sont exécutées en arrière-plan. L'API retourne un identifiant
de tâche ou de ressource et permet d'en consulter l'état.

Prévoir accusés de réception RabbitMQ, tentatives limitées avec backoff,
dead-letter queue, identifiant de corrélation, idempotence et métriques.

## 9. Sécurité des API

-   TLS et validation stricte des jetons.
-   RBAC côté serveur.
-   Limitation de débit.
-   Validation Pydantic et limites de taille.
-   Protection contre injections, SSRF et désérialisation dangereuse.
-   HMAC et anti-rejeu pour webhooks lorsque pertinent.
-   Logs sans secrets ni données personnelles superflues.
-   Autorisation avant chaque réponse.
-   CORS limité aux origines nécessaires.
-   Gestion sécurisée des erreurs et téléchargements.

## 10. Versionnement

Préfixe `/api/v1`, version du schéma d'événement (`schema_version`),
changements incompatibles documentés et tests de contrat pour les
connecteurs.
