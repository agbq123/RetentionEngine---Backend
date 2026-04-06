from ..database import db

class Barber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    square_team_member_id = db.Column(db.String(100), unique=True, nullable=False)
    given_name = db.Column(db.String(100))
    family_name = db.Column(db.String(100))
    display_name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)