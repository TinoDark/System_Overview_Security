# Prototype SOC/SIEM

Prototype de plateforme SOC/SIEM multi-tenant : collecte de fixtures de sécurité, normalisation, détection, corrélation, incidents, approbation, réponse simulée et audit.

## Périmètre et sécurité

- Wazuh, Rspamd, ClamAV et MISP sont simulés. Aucune connexion ni installation de ces outils n'est utilisée.
- Les réponses sont simulées et ne modifient aucun système.
- L'authentification de démonstration n'est pas OIDC et ne doit être activée qu'en développement.
- PostgreSQL est la base de données du prototype. RabbitMQ, Redis, Keycloak et OpenSearch ne sont pas requis ni configurés.
- Ne pas exposer ce prototype à Internet ni l'utiliser avec des données ou identifiants réels.

## Prérequis

- Python 3.12
- Node.js 20 ou ultérieur et npm
- Docker Compose pour PostgreSQL local (ou une instance PostgreSQL 16 accessible)

## Démarrage local

1. Créer `.env` depuis `.env.example` pour Docker Compose et définir un mot de passe local PostgreSQL.
2. Démarrer PostgreSQL : `docker compose up -d postgres`.
3. Créer `backend\.env` depuis `backend\.env.example` et y configurer `DATABASE_URL` avec les mêmes identifiants PostgreSQL. Créer ensuite un environnement virtuel et installer le backend :

   ```powershell
   py -3.12 -m venv backend\.venv
   backend\.venv\Scripts\Activate.ps1
   python -m pip install -e "backend[dev]"
   ```

4. Depuis `backend\`, appliquer les migrations puis initialiser les données de démonstration :

   ```powershell
   alembic upgrade head
   python seed_demo.py
   uvicorn app.main:app --reload
   ```

5. Dans un autre terminal :

   ```powershell
   Set-Location frontend
   npm install
   npm run dev
   ```

6. Ouvrir `http://localhost:3000`. L'API et son OpenAPI sont disponibles sur `http://localhost:8000` et `http://localhost:8000/docs`.

Les utilisateurs de démonstration et les commandes de collecte sont documentés dans `backend/README.md` et l'écran de connexion. Toutes les valeurs de démonstration sont synthétiques.

## Vérifications

Depuis `backend\` : `pytest` et `ruff check app tests migrations`

Depuis `frontend\` : `npm run lint`, `npm run typecheck`, `npm test` et `npm run build`.
`npm audit` vérifie les dépendances.

Le parcours d'acceptation doit vérifier les deux tenants, la collecte répétée sans doublons, l'incident, la séparation demandeur/approbateur, le kill switch et l'audit.

## Documents du projet

- `.github/copilot-instructions.md` : règles de travail des agents.
- `Cadrage/` : besoins fonctionnels et conception initiale.
- `docs/engineering-log.md` : journal officiel des travaux et validations.
- `docs/architecture-decisions.md` : décisions d'architecture et contrats MVP.
