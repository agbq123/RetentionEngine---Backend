from datetime import datetime, timezone
from flask import Blueprint, jsonify
from ..services.churn_service import compute_client_churn
from ..models.client import Client
from ..models.user import User

api_bp = Blueprint("api", __name__)


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _days_since(dt):
    if not dt:
        return None
    now = _utc_now()
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    delta = now - dt
    return max(delta.days, 0)


def _months_between(start_dt, end_dt):
    if not start_dt or not end_dt:
        return 1.0

    if start_dt.tzinfo is not None:
        start_dt = start_dt.astimezone(timezone.utc).replace(tzinfo=None)
    if end_dt.tzinfo is not None:
        end_dt = end_dt.astimezone(timezone.utc).replace(tzinfo=None)

    days = max((end_dt - start_dt).days, 1)
    return max(days / 30.0, 1.0)


def _safe_float(value, default=0.0):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def _avg_ticket(client):
    visits = max(_safe_int(client.visit_count), 1)
    return _safe_float(client.lifetime_value) / visits


def _visits_per_month(client):
    visit_count = _safe_int(client.visit_count)

    if visit_count <= 0:
        return 0.0

    if client.first_visit and client.last_visit:
        months_active = _months_between(client.first_visit, client.last_visit)
    else:
        months_active = 1.0

    return round(visit_count / months_active, 1)


def _risk_level(client):
    days = _days_since(client.last_visit)

    if days is None:
        return "high"
    if days >= 45:
        return "high"
    if days >= 21:
        return "medium"
    return "low"


def _recovery_value(client):
    avg_ticket = _avg_ticket(client)
    risk = _risk_level(client)

    if risk == "high":
        multiplier = 2.0
    elif risk == "medium":
        multiplier = 1.0
    else:
        multiplier = 0.5

    return round(avg_ticket * multiplier, 2)


def _recommendation(risk):
    if risk == "high":
        return "Send a strong win-back SMS with a clear call to book this week."
    if risk == "medium":
        return "Send a friendly reminder SMS and highlight convenience or availability."
    return "Keep warm with a light-touch check-in or loyalty-style message."


def _serialize_client(client):
    risk = _risk_level(client)
    last_visit_days_ago = _days_since(client.last_visit)
    visits_per_month = _visits_per_month(client)
    recovery_value = _recovery_value(client)

    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "email": client.email,
        "risk": risk,
        "recommendation": _recommendation(risk),
        "lastVisitDaysAgo": last_visit_days_ago if last_visit_days_ago is not None else 999,
        "visitsPerMonth": visits_per_month,
        "recoveryValue": recovery_value,
        "visitCount": _safe_int(client.visit_count),
        "lifetimeValue": _safe_float(client.lifetime_value),
        "firstVisit": client.first_visit.isoformat() if client.first_visit else None,
        "lastVisit": client.last_visit.isoformat() if client.last_visit else None,
    }


@api_bp.route("/api/clients", methods=["GET"])
def get_clients():
    user = User.query.first()
    if not user:
        return jsonify({"clients": []})

    clients = Client.query.filter_by(user_id=user.id).all()
    serialized = [_serialize_client(client) for client in clients]
    serialized.sort(key=lambda c: (-c["recoveryValue"], -c["lastVisitDaysAgo"]))

    return jsonify({"clients": serialized})


@api_bp.route("/api/clients/top-opportunities", methods=["GET"])
def get_top_opportunities():
    user = User.query.first()
    if not user:
        return jsonify({"clients": []})

    clients = Client.query.filter_by(user_id=user.id).all()
    serialized = [_serialize_client(client) for client in clients]
    serialized.sort(key=lambda c: (-c["recoveryValue"], -c["lastVisitDaysAgo"]))

    return jsonify({"clients": serialized[:5]})


@api_bp.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    user = User.query.first()
    if not user:
        return jsonify(
            {
                "totalClients": 0,
                "highRiskCount": 0,
                "atRiskClientCount": 0,
                "revenueAtRisk": 0,
            }
        )

    clients = Client.query.filter_by(user_id=user.id).all()
    serialized = [_serialize_client(client) for client in clients]

    total_clients = len(serialized)
    high_risk_count = sum(1 for c in serialized if c["risk"] == "high")
    at_risk_client_count = sum(1 for c in serialized if c["risk"] in {"high", "medium"})
    revenue_at_risk = round(
        sum(c["recoveryValue"] for c in serialized if c["risk"] in {"high", "medium"}),
        2,
    )

    return jsonify(
        {
            "totalClients": total_clients,
            "highRiskCount": high_risk_count,
            "atRiskClientCount": at_risk_client_count,
            "revenueAtRisk": revenue_at_risk,
        }
    )