from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_moment import Moment
from flask_login import LoginManager
from config import config
from flask_mail import Mail

bootstrap = Bootstrap()
db = SQLAlchemy()
mail = Mail()
moment = Moment()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_name="default"):
    app = Flask(__name__)
    app.logger.debug("Created flask app instance")
    app.config.from_object(config[config_name])
    app.logger.debug("Loaded config")
    config[config_name].init_app(app)
    app.logger.debug("Initializing config")

    bootstrap.init_app(app)
    db.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    login_manager.init_app(app)
    app.logger.debug("Initialized all extensions.")

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    app.logger.debug("Registered main blueprint.")

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    app.logger.debug("Registered auth blueprint.")

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    app.logger.debug("Registered api blueprint.")

    if app.config['SSL_REDIRECT']:
        from flask_sslify import SSLify
        sslify = SSLify(app)
        app.logger.debug("SSLified")

    app.logger.debug("App creation complete.")
    return app

from .main import errors
