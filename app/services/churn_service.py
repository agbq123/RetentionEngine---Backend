from datetime import datetime

def calculate_churn_risk(client):
    if not client.last_visit:
        return "Unknown"

    weeks_since = (datetime.utcnow() - client.last_visit).days / 7

    if weeks_since > 8:
        return "High"
    elif weeks_since > 6:
        return "Medium"
    else:
        return "Low"