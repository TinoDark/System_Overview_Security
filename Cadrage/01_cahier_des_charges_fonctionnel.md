# Document 1 --- Cahier des charges fonctionnel

## Plateforme unifiée de supervision et de réponse aux incidents de cybersécurité

**Version :** 1.0 --- **Statut :** conception initiale

## 1. Contexte et problématique

Les systèmes d'information sont exposés aux intrusions, logiciels
malveillants, compromissions de comptes, exfiltrations et erreurs de
configuration. Les organisations disposent souvent de plusieurs outils
spécialisés qui produisent des alertes dans des formats différents.

La plateforme vise à centraliser ces événements, les normaliser, les
corréler et faciliter le traitement des incidents. Elle s'appuie sur des
solutions existantes, notamment Wazuh, sans réécrire leurs moteurs.

**Problématique :** comment fournir aux équipes de sécurité une vue
unifiée des événements et incidents, tout en orchestrant des réponses
contrôlées, traçables et adaptées au niveau de risque ?

## 2. Objectifs

### Objectif général

Concevoir et développer une plateforme modulaire de supervision,
détection, corrélation et réponse aux incidents de cybersécurité.

### Objectifs spécifiques

-   Centraliser les événements issus de plusieurs outils.
-   Normaliser les données dans un modèle commun.
-   Corréler les alertes pour identifier les incidents pertinents.
-   Calculer un score de risque explicable.
-   Gérer le cycle de vie des incidents.
-   Proposer et exécuter des actions de réponse avec validation humaine
    selon les politiques.
-   Fournir tableaux de bord, rapports et traces d'audit.
-   Assurer l'isolation des organisations et la protection des données.

## 3. Périmètre fonctionnel

  -----------------------------------------------------------------------
  Code                    Fonctionnalité          Description
  ----------------------- ----------------------- -----------------------
  F01                     Organisations           Créer et administrer
                                                  les espaces
                                                  organisationnels.

  F02                     Identité et accès       Authentifier les
                                                  utilisateurs et
                                                  contrôler leurs
                                                  permissions.

  F03                     Actifs                  Inventorier les
                                                  équipements et
                                                  ressources surveillés.

  F04                     Intégrations            Configurer les outils
                                                  et sources de sécurité.

  F05                     Collecte                Récupérer, valider et
                                                  homogénéiser les
                                                  événements.

  F06                     Détection               Exploiter les alertes
                                                  et corréler les
                                                  événements.

  F07                     Incidents               Créer, assigner, suivre
                                                  et clôturer les
                                                  incidents.

  F08                     Réponse et reporting    Approuver, exécuter et
                                                  vérifier les actions ;
                                                  produire des rapports.
  -----------------------------------------------------------------------

### Outils envisagés

  Outil      Rôle                            Intégration envisagée
  ---------- ------------------------------- ---------------------------------------
  Wazuh      SIEM/XDR                        API Wazuh et Wazuh Indexer
  Suricata   IDS/IPS réseau                  EVE JSON
  Rspamd     Analyse antispam                HTTP/JSON ou Milter selon le MTA
  ClamAV     Antivirus                       Service/daemon et résultats d'analyse
  MISP       Renseignement sur les menaces   API et indicateurs

Le MVP commence par Wazuh. Les autres connecteurs seront ajoutés après
validation du pipeline principal.

### Hors périmètre initial

-   Réécriture des moteurs Wazuh, Suricata, Rspamd ou ClamAV.
-   Remplacement complet d'un SOC humain.
-   Actions destructrices ou irréversibles sans contrôle renforcé.
-   Déploiement massif multi-sites avant validation du prototype.
-   Entraînement d'un modèle d'IA complexe avant constitution de données
    fiables.

## 4. Acteurs et rôles

  -----------------------------------------------------------------------
  Rôle                                Responsabilités
  ----------------------------------- -----------------------------------
  Super administrateur                Gérer les organisations et
                                      paramètres globaux.

  Administrateur sécurité             Gérer intégrations, actifs,
                                      politiques et utilisateurs de son
                                      organisation.

  Analyste SOC                        Examiner les alertes, qualifier et
                                      suivre les incidents.

  Opérateur                           Exécuter les actions de réponse
                                      autorisées.

  Auditeur                            Consulter les journaux et rapports
                                      autorisés.

  Observateur                         Consulter les tableaux de bord sans
                                      modifier les données.
  -----------------------------------------------------------------------

