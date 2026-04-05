from ..services.square_sync_service import sync_square_data

@integrations_bp.route("/integrations/square/sync")
def square_sync():
    user = User.query.first()
    sync_square_data(user)
    return {"status": "synced"}