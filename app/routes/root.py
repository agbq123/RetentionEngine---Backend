from flask import Blueprint

root_bp = Blueprint("root", __name__)

@root_bp.route("/")
def root():
    return {
        "service": "Retention Engine API",
        "status": "running"
    }