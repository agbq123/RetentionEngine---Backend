from flask import Flask

from .config import Config
from .database import db
from .routes.integrations import integrations_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from .routes.api import api_bp
    from .routes.dashboard import dashboard_bp
    from .routes.dev_seed import dev_seed_bp
    from .routes.health import health_bp
    from .routes.root import root_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(dev_seed_bp)
    app.register_blueprint(root_bp)
    app.register_blueprint(integrations_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app