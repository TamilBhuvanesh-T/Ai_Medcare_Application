from flask import Flask

from .config import Config
from .db import init_db
from .routes import register_routes


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)

    init_db(app.config["DATABASE_PATH"])
    register_routes(app)
    return app
