import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///retention.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE = os.getenv("TWILIO_PHONE")
    TWILIO_STATUS_CALLBACK_URL = os.getenv("TWILIO_STATUS_CALLBACK_URL")

    SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
    SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")
    SQUARE_VERSION = os.getenv("SQUARE_VERSION", "2026-01-22")

    SQUARE_APP_ID = os.getenv("SQUARE_APP_ID")
    SQUARE_APP_SECRET = os.getenv("SQUARE_APP_SECRET")
    SQUARE_REDIRECT_URI = os.getenv(
        "SQUARE_REDIRECT_URI",
        "http://127.0.0.1:5000/integrations/square/callback",
    )
    SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")