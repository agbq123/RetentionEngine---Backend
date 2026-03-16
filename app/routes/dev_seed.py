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

    user = User(
        business_name="Fade Masters",
        email="owner@test.com",
        booking_provider="square"
    )

    db.session.add(user)
    db.session.commit()

    clients = []

    for i in range(50):

        visit_interval = random.randint(2, 6)  # weeks between visits
        visit_count = random.randint(4, 20)

        first_visit = datetime.utcnow() - timedelta(
            weeks=visit_interval * visit_count + random.randint(0, 12)
        )

        avg_price = random.randint(30, 60)

        visit_date = first_visit

        for _ in range(visit_count):
            visit_date += timedelta(weeks=visit_interval)

        last_visit = visit_date - timedelta(weeks=random.randint(0, visit_interval * 2))

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
        clients.append((client, visit_interval, avg_price))

    db.session.commit()

    for client, interval, price in clients:

        visit_date = client.first_visit

        for _ in range(client.visit_count):

            appointment = Appointment(
                client_id=client.id,
                appointment_date=visit_date,
                service_price=price
            )

            db.session.add(appointment)

            visit_date += timedelta(weeks=interval)

    db.session.commit()

    return {
        "status": "seeded",
        "clients_created": len(clients)
    }