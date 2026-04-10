from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify, request

from ..integrations.resend_adapter import send_email
from ..integrations.twilio_adapter import send_sms
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


def _recommendation_from_churn(churn):
    if churn["hasUpcomingAppointment"]:
        return "Client already has an upcoming booking — no outreach needed."

    if churn["risk"] == "high":
        return "Send a strong win-back message this week."

    if churn["risk"] == "medium":
        return "Send a reminder highlighting availability."

    return "Light-touch engagement."


def _serialize_client(client):
    churn = compute_client_churn(client)

    return {
        "id": client.id,
        "name": client.name,
        "phone": client.phone,
        "email": client.email,
        **churn,
        "recommendation": _recommendation_from_churn(churn),
    }


def _default_sms_message(client):
    churn = compute_client_churn(client)
    first_name = (client.name or "there").strip().split()[0]

    if churn["hasUpcomingAppointment"]:
        return f"Hey {first_name}, you're already booked in soon. Looking forward to seeing you."

    if churn["risk"] == "high":
        return (
            f"Hey {first_name}, it's been a little while since your last cut. "
            f"We'd love to get you back in the chair soon—want to book this week?"
        )

    if churn["risk"] == "medium":
        return (
            f"Hey {first_name}, just checking in—if you need your next cut, "
            f"we've got openings coming up."
        )

    return (
        f"Hey {first_name}, hope you're doing well. "
        f"Whenever you're ready for your next appointment, we'd love to have you back."
    )


def _default_email_subject(client):
    churn = compute_client_churn(client)
    first_name = (client.name or "there").strip().split()[0]

    if churn["hasUpcomingAppointment"]:
        return f"{first_name}, you're already booked in"

    if churn["risk"] == "high":
        return f"{first_name}, ready for your next appointment?"

    if churn["risk"] == "medium":
        return f"{first_name}, openings are available this week"

    return f"{first_name}, we'd love to see you again"


def _default_email_html(client):
    churn = compute_client_churn(client)
    first_name = (client.name or "there").strip().split()[0]

    if churn["hasUpcomingAppointment"]:
        return f"""
        <p>Hi {first_name},</p>
        <p>You already have an upcoming appointment booked. We’re looking forward to seeing you soon.</p>
        <p>Thanks!</p>
        """

    if churn["risk"] == "high":
        return f"""
        <p>Hi {first_name},</p>
        <p>It’s been a little while since your last appointment, and we’d love to have you back.</p>
        <p>If you’re ready for your next cut, reply to this email or book your next visit soon.</p>
        <p>Hope to see you again soon.</p>
        """

    if churn["risk"] == "medium":
        return f"""
        <p>Hi {first_name},</p>
        <p>Just checking in — if you need your next appointment, we have openings coming up.</p>
        <p>We’d love to have you back.</p>
        """

    return f"""
    <p>Hi {first_name},</p>
    <p>Hope you’re doing well. Whenever you’re ready for your next appointment, we’d love to see you again.</p>
    """


def _default_email_text(client):
    churn = compute_client_churn(client)
    first_name = (client.name or "there").strip().split()[0]

    if churn["hasUpcomingAppointment"]:
        return f"Hi {first_name}, you already have an upcoming appointment booked. We’re looking forward to seeing you soon."

    if churn["risk"] == "high":
        return (
            f"Hi {first_name}, it’s been a little while since your last appointment. "
            f"We’d love to have you back. If you’re ready for your next cut, reply to this email or book your next visit soon."
        )

    if churn["risk"] == "medium":
        return (
            f"Hi {first_name}, just checking in — if you need your next appointment, "
            f"we have openings coming up. We’d love to have you back."
        )

    return (
        f"Hi {first_name}, hope you’re doing well. "
        f"Whenever you’re ready for your next appointment, we’d love to see you again."
    )


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


@api_bp.route("/api/sms/preview/<int:client_id>", methods=["GET"])
def get_sms_preview(client_id):
    client = Client.query.get(client_id)

    if not client:
        return jsonify({"error": "Client not found"}), 404

    return jsonify(
        {
            "clientId": client.id,
            "clientName": client.name,
            "phone": client.phone,
            "message": _default_sms_message(client),
        }
    )


@api_bp.route("/api/sms/send", methods=["POST"])
def post_sms_send():
    data = request.get_json() or {}

    client_id = data.get("clientId")
    body = (data.get("body") or "").strip()

    if not client_id:
        return jsonify({"error": "clientId is required"}), 400

    if not body:
        return jsonify({"error": "body is required"}), 400

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    if not client.phone:
        return jsonify({"error": "Client has no phone number"}), 400

    twilio_phone = current_app.config.get("TWILIO_PHONE")
    if twilio_phone and client.phone and client.phone.strip() == str(twilio_phone).strip():
        return jsonify({"error": "Client phone number cannot be the same as the Twilio sender number"}), 400

    try:
        result = send_sms(client.phone, body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Unexpected SMS send failure: {str(exc)}"}), 500

    return jsonify(
        {
            "status": "sent",
            "clientId": client.id,
            "message": result,
        }
    )


@api_bp.route("/api/email/preview/<int:client_id>", methods=["GET"])
def get_email_preview(client_id):
    client = Client.query.get(client_id)

    if not client:
        return jsonify({"error": "Client not found"}), 404

    return jsonify(
        {
            "clientId": client.id,
            "clientName": client.name,
            "email": client.email,
            "subject": _default_email_subject(client),
            "html": _default_email_html(client),
            "text": _default_email_text(client),
        }
    )


@api_bp.route("/api/email/send", methods=["POST"])
def post_email_send():
    data = request.get_json() or {}

    client_id = data.get("clientId")
    subject = (data.get("subject") or "").strip()
    html = (data.get("html") or "").strip()
    text = (data.get("text") or "").strip()

    if not client_id:
        return jsonify({"error": "clientId is required"}), 400

    client = Client.query.get(client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404

    if not client.email:
        return jsonify({"error": "Client has no email"}), 400

    if not subject:
        subject = _default_email_subject(client)

    if not html:
        html = _default_email_html(client)

    if not text:
        text = _default_email_text(client)

    try:
        result = send_email(
            to_email=client.email,
            subject=subject,
            html=html,
            text=text,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Unexpected email send failure: {str(exc)}"}), 500

    return jsonify(
        {
            "status": "sent",
            "clientId": client.id,
            "email": result,
        }
    )


@api_bp.route("/api/twilio/status", methods=["POST"])
def twilio_status_callback():
    message_sid = request.form.get("MessageSid")
    message_status = request.form.get("MessageStatus")
    error_code = request.form.get("ErrorCode")

    return jsonify(
        {
            "ok": True,
            "messageSid": message_sid,
            "messageStatus": message_status,
            "errorCode": error_code,
        }
    ), 200