from ..database import db

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))

    first_visit = db.Column(db.DateTime)
    last_visit = db.Column(db.DateTime)

    lifetime_value = db.Column(db.Float, default=0)
    visit_count = db.Column(db.Integer, default=0)

    appointments = db.relationship("Appointment", backref="client", lazy=True)