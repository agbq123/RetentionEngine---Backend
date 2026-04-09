from datetime import datetime
from ..models.appointment import Appointment

def _get_client_appointments(client_id):
    return (
        Appointment.query
        .filter(Appointment.client_id == client_id)
        .order_by(Appointment.appointment_date.asc())
        .all()
    )
