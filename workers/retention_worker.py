from app.database import SessionLocal
from app.models.client import Client
from app.services.retention_service import run_retention


def run():

    db = SessionLocal()

    clients = db.query(Client).all()

    for client in clients:

        action = run_retention(client)

        if action:
            print(action)


if __name__ == "__main__":
    run()