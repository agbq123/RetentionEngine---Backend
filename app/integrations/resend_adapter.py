from flask import current_app
import resend


def _configure_resend():
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        raise ValueError("Missing RESEND_API_KEY")
    resend.api_key = api_key


def send_email(to_email: str, subject: str, html: str, text: str | None = None):
    _configure_resend()

    from_email = current_app.config.get("RESEND_FROM_EMAIL")
    reply_to_email = current_app.config.get("RESEND_REPLY_TO_EMAIL")

    if not from_email:
        raise ValueError("Missing RESEND_FROM_EMAIL")
    if not to_email:
        raise ValueError("Missing destination email")
    if not subject or not str(subject).strip():
        raise ValueError("Email subject cannot be empty")
    if not html or not str(html).strip():
        raise ValueError("Email html body cannot be empty")

    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [str(to_email).strip()],
        "subject": str(subject).strip(),
        "html": str(html).strip(),
    }

    if text and str(text).strip():
        params["text"] = str(text).strip()

    if reply_to_email:
        params["reply_to"] = reply_to_email

    email = resend.Emails.send(params)

    email_id = None
    if isinstance(email, dict):
        email_id = email.get("id")
    else:
        email_id = getattr(email, "id", None)

    return {
        "id": email_id,
        "to": str(to_email).strip(),
        "subject": str(subject).strip(),
    }