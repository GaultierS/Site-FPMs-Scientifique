import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.middleware.proxy_fix import ProxyFix
from .models import db


# Active les clés étrangères uniquement si on tourne en local sur SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Utilise PostgreSQL sous Docker (via DATABASE_URL), ou SQLite en local par défaut
    default_sqlite = f"sqlite:///{os.path.join(app.instance_path, 'site.db')}"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", default_sqlite)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    # Prise en charge du reverse proxy en production Docker
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    db.init_app(app)

    allowed_origin = os.getenv("FRONTEND_URL", "http://localhost:4321")
    CORS(app, resources={r"/api/*": {"origins": [allowed_origin]}})

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return {"ok": True}

    from .routes import api
    app.register_blueprint(api, url_prefix="/api")

    return app








""" from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["http://localhost:4321"]
            }
        }
    )

    from app.routes import api
    app.register_blueprint(api, url_prefix="/api")

    return app """
