from datetime import datetime, timedelta
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

def _risk_bucket(score):
    if score >= 60:
        return "high"
    elif score >= 30:
        return "medium"
    return "low"

def _compute_recovery_value(avg_ticket, cadence_days):
    visits_per_year = 365 / max(cadence_days, 1)
    return round(avg_ticket * visits_per_year, 2)

def compute_client_churn(client, now=None):
    now = now or datetime.utcnow()

    appointments = _get_client_appointments(client.id)
    past, future = _split_past_future(appointments, now)

    has_upcoming = len(future) > 0
    next_appt = min([a.appointment_date for a in future], default=None)

    if len(past) == 0:
        return {
            "risk": "low",
        "riskScore": 0,
        "reason": "No past visit history yet",
        "confidence": "none",
        "lastVisitDaysAgo": 0,
        "cadenceDays": 0,
        "expectedNextVisit": None,
        "daysLate": 0,
        "hasUpcomingAppointment": has_upcoming,
        "upcomingAppointmentDate": next_appt.isoformat() if next_appt else None,
        "recoveryValue": 0,  # ✅ FIX
        "visitCount": 0,
        "lifetimeValue": 0,
        "avgTicket": 0,
        "visitsPerMonth": 0,  # ✅ FIX
        "firstVisit": None,
        "lastVisit": None,
        }

    first = past[0].appointment_date
    last = past[-1].appointment_date
    visit_count = len(past)

    lifetime = sum(a.service_price or 0 for a in past)
    avg_ticket = lifetime / visit_count if visit_count else 0

    cadence = _compute_cadence(past)

    days_since, expected_next, days_late, ratio = _compute_lateness(last, cadence, now)

    score = _compute_risk_score(ratio)
    score = _apply_adjustments(score, has_upcoming, visit_count, avg_ticket)

    risk = _risk_bucket(score)

    confidence = (
        "none" if visit_count == 0 else
        "low" if visit_count == 1 else
        "medium" if visit_count <= 3 else
        "high"
    )

    recovery = _compute_recovery_value(avg_ticket, cadence)

    return {
        "risk": risk,
        "riskScore": score,
        "reason": f"Usually visits every {int(cadence)} days and is {int(days_late)} days late",
        "confidence": confidence,
        "lastVisitDaysAgo": days_since,
        "cadenceDays": cadence,
        "expectedNextVisit": expected_next.isoformat() if expected_next else None,
        "daysLate": days_late,
        "hasUpcomingAppointment": has_upcoming,
        "upcomingAppointmentDate": next_appt.isoformat() if next_appt else None,
        "recoveryValue": recovery,
        "visitCount": visit_count,
        "lifetimeValue": round(lifetime, 2),
        "avgTicket": round(avg_ticket, 2),
        "firstVisit": first.isoformat(),
        "lastVisit": last.isoformat(),
    }

