from datetime import datetime, timedelta
from urllib.parse import urlencode
import secrets

from flask import Blueprint, current_app, jsonify, redirect, request

from ..database import db
from ..integrations.square_adapter import exchange_code_for_token, get_locations
from ..models.integration_account import IntegrationAccount
from ..models.user import User
from ..services.square_sync_service import sync_square_data

integrations_bp = Blueprint("integrations", __name__)


@integrations_bp.route("/integrations/square/connect/<int:user_id>")
def square_connect(user_id):
    state = secrets.token_urlsafe(24)

    base = (
        "https://connect.squareupsandbox.com"
        if current_app.config.get("SQUARE_ENV") == "sandbox"
        else "https://connect.squareup.com"
    )

    params = {
        "client_id": current_app.config["SQUARE_APP_ID"],
        "scope": "CUSTOMERS_READ APPOINTMENTS_READ MERCHANT_PROFILE_READ",
        "session": "false",
        "state": state,
        "redirect_uri": current_app.config["SQUARE_REDIRECT_URI"],
    }

    return redirect(f"{base}/oauth2/authorize?{urlencode(params)}")


@integrations_bp.route("/integrations/square/callback")
def square_callback():
    code = request.args.get("code")
    merchant_id = request.args.get("merchant_id")
    error = request.args.get("error")

    if error:
        return jsonify({"error": error}), 400

    if not code:
        return jsonify({"error": "Missing Square authorization code"}), 400

    token_data = exchange_code_for_token(code)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")

    expires_at = None
    if token_data.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(
                token_data["expires_at"].replace("Z", "+00:00")
            )
        except Exception:
            expires_at = datetime.utcnow() + timedelta(days=30)

    user = User.query.first()
    if not user:
        user = User(
            business_name="Square Test Shop",
            email="test@example.com",
            booking_provider="square",
        )
        db.session.add(user)
        db.session.commit()

    locations = get_locations(access_token)
    primary_location_id = locations[0]["id"] if locations else None

    account = IntegrationAccount.query.filter_by(
        user_id=user.id,
        provider="square",
    ).first()

    if not account:
        account = IntegrationAccount(
            user_id=user.id,
            provider="square",
            merchant_id=merchant_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            location_id=primary_location_id,
        )
        db.session.add(account)
    else:
        account.merchant_id = merchant_id
        account.access_token = access_token
        account.refresh_token = refresh_token
        account.expires_at = expires_at
        account.location_id = primary_location_id

    db.session.commit()

    return jsonify(
        {
            "status": "square_connected",
            "merchant_id": merchant_id,
            "location_id": primary_location_id,
        }
    )


@integrations_bp.route("/integrations/square/setup-test")
def setup_square_test():
    user = User.query.first()

    if not user:
        user = User(
            business_name="Eric Barber Sandbox",
            email="test@example.com",
            booking_provider="square",
        )
        db.session.add(user)
        db.session.commit()

    account = IntegrationAccount.query.filter_by(
        user_id=user.id,
        provider="square",
    ).first()

    if not account:
        access_token = current_app.config.get("SQUARE_ACCESS_TOKEN")
        location_id = current_app.config.get("SQUARE_LOCATION_ID")

        if not access_token or not location_id:
            return jsonify(
                {"error": "Missing SQUARE_ACCESS_TOKEN or SQUARE_LOCATION_ID in .env"}
            ), 400

        account = IntegrationAccount(
            user_id=user.id,
            provider="square",
            merchant_id="sandbox-test",
            access_token=access_token,
            refresh_token=None,
            expires_at=None,
            location_id=location_id,
        )
        db.session.add(account)
        db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "user_id": user.id,
            "provider": "square",
            "location_id": account.location_id,
        }
    )


@integrations_bp.route("/integrations/square/sync")
def square_sync():
    user = User.query.first()

    if not user:
        return jsonify({"error": "No user found. Run /integrations/square/setup-test first."}), 400

    sync_result = sync_square_data(user)

    return jsonify(
        {
            "status": "synced",
            "counts": sync_result,
        }
    )