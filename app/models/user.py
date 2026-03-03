from ..database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    booking_provider = db.Column(db.String(50), nullable=False)

    clients = db.relationship("Client", backref="user", lazy=True)