import os

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///retention.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TWILIO_ACCOUNT_SID = "your_sid"
    TWILIO_AUTH_TOKEN = "your_token"
    TWILIO_PHONE = "+1234567890"