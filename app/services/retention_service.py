from .churn_service import calculate_churn_risk
from .messaging_service import generate_winback_message, send_sms


def run_retention(client):

    risk = calculate_churn_risk(client)

    if risk == "High":

        message = generate_winback_message(client)

        send_sms(client.phone, message)

        return {
            "client": client.name,
            "risk": risk,
            "action": "sms_sent"
        }

    return None