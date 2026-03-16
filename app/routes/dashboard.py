from flask import Blueprint, jsonify
from ..models.client import Client
from ..services.churn_service import calculate_churn_risk
from ..services.revenue_service import estimate_recovery_value

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/clients/at-risk")
def at_risk_clients():
    clients = Client.query.all()
    result = []

    for client in clients:
        risk = calculate_churn_risk(client)
        if risk in ["High", "Medium", "Low"]:
            result.append({
                "name": client.name,
                "risk": risk,
                "recovery_value": estimate_recovery_value(client)
            })

    return jsonify(result)