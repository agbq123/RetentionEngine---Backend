from flask import Blueprint
from datetime import datetime, timedelta
import random

from ..database import db
from ..models.user import User
from ..models.client import Client
from ..models.appointment import Appointment

dev_seed_bp = Blueprint("dev_seed", __name__)


@dev_seed_bp.route("/dev/seed")
def seed_data():

    db.drop_all()
    db.create_all()

    # Create demo barber shop
    user = User(
        business_name="Fade Masters",
        email="owner@test.com",
        booking_provider="square"
    )

    db.session.add(user)
    db.session.commit()

    clients = []

    for i in range(50):

        visit_count = random.randint(3, 20)

        first_visit = datetime.utcnow() - timedelta(days=random.randint(200, 700))

        last_visit = datetime.utcnow() - timedelta(days=random.randint(5, 90))

        avg_price = random.randint(30, 60)

        lifetime_value = visit_count * avg_price

        client = Client(
            user_id=user.id,
            name=f"Client {i}",
            first_visit=first_visit,
            last_visit=last_visit,
            visit_count=visit_count,
            lifetime_value=lifetime_value
        )

        db.session.add(client)
        clients.append(client)

    db.session.commit()

    # Create appointment history
    for client in clients:

        visit_interval = random.randint(2, 6)

        visit_date = client.first_visit

        for _ in range(client.visit_count):

            appointment = Appointment(
                client_id=client.id,
                appointment_date=visit_date,
                service_price=random.randint(30, 60)
            )

            db.session.add(appointment)

            visit_date += timedelta(weeks=visit_interval)

            if visit_date > client.last_visit:
                break

    db.session.commit()

    return {
        "status": "seeded",
        "clients_created": len(clients)
    }