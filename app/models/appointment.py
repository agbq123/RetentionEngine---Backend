from ..database import db

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)

    appointment_date = db.Column(db.DateTime, nullable=False)
    service_price = db.Column(db.Float, nullable=False)