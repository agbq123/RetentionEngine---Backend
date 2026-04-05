from datetime import datetime

from ..models.client import Client
from ..models.appointment import Appointment
from ..models.integration_account import IntegrationAccount
from ..database import db
from ..integrations import square_adapter

#CHECK THIS FILE
def sync_square_data(user):
    account = IntegrationAccount.query.filter_by(
        user_id=user.id,
        provider="square"
    ).first()

    if not account:
        raise Exception("Square not connected")

    customers = square_adapter.search_customers(account.access_token)

    customer_map = {}

    for c in customers:
        email = c.get("email_address")
        phone = c.get("phone_number")
        name = " ".join(filter(None, [c.get("given_name"), c.get("family_name")])).strip() or "Unknown"

        client = Client.query.filter_by(user_id=user.id, email=email).first()
        if not client and phone:
            client = Client.query.filter_by(user_id=user.id, phone=phone).first()

        if not client:
            client = Client(
                user_id=user.id,
                name=name,
                email=email,
                phone=phone,
                visit_count=0,
                lifetime_value=0,
            )
            db.session.add(client)
            db.session.flush()

        customer_map[c["id"]] = client

    bookings = square_adapter.list_bookings(account.access_token, account.location_id)

    for b in bookings:
        customer_id = b.get("customer_id")
        start_at = b.get("start_at")

        if not customer_id or not start_at or customer_id not in customer_map:
            continue

        client = customer_map[customer_id]
        dt = datetime.fromisoformat(start_at.replace("Z", "+00:00"))

        exists = Appointment.query.filter_by(
            client_id=client.id,
            appointment_date=dt
        ).first()

        if exists:
            continue

        appt = Appointment(
            client_id=client.id,
            appointment_date=dt,
            service_price=0,
        )
        db.session.add(appt)

        client.visit_count = (client.visit_count or 0) + 1
        client.last_visit = dt if not client.last_visit or dt > client.last_visit else client.last_visit
        client.first_visit = dt if not client.first_visit or dt < client.first_visit else client.first_visit

    db.session.commit()