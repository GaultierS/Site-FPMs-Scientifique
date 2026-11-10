from flask import Flask
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

    return app
