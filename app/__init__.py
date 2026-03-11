from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    from app.config import Config
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from app.logging_config import setup_logging
    setup_logging(app)

    from app.routes import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()

    return app
