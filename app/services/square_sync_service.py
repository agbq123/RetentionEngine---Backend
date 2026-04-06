from datetime import datetime

from ..database import db
from ..integrations.square_adapter import list_bookings, search_customers
from ..models.appointment import Appointment
from ..models.client import Client
from ..models.integration_account import IntegrationAccount


def _parse_square_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def sync_square_data(user):
    account = IntegrationAccount.query.filter_by(
        user_id=user.id,
        provider="square",
    ).first()

    if not account:
        raise Exception("Square not connected")

    customers = search_customers(account.access_token)
    # Uncomment when the Square account is fully set up for Appointments
    bookings = list_bookings(account.access_token, account.location_id)
   # bookings = []

    customer_map = {}
    customers_created = 0
    customers_updated = 0
    appointments_created = 0

    for customer in customers:
        square_customer_id = customer.id
        email = customer.email_address
        phone = customer.phone_number
        name = " ".join(
            part for part in [customer.given_name, customer.family_name] if part
        ).strip() or "Unknown"

        client = None

        if square_customer_id:
            client = Client.query.filter_by(square_customer_id=square_customer_id).first()

        if not client:
            client = Client(
                user_id=user.id,
                square_customer_id=square_customer_id,
                name=name,
                email=email,
                phone=phone,
                visit_count=0,
                lifetime_value=0,
            )
            db.session.add(client)
            db.session.flush()
            customers_created += 1
        else:
            client.square_customer_id = square_customer_id or client.square_customer_id
            client.name = name or client.name
            client.email = email or client.email
            client.phone = phone or client.phone
            customers_updated += 1

        if square_customer_id:
            customer_map[square_customer_id] = client

    for booking in bookings:
        square_booking_id = booking.id
        square_customer_id = booking.customer_id
        start_at = _parse_square_datetime(booking.start_at)
        status = booking.status
        location_id = booking.location_id

        if not square_customer_id or square_customer_id not in customer_map or not start_at:
            continue

        client = customer_map[square_customer_id]

        appointment = None
        if square_booking_id:
            appointment = Appointment.query.filter_by(square_booking_id=square_booking_id).first()

        if not appointment:
            appointment = Appointment(
                client_id=client.id,
                square_booking_id=square_booking_id,
                appointment_date=start_at,
                start_at=start_at,
                status=status,
                location_id=location_id,
                service_name=None,
                service_price=0,
            )
            db.session.add(appointment)
            appointments_created += 1
        else:
            appointment.client_id = client.id
            appointment.appointment_date = start_at
            appointment.start_at = start_at
            appointment.status = status
            appointment.location_id = location_id

    db.session.commit()

    all_clients = Client.query.filter_by(user_id=user.id).all()

    for client in all_clients:
        appointments = (
            Appointment.query.filter_by(client_id=client.id)
            .order_by(Appointment.appointment_date.asc())
            .all()
        )

        if appointments:
            client.first_visit = appointments[0].appointment_date
            client.last_visit = appointments[-1].appointment_date
            client.visit_count = len(appointments)
            client.lifetime_value = sum((appt.service_price or 0) for appt in appointments)
        else:
            client.first_visit = None
            client.last_visit = None
            client.visit_count = 0
            client.lifetime_value = 0

    db.session.commit()

    return {
        "customers_created": customers_created,
        "customers_updated": customers_updated,
        "appointments_created": appointments_created,
    }