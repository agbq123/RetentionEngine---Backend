def estimate_recovery_value(client):
    if client.visit_count == 0:
        return 0

    avg_value = client.lifetime_value / client.visit_count
    return avg_value * 6  # assume 6 future visits recovered