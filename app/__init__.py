import time
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy.exc import OperationalError

db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    from app.config import Config
    app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    limiter.init_app(app)

    from app.logging_config import setup_logging
    setup_logging(app)

    from app.routes import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        max_attempts = 30
        retry_delay_seconds = 2
        for attempt in range(1, max_attempts + 1):
            try:
                db.create_all()
                logger.info("Database initialization completed")
                break
            except OperationalError as exc:
                if attempt == max_attempts:
                    logger.exception("Database initialization failed after retries")
                    raise
                logger.warning(
                    "Database not ready (attempt %d/%d). Retrying in %ds: %s",
                    attempt,
                    max_attempts,
                    retry_delay_seconds,
                    exc,
                )
                time.sleep(retry_delay_seconds)

    return app
