from ..database import db


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    square_customer_id = db.Column(db.String(100), unique=True, nullable=True)

    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    first_visit = db.Column(db.DateTime, nullable=True)
    last_visit = db.Column(db.DateTime, nullable=True)

    lifetime_value = db.Column(db.Float, default=0)
    visit_count = db.Column(db.Integer, default=0)