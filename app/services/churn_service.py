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

def _compute_lateness(last_visit, cadence_days, now):
    days_since = (now - last_visit).days
    expected_next = last_visit + timedelta(days=cadence_days)
    days_late = max((now - expected_next).days, 0)

    ratio = days_since / max(cadence_days, 1)

    return days_since, expected_next, days_late, ratio

def _compute_risk_score(ratio):
    if ratio < 0.85:
        return 10
    elif ratio < 1.05:
        return 20
    elif ratio < 1.25:
        return 35
    elif ratio < 1.5:
        return 50
    elif ratio < 2.0:
        return 70
    else:
        return 85
    
def _apply_adjustments(score, has_upcoming, visit_count, avg_ticket):
    if has_upcoming:
        return max(score - 25, 0)

    if visit_count >= 5:
        score += 5

    if avg_ticket > 80:  # tweakable
        score += 5

    return min(score, 100)