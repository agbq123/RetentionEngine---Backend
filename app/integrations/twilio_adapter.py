from flask import current_app
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


def _get_twilio_client():
    account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
    auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        raise ValueError("Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN")

    return Client(account_sid, auth_token)


def send_sms(to_number: str, body: str):
    from_number = current_app.config.get("TWILIO_PHONE")
    status_callback_url = current_app.config.get("TWILIO_STATUS_CALLBACK_URL")

    if not from_number:
        raise ValueError("Missing TWILIO_PHONE")

    if not to_number:
        raise ValueError("Missing destination phone number")

    if not body or not str(body).strip():
        raise ValueError("Message body cannot be empty")

    client = _get_twilio_client()

    create_kwargs = {
        "body": str(body).strip(),
        "from_": from_number,
        "to": str(to_number).strip(),
    }

    if status_callback_url:
        create_kwargs["status_callback"] = status_callback_url

    try:
        message = client.messages.create(**create_kwargs)
    except TwilioRestException as exc:
        raise ValueError(f"Twilio error: {exc.msg}") from exc

    return {
        "sid": message.sid,
        "status": message.status,
        "to": message.to,
        "from": message.from_,
        "body": message.body,
    }