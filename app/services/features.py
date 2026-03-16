from datetime import datetime


def client_features(client):

    return {
        "visit_count": client.visit_count,
        "days_since_last": (datetime.utcnow() - client.last_visit).days,
        "lifetime_value": client.lifetime_value
    }