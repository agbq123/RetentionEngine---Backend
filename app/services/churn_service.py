from datetime import datetime
from ..models.appointment import Appointment

def _get_client_appointments(client_id):
    return (
        Appointment.query
        .filter(Appointment.client_id == client_id)
        .order_by(Appointment.appointment_date.asc())
        .all()
    )

def _split_past_future(appointments, now):
    past = []
    future = []

    for appt in appointments:
        if appt.appointment_date <= now:
            past.append(appt)
        else:
            future.append(appt)

    return past, future