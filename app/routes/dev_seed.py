from flask import Blueprint
from datetime import datetime, timedelta
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

    for i in range(20):
        client = Client(
            user_id=user.id,
            name=f"Client {i}",
            last_visit=datetime.utcnow() - timedelta(weeks=i),
            lifetime_value=200 + i*20,
            visit_count=5 + i
        )
        db.session.add(client)

    db.session.commit()

    return {"status": "seeded"}