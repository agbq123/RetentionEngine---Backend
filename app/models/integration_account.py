from datetime import datetime
from ..database import db

class IntegrationAccount(db.Model):
    __tablename__ = "integration_account"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    provider = db.Column(db.String(50), nullable=False)
    merchant_id = db.Column(db.String(120), nullable=True)

    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    location_id = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)