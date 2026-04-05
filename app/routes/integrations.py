import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import Blueprint, current_app, redirect, request, jsonify

from ..database import db
from ..models.user import User
from ..models.integration_account import IntegrationAccount
from ..services.square_sync_service import sync_square_data
from ..integrations import square_adapter


integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("/integrations/square/connect/<int:user_id>")
def square_connect(user_id):
    state = secrets.token_urlsafe(24)

    base = "https://connect.squareupsandbox.com" if current_app.config.get("SQUARE_ENV") == "sandbox" else "https://connect.squareup.com"

    params = {
        "client_id": current_app.config.get("SQUARE_APP_ID"),
        "scope": "CUSTOMERS_READ APPOINTMENTS_READ ORDERS_READ ITEMS_READ MERCHANT_PROFILE_READ",
        "session": "false",
        "state": state,
        "redirect_uri": current_app.config.get("SQUARE_REDIRECT_URI"),
    }

    return redirect(f"{base}/oauth2/authorize?{urlencode(params)}")


@integrations_bp.route("/integrations/square/callback")
def square_callback():
    code = request.args.get("code")
    merchant_id = request.args.get("merchant_id")
    error = request.args.get("error")

    if error:
        return jsonify({"error": error}), 400

    token_data = square_adapter.exchange_code_for_token(code)

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_at", 0))

    user = User.query.first()
    if not user:
        return jsonify({"error": "No local user found"}), 400

    locations = square_adapter.get_locations(access_token)
    primary_location = locations[0]["id"] if locations else None

    account = IntegrationAccount.query.filter_by(
        user_id=user.id,
        provider="square"
    ).first()

    if not account:
        account = IntegrationAccount(
            user_id=user.id,
            provider="square",
            merchant_id=merchant_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            location_id=primary_location,
        )
        db.session.add(account)
    else:
        account.merchant_id = merchant_id
        account.access_token = access_token
        account.refresh_token = refresh_token
        account.expires_at = expires_at
        account.location_id = primary_location

    db.session.commit()

    return jsonify({"status": "square_connected", "location_id": primary_location})


@integrations_bp.route("/integrations/square/sync")
def square_sync():
    user = User.query.first()
    sync_square_data(user)
    return {"status": "synced"}