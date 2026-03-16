from datetime import datetime

def expected_visit_interval(client):
    """
    Estimate customer's typical visit interval in weeks
    """

    if client.visit_count < 2:
        return 4  # default assumption

    weeks_active = (client.last_visit - client.first_visit).days / 7

    if weeks_active <= 0:
        return 4

    return weeks_active / client.visit_count

def calculate_churn_risk(client):

    interval = expected_visit_interval(client)

    weeks_since = (datetime.utcnow() - client.last_visit).days / 7

    ratio = weeks_since / interval

    if ratio > 2:
        return "High"

    elif ratio > 1.5:
        return "Medium"

    else:
        return "Low"