Les permissions sont vérifiées côté serveur. Le masquage d'un bouton
dans l'interface ne constitue pas un contrôle d'accès suffisant.

## 5. Exigences fonctionnelles

  ID     Exigence                                                   Priorité
  ------ ---------------------------------------------------------- ----------
  RF01   Authentifier les utilisateurs via OIDC.                    P0
  RF02   Gérer rôles et permissions.                                P0
  RF03   Isoler les données par organisation.                       P0
  RF04   Gérer les actifs.                                          P0
  RF05   Enregistrer et tester les intégrations.                    P0
  RF06   Collecter les alertes Wazuh.                               P0
  RF07   Normaliser les événements.                                 P0
  RF08   Dédupliquer et rendre les traitements idempotents.         P0
  RF09   Rechercher les événements.                                 P0
  RF10   Exploiter les règles de détection.                         P0
  RF11   Corréler les événements et calculer un score explicable.   P0
  RF12   Créer et suivre les incidents.                             P0
  RF13   Définir des politiques de réponse.                         P0
  RF14   Soumettre les actions sensibles à approbation humaine.     P0
  RF15   Exécuter, vérifier et tracer les actions.                  P0
  RF16   Afficher indicateurs, rapports et audit.                   P1

P0 = indispensable au MVP ; P1 = important pour une version ultérieure ;
P2 = amélioration.

## 6. Exigences non fonctionnelles

### Sécurité

-   Chiffrer les communications sensibles.
-   Externaliser et protéger les secrets.
-   Appliquer les permissions sur chaque opération sensible.
-   Protéger les journaux d'audit.
-   Encadrer les actions de réponse par des garde-fous, l'idempotence et
    une vérification post-exécution.

### Fiabilité et disponibilité

-   Exposer l'état de santé des composants.
-   Prévoir les reprises et files d'échec pour les traitements
    asynchrones.
-   Empêcher qu'une panne de connecteur arrête les autres sources.
-   Tester les sauvegardes et restaurations.

### Performance et évolutivité

Les objectifs de débit, latence, volumétrie, rétention, RPO et RTO
seront fixés après mesure des volumes réels. La conception doit
permettre de faire évoluer indépendamment collecte et traitement.

### Maintenabilité

Architecture modulaire, API OpenAPI, tests automatisés, migrations
versionnées, logs structurés et documentation à jour.

## 7. Règles de gestion

1.  Chaque donnée métier client porte un `organization_id`.
2.  L'utilisateur n'accède qu'aux organisations qui lui sont attribuées.
3.  Les dates sont stockées et échangées en UTC.
4.  Les identifiants internes sont des UUID.
5.  Les événements conservent leur provenance et, si utile, leur contenu
    brut.
6.  La déduplication repose sur une clé stable documentée.
7.  Une action de réponse doit être autorisée par une politique.
8.  Une action nécessitant approbation ne s'exécute pas avant
    approbation valide.
9.  Chaque décision et action sensible est auditée.
10. La clôture d'un incident doit être justifiée.

## 8. Critères de validation du MVP

Le MVP est accepté lorsque, sur un environnement de test : 1. Wazuh
génère une alerte. 2. Le connecteur récupère l'alerte. 3. L'événement
est validé, normalisé et indexé. 4. La détection/corrélation identifie
un cas pertinent. 5. Un incident est créé et consultable. 6. Une
politique propose une action. 7. Un opérateur autorisé approuve ou
refuse l'action. 8. L'action approuvée est exécutée dans un
environnement contrôlé. 9. Le résultat est vérifié et inscrit dans
l'audit.

## 9. Points à confirmer

Version exacte de Wazuh, volumétrie, nombre d'organisations et d'actifs,
rétention, exigences réglementaires, localisation des données,
disponibilité, RPO/RTO et catalogue initial des actions autorisées.
