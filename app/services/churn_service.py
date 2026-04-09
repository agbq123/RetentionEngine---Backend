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

def _compute_cadence(past):
    if len(past) < 2:
        return 28  # default

    gaps = []
    for i in range(1, len(past)):
        delta = (past[i].appointment_date - past[i-1].appointment_date).days
        if delta > 0:
            gaps.append(delta)

    if not gaps:
        return 28

    gaps.sort()
    mid = len(gaps) // 2
    return gaps[mid] if len(gaps) % 2 == 1 else (gaps[mid-1] + gaps[mid]) / 2