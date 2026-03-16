from app import create_app
from app.models.client import Client
from app.services.retention_service import run_retention


def run():
    app = create_app()

    with app.app_context():
        clients = Client.query.all()

        for client in clients:
            action = run_retention(client)

            if action:
                print(action)


if __name__ == "__main__":
    run()