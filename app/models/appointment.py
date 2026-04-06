from ..database import db


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)

    square_booking_id = db.Column(db.String(100), unique=True, nullable=True)

    appointment_date = db.Column(db.DateTime, nullable=False)
    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.String(50), nullable=True)
    location_id = db.Column(db.String(100), nullable=True)
    service_name = db.Column(db.String(200), nullable=True)

    service_price = db.Column(db.Float, default=0)