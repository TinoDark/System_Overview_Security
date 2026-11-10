from app.db.session import SessionLocal
from app.services import fixture_seed

if __name__ == "__main__":
    with SessionLocal() as session:
        fixture_seed(session)
    print("Synthetic two-tenant demo fixtures are ready.")
