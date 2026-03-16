def estimate_recovery_value(client):
    if client.visit_count < 2:
        return 0

    avg_value = client.lifetime_value / client.visit_count

    weeks_active = (client.last_visit - client.first_visit).days / 7

    visits_per_year = client.visit_count / (weeks_active / 52)

    return round(avg_value * visits_per_year, 2)